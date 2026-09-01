"""Slice 7 — CI PR bot control plane (GenAI-first surface).

Runs judgement tools via the Slice 6 API, builds a PR comment, and optionally
adds a narrative. GenAI / narrative NEVER overrides PASS/FAIL.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from regression.impact import (
    ImpactError,
    expand_pack_tools,
    load_impact_map,
    select_impact,
)
from regression.tools import ToolResponse, invoke_tool

REPO_ROOT = Path(__file__).resolve().parents[1]


class PrBotError(Exception):
    def __init__(self, message: str, *, exit_code: int = 1):
        super().__init__(message)
        self.exit_code = exit_code


@dataclass
class StepResult:
    tool: str
    pack: str
    ok: bool
    exit_code: int
    error: Optional[str] = None
    summary: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PrBotReport:
    ok: bool
    exit_code: int
    env: str
    mode: str
    packs: List[str]
    features: List[str]
    steps: List[StepResult]
    narrative: str
    narrative_source: str  # template | llm_disabled_fallback
    verdict_policy: str
    generated_at: str
    pr_number: Optional[str] = None
    head_sha: Optional[str] = None
    impact: Optional[Dict[str, Any]] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "exit_code": self.exit_code,
            "env": self.env,
            "mode": self.mode,
            "packs": self.packs,
            "features": self.features,
            "steps": [s.as_dict() for s in self.steps],
            "narrative": self.narrative,
            "narrative_source": self.narrative_source,
            "verdict_policy": self.verdict_policy,
            "generated_at": self.generated_at,
            "pr_number": self.pr_number,
            "head_sha": self.head_sha,
            "impact": self.impact,
        }


VERDICT_POLICY = (
    "PASS/FAIL is taken only from tool ok/exit_code. "
    "Narrative must not flip verdict."
)


def _summarize_result(resp: ToolResponse) -> Dict[str, Any]:
    result = resp.result or {}
    # Keep comment payloads small
    keys = (
        "env",
        "base_url",
        "ok",
        "item_count",
        "domain_card_count",
        "dry_run",
        "skipped",
        "status",
        "tool_count",
        "mismatches",
        "error",
    )
    out = {k: result[k] for k in keys if k in result}
    if resp.error:
        out["tool_error"] = resp.error
    return out


def build_narrative(report_like: Dict[str, Any]) -> tuple[str, str]:
    """
    Control-plane narrative. Default is deterministic template.
    Optional LLM path only fills text; never returns a verdict.
    """
    mode = (os.environ.get("REGRESSION_NARRATIVE_MODE") or "template").strip().lower()
    ok = bool(report_like.get("ok"))
    steps = report_like.get("steps") or []
    failed = [s for s in steps if not s.get("ok")]
    features = ", ".join(report_like.get("features") or []) or "n/a"
    packs = ", ".join(report_like.get("packs") or []) or "n/a"

    if mode == "llm":
        # Slice 7: do not call external LLMs by default in CI.
        # If a future provider is wired, it must only return narrative text.
        # Falling back keeps CI deterministic and offline-safe.
        pass

    if ok:
        text = (
            f"Regression PR bot completed pack(s) [{packs}] for features [{features}]. "
            f"All {len(steps)} judgement tool step(s) passed. "
            "No product/contract failures detected in this Gate A offline pack."
        )
    else:
        names = ", ".join(f"{s.get('tool')}(exit={s.get('exit_code')})" for s in failed)
        text = (
            f"Regression PR bot FAILED on pack(s) [{packs}] for features [{features}]. "
            f"Failing tools: {names}. "
            "Investigate tool result payloads; do not treat narrative as the oracle."
        )
    return text, "template"


def render_pr_comment(report: PrBotReport) -> str:
    verdict = "PASS" if report.ok else "FAIL"
    lines = [
        "<!-- regression-pr-bot -->",
        "## Regression PR Bot",
        "",
        f"**Verdict:** `{verdict}` (from judgement tools only)",
        f"**Env:** `{report.env}`",
        f"**Mode:** `{report.mode}`",
        f"**Packs:** {', '.join(f'`{p}`' for p in report.packs) or '—'}",
        f"**Features:** {', '.join(f'`{f}`' for f in report.features) or '—'}",
        "",
        "### Steps",
        "",
        "| Tool | Pack | OK | Exit | Summary |",
        "|------|------|----|------|---------|",
    ]
    for s in report.steps:
        summary = json.dumps(s.summary, separators=(",", ":"))
        if len(summary) > 120:
            summary = summary[:117] + "..."
        lines.append(
            f"| `{s.tool}` | `{s.pack}` | `{s.ok}` | `{s.exit_code}` | `{summary}` |"
        )
    lines.extend(
        [
            "",
            "### Narrative",
            "",
            report.narrative,
            "",
            f"_Narrative source: `{report.narrative_source}`_",
            "",
            "### Policy",
            "",
            VERDICT_POLICY,
            "",
        ]
    )
    if report.head_sha:
        lines.append(f"_SHA: `{report.head_sha}`_")
    if report.pr_number:
        lines.append(f"_PR: #{report.pr_number}_")
    lines.append(f"_Generated: {report.generated_at}_")
    return "\n".join(lines) + "\n"


def run_pr_bot(
    *,
    env: str = "epsilon",
    mode: str = "smoke",
    changed_files: Optional[Sequence[str]] = None,
    pr_number: Optional[str] = None,
    head_sha: Optional[str] = None,
    impact_map_path: Optional[Path] = None,
    include_auth_optional: bool = False,
) -> PrBotReport:
    impact_map = load_impact_map(impact_map_path) if impact_map_path else load_impact_map()
    files = list(changed_files or [])
    selection = select_impact(files, mode=mode, impact_map=impact_map)
    packs = list(selection.packs)
    if include_auth_optional and "auth_optional" not in packs:
        packs.append("auth_optional")

    steps_plan = expand_pack_tools(packs, impact_map=impact_map, env=env)
    step_results: List[StepResult] = []
    worst_exit = 0
    all_ok = True

    for step in steps_plan:
        # Resolve fixture paths relative to repo root
        args = dict(step["args"])
        if args.get("fixture") and not Path(str(args["fixture"])).is_file():
            candidate = REPO_ROOT / str(args["fixture"])
            if candidate.is_file():
                args["fixture"] = str(candidate)

        resp = invoke_tool(step["name"], args)
        step_results.append(
            StepResult(
                tool=step["name"],
                pack=str(step.get("pack") or ""),
                ok=bool(resp.ok),
                exit_code=int(resp.exit_code),
                error=resp.error,
                summary=_summarize_result(resp),
            )
        )
        if not resp.ok:
            all_ok = False
            worst_exit = max(worst_exit, int(resp.exit_code) or 1)

    exit_code = 0 if all_ok else (worst_exit or 1)
    draft = {
        "ok": all_ok,
        "steps": [s.as_dict() for s in step_results],
        "features": selection.features,
        "packs": packs,
    }
    narrative, narrative_source = build_narrative(draft)

    return PrBotReport(
        ok=all_ok,
        exit_code=exit_code,
        env=env,
        mode=selection.mode if mode == "impacted" else mode,
        packs=packs,
        features=selection.features,
        steps=step_results,
        narrative=narrative,
        narrative_source=narrative_source,
        verdict_policy=VERDICT_POLICY,
        generated_at=datetime.now(timezone.utc).isoformat(),
        pr_number=pr_number,
        head_sha=head_sha,
        impact=selection.as_dict(),
    )


def git_changed_files(*, base_ref: Optional[str] = None) -> List[str]:
    """Best-effort list of changed files vs base_ref (default origin/master...HEAD)."""
    if base_ref:
        cmd = ["git", "diff", "--name-only", f"{base_ref}...HEAD"]
    else:
        cmd = ["git", "diff", "--name-only", "HEAD"]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise ImpactError(f"git failed: {exc}", exit_code=3) from exc
    if proc.returncode != 0:
        # Fallback: unstaged + staged
        proc2 = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        files = []
        for line in (proc2.stdout or "").splitlines():
            parts = line.strip().split(maxsplit=1)
            if len(parts) == 2:
                files.append(parts[1])
        return files
    return [ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip()]


def post_github_comment(*, body: str, pr_number: str) -> Dict[str, Any]:
    """Post PR comment via gh --body-file. Does not alter verdict."""
    import tempfile

    marker = "<!-- regression-pr-bot -->"
    with tempfile.NamedTemporaryFile(
        "w", suffix=".md", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(body)
        tmp_path = tmp.name
    try:
        proc = subprocess.run(
            ["gh", "pr", "comment", str(pr_number), "--body-file", tmp_path],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except OSError:
            pass
    return {
        "ok": proc.returncode == 0,
        "action": "created",
        "marker": marker,
        "stderr": (proc.stderr or "").strip() or None,
        "stdout": (proc.stdout or "").strip() or None,
        "exit_code": proc.returncode,
    }
