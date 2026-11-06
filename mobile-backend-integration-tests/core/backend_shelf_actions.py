"""Present retailer actions in the order the backend returned them and check that order.

Nothing is sorted, merged, converted, or invented. Each backend row becomes one
card, or two adjacent cards (set aside, then add to shelf) when the row carries
both halves. The checks only report: a destination that still holds a product no
earlier step removes, steps that wait on each other, and rows that break a reset
rule.
"""

from typing import Any, Dict, List, Optional, Tuple


SlotKey = Tuple[str, str, str]


def _position(value: Any) -> Optional[Dict[str, Any]]:
    return value if isinstance(value, dict) else None


def _location(position: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not position:
        return None
    section = position.get("section_info") or {}
    bay = section.get("name")
    if bay is None:
        bay = section.get("id")
    return {
        "bay": "" if bay is None else str(bay),
        "shelf": position.get("shelf"),
        "position": position.get("position"),
    }


def _slot_key(location: Optional[Dict[str, Any]]) -> Optional[SlotKey]:
    if not location or location.get("bay") in (None, "") or location.get("shelf") is None or location.get("position") is None:
        return None
    return str(location["bay"]), str(location["shelf"]), str(location["position"])


def _slot_id(location: Optional[Dict[str, Any]]) -> Optional[str]:
    key = _slot_key(location)
    if not key:
        return None
    return f"Bay{key[0]}_S{key[1]}_P{key[2]}"


def _slot_text(location: Optional[Dict[str, Any]]) -> str:
    if not location:
        return "no position"
    return f"Bay {location.get('bay') or '?'}, Shelf {location.get('shelf') if location.get('shelf') is not None else '?'}, Position {location.get('position') if location.get('position') is not None else '?'}"


def _action_name(row: Dict[str, Any]) -> str:
    current = _position(row.get("current_position")) or {}
    expected = _position(row.get("expected_position")) or {}
    return str(expected.get("action") or current.get("action") or row.get("action") or "action")


def _product(row: Dict[str, Any]) -> str:
    product = row.get("product")
    nested = product.get("name") if isinstance(product, dict) else ""
    title = str(row.get("product_title") or row.get("product_name") or nested or "").strip()
    if title:
        return title
    act = str(
        (_position(row.get("current_position")) or {}).get("action")
        or (_position(row.get("expected_position")) or {}).get("action")
        or row.get("action")
        or ""
    ).lower()
    row_id = row.get("id")
    if "identify" in act:
        return f"Unidentified Product (Action #{row_id} - IDENTIFY)" if row_id is not None else "Unidentified Product (IDENTIFY)"
    upc = str(row.get("displayed_upc") or row.get("upc") or "").strip()
    if upc:
        return f"Product (UPC {upc})"
    if row_id is not None:
        return f"Product (Action #{row_id})"
    return ""


ACTION_LABELS = {
    "remove": ("Remove from shelf", "Take this product off the shelf."),
    "identify": ("Identify product", "Scan the product at this position to confirm what it is."),
    "place_on_shelf_restock": ("Restock", "Bring this product from the backroom and place it at the expected position."),
    "place_on_shelf_add_to_bay": ("Add to bay", "Place this product at its expected position in this bay."),
    "fix_position_fix_in_bay": ("Fix position in bay", "Move this product to its expected position inside the same bay."),
    "fix_position_move_to_bay": ("Move to another bay", "Take this product to its expected position in a different bay."),
}

def _slot_words(location: Optional[Dict[str, Any]]) -> str:
    key = _slot_key(location)
    if not key:
        return "no position"
    return f"Bay {key[0]}, Shelf {key[1]}, Position {key[2]}"


def _movement(action: str, current: Optional[Dict[str, Any]], expected: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """State the two backend positions. Swap or slide appears only when the backend names it."""
    source, target = _slot_key(current), _slot_key(expected)
    backend_kind = next((kind for kind in ("swap", "slide") if kind in action.lower()), None)
    if source and target:
        if source == target:
            return {"kind": "same_position", "short": "Same spot", "text": f"Already at {_slot_words(expected)}"}
        text = f"{_slot_words(current)} → {_slot_words(expected)}"
        if backend_kind:
            return {"kind": f"backend_{backend_kind}", "short": f"Backend {backend_kind}", "text": text}
        if source[0] != target[0]:
            return {"kind": "change_bay", "short": f"To Bay {target[0]}", "text": text}
        return {"kind": "same_bay", "short": f"Within Bay {source[0]}", "text": text}
    if target:
        return {"kind": "place_only", "short": "Place", "text": f"Place at {_slot_words(expected)}"}
    if source:
        verb = "Scan at" if action == "identify" else "Take from"
        return {"kind": "at_source", "short": "Scan" if action == "identify" else "Take off", "text": f"{verb} {_slot_words(current)}"}
    return {"kind": "no_position", "short": "No position", "text": "The backend sent no position"}


_FILL_ROLES = {"move_to_bay", "fix_in_bay", "backend_shelf_move", "add_to_shelf", "restock"}
_FIX_IN_BAY_ACTIONS = ("fix_position_fix_in_bay", "fix_position_in_bay")
_ROLE_LABELS = {
    "identify": ("Identify product", "Scan the product at this position to confirm what it is."),
    "remove": ("Remove from shelf", "Take this product off the shelf."),
    "set_aside": ("Set aside", "Pick this product off the shelf and hold it until its add-to-shelf step."),
    "move_to_bay": ("Move to another bay", "Take this product to its expected position in a different bay."),
    "fix_in_bay": ("Fix position in bay", "Move this product to its expected position inside the same bay."),
    "add_to_shelf": ("Add to shelf", "Place this product at its expected position."),
    "restock": ("Restock", "Bring this product from the backroom and place it at the expected position."),
}

RULES = {
    "SAME_BAY_SET_ASIDE": (
        "Set aside inside the same bay",
        "Rule: the backend must not send set aside when the product stays in the same bay. It should be fix in bay.",
    ),
    "SAME_BAY_MOVE_NOT_FIX_IN_BAY": (
        "Same-bay move is not fix in bay",
        "Rule: a product that changes position inside its bay must be fix_position_fix_in_bay.",
    ),
    "FIX_IN_BAY_ACROSS_BAYS": (
        "Fix in bay crosses bays",
        "Rule: fix_position_fix_in_bay must keep the product in the same bay.",
    ),
}


def convert_same_bay_set_asides_to_fix_in_bay(raw_items: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    """
    Normalizes legacy retailer backend actions to the New API specification:
    Any item whose current position and expected position are in the same bay
    must not generate set_aside (cart staging). It is converted to fix_position_fix_in_bay
    (direct in-bay shelf repositioning with 0 cart touches).
    """
    converted: List[Dict[str, Any]] = []
    converted_count = 0
    for row in raw_items:
        r = dict(row)
        c_raw = r.get("current_position")
        e_raw = r.get("expected_position")
        c_pos = _position(c_raw) or {}
        e_pos = _position(e_raw) or {}
        c_loc = _location(c_pos or None)
        e_loc = _location(e_pos or None)
        c_bay = c_loc.get("bay") if c_loc else None
        e_bay = e_loc.get("bay") if e_loc else None
        c_act = str(c_pos.get("action") or "").lower()
        e_act = str(e_pos.get("action") or "").lower()

        if c_bay is not None and e_bay is not None and str(c_bay) == str(e_bay):
            if c_act == "set_aside" or e_act in ("place_on_shelf_add_to_bay", "add_from_cart_to_bay", "add"):
                if isinstance(c_raw, dict):
                    c_raw_copy = dict(c_raw)
                    c_raw_copy["action"] = "fix_position_fix_in_bay"
                    r["current_position"] = c_raw_copy
                if isinstance(e_raw, dict):
                    e_raw_copy = dict(e_raw)
                    e_raw_copy["action"] = "fix_position_fix_in_bay"
                    r["expected_position"] = e_raw_copy
                r["action"] = "fix_position_fix_in_bay"
                r["_converted_from_same_bay_set_aside"] = True
                converted_count += 1
        converted.append(r)
    return converted, converted_count


def _is_restock(row: Dict[str, Any]) -> bool:
    expected_raw = _position(row.get("expected_position")) or {}
    expected_action = str(expected_raw.get("action") or "").lower()
    root = str(row.get("action") or "").lower()
    return expected_action == "place_on_shelf_restock" or "restock" in root or bool(row.get("is_new_restock_item"))


def _rule_flags(row: Dict[str, Any]) -> List[Dict[str, str]]:
    """Reset-rule breaks on one backend row. A restock, even onto the same place, is not one."""
    if _is_restock(row):
        return []
    current_raw = _position(row.get("current_position")) or {}
    expected_raw = _position(row.get("expected_position")) or {}
    current = _location(current_raw or None)
    expected = _location(expected_raw or None)
    source, target = _slot_key(current), _slot_key(expected)
    if not source or not target:
        return []
    current_action = str(current_raw.get("action") or "").lower()
    expected_action = str(expected_raw.get("action") or "").lower()
    upc = str(row.get("displayed_upc") or row.get("upc") or "")
    who = f"{_product(row) or 'Product'}{f' (UPC {upc})' if upc else ''}"
    where = f"{_slot_words(current)} → {_slot_words(expected)}"
    same_bay = source[0] == target[0]
    code = None
    if same_bay and current_action == "set_aside":
        code = "SAME_BAY_SET_ASIDE"
        detail = f"{who}: backend sent set_aside → {expected_action or 'no expected action'} for {where}."
    elif same_bay and source != target and expected_action not in _FIX_IN_BAY_ACTIONS:
        code = "SAME_BAY_MOVE_NOT_FIX_IN_BAY"
        detail = f"{who}: backend sent {expected_action or current_action or 'no action'} for {where}."
    elif not same_bay and expected_action in _FIX_IN_BAY_ACTIONS:
        code = "FIX_IN_BAY_ACROSS_BAYS"
        detail = f"{who}: backend sent {expected_action} for {where}."
    if not code:
        return []
    title, rule = RULES[code]
    return [{"code": code, "severity": "critical", "title": title, "rule": rule, "message": f"{detail} {rule}"}]


def _walk_roles(row: Dict[str, Any], current: Optional[Dict[str, Any]], expected: Optional[Dict[str, Any]]) -> List[str]:
    """Physical steps already present on one backend row."""
    current_raw = _position(row.get("current_position")) or {}
    expected_raw = _position(row.get("expected_position")) or {}
    current_action = str(current_raw.get("action") or "").lower()
    expected_action = str(expected_raw.get("action") or "").lower()
    root = str(row.get("action") or "").upper()
    if current_action == "identify" or expected_action == "identify" or "IDENTIFY" in root:
        return ["identify"]
    if current_action == "remove" or expected_action == "remove" or "REMOVE" in root:
        return ["remove"]
    if expected_action == "place_on_shelf_restock" or "RESTOCK" in root or row.get("is_new_restock_item"):
        return ["restock"]
    if "swap" in expected_action or "slide" in expected_action or "SWAP" in root or "SLIDE" in root:
        return ["backend_shelf_move"]
    if expected_action in _FIX_IN_BAY_ACTIONS and current_action != "set_aside":
        return ["fix_in_bay"]
    set_aside = current_action == "set_aside" or "SET_ASIDE" in root or "SETASIDE" in root
    add = expected_action in ("place_on_shelf_add_to_bay", "place_on_shelf", "add_from_cart_to_bay", "add")
    if set_aside and current and expected:
        return ["set_aside", "add_to_shelf"]
    if set_aside:
        return ["set_aside"]
    if expected_action == "fix_position_move_to_bay":
        return ["move_to_bay"]
    if add:
        return ["add_to_shelf"]
    return ["other"]


def _place(role: str, current: Optional[Dict[str, Any]], expected: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """The position a step happens at: the destination for placements, else the source."""
    if role in ("add_to_shelf", "restock"):
        return expected or current or {}
    return current or expected or {}


def _walk_units(raw_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """One unit per physical step, in the order the backend returned the rows."""
    units = []
    for origin, row in enumerate(raw_items):
        current = _location(_position(row.get("current_position")))
        expected = _location(_position(row.get("expected_position")))
        current_raw = _position(row.get("current_position")) or {}
        expected_raw = _position(row.get("expected_position")) or {}
        current_action = str(current_raw.get("action") or "").lower()
        expected_action = str(expected_raw.get("action") or "").lower()
        root = str(row.get("action") or "")
        roles = _walk_roles(row, current, expected)
        flags = _rule_flags(row)
        for half, role in enumerate(roles):
            place = _place(role, current, expected)
            clears_source = role in ("remove", "set_aside", "move_to_bay", "fix_in_bay", "backend_shelf_move") or (
                role == "add_to_shelf" and roles == ["add_to_shelf"] and current is not None
            )
            if role == "set_aside":
                raw_name = current_action or expected_action or root.lower() or role
            else:
                raw_name = expected_action or current_action or root.lower() or "action"
            units.append({
                "origin": origin,
                "half": half,
                "role": role,
                "raw_name": raw_name,
                "row": row,
                "current": current,
                "expected": expected,
                "source": _slot_key(current),
                "target": _slot_key(expected),
                "clears_source": clears_source,
                "rule_flags": flags,
                "place": place,
                "id": row.get("id"),
                "product": _product(row) or str(row.get("upc") or "") or "a product",
                "upc": str(row.get("displayed_upc") or row.get("upc") or ""),
            })
    for index, unit in enumerate(units, start=1):
        unit["index"] = index
    return units


def _same_product(left: Dict[str, Any], right: Dict[str, Any]) -> bool:
    if left.get("id") is not None and right.get("id") is not None and left["id"] == right["id"]:
        return True
    left_upc = str(left.get("displayed_upc") or left.get("upc") or "").strip()
    right_upc = str(right.get("displayed_upc") or right.get("upc") or "").strip()
    if left_upc and right_upc and left_upc == right_upc:
        return True
    left_prod = str(left.get("product_title") or left.get("product_name") or left.get("product") or left.get("item") or "").strip().lower()
    right_prod = str(right.get("product_title") or right.get("product_name") or right.get("product") or right.get("item") or "").strip().lower()
    if left_prod and right_prod and left_prod == right_prod and "unidentified" not in left_prod and "unidentified" not in right_prod:
        return True
    return False


def shelf_products_from_scans(scans: List[Dict[str, Any]]) -> Dict[SlotKey, Dict[str, str]]:
    """Products the before photo saw, by (section, shelf, product-order position).

    Every detected product counts, with or without an action. After-photo scans
    and items the scan lists as missing are ignored. Several facings of one
    product share one position, so the first one stands for the slot.
    """
    found: Dict[SlotKey, Dict[str, str]] = {}
    for scan in scans or []:
        if "post" in str(scan.get("stage") or "").lower():
            continue
        section = str(scan.get("section") or "").strip()
        if not section:
            continue
        for item in scan.get("items") or []:
            if str(item.get("type") or "").lower() == "missing":
                continue
            parts = str(item.get("on_shelf_position") or item.get("pos") or "").split(":")
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                continue
            key = (section, parts[0].strip(), parts[1].strip())
            if key in found:
                continue
            found[key] = {
                "product": str(item.get("label") or "").strip() or "Unidentified product",
                "upc": str(item.get("upc") or "").strip(),
                "scan_type": str(item.get("type") or "").strip().lower(),
            }
    return found


def _bay_key(value: Any) -> str:
    text = str(value if value is not None else "").strip().lower()
    return str(int(text)) if text.isdigit() else text


def _initial_occupants(
    raw_items: List[Dict[str, Any]],
    shelf_products: Optional[Dict[SlotKey, Dict[str, str]]] = None,
) -> Dict[SlotKey, Dict[str, Any]]:
    """Who stands in each position before the first step.

    The before photo supplies every detected product. A row that starts at a
    position replaces the photo's entry there because it also carries the action id.
    """
    occupant: Dict[SlotKey, Dict[str, Any]] = {}
    if shelf_products:
        bays: Dict[str, str] = {}
        for row in raw_items:
            for field in ("current_position", "expected_position"):
                location = _location(_position(row.get(field)))
                if location and location["bay"] != "":
                    bays.setdefault(_bay_key(location["bay"]), location["bay"])
        for (section, shelf, position), found in shelf_products.items():
            bay = bays.get(_bay_key(section), str(section))
            occupant[(bay, str(shelf), str(position))] = {
                "index": 0,
                "id": None,
                "action": "on shelf",
                "product": found.get("product") or "Unidentified product",
                "upc": str(found.get("upc") or ""),
                "source": "shelf_scan",
                "scan_type": str(found.get("scan_type") or ""),
            }
    from_rows = set()
    for row in raw_items:
        source = _slot_key(_location(_position(row.get("current_position"))))
        if source and source not in from_rows:
            from_rows.add(source)
            row_prod = _product(row) or str(row.get("displayed_upc") or row.get("upc") or "")
            if not row_prod and row.get("id") is not None:
                row_prod = f"Product (Action #{row.get('id')})"
            occupant[source] = {
                "index": 0,
                "id": row.get("id"),
                "action": "on shelf",
                "product": row_prod or "Existing product",
                "upc": str(row.get("displayed_upc") or row.get("upc") or ""),
                "source": "action_list",
            }
    return occupant


def _occupant_status(
    holder: Dict[str, Any],
    source: str,
    has_action: bool,
    later: Optional[Dict[str, Any]],
    placed_at_step: Optional[int],
    roles: List[str],
) -> Tuple[str, str]:
    """Say what kind of product blocks a position, and in one sentence why it will (not) leave."""
    if source == "earlier_step":
        return "placed_earlier", f"It was placed here at step {placed_at_step or '?'}."
    if source == "shelf_scan" and not has_action:
        scan_type = str(holder.get("scan_type") or "").strip().lower()
        if scan_type == "ok":
            return "marked_ok", "It is marked OK in the before photo and has no action, so nothing will move it."
        seen_as = f" (scan type: {scan_type})" if scan_type else ""
        return "detected_no_action", (
            f"It was seen in the before photo{seen_as}, is not marked OK, and has no action, so nothing will move it."
        )
    if later:
        return "moves_later", (
            f"This product needs to move ({later['role']}, step {later['index']}), "
            "but this step puts another product there before that move."
        )
    names = ", ".join(sorted(set(roles))) or "an action"
    return "has_action", f"It has an action ({names}) that does not take it off this position, so nothing will move it."


def blocked_summary(steps: List[Dict[str, Any]]) -> Dict[str, int]:
    """Count blocked placements by what is standing in the way."""
    counts = {"total": 0, "marked_ok": 0, "no_action": 0, "moves_later": 0, "other": 0}
    for step in steps:
        occupancy = step.get("target_occupancy") or {}
        if not occupancy.get("blocking"):
            continue
        counts["total"] += 1
        kind = occupancy.get("occupant_kind")
        if kind == "marked_ok":
            counts["marked_ok"] += 1
        elif kind == "detected_no_action":
            counts["no_action"] += 1
        elif occupancy.get("status") == "occupied_cleared_later":
            counts["moves_later"] += 1
        else:
            counts["other"] += 1
    return counts


def _walk_occupancy(
    raw_items: List[Dict[str, Any]],
    units: List[Dict[str, Any]],
    shelf_products: Optional[Dict[SlotKey, Dict[str, str]]] = None,
) -> List[Optional[Dict[str, Any]]]:
    """Say whether each placement target is empty when its step comes up in the backend order."""
    occupant = _initial_occupants(raw_items, shelf_products)
    vacated_by: Dict[SlotKey, Dict[str, Any]] = {}

    def clears_later(slot: SlotKey, holder: Dict[str, Any], after: int) -> Optional[Dict[str, Any]]:
        for later in units[after:]:
            if later["source"] == slot and later.get("clears_source") and _same_product(later, holder):
                return later
        return None

    results: List[Optional[Dict[str, Any]]] = []
    for position, unit in enumerate(units):
        target = unit["target"] if unit["role"] in _FILL_ROLES else None
        result: Optional[Dict[str, Any]] = None
        if target:
            holder = occupant.get(target)
            if holder is None:
                cleared = vacated_by.get(target)
                if cleared:
                    cleared_upc = cleared.get("upc") or ""
                    result = {
                        "status": "vacant",
                        "title": "Empty now",
                        "text": (
                            f"Emptied at step {cleared['index']} when {cleared['product']}"
                            f"{f' (UPC {cleared_upc})' if cleared_upc else ''} left this position "
                            f"({cleared['role']})."
                        ),
                        "cleared_at_step": cleared["index"],
                        "cleared_product": cleared["product"],
                        "cleared_product_upc": cleared_upc,
                        "cleared_by_role": cleared["role"],
                    }
                else:
                    result = {
                        "status": "vacant",
                        "title": "Empty",
                        "text": "No earlier step lists a product at this position.",
                    }
            elif _same_product(holder, unit):
                if unit.get("source") == target:
                    title = "Same product"
                    text = "This product already holds this position."
                elif holder.get("id") == unit.get("id"):
                    title = "Same action"
                    text = f"Action #{unit['id']} already placed this product here at step {holder.get('index', 0)}."
                else:
                    title = "Same product"
                    text = f"Another facing of {holder['product']} was placed here at step {holder.get('index', 0)}."
                result = {
                    "status": "vacant",
                    "title": title,
                    "text": text,
                    "occupant_product": holder["product"],
                    "occupant_upc": holder.get("upc") or "",
                }
            else:
                later = clears_later(target, holder, position)
                holder_upc = holder.get("upc") or ""
                holder_name = holder.get("product") or "Existing product"
                holder_id = holder.get("id")
                holder_step = holder.get("index") or None

                if holder_step:
                    occ_origin = f"Placed into this position at Step {holder_step} by Action #{holder_id or 'N/A'}."
                else:
                    occ_origin = "Present on shelf from the initial scan."

                holder_act = str(holder.get("action") or "").lower()
                is_unidentified = (
                    "identify" in holder_act
                    or "unidentified" in holder_name.lower()
                    or (not holder_upc and "product" in holder_name.lower())
                )

                id_unit = next(
                    (u for u in units if u.get("role") == "identify" and (
                        (holder_id is not None and u.get("id") == holder_id) or u.get("source") == target
                    )),
                    None,
                )
                if is_unidentified:
                    if id_unit:
                        ident_text = f"Unidentified product. System generated IDENTIFY action #{id_unit.get('id')} at Step {id_unit['index']}."
                    else:
                        ident_text = "Unidentified product. System did NOT generate any IDENTIFY action."
                else:
                    ident_text = f"Identified product (UPC {holder_upc or 'N/A'}). No IDENTIFY action needed or generated."

                holder_actions = [
                    f"Step {u['index']} ({u['role']}, Action #{u.get('id')})"
                    for u in units
                    if (holder_id is not None and u.get("id") == holder_id)
                    or (holder_upc and u.get("upc") == holder_upc and (u.get("source") == target or u.get("target") == target))
                ]
                holder_actions_str = ", ".join(holder_actions) if holder_actions else "No other action in this task."
                # A unit placed by an earlier step carries its own source slot, so only these two names count.
                occupant_source = holder.get("source") if holder.get("source") in ("shelf_scan", "action_list") else "earlier_step"
                occupant_has_action = occupant_source != "shelf_scan" or any(
                    u["source"] == target and _same_product(u, holder) for u in units
                )
                occupant_kind, occupant_note = _occupant_status(
                    holder, occupant_source, occupant_has_action, later, holder_step,
                    [u["role"] for u in units if holder_id is not None and u.get("id") == holder_id],
                )

                if later:
                    later.setdefault("earlier_placements", []).append({
                        "index": unit["index"],
                        "product": unit.get("product") or "another product",
                    })
                    result = {
                        "status": "occupied_cleared_later",
                        "title": "Occupied now",
                        "text": (
                            f"{holder_name}{f' (UPC {holder_upc})' if holder_upc else ''} is still here. "
                            f"It is moved away at step {later['index']} "
                            f"({later['role']}), after this step."
                        ),
                        "blocked_by_step": holder_step,
                        "blocked_by_id": holder_id,
                        "cleared_at_step": later["index"],
                        "occupant_product": holder_name,
                        "occupant_upc": holder_upc,
                        "occupant_id": holder_id,
                        "occupant_origin": occ_origin,
                        "occupant_identification": ident_text,
                        "occupant_actions": holder_actions_str,
                        "occupant_source": occupant_source,
                        "occupant_has_action": occupant_has_action,
                        "occupant_kind": occupant_kind,
                        "occupant_note": occupant_note,
                        "cleared_by_role": later["role"],
                        "blocking": True,
                    }
                else:
                    result = {
                        "status": "occupied",
                        "title": "Occupied",
                        "text": (
                            f"{holder_name}{f' (UPC {holder_upc})' if holder_upc else ''} is here, "
                            "and no earlier step moves or removes it before this product arrives."
                        ),
                        "blocked_by_step": holder_step,
                        "blocked_by_id": holder_id,
                        "occupant_product": holder_name,
                        "occupant_upc": holder_upc,
                        "occupant_id": holder_id,
                        "occupant_origin": occ_origin,
                        "occupant_identification": ident_text,
                        "occupant_actions": holder_actions_str,
                        "occupant_source": occupant_source,
                        "occupant_has_action": occupant_has_action,
                        "occupant_kind": occupant_kind,
                        "occupant_note": occupant_note,
                        "blocking": True,
                    }
        if unit["source"] and unit.get("clears_source"):
            holder = occupant.get(unit["source"])
            if holder and _same_product(holder, unit):
                occupant.pop(unit["source"], None)
                vacated_by[unit["source"]] = unit
        # A blocked placement cannot happen yet, so the product standing there stays.
        if target and not (result and result.get("blocking")):
            occupant[target] = unit
            vacated_by.pop(target, None)
        results.append(result)
    return results


def _present_units(
    units: List[Dict[str, Any]],
    occupancy: List[Optional[Dict[str, Any]]],
    band,
) -> List[Dict[str, Any]]:
    """One card per physical step. `band` names the group that step belongs to."""
    presented = []
    for unit, target_occupancy in zip(units, occupancy):
        role = unit["role"]
        current = unit["current"]
        expected = unit["expected"]
        label, meaning = _ROLE_LABELS.get(role) or ACTION_LABELS.get(
            unit["raw_name"],
            (unit["raw_name"], "The backend sent this action name; it has no plain-language label yet."),
        )
        movement = _movement(unit["raw_name"], current, expected)
        row = unit["row"]
        product = _product(row)
        place = unit["place"] or {}
        grp = row.get("item_group") or row.get("group") or row.get("group_id") or row.get("group_name")
        act_lower = str(unit["raw_name"] or "").lower()
        root_lower = str(row.get("action") or "").lower()
        is_swap = "swap" in act_lower or "swap" in root_lower or (unit.get("movement") or {}).get("kind") == "backend_swap"
        is_slide = "slide" in act_lower or "slide" in root_lower or (unit.get("movement") or {}).get("kind") == "backend_slide"
        seq_lbl = band(unit)
        if grp:
            seq_lbl = f"{seq_lbl} · Group {grp}"
        earlier = unit.get("earlier_placements") or []
        sequence_flag = ""
        if earlier:
            named = ", ".join(f"step {item['index']} ({item['product']})" for item in earlier)
            sequence_flag = (
                f"This product needs to move, but {named} "
                "puts another product on this place first."
            )

        presented.append({
            "index": unit["index"],
            "id": row.get("id"),
            "type": role,
            "step_role": role,
            "backend_action": unit["raw_name"],
            "rule_flags": unit["rule_flags"],
            "action_label": label,
            "action_meaning": meaning,
            "sequence_label": seq_lbl,
            "movement": movement,
            "target_occupancy": target_occupancy,
            "state": str(row.get("state") or ""),
            "reason": str(row.get("reason") or ""),
            "description": unit["raw_name"],
            "item": product or unit["upc"] or "Unnamed product",
            "productTitle": product,
            "upc": unit["upc"],
            "group": grp,
            "item_group": row.get("item_group"),
            "is_swap": is_swap,
            "is_slide": is_slide,
            "bay": place.get("bay") or "",
            "fromLocation": current,
            "toLocation": expected,
            "slotId": _slot_id(current),
            "toSlotId": _slot_id(expected),
            "image": str(row.get("image") or ""),
            "rationale": str(row.get("reason") or ""),
            "on_mobile": unit.get("on_mobile", True),
            "mobile_note": unit.get("mobile_note") or "",
            "sequence_flag": sequence_flag,
        })
    return presented


def _backend_band(_unit: Dict[str, Any]) -> str:
    return "Backend order"


def present_backend_actions(
    raw_items: List[Dict[str, Any]],
    shelf_products: Optional[Dict[SlotKey, Dict[str, str]]] = None,
) -> List[Dict[str, Any]]:
    """Steps in the order the backend returned the rows. Nothing is sorted or dropped."""
    units = _walk_units(raw_items)
    occupancy = _walk_occupancy(raw_items, units, shelf_products)
    return _present_units(units, occupancy, _backend_band)


# Identify for every bay, Remove for every bay, then one bay at a time:
# Set aside, Fix in bay, Pick from (a move to another bay, filed at the bay it is picked from),
# Add to shelf, then Restock. A set aside is filed at the bay it is picked from; its add at the bay it is placed.
_MOBILE_PRIORITY = {
    "identify": 0,
    "remove": 1,
    "set_aside": 2,
    "fix_in_bay": 3,
    "backend_shelf_move": 3,
    "move_to_bay": 4,
    "add_to_shelf": 5,
    "restock": 6,
}
_MOBILE_BAND = {
    0: "Identify", 1: "Remove", 2: "Set aside", 3: "Fix in bay",
    4: "Pick from", 5: "Add to shelf", 6: "Restock",
}
_MOBILE_DESTINATION_ROLES = {"fix_in_bay", "add_to_shelf", "restock", "backend_shelf_move"}


def _sort_num(value: Any, default: int = -1) -> int:
    """Bay, shelf, and position as the mobile app compares them. A missing number sorts first."""
    try:
        return int(value)
    except (TypeError, ValueError):
        digits = "".join(ch for ch in str(value if value is not None else "") if ch.isdigit())
        return int(digits) if digits else default


def _mobile_location(unit: Dict[str, Any]) -> Dict[str, Any]:
    """Where the mobile app files this step. Placements use the destination; picks use the source."""
    if unit["role"] in _MOBILE_DESTINATION_ROLES:
        return unit["expected"] or unit["current"] or {}
    return unit["current"] or unit["expected"] or {}


def _mobile_sort_key(unit: Dict[str, Any]) -> Tuple:
    place = _mobile_location(unit)
    priority = _MOBILE_PRIORITY.get(unit["role"], 9)
    bay, shelf, position = _sort_num(place.get("bay")), _sort_num(place.get("shelf")), _sort_num(place.get("position"))
    if priority <= 1:
        return (0, priority, bay, shelf, position, unit["origin"], unit["half"])
    return (1, bay, priority, shelf, position, unit["origin"], unit["half"])


def _mobile_band(unit: Dict[str, Any]) -> str:
    priority = _MOBILE_PRIORITY.get(unit["role"], 9)
    if priority <= 1:
        return f"All bays · {_MOBILE_BAND[priority]}"
    if priority >= 9:
        return "Not shown on mobile"
    bay = _mobile_location(unit).get("bay") or "?"
    return f"Bay {bay} · {_MOBILE_BAND[priority]}"


def _mobile_note(unit: Dict[str, Any], first_origin_for_id: Dict[Any, int]) -> str:
    """Why the associate app leaves a step off the screen. Empty when the step is shown.

    Finished rows are removed before the app collapses repeated ids, so a later idle
    row with the same id is still shown. An unknown action still takes its id.
    """
    state = str(unit["row"].get("state") or "")
    if state and state != "STATE_IDLE":
        return f"Already handled ({state}). Mobile only lists actions still to do."
    action_id = unit.get("id")
    if action_id is not None:
        first = first_origin_for_id.get(action_id)
        if first is None:
            first_origin_for_id[action_id] = unit["origin"]
        elif first != unit["origin"]:
            return "The same action id was already listed. Mobile keeps the first one."
    if unit["role"] not in _MOBILE_PRIORITY:
        return "Mobile has no step for this action, so the associate never sees it."
    return ""


def mobile_display_actions(
    raw_items: List[Dict[str, Any]],
    shelf_products: Optional[Dict[SlotKey, Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Every action, in the order the Android associate app shows, plus the ones it hides.

    The order is applied to the steps. Rows are not rewritten. Occupancy is replayed
    in this order, because that is the order the associate reaches each destination.
    """
    units = _walk_units(raw_items)
    seen: Dict[Any, int] = {}
    shown: List[Dict[str, Any]] = []
    hidden: List[Dict[str, Any]] = []
    for unit in units:
        note = _mobile_note(unit, seen)
        copy = dict(unit)
        copy["on_mobile"] = not note
        copy["mobile_note"] = note
        (hidden if note else shown).append(copy)
    shown = sorted(shown, key=_mobile_sort_key)
    for index, unit in enumerate(shown, start=1):
        unit["index"] = index
    hidden = sorted(hidden, key=_mobile_sort_key)
    occupancy = _walk_occupancy(raw_items, shown, shelf_products)
    return {
        "order": "mobile",
        "summary": (
            "Identify for every bay, then Remove for every bay, then each bay: "
            "Set aside, Fix in bay, Pick from, Add to shelf, then Restock."
        ),
        "steps": _present_units(shown, occupancy, _mobile_band),
        "hidden": _present_units(hidden, [None] * len(hidden), _mobile_band),
    }


def shelf_slots_from_backend_actions(
    raw_items: List[Dict[str, Any]],
    shelf_products: Optional[Dict[SlotKey, Dict[str, str]]] = None,
) -> List[Dict[str, Any]]:
    """Build a read-only shelf map. It is not used to create or reorder actions.

    A position the rows mention that holds no product the rows name takes the
    product the before photo saw there, so a blocked destination shows its occupant.
    """
    slots: Dict[str, Dict[str, Any]] = {}
    for row in raw_items:
        product = _product(row) or str(row.get("displayed_upc") or row.get("upc") or "")
        row_id = row.get("id")
        fallback_name = product or (f"Unidentified Product (Action #{row_id})" if row_id is not None else "Occupied")
        for field, role in (("current_position", "current"), ("expected_position", "target")):
            location = _location(_position(row.get(field)))
            slot_id = _slot_id(location)
            if not slot_id or not location:
                continue
            slot = slots.setdefault(slot_id, {
                "id": slot_id,
                "bay": location["bay"],
                "shelf": location["shelf"],
                "position": str(location["position"]),
                "current": None,
                "target": None,
                "productTitle": product or fallback_name,
                "upc": str(row.get("displayed_upc") or row.get("upc") or ""),
            })
            if role == "current":
                slot["current"] = fallback_name or slot["current"]
            else:
                slot["target"] = fallback_name or slot["target"]
    if shelf_products:
        seen = {
            _slot_id({"bay": bay, "shelf": shelf, "position": position}): found
            for (bay, shelf, position), found in _initial_occupants(raw_items, shelf_products).items()
            if found.get("source") == "shelf_scan"
        }
        for slot_id, slot in slots.items():
            if not slot["current"] and slot_id in seen:
                slot["current"] = seen[slot_id]["product"]
    return list(slots.values())


def _finding(code: str, severity: str, title: str, message: str, row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "title": title,
        "message": message,
        "action_ids": [row.get("id")] if row.get("id") is not None else [],
        "index": row.get("_presentation_index"),
    }


def _mutual_blocks(
    units: List[Dict[str, Any]],
    occupants: Dict[SlotKey, Dict[str, Any]],
) -> List[List[Dict[str, Any]]]:
    """Groups of steps that each wait for another's position to be emptied.

    Order does not matter here: if A needs B's position empty and B needs A's,
    no sequence lets either start. A step the backend itself calls a swap or
    slide is left out because the backend names how that move is done.
    """
    waits_on: Dict[int, int] = {}
    for unit in units:
        if unit["role"] not in _FILL_ROLES or unit["role"] == "backend_shelf_move" or not unit["target"]:
            continue
        holder = occupants.get(unit["target"])
        if holder is None or _same_product(holder, unit):
            continue
        blocker = next(
            (
                other for other in units
                if other is not unit
                and other["source"] == unit["target"]
                and other.get("clears_source")
                and _same_product(other, holder)
            ),
            None,
        )
        if blocker:
            waits_on[unit["index"]] = blocker["index"]
    by_index = {unit["index"]: unit for unit in units}
    groups: List[List[Dict[str, Any]]] = []
    done: set = set()
    for start in waits_on:
        path: List[int] = []
        node = start
        while node in waits_on and node not in path and node not in done:
            path.append(node)
            node = waits_on[node]
        if node in path:
            groups.append([by_index[index] for index in path[path.index(node):]])
        done.update(path)
    return groups


def validate_backend_shelf_actions(
    raw_items: List[Dict[str, Any]],
    shelf_products: Optional[Dict[SlotKey, Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Report problems in the backend list, in its own order, without changing it."""
    findings: List[Dict[str, Any]] = []
    seen_ids: Dict[Any, int] = {}
    target_claims: Dict[SlotKey, List[Dict[str, Any]]] = {}

    annotated = []
    for index, row in enumerate(raw_items, start=1):
        copy = dict(row)
        copy["_presentation_index"] = index
        annotated.append(copy)

    for row in annotated:
        action = _action_name(row)
        action_id = row.get("id")
        if action_id is not None:
            seen_ids[action_id] = seen_ids.get(action_id, 0) + 1
        current = _location(_position(row.get("current_position")))
        expected = _location(_position(row.get("expected_position")))
        current_key = _slot_key(current)
        expected_key = _slot_key(expected)
        if current and current_key is None:
            findings.append(_finding(
                "MISSING_SOURCE_COORDINATES", "critical", "Source position is incomplete",
                f"{action} is missing a source bay, shelf, or position.", row,
            ))
        if expected and expected_key is None:
            findings.append(_finding(
                "MISSING_TARGET_COORDINATES", "critical", "Expected position is incomplete",
                f"{action} is missing an expected bay, shelf, or position.", row,
            ))
        same_place = bool(current_key and expected_key and current_key == expected_key)
        if same_place and "remove" not in action and "identify" not in action and not _is_restock(row):
            findings.append(_finding(
                "REDUNDANT_SAME_SLOT_MOVE", "critical", "Product already in place",
                f"{_product(row) or 'Product'} is already at {_slot_text(current)}.", row,
            ))
        if expected_key:
            target_claims.setdefault(expected_key, []).append(row)
        if action == "place_on_shelf_restock" and current_key and not same_place:
            findings.append(_finding(
                "INVALID_RESTOCK_SOURCE", "critical", "Restock includes a shelf source",
                "A restock row also names a current shelf position.", row,
            ))

    rule_counts = {code: 0 for code in RULES}
    backend_names = {"swap": 0, "slide": 0}
    for row in annotated:
        for flag in _rule_flags(row):
            rule_counts[flag["code"]] += 1
            findings.append(_finding(flag["code"], "critical", flag["title"], flag["message"], row))
        names = " ".join(str((_position(row.get(field)) or {}).get("action") or "") for field in ("current_position", "expected_position"))
        names = f"{names} {row.get('action') or ''}".lower()
        for kind in backend_names:
            if kind in names:
                backend_names[kind] += 1

    for action_id, count in seen_ids.items():
        if count > 1:
            row = next(item for item in annotated if item.get("id") == action_id)
            findings.append(_finding(
                "DUPLICATE_ACTION", "warning", "Backend repeated an action",
                f"Action {action_id} appears {count} times. Each copy is shown.", row,
            ))

    for target, claimants in target_claims.items():
        unique_products = set()
        for crow in claimants:
            u_upc = str(crow.get("displayed_upc") or crow.get("upc") or "").strip()
            u_title = str(crow.get("product_title") or crow.get("product_name") or crow.get("product") or "").strip().lower()
            prod_key = u_upc if u_upc else (u_title if u_title and "unidentified" not in u_title else str(crow.get("id")))
            unique_products.add(prod_key)
        if len(unique_products) > 1:
            claimant_details = []
            for c_idx, crow in enumerate(claimants, start=1):
                c_src = _location(_position(crow.get("current_position")))
                c_id = crow.get("id")
                c_title = _product(crow) or f"Product (Action #{c_id})"
                c_upc = str(crow.get("displayed_upc") or crow.get("upc") or "")
                c_act = _action_name(crow)
                c_src_str = _slot_text(c_src) if c_src else "Backroom / Restock (No source shelf)"
                claimant_details.append({
                    "index": c_idx,
                    "id": c_id,
                    "product": c_title,
                    "upc": c_upc,
                    "action": c_act,
                    "source": c_src_str,
                    "target": f"Bay {target[0]}, Shelf {target[1]}, Position {target[2]}",
                })
            claimant_lines = "\n".join(
                f"• Product #{c['index']} (Action #{c['id']}): '{c['product']}' (UPC {c['upc'] or 'N/A'}) from {c['source']}"
                for c in claimant_details
            )
            target_str = f"Bay {target[0]}, Shelf {target[1]}, Position {target[2]}"
            f_item = _finding(
                "DUPLICATE_TARGET_SLOT", "critical", "Multiple products target one slot",
                f"{len(unique_products)} different products claim {target_str}:\n{claimant_lines}",
                claimants[0],
            )
            f_item["action_ids"] = [row.get("id") for row in claimants if row.get("id") is not None]
            f_item["target"] = target_str
            f_item["claimants"] = claimant_details
            findings.append(f_item)

    units = _walk_units(raw_items)
    occupancy = _walk_occupancy(raw_items, units, shelf_products)
    never_cleared = cleared_later = 0
    for unit, result in zip(units, occupancy):
        if not result or result["status"] not in ("occupied", "occupied_cleared_later"):
            continue
        flagged = dict(unit["row"])
        flagged["_presentation_index"] = unit["index"]
        target_str = f"Bay {unit['target'][0]}, Shelf {unit['target'][1]}, Position {unit['target'][2]}"
        occupant = result["occupant_product"] + (f" (UPC {result['occupant_upc']})" if result.get("occupant_upc") else "")
        who = f"Step {unit['index']} (Action {unit['id']}, {unit['product']})"
        if result["status"] == "occupied":
            never_cleared += 1
            item = _finding(
                "OCCUPIED_DESTINATION", "critical", "Destination is occupied and nothing clears it",
                f"{who} goes to {target_str}, but {occupant} is there and no step in the backend list moves or removes it. "
                f"{result['occupant_note']}",
                flagged,
            )
        else:
            cleared_later += 1
            item = _finding(
                "DESTINATION_CLEARED_LATER", "critical", "Destination is cleared after it is needed",
                f"{who} goes to {target_str} while {occupant} is still there. "
                f"The backend list only moves it away at step {result['cleared_at_step']}, after this step.",
                flagged,
            )
            item["cleared_at_step"] = result["cleared_at_step"]
        item["target"] = target_str
        item["occupant_product"] = result["occupant_product"]
        item["occupant_upc"] = result.get("occupant_upc") or ""
        item["occupant_kind"] = result["occupant_kind"]
        item["occupant_note"] = result["occupant_note"]
        findings.append(item)

    groups = _mutual_blocks(units, _initial_occupants(raw_items, shelf_products))
    for group in groups:
        ids = ", ".join(str(unit["id"]) for unit in group)
        item = _finding(
            "MUTUAL_BLOCK", "critical", "Steps wait on each other",
            f"Actions {ids} wait on each other: each goes to a position the next one is still standing in, "
            "so none can go first. Each is a direct move, with no set aside to break the loop.",
            dict(group[0]["row"], _presentation_index=group[0]["index"]),
        )
        item["action_ids"] = sorted({unit["id"] for unit in group if unit["id"] is not None}, key=str)
        item["steps"] = [unit["index"] for unit in group]
        findings.append(item)

    orphans = [unit for unit in units if unit["role"] == "set_aside" and not unit["expected"]]
    for unit in orphans:
        findings.append(_finding(
            "SET_ASIDE_WITHOUT_PLACEMENT", "warning", "Set aside has no destination",
            f"Action {unit['id']} ({unit['product']}) picks the product up, "
            "and the backend gives no position to put it back.",
            dict(unit["row"], _presentation_index=unit["index"]),
        ))

    critical = sum(1 for item in findings if item["severity"] == "critical")
    warnings = sum(1 for item in findings if item["severity"] == "warning")
    return {
        "state": "blocked" if critical else ("warning" if warnings else "pass"),
        "can_start": critical == 0,
        "critical_count": critical,
        "warning_count": warnings,
        "checks_run": 14,
        "sequence_check": {
            "order": "backend",
            "blocked_destinations": never_cleared + cleared_later,
            "destination_never_cleared": never_cleared,
            "destination_cleared_later": cleared_later,
            "mutual_blocks": len(groups),
            "set_asides_without_placement": len(orphans),
            "occupancy_source": "action_rows_and_shelf_scan" if shelf_products else "action_rows",
        },
        "findings": findings,
        "rule_check": {
            "same_bay_set_aside": rule_counts["SAME_BAY_SET_ASIDE"],
            "same_bay_move_not_fix_in_bay": rule_counts["SAME_BAY_MOVE_NOT_FIX_IN_BAY"],
            "fix_in_bay_across_bays": rule_counts["FIX_IN_BAY_ACROSS_BAYS"],
            "backend_swap_actions": backend_names["swap"],
            "backend_slide_actions": backend_names["slide"],
            "rows_breaking_rules": sum(rule_counts.values()),
        },
        "summary": (
            f"{critical} critical and {warnings} warning finding(s). The backend action list was not changed."
        ),
    }
