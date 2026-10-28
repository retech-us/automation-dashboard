"""Structured validation for Intelligent Reset generated mobile actions."""

from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple

from core.action_list_domain_mapper import transform_action_list_to_domain


Slot = Tuple[str, Optional[int], str]


def _slot(position: Optional[Dict[str, Any]]) -> Optional[Slot]:
    if not isinstance(position, dict):
        return None
    section = position.get("section_info") or {}
    bay = section.get("name")
    shelf = position.get("shelf")
    pos = position.get("position")
    if bay is None or shelf is None or pos is None:
        return None
    try:
        return str(bay), int(shelf), str(pos)
    except (ValueError, TypeError):
        return str(bay), None, str(pos)


def _extract_slot(row: Optional[Dict[str, Any]], role: str = "source") -> Optional[Slot]:
    if not isinstance(row, dict):
        return None
    pos_key = "current_position" if role == "source" else "expected_position"
    if pos_key in row and isinstance(row[pos_key], dict):
        res = _slot(row[pos_key])
        if res:
            return res

    if role == "source":
        bay = row.get("source_bay") or row.get("bay")
        shelf = row.get("source_shelf") if row.get("source_shelf") is not None else row.get("cur_shelf")
        pos = row.get("source_position") if row.get("source_position") is not None else row.get("cur_pos_num")
    else:
        bay = row.get("target_bay") or row.get("bay")
        shelf = row.get("target_shelf") if row.get("target_shelf") is not None else row.get("exp_shelf")
        pos = row.get("target_position") if row.get("target_position") is not None else row.get("exp_pos_num")

    if bay is not None and shelf is not None and pos is not None:
        try:
            return str(bay), int(shelf), str(pos)
        except (ValueError, TypeError):
            return str(bay), None, str(pos)
    return None


def _slot_text(slot: Optional[Slot]) -> str:
    if not slot or (slot[0] is None and slot[1] is None and slot[2] is None):
        return "unknown slot"
    shelf_str = f"Shelf {slot[1]}" if slot[1] is not None else "Shelf ?"
    return f"Bay {slot[0]}, {shelf_str}, Position {slot[2]}"


def _is_same_product(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    if a.get("id") is not None and b.get("id") is not None and str(a.get("id")) == str(b.get("id")):
        return True
    upc_a = str(a.get("displayed_upc") or a.get("upc") or "").strip()
    upc_b = str(b.get("displayed_upc") or b.get("upc") or "").strip()
    if upc_a and upc_b and upc_a == upc_b:
        return True
    title_a = str(
        a.get("product_title")
        or a.get("title")
        or a.get("product_name")
        or ((a.get("product") or {}).get("name") if isinstance(a.get("product"), dict) else a.get("product"))
        or ""
    ).strip().lower()
    title_b = str(
        b.get("product_title")
        or b.get("title")
        or b.get("product_name")
        or ((b.get("product") or {}).get("name") if isinstance(b.get("product"), dict) else b.get("product"))
        or ""
    ).strip().lower()
    if title_a and title_b and title_a == title_b and "unidentified" not in title_a and "unidentified" not in title_b:
        return True
    return False


def _finding(
    code: str,
    severity: str,
    title: str,
    message: str,
    row: Optional[Dict[str, Any]] = None,
    action_ids: Optional[List[Any]] = None,
    source_slot: Optional[Slot] = None,
    target_slot: Optional[Slot] = None,
    occupant_info: Optional[Dict[str, Any]] = None,
    claimants: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    row = row or {}
    src = source_slot or _extract_slot(row, "source")
    tgt = target_slot or _extract_slot(row, "target")
    data = {
        "code": code,
        "severity": severity,
        "title": title,
        "message": message,
        "action_ids": [value for value in (action_ids or [row.get("id")]) if value is not None],
        "upc": str(row.get("upc") or ""),
        "product": str(row.get("product_title") or row.get("title") or ""),
        "source": _slot_text(src),
        "target": _slot_text(tgt),
    }
    if occupant_info:
        data["occupant"] = occupant_info
    if claimants:
        data["claimants"] = claimants
    return data


def validate_action_generation(
    raw_items: List[Dict[str, Any]],
    actions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Validate generated cards and replay physical shelf occupancy."""
    findings: List[Dict[str, Any]] = []
    movement_rows: List[Dict[str, Any]] = []
    target_claims: Dict[Slot, List[Dict[str, Any]]] = defaultdict(list)
    initial_occupancy: Dict[Slot, Dict[str, Any]] = {}

    for row in raw_items:
        src = _slot(row.get("current_position"))
        dst = _slot(row.get("expected_position"))
        if src:
            initial_occupancy[src] = row
        if dst:
            target_claims[dst].append(row)
        if src and dst:
            movement_rows.append(row)
            if src == dst:
                findings.append(_finding(
                    "REDUNDANT_SAME_SLOT_MOVE",
                    "critical",
                    "Product already in place",
                    f"{row.get('product_title') or row.get('upc') or 'Product'} is already at {_slot_text(src)} and must not receive a move action.",
                    row,
                ))

    for target, claimants in target_claims.items():
        unique_products = set()
        for crow in claimants:
            u_upc = str(crow.get("displayed_upc") or crow.get("upc") or "").strip()
            u_title = str(
                crow.get("product_title")
                or crow.get("title")
                or ((crow.get("product") or {}).get("name") if isinstance(crow.get("product"), dict) else crow.get("product"))
                or ""
            ).strip().lower()
            prod_key = u_upc if u_upc else (u_title if u_title and "unidentified" not in u_title else str(crow.get("id")))
            unique_products.add(prod_key)
        if len(unique_products) > 1:
            claimant_details = []
            for c_idx, crow in enumerate(claimants, start=1):
                c_src = _slot(crow.get("current_position"))
                c_id = crow.get("id")
                c_title = (
                    crow.get("product_title")
                    or crow.get("title")
                    or (crow.get("product") or {}).get("name")
                    or f"Product (Action #{c_id})"
                )
                c_upc = str(crow.get("upc") or crow.get("displayed_upc") or "")
                c_act = (
                    crow.get("action")
                    or (crow.get("current_position") or {}).get("action")
                    or crow.get("type")
                    or "MOVE"
                )
                c_src_str = _slot_text(c_src) if c_src else "Backroom / Restock (No source shelf)"
                claimant_details.append({
                    "index": c_idx,
                    "id": c_id,
                    "product": c_title,
                    "upc": c_upc,
                    "action": c_act,
                    "source": c_src_str,
                    "source_slot": c_src,
                    "target": _slot_text(target),
                    "target_slot": target,
                })

            unique_ids = {row.get("id") for row in claimants if row.get("id") is not None}
            claimant_lines = "\n".join(
                f"• Product #{c['index']} (Action #{c['id']}): '{c['product']}' (UPC {c['upc'] or 'N/A'}) from {c['source']}"
                for c in claimant_details
            )
            msg = (
                f"{len(unique_ids)} generated actions claim {_slot_text(target)}:\n"
                f"{claimant_lines}"
            )
            findings.append(_finding(
                "DUPLICATE_TARGET_SLOT",
                "critical",
                "Multiple products target one slot",
                msg,
                claimants[0],
                action_ids=[row.get("id") for row in claimants if row.get("id") is not None],
                target_slot=target,
                claimants=claimant_details,
            ))

    generated_keys = Counter(
        (
            str(action.get("id")),
            str(action.get("type") or ""),
            str(action.get("source_bay") or action.get("bay") or ""),
            str(action.get("source_shelf") if action.get("source_shelf") is not None else action.get("cur_shelf")),
            str(action.get("source_position") if action.get("source_position") is not None else action.get("cur_pos_num")),
            str(action.get("target_bay") or action.get("bay") or ""),
            str(action.get("target_shelf") if action.get("target_shelf") is not None else action.get("exp_shelf")),
            str(action.get("target_position") if action.get("target_position") is not None else action.get("exp_pos_num")),
        )
        for action in actions
    )
    for key, count in generated_keys.items():
        if count > 1:
            findings.append(_finding(
                "DUPLICATE_ACTION_CARD",
                "critical",
                "Duplicate action card",
                f"The same physical action was generated {count} times.",
                {"id": key[0]},
            ))

    for action in actions:
        kind = str(action.get("type") or "")
        source_complete = all(
            action.get(name) is not None
            for name in ("source_bay", "source_shelf", "source_position")
        )
        target_complete = all(
            action.get(name) is not None
            for name in ("target_bay", "target_shelf", "target_position")
        )
        if kind in ("FIX_IN_BAY", "ADD_TO_SHELF", "RESTOCK") and not target_complete:
            findings.append(_finding(
                "MISSING_TARGET_COORDINATES",
                "critical",
                "Target coordinates are incomplete",
                f"{kind.replace('_', ' ').title()} requires bay, shelf, and position.",
                action,
            ))
        if kind == "FIX_IN_BAY" and not source_complete:
            findings.append(_finding(
                "MISSING_SOURCE_COORDINATES",
                "critical",
                "Slide source coordinates are incomplete",
                "A slide requires a known source bay, shelf, and position.",
                action,
            ))
        if kind == "RESTOCK" and source_complete:
            findings.append(_finding(
                "INVALID_RESTOCK_SOURCE",
                "critical",
                "Restock incorrectly uses a shelf source",
                "Restock must come from backroom inventory, not move an existing shelf product.",
                action,
            ))
        if kind == "IDENTIFY" and not source_complete:
            findings.append(_finding(
                "IDENTIFY_LOCATION_MISSING",
                "warning",
                "Identify card has no exact location",
                "The associate can start, but the barcode scan card should identify its bay, shelf, and position.",
                action,
            ))

    # Legal two-product swaps are simultaneous and therefore exempt from the
    # normal empty-destination replay.
    move_by_edge = {
        (_slot(row.get("current_position")), _slot(row.get("expected_position"))): row
        for row in movement_rows
    }
    swap_ids = set()
    for (src, dst), row in move_by_edge.items():
        reverse = move_by_edge.get((dst, src))
        if src and dst and reverse and row.get("id") != reverse.get("id"):
            swap_ids.update((row.get("id"), reverse.get("id")))
    for action in actions:
        if action.get("id") in swap_ids:
            action["is_swap"] = True
            action["movement_kind"] = "swap"
        elif action.get("type") == "FIX_IN_BAY":
            action["movement_kind"] = (
                "slide"
                if action.get("source_shelf") == action.get("target_shelf")
                else "in_bay_reposition"
            )

    # Generated-card conservation and cross-bay pairing.
    expected_cards = transform_action_list_to_domain(raw_items, include_completed=True)
    if len(expected_cards) != len(actions):
        findings.append(_finding(
            "ACTION_CARD_CONSERVATION",
            "critical",
            "Generated cards were dropped or duplicated",
            f"Expected {len(expected_cards)} mobile cards from {len(raw_items)} backend actions, but received {len(actions)}.",
        ))
    types_by_id: Dict[str, Counter] = defaultdict(Counter)
    for action in actions:
        types_by_id[str(action.get("id"))][str(action.get("type") or "")] += 1
    for row in movement_rows:
        src = _slot(row.get("current_position"))
        dst = _slot(row.get("expected_position"))
        if not src or not dst or src[0] == dst[0]:
            continue
        counts = types_by_id[str(row.get("id"))]
        if counts["SET_ASIDE"] != 1 or counts["ADD_TO_SHELF"] != 1:
            findings.append(_finding(
                "CROSS_BAY_PAIRING",
                "critical",
                "Cross-bay move is not paired",
                "Every cross-bay product requires exactly one Set Aside card and one Add to Shelf card.",
                row,
            ))

    phase = {
        "SET_ASIDE": 0,
        "FIX_IN_BAY": 1,
        "SWAP": 1,
        "ADD_TO_SHELF": 2,
        "RESTOCK": 3,
        "EXCEPTION": 4,
    }

    def sequence_key(action: Dict[str, Any]) -> Tuple[int, int, int]:
        kind = str(action.get("type") or "")
        try:
            bay = int(action.get("bay") or action.get("source_bay") or action.get("target_bay") or 99)
        except (TypeError, ValueError):
            bay = 99
        if kind == "IDENTIFY":
            return 0, bay, 0
        if kind == "REMOVE":
            return 1, bay, 0
        return 2, bay, phase.get(kind, 99)

    sequence_values = [sequence_key(action) for action in actions]
    if sequence_values != sorted(sequence_values):
        findings.append(_finding(
            "ACTION_SEQUENCE",
            "critical",
            "Action phases are out of order",
            "Expected Identify → Remove → Set Aside → Slide/Swap → Add → Restock.",
        ))

    def _diagnose_occupant_conflict(
        action_idx: int,
        action: Dict[str, Any],
        dst: Slot,
        occupant: Dict[str, Any],
        verb: str = "moves",
    ) -> Tuple[str, Dict[str, Any]]:
        action_id = action.get("id")
        occ_id = occupant.get("id")
        occ_upc = str(occupant.get("upc") or "")
        raw_occ_title = str(
            occupant.get("product_title")
            or occupant.get("title")
            or occupant.get("product")
            or ""
        ).strip()
        if raw_occ_title and raw_occ_title != "Existing product":
            occ_title = raw_occ_title
        else:
            occ_act = str(
                (occupant.get("current_position") or {}).get("action")
                or occupant.get("action")
                or occupant.get("type")
                or ""
            ).lower()
            if "identify" in occ_act:
                occ_title = f"Unidentified Product (Action #{occ_id or 'N/A'} - IDENTIFY)"
            elif occ_upc:
                occ_title = f"Product (UPC {occ_upc})"
            elif occ_id is not None:
                occ_title = f"Product (Action #{occ_id})"
            else:
                occ_title = "Existing product"

        # 1. Occupant Origin / Provenance: check if placed by an earlier action in this task
        placed_by_earlier_action = None
        placed_by_earlier_step = None
        for prev_idx, prev_act in enumerate(actions[:action_idx]):
            prev_dst = (
                str(prev_act.get("target_bay") or prev_act.get("bay") or ""),
                prev_act.get("target_shelf") if prev_act.get("target_shelf") is not None else prev_act.get("exp_shelf"),
                str(prev_act.get("target_position") if prev_act.get("target_position") is not None else prev_act.get("exp_pos_num")),
            )
            if prev_dst == dst:
                if occ_id is not None and str(prev_act.get("id")) == str(occ_id):
                    placed_by_earlier_action = prev_act
                    placed_by_earlier_step = prev_idx + 1
                    break
                elif occ_upc and str(prev_act.get("upc") or "") == occ_upc:
                    placed_by_earlier_action = prev_act
                    placed_by_earlier_step = prev_idx + 1
                    break

        if placed_by_earlier_action:
            prev_src = (
                str(placed_by_earlier_action.get("source_bay") or placed_by_earlier_action.get("bay") or ""),
                placed_by_earlier_action.get("source_shelf") if placed_by_earlier_action.get("source_shelf") is not None else placed_by_earlier_action.get("cur_shelf"),
                str(placed_by_earlier_action.get("source_position") if placed_by_earlier_action.get("source_position") is not None else placed_by_earlier_action.get("cur_pos_num")),
            )
            prev_type = placed_by_earlier_action.get("type") or "MOVE"
            occ_origin = (
                f"Placed into {_slot_text(dst)} at Step {placed_by_earlier_step} "
                f"by Action #{placed_by_earlier_action.get('id')} ({prev_type}) from {_slot_text(prev_src)}."
            )
        else:
            occ_origin = f"Present on shelf at {_slot_text(dst)} from the initial scan."

        # 2. Identification Status & IDENTIFY action analysis
        occ_act = str(
            (occupant.get("current_position") or {}).get("action")
            or occupant.get("action")
            or occupant.get("type")
            or ""
        ).lower()
        is_unidentified = bool(
            "identify" in occ_act
            or occupant.get("is_unidentified") is True
            or str(occupant.get("type") or "").upper() == "IDENTIFY"
            or "unidentified" in occ_title.lower()
            or occupant.get("report_product_status") == "unidentified"
            or (not occ_upc and not raw_occ_title)
        )

        identify_action = None
        identify_step = None
        for idx, act in enumerate(actions, start=1):
            if str(act.get("type") or "").upper() == "IDENTIFY":
                act_slot = (
                    str(act.get("source_bay") or act.get("bay") or ""),
                    act.get("source_shelf") if act.get("source_shelf") is not None else act.get("cur_shelf"),
                    str(act.get("source_position") if act.get("source_position") is not None else act.get("cur_pos_num")),
                )
                if occ_id is not None and str(act.get("id")) == str(occ_id):
                    identify_action = act
                    identify_step = idx
                    break
                elif act_slot == dst:
                    identify_action = act
                    identify_step = idx
                    break

        if is_unidentified:
            if identify_action:
                id_state = identify_action.get("state") or identify_action.get("status") or ""
                id_reason = identify_action.get("reason") or ""
                status_extra = f" (State: {id_state}{f', Reason: {id_reason}' if id_reason else ''})" if id_state or id_reason else ""
                ident_status_text = f"Unidentified product. System generated IDENTIFY Action #{identify_action.get('id')} at Step {identify_step}{status_extra}."
            else:
                ident_status_text = "Unidentified product. System did NOT generate any IDENTIFY action for this product."
        else:
            ident_status_text = f"Identified product (UPC {occ_upc or 'N/A'}). No IDENTIFY action needed or generated."

        # 3. Actions generated for occupied product in this task
        all_product_actions = []
        for idx, act in enumerate(actions, start=1):
            is_match = False
            if occ_id is not None and str(act.get("id")) == str(occ_id):
                is_match = True
            elif occ_upc and str(act.get("upc") or "") == occ_upc:
                act_src = (
                    str(act.get("source_bay") or act.get("bay") or ""),
                    act.get("source_shelf") if act.get("source_shelf") is not None else act.get("cur_shelf"),
                    str(act.get("source_position") if act.get("source_position") is not None else act.get("cur_pos_num")),
                )
                act_dst = (
                    str(act.get("target_bay") or act.get("bay") or ""),
                    act.get("target_shelf") if act.get("target_shelf") is not None else act.get("exp_shelf"),
                    str(act.get("target_position") if act.get("target_position") is not None else act.get("exp_pos_num")),
                )
                if act_src == dst or act_dst == dst:
                    is_match = True

            if is_match:
                all_product_actions.append({
                    "step": idx,
                    "id": act.get("id"),
                    "type": act.get("type") or "MOVE",
                })

        if all_product_actions:
            actions_summary_str = ", ".join(
                f"Step {a['step']} (Action #{a['id']}, {a['type']})"
                for a in all_product_actions
            )
        else:
            actions_summary_str = "None. No action was generated anywhere in this task for this product."

        # 4. Evacuation action / clearing action
        scheduled_later = None
        scheduled_later_step = None
        for future_idx, later_act in enumerate(actions[action_idx + 1:], start=action_idx + 2):
            later_src = (
                str(later_act.get("source_bay") or later_act.get("bay") or ""),
                later_act.get("source_shelf") if later_act.get("source_shelf") is not None else later_act.get("cur_shelf"),
                str(later_act.get("source_position") if later_act.get("source_position") is not None else later_act.get("cur_pos_num")),
            )
            is_same = False
            if occ_id is not None and str(later_act.get("id")) == str(occ_id) and later_src == dst:
                is_same = True
            elif occ_upc and str(later_act.get("upc") or "") == occ_upc and later_src == dst:
                is_same = True
            elif later_src == dst and str(later_act.get("type")) in ("REMOVE", "SET_ASIDE", "FIX_IN_BAY"):
                is_same = True

            if is_same:
                scheduled_later = later_act
                scheduled_later_step = future_idx
                break

        if scheduled_later:
            conflict_type = "sequence_deadlock"
            later_type = scheduled_later.get("type") or "MOVE"
            detail_msg = (
                f"Action {action_id} {verb} into {_slot_text(dst)} before the existing product is cleared.\n"
                f"Occupant details: '{occ_title}' (UPC {occ_upc or 'N/A'}, Action #{occ_id or 'N/A'}) currently occupies this position.\n"
                f"• Origin: {occ_origin}\n"
                f"• Identification: {ident_status_text}\n"
                f"• Evacuation Action: Scheduled to vacate via Action #{scheduled_later.get('id')} ({later_type}) at Step {scheduled_later_step}, "
                f"which is ordered AFTER this action (Step {action_idx + 1}). Reorder actions to clear the slot first.\n"
                f"• All Actions for Occupant: {actions_summary_str}"
            )
            guidance = (
                f"Sequence deadlock: '{occ_title}' vacates at Step {scheduled_later_step}. "
                f"Move Step {scheduled_later_step} before Step {action_idx + 1}."
            )
        else:
            conflict_type = "missing_evacuation"
            detail_msg = (
                f"Action {action_id} {verb} into {_slot_text(dst)} before the existing product is cleared.\n"
                f"Occupant details: '{occ_title}' (UPC {occ_upc or 'N/A'}, ID {occ_id or 'N/A'}) currently occupies this position, and NO action exists anywhere in this task to move or remove it. "
                f"This is an actual issue: no action is planned to make this place empty.\n"
                f"• Origin: {occ_origin}\n"
                f"• Identification: {ident_status_text}\n"
                f"• Evacuation Action: None. No action is planned to vacate this position.\n"
                f"• All Actions for Occupant: {actions_summary_str}"
            )
            guidance = (
                f"Actual collision issue: '{occ_title}' has no action to vacate {_slot_text(dst)}. "
                f"A REMOVE or SET_ASIDE action must be generated for this product."
            )

        occupant_info = {
            "product": occ_title,
            "upc": occ_upc,
            "id": occ_id,
            "conflict_type": conflict_type,
            "provenance": occ_origin,
            "is_unidentified": is_unidentified,
            "has_identify_action": identify_action is not None,
            "identify_step": identify_step,
            "identify_action_id": identify_action.get("id") if identify_action else None,
            "identify_status_text": ident_status_text,
            "has_scheduled_action": scheduled_later is not None,
            "scheduled_step": scheduled_later_step,
            "scheduled_action_id": scheduled_later.get("id") if scheduled_later else None,
            "scheduled_action_type": scheduled_later.get("type") if scheduled_later else None,
            "all_actions": all_product_actions,
            "all_actions_summary": actions_summary_str,
            "validation_guidance": guidance,
        }
        return detail_msg, occupant_info

    occupancy = dict(initial_occupancy)
    processed_swaps = set()
    for action_idx, action in enumerate(actions):
        kind = str(action.get("type") or "")
        action_id = action.get("id")
        src = (
            str(action.get("source_bay") or action.get("bay") or ""),
            action.get("source_shelf") if action.get("source_shelf") is not None else action.get("cur_shelf"),
            str(action.get("source_position") if action.get("source_position") is not None else action.get("cur_pos_num")),
        )
        dst = (
            str(action.get("target_bay") or action.get("bay") or ""),
            action.get("target_shelf") if action.get("target_shelf") is not None else action.get("exp_shelf"),
            str(action.get("target_position") if action.get("target_position") is not None else action.get("exp_pos_num")),
        )
        if kind in ("REMOVE", "SET_ASIDE"):
            occupancy.pop(src, None)
        elif kind == "FIX_IN_BAY":
            if action_id in swap_ids:
                if action_id not in processed_swaps:
                    pair = next(
                        (
                            other for other in actions
                            if other.get("id") in swap_ids
                            and other.get("id") != action_id
                            and str(other.get("source_bay") or other.get("bay") or "") == dst[0]
                            and str(other.get("source_position") if other.get("source_position") is not None else other.get("cur_pos_num")) == dst[2]
                        ),
                        None,
                    )
                    processed_swaps.add(action_id)
                    if pair:
                        processed_swaps.add(pair.get("id"))
                continue
            occupant = occupancy.get(dst)
            if occupant and not _is_same_product(occupant, action):
                msg, occ_info = _diagnose_occupant_conflict(action_idx, action, dst, occupant, verb="moves")
                findings.append(_finding(
                    "OCCUPIED_DESTINATION",
                    "critical",
                    "Slide destination is still occupied",
                    msg,
                    action,
                    source_slot=src,
                    target_slot=dst,
                    occupant_info=occ_info,
                ))
            product = occupancy.pop(src, action)
            occupancy[dst] = product
        elif kind in ("ADD_TO_SHELF", "RESTOCK"):
            occupant = occupancy.get(dst)
            if occupant and not _is_same_product(occupant, action):
                msg, occ_info = _diagnose_occupant_conflict(action_idx, action, dst, occupant, verb="places")
                findings.append(_finding(
                    "OCCUPIED_DESTINATION",
                    "critical",
                    "Placement destination is still occupied",
                    msg,
                    action,
                    source_slot=src,
                    target_slot=dst,
                    occupant_info=occ_info,
                ))
            occupancy[dst] = action

    # Direction and vacancy-safe ordering inside each slide chain.
    slide_groups: Dict[Tuple[str, Any], List[Dict[str, Any]]] = defaultdict(list)
    for action in actions:
        if (
            action.get("type") == "FIX_IN_BAY"
            and action.get("id") not in swap_ids
            and action.get("source_shelf") == action.get("target_shelf")
        ):
            slide_groups[(
                str(action.get("source_bay") or action.get("bay") or ""),
                action.get("source_shelf") if action.get("source_shelf") is not None else action.get("cur_shelf"),
            )].append(action)
    for (_bay, _shelf), group in slide_groups.items():
        directions = {action.get("slide_direction") for action in group if action.get("slide_direction")}
        if len(directions) > 1:
            findings.append(_finding(
                "MIXED_SLIDE_DIRECTION",
                "critical",
                "Slide chain changes direction",
                "A shelf slide chain must move consistently left or consistently right.",
                group[0],
                [action.get("id") for action in group],
            ))

    critical_count = sum(1 for item in findings if item["severity"] == "critical")
    warning_count = sum(1 for item in findings if item["severity"] == "warning")
    return {
        "state": "blocked" if critical_count else ("warning" if warning_count else "pass"),
        "can_start": critical_count == 0,
        "critical_count": critical_count,
        "warning_count": warning_count,
        "checks_run": 12,
        "findings": findings,
        "summary": (
            f"Blocked by {critical_count} critical action-generation issue(s)."
            if critical_count
            else "All generated actions passed spatial, sequence, pairing, and occupancy checks."
        ),
        "swap_action_ids": sorted(value for value in swap_ids if value is not None),
    }
