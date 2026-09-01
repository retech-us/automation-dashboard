"""Contract assertion engine for API payloads."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ACTION_LIST_CONTRACT = (
    REPO_ROOT / "docs" / "regression" / "baselines" / "action_list_retailer_contract.yaml"
)


class ContractError(Exception):
    def __init__(self, message: str, *, exit_code: int = 1):
        super().__init__(message)
        self.exit_code = exit_code


@dataclass
class ContractViolation:
    path: str
    rule: str
    message: str
    severity: str = "error"  # error | warning

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ContractReport:
    ok: bool
    endpoint: str
    item_count: int
    errors: List[ContractViolation] = field(default_factory=list)
    warnings: List[ContractViolation] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "endpoint": self.endpoint,
            "item_count": self.item_count,
            "errors": [e.as_dict() for e in self.errors],
            "warnings": [w.as_dict() for w in self.warnings],
        }


def load_contract(path: Optional[Path] = None) -> Dict[str, Any]:
    p = path or DEFAULT_ACTION_LIST_CONTRACT
    if not p.is_file():
        raise ContractError(f"Contract baseline not found: {p}", exit_code=2)
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def extract_action_items(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        results = payload.get("results")
        if isinstance(results, list):
            return [x for x in results if isinstance(x, dict)]
        # single object mistakenly returned
        if "id" in payload and "action" in payload:
            return [payload]
    raise ContractError(
        "Action-list envelope must be a list or {results: [...]}",
        exit_code=1,
    )


def _type_ok(value: Any, allowed: Sequence[str]) -> bool:
    for spec in allowed:
        if spec == "null" and value is None:
            return True
        if spec == "int" and isinstance(value, int) and not isinstance(value, bool):
            return True
        if spec == "str" and isinstance(value, str):
            return True
        if spec == "bool" and isinstance(value, bool):
            return True
        if spec == "dict" and isinstance(value, dict):
            return True
        if spec == "list" and isinstance(value, list):
            return True
    return False


def assert_action_list_contract(
    payload: Any,
    *,
    contract: Optional[Dict[str, Any]] = None,
    strict_unknown_actions: bool = False,
) -> ContractReport:
    cfg = contract or load_contract()
    endpoint = str(cfg.get("endpoint") or "action-list/retailer")
    errors: List[ContractViolation] = []
    warnings: List[ContractViolation] = []

    try:
        items = extract_action_items(payload)
    except ContractError as exc:
        errors.append(
            ContractViolation(path="$", rule="envelope", message=str(exc), severity="error")
        )
        return ContractReport(ok=False, endpoint=endpoint, item_count=0, errors=errors)

    required = list(cfg.get("item_required_fields") or [])
    field_types: Dict[str, List[str]] = cfg.get("item_field_types") or {}
    upc_fields = list(cfg.get("upc_fields") or [])
    known_actions = {str(a) for a in (cfg.get("known_actions") or [])}
    unknown_policy = str(cfg.get("unknown_action_policy") or "warn")
    if strict_unknown_actions:
        unknown_policy = "error"

    for idx, item in enumerate(items):
        base = f"$.results[{idx}]" if isinstance(payload, dict) else f"$[{idx}]"

        for field in required:
            if field not in item or item.get(field) in (None, ""):
                errors.append(
                    ContractViolation(
                        path=f"{base}.{field}",
                        rule="required",
                        message=f"Missing required field {field!r}",
                    )
                )

        for field, allowed in field_types.items():
            if field not in item:
                continue
            if not _type_ok(item.get(field), allowed):
                errors.append(
                    ContractViolation(
                        path=f"{base}.{field}",
                        rule="type",
                        message=f"Field {field!r} type invalid; allowed={allowed} actual={type(item.get(field)).__name__}",
                    )
                )

        # UPC presence soft/hard: if product_id set, need a upc-like field
        if item.get("product_id") not in (None, ""):
            upc_ok = False
            for uf in upc_fields:
                val = item.get(uf)
                if isinstance(val, str) and val.strip():
                    upc_ok = True
                    break
            if not upc_ok:
                errors.append(
                    ContractViolation(
                        path=base,
                        rule="upc",
                        message="product_id present but displayed_upc/upc missing or empty",
                    )
                )

        action = item.get("action")
        if isinstance(action, str) and action and known_actions and action not in known_actions:
            sev = "error" if unknown_policy == "error" else "warning"
            viol = ContractViolation(
                path=f"{base}.action",
                rule="known_action",
                message=f"Unknown action token {action!r}",
                severity=sev,
            )
            (errors if sev == "error" else warnings).append(viol)

        for pos_key in ("current_position", "expected_position"):
            pos = item.get(pos_key)
            if pos is None:
                continue
            if not isinstance(pos, dict):
                errors.append(
                    ContractViolation(
                        path=f"{base}.{pos_key}",
                        rule="type",
                        message=f"{pos_key} must be object or null",
                    )
                )

    ok = len(errors) == 0
    return ContractReport(
        ok=ok,
        endpoint=endpoint,
        item_count=len(items),
        errors=errors,
        warnings=warnings,
    )
