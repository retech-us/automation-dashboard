"""Present retailer actions in store walk order and check them against reset rules.

Identify across every bay, then remove across every bay, then each bay in
order: set aside, move to another bay, fix in bay, add to shelf, restock.
Only position actions the backend sent become cards; no swap, slide, or pick
action is invented. Rows that break a reset rule carry red flags.
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
    return str(row.get("product_title") or row.get("product_name") or nested or "")


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


_GLOBAL_PHASE = {"identify": 0, "remove": 1}
_BAY_PHASE = {"set_aside": 0, "move_to_bay": 1, "fix_in_bay": 2, "backend_shelf_move": 2, "add_to_shelf": 3, "restock": 4, "other": 5}
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


def _rule_flags(row: Dict[str, Any]) -> List[Dict[str, str]]:
    """Reset-rule breaks on one backend row."""
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


def _coord_num(value: Any, default: int = 10 ** 6) -> int:
    digits = "".join(ch for ch in str(value if value is not None else "") if ch.isdigit())
    return int(digits) if digits else default


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


def _sort_location(role: str, current: Optional[Dict[str, Any]], expected: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if role in ("add_to_shelf", "restock"):
        return expected or current or {}
    return current or expected or {}


def _walk_units(raw_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
            place = _sort_location(role, current, expected)
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
                "sort_at": place,
                "id": row.get("id"),
                "product": _product(row) or str(row.get("upc") or "") or "a product",
                "upc": str(row.get("displayed_upc") or row.get("upc") or ""),
            })
    units.sort(key=lambda unit: _walk_sort_key(unit))
    for index, unit in enumerate(units, start=1):
        unit["index"] = index
    return units


def _walk_sort_key(unit: Dict[str, Any]) -> Tuple:
    place = unit["sort_at"] or {}
    bay = _coord_num(place.get("bay"))
    shelf = _coord_num(place.get("shelf"))
    position = _coord_num(place.get("position"))
    role = unit["role"]
    if role in _GLOBAL_PHASE:
        return (_GLOBAL_PHASE[role], 0, bay, shelf, position, unit["origin"], unit["half"])
    return (2, bay, _BAY_PHASE[role], shelf, position, unit["origin"], unit["half"])


def _same_product(left: Dict[str, Any], right: Dict[str, Any]) -> bool:
    if left.get("id") is not None and left.get("id") == right.get("id"):
        return True
    if left.get("upc") and left.get("upc") == right.get("upc"):
        return True
    return bool(left.get("product") and left.get("product") == right.get("product"))


def _walk_occupancy(raw_items: List[Dict[str, Any]], units: List[Dict[str, Any]]) -> List[Optional[Dict[str, Any]]]:
    """Say whether each placement target is empty at that point in the walk."""
    occupant: Dict[SlotKey, Dict[str, Any]] = {}
    for index, row in enumerate(raw_items, start=1):
        source = _slot_key(_location(_position(row.get("current_position"))))
        if source and source not in occupant:
            occupant[source] = {
                "index": 0,
                "id": row.get("id"),
                "action": "on shelf",
                "product": _product(row) or str(row.get("upc") or "") or "a product",
                "upc": str(row.get("displayed_upc") or row.get("upc") or ""),
            }
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
                result = {
                    "status": "vacant",
                    "title": "Same product",
                    "text": "This product already holds this position.",
                    "occupant_product": holder["product"],
                    "occupant_upc": holder.get("upc") or "",
                }
            else:
                later = clears_later(target, holder, position)
                holder_upc = holder.get("upc") or ""
                if later:
                    result = {
                        "status": "occupied_cleared_later",
                        "title": "Occupied now",
                        "text": (
                            f"{holder['product']}{f' (UPC {holder_upc})' if holder_upc else ''} is still here. "
                            f"It is moved away at step {later['index']} "
                            f"({later['role']}), after this step."
                        ),
                        "blocked_by_step": holder["index"] or None,
                        "cleared_at_step": later["index"],
                        "occupant_product": holder["product"],
                        "occupant_upc": holder_upc,
                        "cleared_by_role": later["role"],
                    }
                else:
                    result = {
                        "status": "occupied",
                        "title": "Occupied",
                        "text": (
                            f"{holder['product']}{f' (UPC {holder_upc})' if holder_upc else ''} is here, "
                            "and no earlier step moves or removes it before this product arrives."
                        ),
                        "blocked_by_step": holder["index"] or None,
                        "occupant_product": holder["product"],
                        "occupant_upc": holder_upc,
                        "blocking": True,
                    }
        if unit["source"] and unit.get("clears_source"):
            holder = occupant.get(unit["source"])
            if holder and _same_product(holder, unit):
                occupant.pop(unit["source"], None)
                vacated_by[unit["source"]] = unit
        if target:
            occupant[target] = unit
            vacated_by.pop(target, None)
        results.append(result)
    return results


def _sequence_label(role: str, place: Dict[str, Any], label: str) -> str:
    bay = place.get("bay") or ""
    if role == "identify":
        return "All bays · Identify"
    if role == "remove":
        return "All bays · Remove"
    names = {
        "set_aside": "Set aside",
        "move_to_bay": "Move to another bay",
        "fix_in_bay": "Fix in bay",
        "add_to_shelf": "Add to shelf",
        "restock": "Restock",
    }
    return f"Bay {bay} · {names.get(role, label)}"


def present_backend_actions(raw_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Walk steps for the associate, in store order."""
    units = _walk_units(raw_items)
    occupancy = _walk_occupancy(raw_items, units)
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
        place = unit["sort_at"] or {}
        presented.append({
            "index": unit["index"],
            "id": row.get("id"),
            "type": role,
            "step_role": role,
            "backend_action": unit["raw_name"],
            "rule_flags": unit["rule_flags"],
            "action_label": label,
            "action_meaning": meaning,
            "sequence_label": _sequence_label(role, place, label),
            "movement": movement,
            "target_occupancy": target_occupancy,
            "state": str(row.get("state") or ""),
            "reason": str(row.get("reason") or ""),
            "description": unit["raw_name"],
            "item": product or unit["upc"] or "Unnamed product",
            "productTitle": product,
            "upc": unit["upc"],
            "bay": place.get("bay") or "",
            "fromLocation": current,
            "toLocation": expected,
            "slotId": _slot_id(current),
            "toSlotId": _slot_id(expected),
            "image": str(row.get("image") or ""),
            "rationale": str(row.get("reason") or ""),
        })
    return presented


def shelf_slots_from_backend_actions(raw_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build a read-only shelf map. It is not used to create or reorder actions."""
    slots: Dict[str, Dict[str, Any]] = {}
    for row in raw_items:
        product = _product(row) or str(row.get("upc") or "")
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
                "productTitle": product,
                "upc": str(row.get("upc") or ""),
            })
            if role == "current":
                slot["current"] = product or slot["current"]
            else:
                slot["target"] = product or slot["target"]
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


def validate_backend_shelf_actions(raw_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Report problems in the backend list without changing that list."""
    findings: List[Dict[str, Any]] = []
    seen_ids: Dict[Any, int] = {}
    target_claims: Dict[SlotKey, List[Dict[str, Any]]] = {}
    occupancy: Dict[SlotKey, Dict[str, Any]] = {}

    annotated = []
    for index, row in enumerate(raw_items, start=1):
        copy = dict(row)
        copy["_presentation_index"] = index
        annotated.append(copy)
        current = _location(_position(row.get("current_position")))
        current_key = _slot_key(current)
        if current_key and current_key not in occupancy:
            occupancy[current_key] = copy

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
        if current_key and expected_key and current_key == expected_key and "remove" not in action and "identify" not in action:
            findings.append(_finding(
                "REDUNDANT_SAME_SLOT_MOVE", "critical", "Product already in place",
                f"{_product(row) or 'Product'} is already at {_slot_text(current)}.", row,
            ))
        if expected_key:
            target_claims.setdefault(expected_key, []).append(row)
        if action == "place_on_shelf_restock" and current_key:
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
        identities = []
        for row in claimants:
            identity = row.get("id")
            if identity not in identities:
                identities.append(identity)
        if len(identities) > 1:
            findings.append(_finding(
                "DUPLICATE_TARGET_SLOT", "critical", "Multiple products target one slot",
                f"{len(identities)} backend actions claim Bay {target[0]}, Shelf {target[1]}, Position {target[2]}.",
                claimants[0],
            ))

    for unit in _walk_units(raw_items):
        if unit["role"] not in _FILL_ROLES or not unit["target"]:
            if unit["source"] and unit.get("clears_source"):
                holder = occupancy.get(unit["source"])
                if holder and holder.get("id") == unit["id"]:
                    occupancy.pop(unit["source"], None)
            continue
        occupant = occupancy.get(unit["target"])
        same_id = occupant and occupant.get("id") is not None and occupant.get("id") == unit["id"]
        if occupant and not same_id:
            flagged = dict(unit["row"])
            flagged["_presentation_index"] = unit["index"]
            findings.append(_finding(
                "OCCUPIED_DESTINATION", "critical", "Expected position is still occupied",
                f"Action {unit['id']} targets a position that an earlier walk step has not cleared.", flagged,
            ))
        if unit["source"] and unit.get("clears_source"):
            holder = occupancy.get(unit["source"])
            if holder and holder.get("id") == unit["id"]:
                occupancy.pop(unit["source"], None)
        occupancy[unit["target"]] = unit["row"]

    critical = sum(1 for item in findings if item["severity"] == "critical")
    warnings = sum(1 for item in findings if item["severity"] == "warning")
    return {
        "state": "blocked" if critical else ("warning" if warnings else "pass"),
        "can_start": critical == 0,
        "critical_count": critical,
        "warning_count": warnings,
        "checks_run": 10,
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
