"""Gate C — Release pack: unified PASS/FAIL artifact for dashboard."""

from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from regression.gate_b import GateBError, run_gate_b
from regression.pr_bot import run_pr_bot
from regression.tools import invoke_tool

REPO_ROOT = Path(__file__).resolve().parents[1]


class GateCError(Exception):
    def __init__(self, message: str, *, exit_code: int = 1):
        super().__init__(message)
        self.exit_code = exit_code


@dataclass
class LayerResult:
    name: str
    status: str  # passed | failed | skipped
    exit_code: int
    detail: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GateCReport:
    ok: bool
    exit_code: int
    gate: str
    env: str
    layers: List[LayerResult]
    started_at: str
    finished_at: str
    duration_ms: int
    run_id: str
    notes: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "exit_code": self.exit_code,
            "gate": self.gate,
            "env": self.env,
            "layers": [x.as_dict() for x in self.layers],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "run_id": self.run_id,
            "notes": self.notes,
            "verdict_policy": "PASS/FAIL from Gate C layers only; GenAI must not override",
        }


def _count_layers(layers: Sequence[LayerResult]) -> Dict[str, int]:
    total = len(layers)
    passed = sum(1 for x in layers if x.status == "passed")
    failed = sum(1 for x in layers if x.status == "failed")
    skipped = sum(1 for x in layers if x.status == "skipped")
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "broken": 0,
    }


def to_run_summary(
    report: GateCReport,
    *,
    report_url: str = "file://regression-gate-c.json",
    branch: Optional[str] = None,
    commit: Optional[str] = None,
    ci_run_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Dashboard-oriented run-summary (+ regression_platform extension)."""
    summary = _count_layers(report.layers)
    status = "passed" if report.ok else "failed"
    top_failures = []
    for layer in report.layers:
        if layer.status != "failed":
            continue
        top_failures.append(
            {
                "name": layer.name,
                "fullName": f"gate-c/{layer.name}",
                "status": "failed",
                "category": "assertion"
                if layer.exit_code == 1
                else ("environment" if layer.exit_code == 2 else "unknown"),
                "reason": layer.error or "layer failed",
                "feature": "FEATURE-PLATFORM",
            }
        )
    payload: Dict[str, Any] = {
        "schemaVersion": "1.0",
        "repo": "regression",
        "repoName": "automation-dashboard",
        "repository": "retech-us/automation-dashboard",
        "runId": report.run_id,
        "workflow": "regression-gate-c",
        "branch": branch or os.environ.get("GITHUB_REF_NAME"),
        "commit": commit or os.environ.get("GITHUB_SHA"),
        "environment": report.env,
        "suite": "regression-gate-c",
        "status": status,
        "startedAt": report.started_at,
        "finishedAt": report.finished_at,
        "durationMs": report.duration_ms,
        "summary": summary,
        "reportUrl": report_url,
        "topFailures": top_failures,
        "jobs": [
            {
                "name": layer.name,
                "status": layer.status,
                "summary": {
                    "total": 1,
                    "passed": 1 if layer.status == "passed" else 0,
                    "failed": 1 if layer.status == "failed" else 0,
                    "skipped": 1 if layer.status == "skipped" else 0,
                },
            }
            for layer in report.layers
        ],
        "regression_platform": {
            "gate": "C",
            "ok": report.ok,
            "exit_code": report.exit_code,
            "notes": report.notes,
            "layers": [x.as_dict() for x in report.layers],
        },
    }
    server = (os.environ.get("GITHUB_SERVER_URL") or "").rstrip("/")
    repo = os.environ.get("GITHUB_REPOSITORY") or ""
    run = os.environ.get("GITHUB_RUN_ID") or ""
    if ci_run_url:
        payload["ciRunUrl"] = ci_run_url
    elif server and repo and run:
        payload["ciRunUrl"] = f"{server}/{repo}/actions/runs/{run}"
    return payload


def render_gate_c_markdown(report: GateCReport) -> str:
    verdict = "PASS" if report.ok else "FAIL"
    lines = [
        "## Regression Gate C (Release)",
        "",
        f"**Verdict:** `{verdict}` (from release layers only)",
        f"**Env:** `{report.env}`",
        f"**Run ID:** `{report.run_id}`",
        f"**Duration:** {report.duration_ms} ms",
        "",
        "### Layers",
        "",
        "| Layer | Status | Exit | Notes |",
        "|-------|--------|------|-------|",
    ]
    for layer in report.layers:
        note = layer.error or json.dumps(layer.detail, separators=(",", ":"))[:80]
        lines.append(
            f"| `{layer.name}` | `{layer.status}` | `{layer.exit_code}` | {note} |"
        )
    lines.extend(
        [
            "",
            "### Policy",
            "",
            "PASS/FAIL is taken only from Gate C layer results. GenAI must not override.",
            "",
            f"_Generated: {report.finished_at}_",
            "",
        ]
    )
    return "\n".join(lines)


def _run_external(
    name: str,
    cmd: Optional[str],
    *,
    skip_reason: str,
) -> LayerResult:
    if not cmd or not cmd.strip():
        return LayerResult(
            name=name,
            status="skipped",
            exit_code=0,
            detail={"reason": skip_reason},
        )
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=int(os.environ.get("REGRESSION_EXTERNAL_TIMEOUT_SEC") or 600),
        )
        ok = proc.returncode == 0
        return LayerResult(
            name=name,
            status="passed" if ok else "failed",
            exit_code=proc.returncode,
            detail={
                "cmd": cmd,
                "stdout_tail": (proc.stdout or "")[-500:],
                "stderr_tail": (proc.stderr or "")[-500:],
            },
            error=None if ok else f"exit {proc.returncode}",
        )
    except subprocess.TimeoutExpired:
        return LayerResult(
            name=name,
            status="failed",
            exit_code=1,
            error="timeout",
            detail={"cmd": cmd},
        )
    except OSError as exc:
        return LayerResult(
            name=name,
            status="failed",
            exit_code=3,
            error=str(exc),
            detail={"cmd": cmd},
        )


def run_gate_c(
    *,
    env: str = "epsilon",
    require_live: bool = False,
    task_id: Optional[int] = None,
    api_ir_cmd: Optional[str] = None,
    appium_cmd: Optional[str] = None,
) -> GateCReport:
    """
    Release pack composition:
      1. gate_a_pr_bot_smoke (offline judgement)
      2. domain_parity_cat1 (Android-locked counts)
      3. gate_b_live (live IR) — skipped if no creds unless require_live
      4. api_ir_subset — optional external cmd (REGRESSION_API_IR_CMD)
      5. appium_ir_thin — optional external cmd (REGRESSION_APPIUM_CMD)
    """
    started = datetime.now(timezone.utc)
    t0 = time.time()
    run_id = os.environ.get("GITHUB_RUN_ID") or str(uuid.uuid4())
    layers: List[LayerResult] = []
    notes: List[str] = []

    # 1. Gate A smoke via pr-bot
    try:
        a = run_pr_bot(env=env, mode="smoke")
        layers.append(
            LayerResult(
                name="gate_a_pr_bot_smoke",
                status="passed" if a.ok else "failed",
                exit_code=a.exit_code,
                detail={"packs": a.packs, "steps": len(a.steps)},
                error=None if a.ok else "Gate A smoke failed",
            )
        )
    except Exception as exc:  # noqa: BLE001
        layers.append(
            LayerResult(
                name="gate_a_pr_bot_smoke",
                status="failed",
                exit_code=3,
                error=str(exc),
            )
        )

    # 2. Explicit CAT1 domain parity (release must keep Android lock)
    cat1 = invoke_tool("domain_parity", {"env": env, "case": "cat1_t5_mixed"})
    layers.append(
        LayerResult(
            name="domain_parity_cat1",
            status="passed" if cat1.ok else "failed",
            exit_code=cat1.exit_code,
            detail=(cat1.result or {}),
            error=cat1.error,
        )
    )

    # 3. Gate B live
    has_creds = bool(
        (os.environ.get("REGRESSION_USERNAME") or "").strip()
        or (os.environ.get("REGRESSION_PASSWORD") or "").strip()
    )
    # Also allow gitignored accounts file path used by auth loader
    accounts = (
        REPO_ROOT
        / "mobile-backend-integration-tests"
        / "config"
        / "test-accounts.json"
    )
    if accounts.is_file():
        has_creds = True

    if not has_creds and not require_live:
        layers.append(
            LayerResult(
                name="gate_b_live",
                status="skipped",
                exit_code=0,
                detail={"reason": "no credentials; set REGRESSION_USERNAME/PASSWORD"},
            )
        )
        notes.append("gate_b_live skipped (no creds)")
    else:
        try:
            b = run_gate_b(env=env, task_id=task_id)
            layers.append(
                LayerResult(
                    name="gate_b_live",
                    status="passed" if b.ok else "failed",
                    exit_code=b.exit_code,
                    detail={"task_id": b.task_id, "steps": [s.name for s in b.steps]},
                    error=None if b.ok else "Gate B live failed",
                )
            )
        except GateBError as exc:
            layers.append(
                LayerResult(
                    name="gate_b_live",
                    status="failed",
                    exit_code=exc.exit_code,
                    error=str(exc),
                )
            )
        except Exception as exc:  # noqa: BLE001
            code = 2 if "credential" in str(exc).lower() else 1
            if require_live:
                layers.append(
                    LayerResult(
                        name="gate_b_live",
                        status="failed",
                        exit_code=code,
                        error=str(exc),
                    )
                )
            else:
                layers.append(
                    LayerResult(
                        name="gate_b_live",
                        status="skipped",
                        exit_code=0,
                        detail={"reason": str(exc)},
                    )
                )
                notes.append(f"gate_b_live skipped: {exc}")

    # 4. API IR subset (external)
    api_cmd = api_ir_cmd or (os.environ.get("REGRESSION_API_IR_CMD") or "").strip() or None
    layers.append(
        _run_external(
            "api_ir_subset",
            api_cmd,
            skip_reason="Set REGRESSION_API_IR_CMD to enable API IR subset (e.g. Maven test filter)",
        )
    )
    if not api_cmd:
        notes.append("api_ir_subset skipped (no REGRESSION_API_IR_CMD)")

    # 5. Thin Appium IR (external)
    appium = appium_cmd or (os.environ.get("REGRESSION_APPIUM_CMD") or "").strip() or None
    layers.append(
        _run_external(
            "appium_ir_thin",
            appium,
            skip_reason="Set REGRESSION_APPIUM_CMD to enable thin Appium IR smoke",
        )
    )
    if not appium:
        notes.append("appium_ir_thin skipped (no REGRESSION_APPIUM_CMD)")

    finished = datetime.now(timezone.utc)
    # Failed layers fail the gate; skipped do not
    failed = [x for x in layers if x.status == "failed"]
    ok = len(failed) == 0
    worst = 0
    for x in failed:
        worst = max(worst, x.exit_code or 1)

    return GateCReport(
        ok=ok,
        exit_code=0 if ok else (worst or 1),
        gate="C",
        env=env,
        layers=layers,
        started_at=started.isoformat(),
        finished_at=finished.isoformat(),
        duration_ms=int((time.time() - t0) * 1000),
        run_id=str(run_id),
        notes=notes,
    )
