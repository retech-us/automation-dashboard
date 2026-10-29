"""
Ground Truth Domain Assertions for Shelf Intelligence Actions.
Provides reusable, strict assertions for action completeness, correctness,
invader detection, wandering prevention, OOS additions, and post-photo reconciliation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple


def _normalize_action_key(action: Dict[str, Any]) -> Tuple[str, str, int, int]:
    """Generates a stable tuple key: (action_type, upc, shelf, position)."""
    atype = str(action.get("action_type") or action.get("action") or "").upper()
    upc = str(action.get("upc") or action.get("primary_product_code") or "").strip()
    shelf = int(action.get("shelf") or 0)
    pos = int(action.get("position") or 0)
    return (atype, upc, shelf, pos)


class ShelfActionAssertionError(AssertionError):
    """Custom assertion error providing structured action failure diagnostics."""
    pass


def assert_action_completeness(
    expected_actions: List[Dict[str, Any]],
    actual_actions: List[Dict[str, Any]],
    context_msg: str = "",
) -> None:
    """
    Asserts that ALL required expected actions exist in actual results.
    Fails if any expected action is missing.
    """
    actual_keys = {_normalize_action_key(a) for a in actual_actions}
    missing = []

    for exp in expected_actions:
        k = _normalize_action_key(exp)
        if k not in actual_keys:
            missing.append(exp)

    if missing:
        msg = (
            f"Action Completeness Failed: {len(missing)} expected action(s) missing from API response.\n"
            f"Missing Actions:\n"
            + "\n".join(f"  • {m.get('action_type')} UPC:{m.get('upc')} (Shelf {m.get('shelf')}, Pos {m.get('position')})" for m in missing)
            + f"\nActual Actions Count: {len(actual_actions)}"
        )
        if context_msg:
            msg = f"[{context_msg}] " + msg
        raise ShelfActionAssertionError(msg)


def assert_action_correctness(
    expected_actions: List[Dict[str, Any]],
    actual_actions: List[Dict[str, Any]],
    context_msg: str = "",
) -> None:
    """
    Asserts that NO unexpected or spurious actions exist in actual results.
    Fails if the backend generated unverified extra actions.
    """
    expected_keys = {_normalize_action_key(a) for a in expected_actions}
    unexpected = []

    for act in actual_actions:
        k = _normalize_action_key(act)
        if k not in expected_keys:
            unexpected.append(act)

    if unexpected:
        msg = (
            f"Action Correctness Failed: {len(unexpected)} spurious/unexpected action(s) found in API response.\n"
            f"Unexpected Actions:\n"
            + "\n".join(f"  • {u.get('action_type')} UPC:{u.get('upc')} (Shelf {u.get('shelf')}, Pos {u.get('position')})" for u in unexpected)
            + f"\nExpected Actions Count: {len(expected_actions)}"
        )
        if context_msg:
            msg = f"[{context_msg}] " + msg
        raise ShelfActionAssertionError(msg)


def assert_exact_action_parity(
    expected_actions: List[Dict[str, Any]],
    actual_actions: List[Dict[str, Any]],
    context_msg: str = "",
) -> None:
    """Asserts both 100% completeness and 100% correctness (exact bidirectional set parity)."""
    assert_action_completeness(expected_actions, actual_actions, context_msg)
    assert_action_correctness(expected_actions, actual_actions, context_msg)


def assert_no_false_positive_wandering(
    product_upc: str,
    actual_actions: List[Dict[str, Any]],
) -> None:
    """Asserts that an in-planogram product in its expected position did not generate a wandering or move action."""
    clean_upc = str(product_upc).strip()
    wandering_actions = [
        a for a in actual_actions
        if str(a.get("upc") or a.get("primary_product_code")).strip() == clean_upc
        and str(a.get("action_type")).upper() in ("MOVE", "REMOVE")
    ]
    if wandering_actions:
        raise ShelfActionAssertionError(
            f"False Positive Wandering Defect! In-planogram product UPC '{clean_upc}' "
            f"generated spurious action(s): {wandering_actions}"
        )


def assert_invader_action(
    product_upc: str,
    expected_shelf: int,
    expected_position: int,
    actual_actions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Asserts that an out-of-planogram product generated an invader REMOVE action."""
    clean_upc = str(product_upc).strip()
    for a in actual_actions:
        upc = str(a.get("upc") or a.get("primary_product_code")).strip()
        atype = str(a.get("action_type") or a.get("action")).upper()
        if upc == clean_upc and atype == "REMOVE":
            sh = int(a.get("shelf") or 0)
            pos = int(a.get("position") or 0)
            if sh == expected_shelf and pos == expected_position:
                return a
    raise ShelfActionAssertionError(
        f"Missing Invader Action! Product UPC '{clean_upc}' did not generate expected REMOVE action "
        f"at Shelf {expected_shelf}, Position {expected_position}."
    )


def assert_oos_add_action(
    product_upc: str,
    expected_shelf: int,
    expected_position: int,
    actual_actions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Asserts that a missing planogram item generated an ADD action."""
    clean_upc = str(product_upc).strip()
    for a in actual_actions:
        upc = str(a.get("upc") or a.get("primary_product_code")).strip()
        atype = str(a.get("action_type") or a.get("action")).upper()
        if upc == clean_upc and atype == "ADD":
            sh = int(a.get("shelf") or 0)
            pos = int(a.get("position") or 0)
            if sh == expected_shelf and pos == expected_position:
                return a
    raise ShelfActionAssertionError(
        f"Missing Out-of-Stock Action! Planogram product UPC '{clean_upc}' did not generate expected ADD action "
        f"at Shelf {expected_shelf}, Position {expected_position}."
    )


def assert_post_photo_reconciliation(
    pre_actions: List[Dict[str, Any]],
    post_actions: List[Dict[str, Any]],
    resolved_upcs: List[str],
) -> None:
    """
    Asserts that actions resolved in the physical aisle do not reappear in post-photo action set.
    """
    post_keys = {
        str(a.get("upc") or a.get("primary_product_code")).strip()
        for a in post_actions
        if str(a.get("action_type")).upper() in ("ADD", "REMOVE", "MOVE")
    }

    unresolved = [u for u in resolved_upcs if u in post_keys]
    if unresolved:
        raise ShelfActionAssertionError(
            f"Post-Photo Reconciliation Failed: {len(unresolved)} resolved action(s) still present in post-photo:\n"
            + "\n".join(f"  • UPC: {u}" for u in unresolved)
        )
