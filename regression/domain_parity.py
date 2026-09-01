"""Slice 5 — Mobile domain count parity (Android CAT1-locked).

Uses the interim MBIT Python ActionListDomainMapper. Expected counts come from
Android ActionListDomainMapperTest (not from re-deriving business rules here).
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from regression.action_list import ActionListError, fetch_action_list_retailer
from regression.auth import AuthCredentials, AuthCredentialsMissing, load_credentials
from regression.contracts import extract_action_items
from regression.env import resolve_base_url
from regression.provisioner import _login_token

REPO_ROOT = Path(__file__).resolve().parents[1]
MBIT_ROOT = REPO_ROOT / "mobile-backend-integration-tests"
DEFAULT_BASELINE = (
    REPO_ROOT / "docs" / "regression" / "baselines" / "domain_count_parity.yaml"
)


class DomainParityError(Exception):
    def __init__(self, message: str, *, exit_code: int = 1):
        super().__init__(message)
        self.exit_code = exit_code


@dataclass
class DomainParityResult:
    ok: bool
    env: str
    base_url: str
    task_id: Optional[int]
    source: str
    mapper: str
    raw_item_count: int
    domain_card_count: int
    counts_by_type: Dict[str, int]
    counts_by_type_android_normalized: Dict[str, int]
    expected_domain_total: Optional[int]
    expected_by_type: Dict[str, int]
    mismatches: List[str] = field(default_factory=list)
    sample_cards: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    interim_note: str = (
        "Python MBIT mapper is interim; Android CAT1 counts are the parity source of truth."
    )

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _ensure_mbit_on_path() -> None:
    path = str(MBIT_ROOT)
    if path not in sys.path:
        sys.path.insert(0, path)


def transform_via_interim_mapper(
    raw_items: List[Dict[str, Any]],
    *,
    include_completed: bool = False,
) -> List[Any]:
    _ensure_mbit_on_path()
    from core.action_list_domain_mapper import transform_action_list_to_domain

    return list(
        transform_action_list_to_domain(raw_items, include_completed=include_completed)
    )


def load_parity_baseline(path: Optional[Path] = None) -> Dict[str, Any]:
    p = path or DEFAULT_BASELINE
    if not p.is_file():
        raise DomainParityError(f"Domain parity baseline not found: {p}", exit_code=2)
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def android_normalize_counts(
    counts: Dict[str, int],
    normalize_map: Optional[Dict[str, str]] = None,
) -> Dict[str, int]:
    mapping = normalize_map or {"Restock": "AddItems"}
    out: Counter[str] = Counter()
    for name, n in counts.items():
        out[mapping.get(name, name)] += int(n)
    return dict(out)


def count_domain_types(domain_models: List[Any]) -> Dict[str, int]:
    return dict(Counter(getattr(m, "action_type", "?") for m in domain_models))


def assert_count_parity(
    domain_models: List[Any],
    *,
    expected_domain_total: int,
    expected_by_type: Dict[str, int],
    normalize_map: Optional[Dict[str, str]] = None,
) -> List[str]:
    mismatches: List[str] = []
    actual_total = len(domain_models)
    if actual_total != expected_domain_total:
        mismatches.append(
            f"domain_total expected={expected_domain_total} actual={actual_total}"
        )
    actual_norm = android_normalize_counts(
        count_domain_types(domain_models), normalize_map
    )
    for typ, expected_n in expected_by_type.items():
        actual_n = int(actual_norm.get(typ, 0))
        if actual_n != int(expected_n):
            mismatches.append(f"type {typ!r} expected={expected_n} actual={actual_n}")
    for typ, actual_n in actual_norm.items():
        if typ not in expected_by_type and actual_n:
            mismatches.append(f"unexpected type {typ!r} count={actual_n}")
    return mismatches


def run_domain_parity(
    *,
    env: str,
    task_id: Optional[int] = None,
    base_url_override: Optional[str] = None,
    credentials: Optional[AuthCredentials] = None,
    payload_override: Any = None,
    case: str = "cat1_t5_mixed",
    baseline_path: Optional[Path] = None,
    include_completed: bool = False,
) -> DomainParityResult:
    resolved = resolve_base_url(env, base_url_override=base_url_override)
    baseline = load_parity_baseline(baseline_path)
    cases = baseline.get("cases") or {}
    case_cfg = cases.get(case) or {}
    normalize_map = dict(baseline.get("android_normalize") or {"Restock": "AddItems"})

    if payload_override is not None:
        payload = payload_override
        source = "fixture"
        tid = task_id
    elif task_id is not None:
        try:
            creds = credentials or load_credentials()
            base_url, token = _login_token(
                env, base_url_override=base_url_override, credentials=creds
            )
            _status, payload, _url = fetch_action_list_retailer(base_url, token, task_id)
        except (ActionListError, AuthCredentialsMissing) as exc:
            raise DomainParityError(str(exc), exit_code=getattr(exc, "exit_code", 1)) from exc
        source = "live"
        tid = task_id
    else:
        fixture_rel = case_cfg.get("fixture")
        if not fixture_rel:
            raise DomainParityError(
                "Provide --task-id, --fixture, or a baseline case with fixture",
                exit_code=2,
            )
        fixture_path = REPO_ROOT / str(fixture_rel)
        if not fixture_path.is_file():
            raise DomainParityError(f"Case fixture not found: {fixture_path}", exit_code=2)
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        source = f"baseline_case:{case}"
        tid = task_id

    raw_items = extract_action_items(payload)
    domain_models = transform_via_interim_mapper(
        raw_items, include_completed=include_completed
    )
    by_type = count_domain_types(domain_models)
    by_type_norm = android_normalize_counts(by_type, normalize_map)

    expected_total = case_cfg.get("expected_domain_total")
    expected_by_type = dict(case_cfg.get("expected_by_type") or {})

    # Live arbitrary tasks: report counts only (do not assert CAT1 fixture expectations).
    should_assert = (
        expected_total is not None
        and bool(expected_by_type)
        and source != "live"
    )
    mismatches: List[str] = []
    if should_assert:
        mismatches = assert_count_parity(
            domain_models,
            expected_domain_total=int(expected_total),
            expected_by_type=expected_by_type,
            normalize_map=normalize_map,
        )
    else:
        expected_total = None if source == "live" else expected_total
        if source == "live":
            expected_by_type = {}

    samples = [
        {
            "id": getattr(m, "id", None),
            "action_type": getattr(m, "action_type", None),
            "step_subtype": getattr(m, "step_subtype", None),
            "upc": getattr(m, "upc", None),
        }
        for m in domain_models[:8]
    ]

    ok = len(mismatches) == 0
    return DomainParityResult(
        ok=ok,
        env=resolved.env,
        base_url=resolved.base_url,
        task_id=tid,
        source=source,
        mapper=str(baseline.get("mapper") or "interim_python_mbit"),
        raw_item_count=len(raw_items),
        domain_card_count=len(domain_models),
        counts_by_type=by_type,
        counts_by_type_android_normalized=by_type_norm,
        expected_domain_total=int(expected_total) if expected_total is not None else None,
        expected_by_type=expected_by_type,
        mismatches=mismatches,
        sample_cards=samples,
        error=None if ok else f"{len(mismatches)} count parity mismatch(es)",
    )
