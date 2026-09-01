"""Gate B — Live merge/nightly smoke against https://{env}.rebotics.net."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from regression.action_list import ActionListError, fetch_action_list_retailer
from regression.auth import (
    AuthCredentials,
    AuthCredentialsMissing,
    AuthSmokeError,
    load_credentials,
    run_auth_smoke,
    _http_json,
)
from regression.contracts import assert_action_list_contract, extract_action_items
from regression.domain_parity import (
    android_normalize_counts,
    count_domain_types,
    transform_via_interim_mapper,
)
from regression.env import EnvironmentResolutionError, resolve_base_url
from regression.provisioner import ProvisionerError, _auth_headers, _login_token, run_provision
from regression.tools import invoke_tool


class GateBError(Exception):
    def __init__(self, message: str, *, exit_code: int = 1):
        super().__init__(message)
        self.exit_code = exit_code


@dataclass
class GateBStep:
    name: str
    ok: bool
    exit_code: int
    detail: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GateBReport:
    ok: bool
    exit_code: int
    env: str
    base_url: str
    gate: str
    task_id: Optional[int]
    steps: List[GateBStep]
    generated_at: str
    mutate_executed: bool = False
    notes: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "exit_code": self.exit_code,
            "env": self.env,
            "base_url": self.base_url,
            "gate": self.gate,
            "task_id": self.task_id,
            "mutate_executed": self.mutate_executed,
            "steps": [s.as_dict() for s in self.steps],
            "notes": self.notes,
            "generated_at": self.generated_at,
            "verdict_policy": "PASS/FAIL from Gate B steps only; GenAI must not override",
        }


def _env_int(name: str) -> Optional[int]:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return None
    return int(raw)


def list_recent_tasks(
    base_url: str,
    token: str,
    *,
    limit: int = 50,
    search: Optional[str] = None,
) -> List[Dict[str, Any]]:
    qs = f"limit={limit}&ordering=-id"
    if search:
        qs += f"&search={search}"
    status, payload, _ = _http_json(
        "GET",
        f"{base_url}/api/v1/tasks/?{qs}",
        headers=_auth_headers(token),
    )
    if status >= 400:
        raise GateBError(f"Task list failed HTTP {status}: {payload}", exit_code=2)
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        raise GateBError("Unexpected tasks list envelope", exit_code=2)
    return [r for r in results if isinstance(r, dict)]


def discover_ir_task_id(
    base_url: str,
    token: str,
    *,
    preferred_task_id: Optional[int] = None,
    search_terms: Sequence[str] = ("Intelligent Reset",),
) -> tuple[int, str]:
    """
    Resolve a live task id for Gate B.
    Preference: explicit id → type name Intelligent Reset with actions → any IR type.
    """
    if preferred_task_id is not None:
        return preferred_task_id, "env_or_arg"

    # Prefer Intelligent Reset by search
    candidates: List[Dict[str, Any]] = []
    for term in search_terms:
        try:
            candidates.extend(list_recent_tasks(base_url, token, limit=40, search=term))
        except GateBError:
            continue

    # De-dupe by id preserving order
    seen = set()
    ordered: List[Dict[str, Any]] = []
    for t in candidates:
        tid = t.get("id")
        if tid in seen:
            continue
        seen.add(tid)
        ordered.append(t)

    ir_named = [
        t
        for t in ordered
        if "intelligent reset" in str((t.get("type") or {}).get("name") or "").lower()
    ]
    pool = ir_named or ordered

    for t in pool:
        tid = int(t["id"])
        try:
            _st, payload, _url = fetch_action_list_retailer(base_url, token, tid)
            items = extract_action_items(payload)
        except (ActionListError, Exception):
            continue
        if items:
            return tid, f"discovered_with_actions:{t.get('type')}"

    # Fall back: first IR-named task even if empty actions (still validates fetch path)
    if ir_named:
        return int(ir_named[0]["id"]), "discovered_ir_maybe_empty"

    raise GateBError(
        "No live Intelligent Reset task found. Set REGRESSION_TASK_ID.",
        exit_code=2,
    )


def run_gate_b(
    *,
    env: str = "epsilon",
    base_url_override: Optional[str] = None,
    task_id: Optional[int] = None,
    credentials: Optional[AuthCredentials] = None,
    execute_provision: bool = False,
    category: str = "pasta",
    bays: Optional[Sequence[int]] = None,
    store_id: Optional[int] = None,
    pog_id: Optional[int] = None,
    category_id: Optional[int] = None,
) -> GateBReport:
    """
    Gate B live smoke:
      1. resolve_env
      2. auth_smoke (required)
      3. discover IR task (or REGRESSION_TASK_ID / --task-id)
      4. action-list fetch + contract
      5. domain mapper transform (report counts; no CAT1 fixture assert)
      6. provision dry-run (always); optional --execute with store/pog ids
    """
    notes: List[str] = []
    steps: List[GateBStep] = []
    bays = list(bays or [1])
    preferred = task_id if task_id is not None else _env_int("REGRESSION_TASK_ID")
    store_id = store_id if store_id is not None else _env_int("REGRESSION_STORE_ID")
    pog_id = pog_id if pog_id is not None else _env_int("REGRESSION_POG_ID")
    category_id = category_id if category_id is not None else _env_int("REGRESSION_CATEGORY_ID")

    try:
        resolved = resolve_base_url(env, base_url_override=base_url_override)
    except EnvironmentResolutionError as exc:
        raise GateBError(str(exc), exit_code=2) from exc

    # 1. resolve_env via tools (stable JSON)
    env_resp = invoke_tool(
        "resolve_env",
        {"env": env, "base_url": base_url_override},
    )
    steps.append(
        GateBStep(
            name="resolve_env",
            ok=env_resp.ok,
            exit_code=env_resp.exit_code,
            detail=env_resp.result or {},
            error=env_resp.error,
        )
    )

    # 2. auth (required)
    try:
        creds = credentials or load_credentials()
        auth = run_auth_smoke(
            env, base_url_override=base_url_override, credentials=creds
        )
        steps.append(
            GateBStep(
                name="auth_smoke",
                ok=bool(auth.ok),
                exit_code=0 if auth.ok else 1,
                detail={
                    "user_id": auth.user_id,
                    "username": auth.username,
                    "me_status": auth.me_status,
                },
                error=auth.error,
            )
        )
    except AuthCredentialsMissing as exc:
        steps.append(
            GateBStep(
                name="auth_smoke",
                ok=False,
                exit_code=2,
                error=str(exc),
            )
        )
        return _finalize(env, resolved.base_url, None, steps, notes, False)
    except AuthSmokeError as exc:
        steps.append(
            GateBStep(
                name="auth_smoke",
                ok=False,
                exit_code=getattr(exc, "exit_code", 1),
                error=str(exc),
            )
        )
        return _finalize(env, resolved.base_url, None, steps, notes, False)

    base_url, token = _login_token(
        env, base_url_override=base_url_override, credentials=creds
    )

    # 3. discover task
    try:
        tid, how = discover_ir_task_id(
            base_url, token, preferred_task_id=preferred
        )
        notes.append(f"task_source={how}")
        steps.append(
            GateBStep(
                name="discover_task",
                ok=True,
                exit_code=0,
                detail={"task_id": tid, "source": how},
            )
        )
    except GateBError as exc:
        steps.append(
            GateBStep(
                name="discover_task",
                ok=False,
                exit_code=exc.exit_code,
                error=str(exc),
            )
        )
        return _finalize(env, resolved.base_url, None, steps, notes, False)

    # 4. action-list + contract
    try:
        http_status, payload, url = fetch_action_list_retailer(base_url, token, tid)
        items = extract_action_items(payload)
        contract = assert_action_list_contract(payload)
        steps.append(
            GateBStep(
                name="action_list_live",
                ok=bool(contract.ok),
                exit_code=0 if contract.ok else 1,
                detail={
                    "task_id": tid,
                    "url": url,
                    "http_status": http_status,
                    "item_count": len(items),
                    "contract_errors": len(contract.errors),
                    "contract_warnings": len(contract.warnings),
                },
                error=None
                if contract.ok
                else f"{len(contract.errors)} contract error(s)",
            )
        )
    except (ActionListError, Exception) as exc:
        steps.append(
            GateBStep(
                name="action_list_live",
                ok=False,
                exit_code=getattr(exc, "exit_code", 1),
                error=str(exc),
            )
        )
        return _finalize(env, resolved.base_url, tid, steps, notes, False)

    # 5. domain transform (live report — not CAT1 fixture assert)
    try:
        domain = transform_via_interim_mapper(items)
        by_type = count_domain_types(domain)
        steps.append(
            GateBStep(
                name="domain_transform_live",
                ok=True,
                exit_code=0,
                detail={
                    "raw_item_count": len(items),
                    "domain_card_count": len(domain),
                    "counts_by_type": by_type,
                    "counts_android_normalized": android_normalize_counts(by_type),
                },
            )
        )
        if len(items) > 0 and len(domain) == 0:
            notes.append(
                "raw_actions_present_but_domain_empty (often all STATE_ACCEPTED)"
            )
    except Exception as exc:  # noqa: BLE001
        steps.append(
            GateBStep(
                name="domain_transform_live",
                ok=False,
                exit_code=1,
                error=str(exc),
            )
        )

    # 6. provision dry-run always
    try:
        prov = run_provision(
            env=env,
            category=category,
            bays=bays,
            dry_run=True,
            base_url_override=base_url_override,
        )
        steps.append(
            GateBStep(
                name="provision_dry_run",
                ok=bool(prov.ok),
                exit_code=0 if prov.ok else 1,
                detail={"dry_run": True, "scans": len(prov.plan.scans)},
            )
        )
    except (ProvisionerError, Exception) as exc:
        steps.append(
            GateBStep(
                name="provision_dry_run",
                ok=False,
                exit_code=getattr(exc, "exit_code", 1),
                error=str(exc),
            )
        )

    mutate_executed = False
    if execute_provision:
        if store_id is None or pog_id is None:
            steps.append(
                GateBStep(
                    name="provision_execute",
                    ok=False,
                    exit_code=2,
                    error="--execute requires --store-id/--pog-id (or REGRESSION_STORE_ID/POG_ID)",
                )
            )
        else:
            try:
                prov_ex = run_provision(
                    env=env,
                    category=category,
                    bays=bays,
                    dry_run=False,
                    store_id=store_id,
                    pog_id=pog_id,
                    task_id=tid,
                    category_id=category_id,
                    base_url_override=base_url_override,
                    credentials=creds,
                )
                mutate_executed = True
                steps.append(
                    GateBStep(
                        name="provision_execute",
                        ok=bool(prov_ex.ok),
                        exit_code=0 if prov_ex.ok else 1,
                        detail={
                            "task_id": prov_ex.task_id,
                            "uploads": len(prov_ex.uploads or []),
                        },
                    )
                )
            except (ProvisionerError, Exception) as exc:
                steps.append(
                    GateBStep(
                        name="provision_execute",
                        ok=False,
                        exit_code=getattr(exc, "exit_code", 1),
                        error=str(exc),
                    )
                )

    return _finalize(env, resolved.base_url, tid, steps, notes, mutate_executed)


def _finalize(
    env: str,
    base_url: str,
    task_id: Optional[int],
    steps: List[GateBStep],
    notes: List[str],
    mutate_executed: bool,
) -> GateBReport:
    all_ok = all(s.ok for s in steps)
    worst = 0
    for s in steps:
        if not s.ok:
            worst = max(worst, s.exit_code or 1)
    return GateBReport(
        ok=all_ok,
        exit_code=0 if all_ok else (worst or 1),
        env=env,
        base_url=base_url,
        gate="B",
        task_id=task_id,
        steps=steps,
        generated_at=datetime.now(timezone.utc).isoformat(),
        mutate_executed=mutate_executed,
        notes=notes,
    )
