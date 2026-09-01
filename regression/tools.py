"""Slice 6 — Regression agent tools JSON API (GenAI-first G1).

Stable machine I/O for the control plane. Tools wrap judgement-plane modules;
PASS/FAIL comes only from tool results (never from GenAI).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from regression.action_list import ActionListError, run_action_list_check
from regression.auth import (
    AuthCredentialsMissing,
    AuthSmokeError,
    load_credentials,
    run_auth_smoke,
    skipped_result,
)
from regression.domain_parity import DomainParityError, run_domain_parity
from regression.env import EnvironmentResolutionError, resolve_base_url
from regression.image_catalog import ImageCatalog, ImageCatalogError
from regression.provisioner import ProvisionerError, run_provision

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_API_VERSION = "1"


class ToolError(Exception):
    def __init__(self, message: str, *, exit_code: int = 1):
        super().__init__(message)
        self.exit_code = exit_code


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: Dict[str, Any]
    mutates: bool = False
    judgement: bool = True  # contributes to PASS/FAIL when ok=false


@dataclass
class ToolResponse:
    ok: bool
    tool: str
    exit_code: int
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    api_version: str = TOOLS_API_VERSION

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


Handler = Callable[[Dict[str, Any]], ToolResponse]


def _require(args: Dict[str, Any], *keys: str) -> None:
    missing = [k for k in keys if args.get(k) in (None, "")]
    if missing:
        raise ToolError(f"Missing required args: {', '.join(missing)}", exit_code=2)


def _tool_resolve_env(args: Dict[str, Any]) -> ToolResponse:
    _require(args, "env")
    try:
        resolved = resolve_base_url(
            str(args["env"]),
            base_url_override=args.get("base_url"),
            allow_mutate=bool(args.get("allow_mutate", False)),
        )
    except EnvironmentResolutionError as exc:
        return ToolResponse(ok=False, tool="resolve_env", exit_code=2, error=str(exc))
    return ToolResponse(
        ok=True,
        tool="resolve_env",
        exit_code=0,
        result={
            "env": resolved.env,
            "base_url": resolved.base_url,
            "mutate_allowed": resolved.mutate_allowed,
            "source": resolved.source,
        },
    )


def _tool_resolve_images(args: Dict[str, Any]) -> ToolResponse:
    _require(args, "category")
    bays_raw = args.get("bays", [1])
    if isinstance(bays_raw, str):
        bays = [int(x) for x in bays_raw.split(",") if x.strip()]
    else:
        bays = [int(x) for x in bays_raw]
    try:
        catalog = ImageCatalog.load(
            Path(args["catalog"]) if args.get("catalog") else None,
            repo_root=REPO_ROOT,
        )
        resolutions = catalog.resolve_bays(
            category=str(args["category"]),
            bays=bays,
            stage=str(args.get("stage") or "pre_photo"),
            require_file_exists=not bool(args.get("allow_missing_files", False)),
        )
    except (ImageCatalogError, ValueError, TypeError) as exc:
        return ToolResponse(ok=False, tool="resolve_images", exit_code=2, error=str(exc))
    return ToolResponse(
        ok=True,
        tool="resolve_images",
        exit_code=0,
        result={
            "category": args["category"],
            "stage": args.get("stage") or "pre_photo",
            "images": [r.entry.as_dict() for r in resolutions],
        },
    )


def _tool_auth_smoke(args: Dict[str, Any]) -> ToolResponse:
    _require(args, "env")
    env = str(args["env"])
    if args.get("skip_if_no_creds"):
        try:
            load_credentials(
                username=args.get("username"),
                password=args.get("password"),
            )
        except AuthCredentialsMissing as exc:
            resolved = resolve_base_url(env, base_url_override=args.get("base_url"))
            result = skipped_result(resolved.env, str(exc), base_url=resolved.base_url)
            return ToolResponse(
                ok=True, tool="auth_smoke", exit_code=0, result=result.as_dict()
            )
    try:
        result = run_auth_smoke(
            env,
            base_url_override=args.get("base_url"),
            credentials=load_credentials(
                username=args.get("username"),
                password=args.get("password"),
            ),
            allow_mutate=bool(args.get("allow_mutate", False)),
        )
    except AuthCredentialsMissing as exc:
        return ToolResponse(ok=False, tool="auth_smoke", exit_code=2, error=str(exc))
    except (AuthSmokeError, EnvironmentResolutionError) as exc:
        return ToolResponse(
            ok=False,
            tool="auth_smoke",
            exit_code=getattr(exc, "exit_code", 1),
            error=str(exc),
        )
    ok = bool(result.ok or result.skipped)
    return ToolResponse(
        ok=ok,
        tool="auth_smoke",
        exit_code=0 if ok else 1,
        result=result.as_dict(),
    )


def _tool_provision(args: Dict[str, Any]) -> ToolResponse:
    _require(args, "env", "category")
    bays_raw = args.get("bays", [1])
    if isinstance(bays_raw, str):
        bays = [int(x) for x in bays_raw.split(",") if x.strip()]
    else:
        bays = [int(x) for x in (bays_raw or [1])]
    execute = bool(args.get("execute", False))
    try:
        result = run_provision(
            env=str(args["env"]),
            category=str(args["category"]),
            bays=bays,
            stage=str(args.get("stage") or "pre_photo"),
            store_id=args.get("store_id"),
            task_id=args.get("task_id"),
            pog_id=args.get("pog_id"),
            category_id=args.get("category_id"),
            category_name=args.get("category_name"),
            base_url_override=args.get("base_url"),
            dry_run=not execute,
        )
    except (ProvisionerError, ImageCatalogError, AuthCredentialsMissing) as exc:
        return ToolResponse(
            ok=False,
            tool="provision",
            exit_code=getattr(exc, "exit_code", 2),
            error=str(exc),
        )
    return ToolResponse(
        ok=bool(result.ok),
        tool="provision",
        exit_code=0 if result.ok else 1,
        result=result.as_dict(),
    )


def _load_fixture(path: Optional[str]) -> Any:
    if not path:
        return None
    p = Path(path)
    if not p.is_file():
        raise ToolError(f"Fixture not found: {p}", exit_code=2)
    return json.loads(p.read_text(encoding="utf-8"))


def _tool_action_list(args: Dict[str, Any]) -> ToolResponse:
    _require(args, "env", "task_id")
    try:
        payload_override = _load_fixture(args.get("fixture"))
        result = run_action_list_check(
            env=str(args["env"]),
            task_id=int(args["task_id"]),
            base_url_override=args.get("base_url"),
            credentials=(
                None
                if payload_override is not None
                else load_credentials(
                    username=args.get("username"),
                    password=args.get("password"),
                )
            ),
            payload_override=payload_override,
            strict_unknown_actions=bool(args.get("strict_unknown_actions", False)),
            contract_path=Path(args["contract"]) if args.get("contract") else None,
        )
    except (ToolError, AuthCredentialsMissing) as exc:
        return ToolResponse(
            ok=False,
            tool="action_list",
            exit_code=getattr(exc, "exit_code", 2),
            error=str(exc),
        )
    except (ActionListError, EnvironmentResolutionError) as exc:
        return ToolResponse(
            ok=False,
            tool="action_list",
            exit_code=getattr(exc, "exit_code", 1),
            error=str(exc),
        )
    return ToolResponse(
        ok=bool(result.ok),
        tool="action_list",
        exit_code=0 if result.ok else 1,
        result=result.as_dict(),
    )


def _tool_domain_parity(args: Dict[str, Any]) -> ToolResponse:
    _require(args, "env")
    try:
        payload_override = _load_fixture(args.get("fixture"))
        task_id = args.get("task_id")
        result = run_domain_parity(
            env=str(args["env"]),
            task_id=int(task_id) if task_id is not None else None,
            base_url_override=args.get("base_url"),
            credentials=(
                None
                if payload_override is not None or task_id is None
                else load_credentials(
                    username=args.get("username"),
                    password=args.get("password"),
                )
            ),
            payload_override=payload_override,
            case=str(args.get("case") or "cat1_t5_mixed"),
            baseline_path=Path(args["baseline"]) if args.get("baseline") else None,
            include_completed=bool(args.get("include_completed", False)),
        )
    except (ToolError, AuthCredentialsMissing, DomainParityError) as exc:
        return ToolResponse(
            ok=False,
            tool="domain_parity",
            exit_code=getattr(exc, "exit_code", 2),
            error=str(exc),
        )
    except EnvironmentResolutionError as exc:
        return ToolResponse(ok=False, tool="domain_parity", exit_code=2, error=str(exc))
    return ToolResponse(
        ok=bool(result.ok),
        tool="domain_parity",
        exit_code=0 if result.ok else 1,
        result=result.as_dict(),
    )


def _tool_health(_args: Dict[str, Any]) -> ToolResponse:
    specs = list_tool_specs()
    return ToolResponse(
        ok=True,
        tool="health",
        exit_code=0,
        result={
            "status": "ok",
            "api_version": TOOLS_API_VERSION,
            "tool_count": len(specs),
            "tools": [s.name for s in specs],
            "verdict_policy": "PASS/FAIL only from tool ok/exit_code; GenAI must not override",
        },
    )


_TOOL_HANDLERS: Dict[str, Handler] = {
    "health": _tool_health,
    "resolve_env": _tool_resolve_env,
    "resolve_images": _tool_resolve_images,
    "auth_smoke": _tool_auth_smoke,
    "provision": _tool_provision,
    "action_list": _tool_action_list,
    "domain_parity": _tool_domain_parity,
}


def list_tool_specs() -> List[ToolSpec]:
    return [
        ToolSpec(
            name="health",
            description="API health + tool inventory",
            parameters={"type": "object", "properties": {}, "additionalProperties": False},
            judgement=False,
        ),
        ToolSpec(
            name="resolve_env",
            description="Resolve --env slug to https://{env}.rebotics.net",
            parameters={
                "type": "object",
                "required": ["env"],
                "properties": {
                    "env": {"type": "string"},
                    "base_url": {"type": ["string", "null"]},
                    "allow_mutate": {"type": "boolean", "default": False},
                },
            },
        ),
        ToolSpec(
            name="resolve_images",
            description="Resolve planogram-category scan images from catalog",
            parameters={
                "type": "object",
                "required": ["category"],
                "properties": {
                    "category": {"type": "string"},
                    "bays": {
                        "oneOf": [
                            {"type": "array", "items": {"type": "integer"}},
                            {"type": "string"},
                        ],
                        "default": [1],
                    },
                    "stage": {"type": "string", "default": "pre_photo"},
                    "catalog": {"type": ["string", "null"]},
                    "allow_missing_files": {"type": "boolean", "default": False},
                },
            },
        ),
        ToolSpec(
            name="auth_smoke",
            description="Login + /api/v4/me/ smoke",
            parameters={
                "type": "object",
                "required": ["env"],
                "properties": {
                    "env": {"type": "string"},
                    "base_url": {"type": ["string", "null"]},
                    "username": {"type": ["string", "null"]},
                    "password": {"type": ["string", "null"]},
                    "skip_if_no_creds": {"type": "boolean", "default": False},
                    "allow_mutate": {"type": "boolean", "default": False},
                },
            },
        ),
        ToolSpec(
            name="provision",
            description="Plan/execute IR provision with catalog images (dry-run default)",
            parameters={
                "type": "object",
                "required": ["env", "category"],
                "properties": {
                    "env": {"type": "string"},
                    "category": {"type": "string"},
                    "bays": {
                        "oneOf": [
                            {"type": "array", "items": {"type": "integer"}},
                            {"type": "string"},
                        ],
                        "default": [1],
                    },
                    "stage": {"type": "string", "default": "pre_photo"},
                    "store_id": {"type": ["integer", "null"]},
                    "task_id": {"type": ["integer", "null"]},
                    "pog_id": {"type": ["integer", "null"]},
                    "category_id": {"type": ["integer", "null"]},
                    "category_name": {"type": ["string", "null"]},
                    "base_url": {"type": ["string", "null"]},
                    "execute": {"type": "boolean", "default": False},
                },
            },
            mutates=True,
        ),
        ToolSpec(
            name="action_list",
            description="Fetch retailer action-list and assert contract",
            parameters={
                "type": "object",
                "required": ["env", "task_id"],
                "properties": {
                    "env": {"type": "string"},
                    "task_id": {"type": "integer"},
                    "base_url": {"type": ["string", "null"]},
                    "username": {"type": ["string", "null"]},
                    "password": {"type": ["string", "null"]},
                    "fixture": {"type": ["string", "null"]},
                    "contract": {"type": ["string", "null"]},
                    "strict_unknown_actions": {"type": "boolean", "default": False},
                },
            },
        ),
        ToolSpec(
            name="domain_parity",
            description="Android CAT1-locked domain count parity via interim mapper",
            parameters={
                "type": "object",
                "required": ["env"],
                "properties": {
                    "env": {"type": "string"},
                    "task_id": {"type": ["integer", "null"]},
                    "base_url": {"type": ["string", "null"]},
                    "username": {"type": ["string", "null"]},
                    "password": {"type": ["string", "null"]},
                    "fixture": {"type": ["string", "null"]},
                    "case": {"type": "string", "default": "cat1_t5_mixed"},
                    "baseline": {"type": ["string", "null"]},
                    "include_completed": {"type": "boolean", "default": False},
                },
            },
        ),
    ]


def list_tools_payload() -> Dict[str, Any]:
    return {
        "api_version": TOOLS_API_VERSION,
        "verdict_policy": "PASS/FAIL only from tool ok/exit_code; GenAI must not override",
        "tools": [asdict(s) for s in list_tool_specs()],
    }


def invoke_tool(name: str, args: Optional[Dict[str, Any]] = None) -> ToolResponse:
    key = (name or "").strip()
    handler = _TOOL_HANDLERS.get(key)
    if handler is None:
        return ToolResponse(
            ok=False,
            tool=key or "unknown",
            exit_code=2,
            error=f"Unknown tool: {key!r}. Use list_tools / GET /v1/tools",
        )
    try:
        return handler(dict(args or {}))
    except ToolError as exc:
        return ToolResponse(
            ok=False, tool=key, exit_code=exc.exit_code, error=str(exc)
        )
    except Exception as exc:  # noqa: BLE001 — surface framework errors as exit 3
        return ToolResponse(
            ok=False,
            tool=key,
            exit_code=3,
            error=f"Framework error: {exc}",
        )
