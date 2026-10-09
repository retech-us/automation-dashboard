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
    return str(bay), int(shelf), str(pos)


def _slot_text(slot: Optional[Slot]) -> str:
    if not slot:
        return "unknown slot"
    return f"Bay {slot[0]}, Shelf {slot[1]}, Position {slot[2]}"


def _finding(
    code: str,
    severity: str,
    title: str,
    message: str,
    row: Optional[Dict[str, Any]] = None,
    action_ids: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    row = row or {}
    return {
        "code": code,
        "severity": severity,
        "title": title,
        "message": message,
        "action_ids": [value for value in (action_ids or [row.get("id")]) if value is not None],
        "upc": str(row.get("upc") or ""),
        "product": str(row.get("product_title") or row.get("title") or ""),
        "source": _slot_text(_slot(row.get("current_position"))),
        "target": _slot_text(_slot(row.get("expected_position"))),
    }


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
        unique_ids = {str(row.get("id")) for row in claimants}
        if len(unique_ids) > 1:
            findings.append(_finding(
                "DUPLICATE_TARGET_SLOT",
                "critical",
                "Multiple products target one slot",
                f"{len(unique_ids)} generated actions claim {_slot_text(target)}.",
                claimants[0],
                [row.get("id") for row in claimants],
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

    occupancy = dict(initial_occupancy)
    processed_swaps = set()
    for action in actions:
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
            if occupant and str(occupant.get("id")) != str(action_id):
                findings.append(_finding(
                    "OCCUPIED_DESTINATION",
                    "critical",
                    "Slide destination is still occupied",
                    f"Action {action_id} moves into {_slot_text(dst)} before the existing product is cleared.",
                    action,
                ))
            product = occupancy.pop(src, action)
            occupancy[dst] = product
        elif kind in ("ADD_TO_SHELF", "RESTOCK"):
            occupant = occupancy.get(dst)
            if occupant and str(occupant.get("id")) != str(action_id):
                findings.append(_finding(
                    "OCCUPIED_DESTINATION",
                    "critical",
                    "Placement destination is still occupied",
                    f"Action {action_id} places into {_slot_text(dst)} before the existing product is cleared.",
                    action,
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
