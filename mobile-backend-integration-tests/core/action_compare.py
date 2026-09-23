"""Deterministic comparison of generated IR steps and Digital Report actions."""

from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ActionComparisonRow:
    status: str
    scan_id: Optional[int]
    upc: str
    product_name: str
    generated_action_type: str
    digital_action_type: str
    digital_action_taken: str
    digital_position: str = ""
    is_extra_facing: bool = False
    pog_facings: int = 0
    rog_facings: int = 0


@dataclass
class ActionComparisonResult:
    rows: List[ActionComparisonRow]
    counts: Dict[str, int]
    digital_alignment_pct: Optional[float]
    combined_compliance_pct: float
    loaded: bool
    error: Optional[str] = None


def _as_mapping(value: Any) -> Dict[str, Any]:
    if is_dataclass(value):
        return asdict(value)
    return value if isinstance(value, dict) else {}


def _normalized(value: Any) -> str:
    return str(value or "").strip().replace("-", "_").replace(" ", "_").casefold()


# Digital Report "reason" wording mapped to the IR action types it satisfies.
DIGITAL_ACTION_EQUIVALENTS = {
    "fixed_item": frozenset({"fix_in_bay", "fix_position", "move"}),
    "restocked_item": frozenset({"restock"}),
    "removed_item": frozenset({"remove"}),
    "add_item": frozenset({"add_to_shelf", "set_aside"}),
    # Cross-bay move: IR shows pick (SET_ASIDE) + place (ADD_TO_SHELF);
    # Digital Shelf records one "Moved Item" row for that product.
    "moved_item": frozenset({"set_aside", "add_to_shelf", "move"}),
    "image_not_ideal_to_add_to_database": frozenset({"identify"}),
}

_NO_ACTION_TAKEN = {"", "_"}


def _actions_match(generated: Dict[str, Any], digital: Dict[str, Any]) -> bool:
    expected = _normalized(
        generated.get("generated_action_type", generated.get("action_type"))
    )
    action_taken = _normalized(digital.get("action_taken"))
    if not expected or action_taken in _NO_ACTION_TAKEN:
        return False
    if expected == action_taken:
        return True
    return expected in DIGITAL_ACTION_EQUIVALENTS.get(action_taken, frozenset())


def _position(value: Dict[str, Any]) -> str:
    return str(
        value.get("position")
        or value.get("pog_position")
        or value.get("rog_position")
        or ""
    ).strip()


def _same_identity(generated: Dict[str, Any], digital: Dict[str, Any]) -> bool:
    generated_upc = str(generated.get("upc") or "")
    if str(digital.get("upc") or "") != generated_upc:
        return False

    generated_scan_id = generated.get("scan_id")
    digital_scan_id = digital.get("scan_id")
    scans_present = generated_scan_id is not None and digital_scan_id is not None
    if scans_present and str(generated_scan_id).strip() != str(digital_scan_id).strip():
        return False

    if not generated_upc:
        # Unidentified products share empty UPC. Position alone is not unique across
        # bays — Bay 1 @ 4:2 and Bay 2 @ 4:2 are different Digital Shelf rows.
        generated_position = _position(generated)
        if not (
            generated_position and generated_position == _position(digital)
        ):
            return False
        if scans_present:
            return True
        generated_section = str(
            generated.get("section") or generated.get("bay") or ""
        ).strip()
        digital_section = str(
            digital.get("section") or digital.get("bay") or ""
        ).strip()
        if generated_section and digital_section:
            return generated_section == digital_section
        return True

    if scans_present:
        return True
    generated_position = _position(generated)
    return bool(
        generated_position
        and _position(digital)
        and generated_position == _position(digital)
    )


def _row(
    status: str,
    generated: Optional[Dict[str, Any]] = None,
    digital: Optional[Dict[str, Any]] = None,
) -> ActionComparisonRow:
    generated = generated or {}
    digital = digital or {}
    return ActionComparisonRow(
        status=status,
        scan_id=generated.get("scan_id", digital.get("scan_id")),
        upc=str(generated.get("upc") or digital.get("upc") or ""),
        product_name=str(
            generated.get("product_title")
            or digital.get("product_name")
            or ""
        ),
        generated_action_type=str(
            generated.get("generated_action_type")
            or generated.get("action_type")
            or ""
        ),
        digital_action_type=str(digital.get("action_type") or ""),
        digital_action_taken=str(digital.get("action_taken") or "-"),
        digital_position=_position(digital) or _position(generated),
        is_extra_facing=bool(
            generated.get("is_extra_facing")
            or digital.get("is_extra_facing")
            or False
        ),
        pog_facings=int(
            generated.get("pog_facings")
            or digital.get("pog_facings")
            or 0
        ),
        rog_facings=int(
            generated.get("rog_facings")
            or digital.get("rog_facings")
            or 0
        ),
    )


def compare_actions(
    generated_actions: List[Any],
    digital_actions: List[Any],
    execution_compliance_pct: float,
    digital_loaded: bool = True,
    digital_error: Optional[str] = None,
    unavailable_scan_ids: Optional[List[int]] = None,
) -> ActionComparisonResult:
    """Join action sets and calculate alignment and combined compliance."""
    generated = [_as_mapping(item) for item in generated_actions]
    digital = [_as_mapping(item) for item in digital_actions]
    rows: List[ActionComparisonRow] = []
    used_digital = set()
    ambiguous_digital = set()
    logical_statuses: Dict[Any, str] = {}
    unavailable_scans = {str(scan_id).strip() for scan_id in unavailable_scan_ids or []}
    status_priority = {
        "MATCH": 0,
        "NO_ACTION_NEEDED": 0,
        "UNAVAILABLE": 1,
        "GENERATED_ONLY": 2,
        "AMBIGUOUS": 3,
        "MISMATCH": 4,
        "DIGITAL_ONLY": 4,
    }

    def record_logical_status(key: Any, status: str) -> None:
        existing = logical_statuses.get(key)
        if existing is None or status_priority[status] > status_priority[existing]:
            logical_statuses[key] = status

    if not digital_loaded:
        return ActionComparisonResult(
            rows=[],
            counts=_empty_counts(),
            digital_alignment_pct=None,
            combined_compliance_pct=execution_compliance_pct,
            loaded=False,
            error=digital_error,
        )

    # A cross-bay move is split into a pick and a place step, but the Digital Report
    # holds one row for the product, so both halves may claim the same row.
    digital_owner: Dict[int, Any] = {}

    for generated_index, generated_item in enumerate(generated):
        source_action_id = generated_item.get("source_action_id")
        logical_key = (
            ("generated", source_action_id)
            if source_action_id is not None
            else ("generated-row", generated_index)
        )
        if str(generated_item.get("scan_id") or "").strip() in unavailable_scans:
            rows.append(_row("UNAVAILABLE", generated=generated_item))
            record_logical_status(logical_key, "UNAVAILABLE")
            continue
        candidates = [
            index
            for index in enumerate(digital)
            if (
                index[0] not in used_digital
                or (
                    source_action_id is not None
                    and digital_owner.get(index[0]) == source_action_id
                )
            )
            and _same_identity(generated_item, index[1])
        ]
        candidates = [idx for idx, _ in candidates]
        generated_position = _position(generated_item)
        identity_pool = [
            index
            for index, digital_item in enumerate(digital)
            if str(digital_item.get("upc") or "")
            == str(generated_item.get("upc") or "")
            and (
                generated_item.get("scan_id") is None
                or digital_item.get("scan_id") is None
                or str(generated_item.get("scan_id")).strip()
                == str(digital_item.get("scan_id")).strip()
            )
        ]
        position_matches = [
            index
            for index in candidates
            if generated_position
            and _position(digital[index]) == generated_position
        ]
        if position_matches:
            # If candidates match this specific shelf position (even multiple duplicate facings),
            # match them sequentially against available candidates at this slot.
            candidates = position_matches
        elif len(identity_pool) > 1 and len(candidates) == 1 and generated_position:
            # Do not let a later duplicate-facing step claim the sole remaining
            # row at a different slot merely because UPC and scan still match.
            candidates = []

        if not candidates:
            rows.append(_row("GENERATED_ONLY", generated=generated_item))
            record_logical_status(logical_key, "GENERATED_ONLY")
            continue
        if len(candidates) > 1 and not position_matches:
            ambiguous_digital.update(candidates)
            # Use the first candidate's digital data so action type / action
            # taken are still visible in the report even though the exact
            # 1-to-1 facing match is ambiguous.
            rows.append(_row("AMBIGUOUS", generated=generated_item, digital=digital[candidates[0]]))
            record_logical_status(logical_key, "AMBIGUOUS")
            continue

        match_index = candidates[0]
        used_digital.add(match_index)
        digital_owner.setdefault(match_index, source_action_id)
        digital_item = digital[match_index]
        status = "MATCH" if _actions_match(generated_item, digital_item) else "MISMATCH"
        rows.append(_row(status, generated_item, digital_item))
        record_logical_status(logical_key, status)

    for index, digital_item in enumerate(digital):
        if index in used_digital or index in ambiguous_digital:
            continue
        # A shelf product the user was never asked to touch and did not touch is
        # not a compliance failure, only context.
        untouched = _normalized(digital_item.get("action_taken")) in _NO_ACTION_TAKEN
        status = "NO_ACTION_NEEDED" if untouched else "DIGITAL_ONLY"
        rows.append(_row(status, digital=digital_item))
        record_logical_status(("digital-row", index), status)

    counts = _empty_counts()
    count_keys = {
        "MATCH": "matched",
        "MISMATCH": "mismatched",
        "GENERATED_ONLY": "generated_only",
        "DIGITAL_ONLY": "digital_only",
        "NO_ACTION_NEEDED": "no_action_needed",
        "AMBIGUOUS": "ambiguous",
        "UNAVAILABLE": "unavailable",
    }
    for status in logical_statuses.values():
        counts[count_keys[status]] += 1

    scored_row_count = (
        sum(counts.values()) - counts["unavailable"] - counts["no_action_needed"]
    )
    alignment = (
        round((counts["matched"] / scored_row_count) * 100.0, 1)
        if scored_row_count
        else 100.0
    )
    return ActionComparisonResult(
        rows=rows,
        counts=counts,
        digital_alignment_pct=alignment,
        combined_compliance_pct=min(execution_compliance_pct, alignment),
        loaded=True,
        error=digital_error,
    )


def _empty_counts() -> Dict[str, int]:
    return {
        "matched": 0,
        "mismatched": 0,
        "generated_only": 0,
        "digital_only": 0,
        "no_action_needed": 0,
        "ambiguous": 0,
        "unavailable": 0,
    }
