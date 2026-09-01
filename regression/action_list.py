"""Slice 4 — Fetch action-list and assert contract."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from regression.auth import AuthCredentials, load_credentials, _http_json
from regression.contracts import (
    ContractError,
    ContractReport,
    assert_action_list_contract,
    extract_action_items,
    load_contract,
)
from regression.env import resolve_base_url
from regression.provisioner import _auth_headers, _login_token


class ActionListError(Exception):
    def __init__(self, message: str, *, exit_code: int = 1):
        super().__init__(message)
        self.exit_code = exit_code


@dataclass
class ActionListResult:
    ok: bool
    env: str
    base_url: str
    task_id: int
    url: str
    http_status: int
    item_count: int
    contract: Dict[str, Any]
    sample_actions: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _is_action_list_payload(payload: Any) -> bool:
    if isinstance(payload, list):
        return True
    if isinstance(payload, dict) and "_raw" in payload and len(payload) == 1:
        return False  # HTML/non-JSON body from SPA catch-all
    if isinstance(payload, dict) and isinstance(payload.get("results"), list):
        return True
    if isinstance(payload, dict) and "id" in payload and "action" in payload:
        return True
    return False


def fetch_action_list_retailer(
    base_url: str,
    token: str,
    task_id: int,
    *,
    limit: int = 1000,
) -> tuple[int, Any, str]:
    url = f"{base_url}/api/v1/tasks/{task_id}/action-list/retailer/?limit={limit}"
    status, payload, _raw = _http_json("GET", url, headers=_auth_headers(token))
    if status < 400 and _is_action_list_payload(payload):
        return status, payload, url

    # Some tenants expose the same resource under v4; only accept real JSON envelopes.
    alt = f"{base_url}/api/v4/tasks/{task_id}/action-list/retailer/?limit={limit}"
    status2, payload2, _raw2 = _http_json("GET", alt, headers=_auth_headers(token))
    if status2 < 400 and _is_action_list_payload(payload2):
        return status2, payload2, alt

    raise ActionListError(
        f"Action-list fetch failed HTTP {status}: {payload}",
        exit_code=1,
    )


def run_action_list_check(
    *,
    env: str,
    task_id: int,
    base_url_override: Optional[str] = None,
    credentials: Optional[AuthCredentials] = None,
    payload_override: Any = None,
    strict_unknown_actions: bool = False,
    contract_path: Optional[Path] = None,
) -> ActionListResult:
    """
    Fetch (or accept override payload) and run contract asserts.
    payload_override is for offline unit tests.
    """
    resolved = resolve_base_url(env, base_url_override=base_url_override)
    url = f"{resolved.base_url}/api/v1/tasks/{task_id}/action-list/retailer/?limit=1000"
    http_status = 200
    payload: Any

    if payload_override is not None:
        payload = payload_override
    else:
        creds = credentials or load_credentials()
        base_url, token = _login_token(
            env, base_url_override=base_url_override, credentials=creds
        )
        http_status, payload, url = fetch_action_list_retailer(base_url, token, task_id)

    try:
        contract_cfg = load_contract(contract_path) if contract_path else load_contract()
        report: ContractReport = assert_action_list_contract(
            payload,
            contract=contract_cfg,
            strict_unknown_actions=strict_unknown_actions,
        )
        try:
            items = extract_action_items(payload)
        except ContractError:
            items = []
        samples = [
            it["action"]
            for it in items[:5]
            if isinstance(it.get("action"), str)
        ]
        return ActionListResult(
            ok=report.ok,
            env=resolved.env,
            base_url=resolved.base_url,
            task_id=task_id,
            url=url,
            http_status=http_status,
            item_count=report.item_count,
            contract=report.as_dict(),
            sample_actions=samples,
            error=None if report.ok else f"{len(report.errors)} contract error(s)",
        )
    except ContractError as exc:
        return ActionListResult(
            ok=False,
            env=resolved.env,
            base_url=resolved.base_url,
            task_id=task_id,
            url=url,
            http_status=http_status,
            item_count=0,
            contract={"ok": False, "errors": [{"message": str(exc)}]},
            error=str(exc),
        )
