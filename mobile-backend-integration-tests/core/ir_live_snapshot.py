"""Build a truthful, plain-language Intelligent Reset live scorecard."""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, Optional


QUALITY_GATE_PCT = 95.0


def save_ir_snapshot(snapshot: Dict[str, Any], path: Path) -> None:
    """Atomically persist the public scorecard contract (which contains no auth)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def load_ir_snapshot(path: Path) -> Optional[Dict[str, Any]]:
    """Read the last valid public scorecard; corrupt files degrade to no snapshot."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        return None
    return value


def _number(data: Dict[str, Any], key: str) -> Optional[float]:
    value = data.get(key)
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _post_photo(audit: Dict[str, Any]) -> Dict[str, Any]:
    timeline = audit.get("task_timeline") or {}
    post_scan = timeline.get("post_scan") or {}
    error = audit.get("post_digital_error")

    if audit.get("post_digital_loaded"):
        return {
            "state": "verified",
            "scan_id": post_scan.get("scan_id"),
            "explanation": "Post-photo actions and Digital Shelf data were loaded from the post stage.",
        }
    if error:
        return {
            "state": "unavailable",
            "scan_id": post_scan.get("scan_id"),
            "explanation": str(error),
        }
    if audit:
        return {
            "state": "not_available",
            "scan_id": post_scan.get("scan_id"),
            "explanation": "No verified post-photo comparison is available for this task.",
        }
    return {
        "state": "not_checked",
        "scan_id": None,
        "explanation": "Post photo has not been checked yet.",
    }


def _scan_diagnostics(scans: Any) -> list:
    diagnostics = []
    for scan in scans if isinstance(scans, list) else []:
        if not isinstance(scan, dict):
            continue
        scan_id = scan.get("id") or scan.get("scan_id")
        if scan_id is None:
            continue
        type_text = " ".join(
            str(scan.get(key) or "") for key in ("scan_type", "type", "photo_type", "stage")
        ).casefold()
        if scan.get("is_post_photo") is True or "post" in type_text:
            stage = "post_photo"
        elif scan.get("is_pre_photo") is True or "pre" in type_text:
            stage = "pre_photo"
        else:
            stage = "unknown"
        diagnostics.append({
            "scan_id": scan_id,
            "stage": stage,
            "status": scan.get("status") or None,
            "image_quality": _number(scan, "image_quality"),
            "blurry_pct": _number(scan, "blurry_pct"),
            "shelf_mismatch": (
                scan.get("shelf_mismatch")
                if isinstance(scan.get("shelf_mismatch"), bool)
                else None
            ),
        })
    return diagnostics


def _findings(task_id: Any, audit: Dict[str, Any], gate_state: str) -> list:
    if not audit or not task_id:
        return []

    findings = []

    def add(code: str, title: str, severity: str, evidence: str) -> None:
        findings.append({
            "code": code,
            "title": title,
            "severity": severity,
            "evidence": evidence,
            "jira": {
                "reference": f"IR-TASK-{task_id}-{code.removeprefix('IR-')}",
                "summary": f"[{code}] Task {task_id}: {title}",
                "labels": ["intelligent-reset", code.casefold()],
            },
        })

    counts = audit.get("digital_compare_counts") or {}
    mismatched = int(counts.get("mismatched", 0) or 0)
    if gate_state == "fail":
        add(
            "IR-QUALITY-GATE",
            "Overall quality is below 95%",
            "critical",
            f"Overall score: {_number(audit, 'combined_compliance_pct'):.1f}%.",
        )
    if mismatched:
        add(
            "IR-DIGITAL-MISMATCH",
            "Actions were done differently than instructed",
            "critical",
            f"{mismatched} generated action(s) did not match Digital Shelf.",
        )
    incomplete = sum(
        int(audit.get(key, 0) or 0)
        for key in ("total_pending_actions", "total_rejected_actions", "total_dropped_actions")
    )
    if incomplete:
        add(
            "IR-ACTION-INCOMPLETE",
            "Requested work is not fully completed",
            "warning",
            f"{incomplete} action(s) are pending, rejected, or dropped.",
        )
    if not audit.get("post_digital_loaded"):
        add(
            "IR-POST-UNAVAILABLE",
            "Post-photo proof is unavailable",
            "warning",
            str(audit.get("post_digital_error") or "No verified post-photo comparison."),
        )
    if audit.get("digital_fetch_error"):
        add(
            "IR-DIGITAL-UNAVAILABLE",
            "Digital Shelf data could not be read",
            "warning",
            str(audit["digital_fetch_error"]),
        )
    return findings


def build_ir_live_snapshot(state: Dict[str, Any]) -> Dict[str, Any]:
    """Return the UI contract without converting missing data to zero."""
    audit = state.get("latest_audit") or {}
    active_task_id = state.get("active_task_id")
    if audit and active_task_id and audit.get("task_id") != active_task_id:
        audit = {}
    pipeline = state.get("pipeline") or {}
    task_id = audit.get("task_id") or active_task_id
    post = _post_photo(audit)

    combined = _number(audit, "combined_compliance_pct")
    if combined is None:
        gate_state = "unknown"
        gate_explanation = "The quality gate will be calculated after comparison data is available."
    elif combined >= QUALITY_GATE_PCT:
        gate_state = "pass"
        gate_explanation = f"Overall score {combined:.1f}% meets the {QUALITY_GATE_PCT:.0f}% quality gate."
    else:
        gate_state = "fail"
        gate_explanation = f"Overall score {combined:.1f}% is below the {QUALITY_GATE_PCT:.0f}% quality gate."

    action_counts = audit.get("action_counts_by_type") or {}
    set_aside = int(action_counts.get("SET_ASIDE", 0) or 0)
    add_to_shelf = int(action_counts.get("ADD_TO_SHELF", 0) or 0)
    live_actions = state.get("actions") if isinstance(state.get("actions"), list) else []
    telemetry = (
        state.get("step_telemetry")
        if isinstance(state.get("step_telemetry"), list)
        else []
    )
    live_step_keys = {
        (entry.get("step_index"), entry.get("action_id"))
        for entry in telemetry
        if isinstance(entry, dict)
    }
    live_total = len(live_actions) if live_actions else None
    live_performed = len(live_step_keys) if live_total is not None else None
    live_pending = (
        max(live_total - live_performed, 0)
        if live_total is not None and live_performed is not None
        else None
    )
    live_finished_pct = (
        round((live_performed / live_total) * 100, 1)
        if live_total
        else (0.0 if live_total == 0 and task_id else None)
    )

    if pipeline.get("is_running"):
        live_state = "running"
    elif task_id:
        live_state = "ready"
    else:
        live_state = "idle"

    if not task_id:
        summary = "No Intelligent Reset task is loaded. Load a Task ID to see live quality checks."
    elif not audit:
        progress = (
            f"{live_performed} of {live_total} steps completed. "
            if live_total is not None
            else ""
        )
        summary = (
            f"Task #{task_id} is loaded. {progress}Post photo has not been checked yet; "
            "run the audit to verify Digital Shelf alignment."
        )
    else:
        alignment = _number(audit, "digital_alignment_pct")
        alignment_text = f"{alignment:.1f}% Digital alignment" if alignment is not None else "Digital alignment not available"
        summary = f"Task #{task_id}: {alignment_text}. {gate_explanation}"

    scan_diagnostics = _scan_diagnostics(state.get("scan_results"))
    findings = _findings(task_id, audit, gate_state)
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "task_id": task_id,
        "instance": state.get("instance_slug"),
        "task_status": state.get("task_status"),
        "live_state": live_state,
        "pipeline_step": pipeline.get("step_name"),
        "capabilities": {
            "fresh_e2e_includes_post_photo": False,
            "post_photo_scope": "historical_audit_only",
        },
        "plain_language_summary": summary,
        "quality_gate": {
            "threshold_pct": QUALITY_GATE_PCT,
            "state": gate_state,
            "explanation": gate_explanation,
        },
        "metrics": {
            "logical_actions": (
                _number(audit, "unique_backend_actions")
                if audit
                else len({str(action.get("id")) for action in live_actions if isinstance(action, dict)})
                if live_actions
                else None
            ),
            "displayed_steps": _number(audit, "total_generated_mobile_cards") if audit else live_total,
            "performed_steps": _number(audit, "total_performed_actions") if audit else live_performed,
            "pending_steps": _number(audit, "total_pending_actions") if audit else live_pending,
            "work_finished_pct": _number(audit, "compliance_score_pct") if audit else live_finished_pct,
            "digital_alignment_pct": _number(audit, "digital_alignment_pct"),
            "post_alignment_pct": _number(audit, "post_digital_alignment_pct"),
            "overall_score_pct": combined,
        },
        "comparison": dict(audit.get("digital_compare_counts") or {}),
        "post_comparison": dict(audit.get("post_digital_compare_counts") or {}),
        "action_mix": {
            "moved_items": min(set_aside, add_to_shelf),
            "removed": int(action_counts.get("REMOVE", 0) or 0),
            "added": int(action_counts.get("ADD", 0) or 0),
            "identified": int(action_counts.get("IDENTIFY", 0) or 0),
        },
        "post_photo": post,
        "scan_diagnostics": scan_diagnostics,
        "findings": findings,
        "report_url": (
            f"/api/runner/e2e_audit_report?task_id={task_id}" if task_id else None
        ),
    }
