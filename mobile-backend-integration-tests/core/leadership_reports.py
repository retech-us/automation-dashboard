"""Safe leadership document exports for grounded Agent Center results."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlsplit, urlunsplit


SENSITIVE_KEYS = {
    "authorization", "cookie", "password", "passkey", "secret", "signature",
    "token", "access_token", "api_key", "apikey",
}
ALLOWED_FORMATS = {"docx", "pptx"}


def _safe_text(value: Any, limit: int = 4000) -> str:
    return str(value or "").strip()[:limit]


def _safe_value(value: Any, key: str = "") -> Any:
    if key.casefold() in SENSITIVE_KEYS:
        return "[REDACTED]"
    if isinstance(value, dict):
        return {
            _safe_text(name, 80): _safe_value(item, str(name))
            for name, item in list(value.items())[:40]
        }
    if isinstance(value, list):
        return [_safe_value(item) for item in value[:50]]
    if isinstance(value, str):
        text = value[:2000]
        if text.startswith(("http://", "https://")):
            try:
                parts = urlsplit(text)
                return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
            except ValueError:
                return "[REDACTED URL]"
        return text
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return _safe_text(value, 2000)


def _metrics(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    metrics: List[Dict[str, Any]] = []
    seen = set()

    def collect(value: Any, prefix: str) -> None:
        if len(metrics) >= 8:
            return
        if isinstance(value, dict):
            for name, item in value.items():
                collect(item, f"{prefix} {name}".strip())
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            label = re.sub(r"[_-]+", " ", prefix).strip()
            label = (label[:1].upper() + label[1:])[:60] or "Metric"
            marker = (label, value)
            if marker not in seen:
                seen.add(marker)
                metrics.append({"label": label[:60], "value": value})

    for finding in findings:
        for evidence in finding.get("evidence") or []:
            collect(evidence.get("value"), finding.get("title") or evidence.get("source") or "")
    return metrics


def normalize_analysis(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Reduce an agent result to a bounded, credential-free reporting contract."""
    if not isinstance(analysis, dict):
        raise ValueError("Analysis must be an object.")
    context = _safe_text(analysis.get("context_label") or "Dashboard", 100)
    answer = _safe_text(analysis.get("answer") or analysis.get("summary"), 6000)
    if not answer:
        raise ValueError("Run an analysis before generating a leadership report.")

    findings = []
    for row in (analysis.get("findings") or [])[:12]:
        if not isinstance(row, dict):
            continue
        findings.append({
            "severity": _safe_text(row.get("severity") or "info", 30).lower(),
            "title": _safe_text(row.get("title") or "Finding", 160),
            "detail": _safe_text(row.get("detail"), 1600),
            "evidence": _safe_value(row.get("evidence") or []),
        })

    brief = {
        "title": f"{context} leadership analysis",
        "context": context,
        "question": _safe_text(analysis.get("question") or "Dashboard analysis", 500),
        "executive_summary": answer,
        "verdict": _safe_text(analysis.get("verdict") or "answered", 40).upper(),
        "confidence": _safe_text(analysis.get("confidence") or "unknown", 30).title(),
        "findings": findings,
        "recommendations": [
            _safe_text(item, 1000)
            for item in (analysis.get("recommendations") or [])[:10]
            if _safe_text(item)
        ],
        "sources": [
            _safe_text(item, 240)
            for item in (analysis.get("sources") or [])[:20]
            if _safe_text(item)
        ],
        "generated_at": _safe_text(analysis.get("generated_at"), 80),
        "run_id": _safe_text(analysis.get("run_id"), 100),
    }
    brief["metrics"] = _metrics(findings)
    return brief


def report_filename(context: str, export_format: str) -> str:
    export_format = str(export_format or "").lower()
    if export_format not in ALLOWED_FORMATS:
        raise ValueError("Export format must be docx or pptx.")
    slug = re.sub(r"[^a-z0-9]+", "-", str(context or "dashboard").lower()).strip("-")
    return f"{slug[:80] or 'dashboard'}-leadership-report.{export_format}"


def generate_leadership_report(
    analysis: Dict[str, Any],
    export_format: str,
    output_dir: Path,
    workspace_dir: Path,
) -> Path:
    brief = normalize_analysis(analysis)
    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = report_filename(brief["context"], export_format)
    stem, suffix = base_name.rsplit(".", 1)
    run_suffix = re.sub(r"[^a-zA-Z0-9]+", "", brief.get("run_id") or "")[:8].lower()
    output_name = f"{stem}-{run_suffix}.{suffix}" if run_suffix else base_name
    output_path = output_dir / output_name
    input_path = output_dir / f".{output_path.stem}.json"
    input_path.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    if export_format == "pptx":
        command = [
            sys.executable,
            str(workspace_dir / "scripts" / "apply_symphonyai_deck.py"),
            str(input_path),
            str(output_path),
        ]
    else:
        command = [
            "node",
            str(workspace_dir / "scripts" / "generate-leadership-report.js"),
            export_format,
            str(input_path),
            str(output_path),
        ]
    try:
        completed = subprocess.run(
            command,
            cwd=str(workspace_dir),
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
        if completed.returncode != 0 or not output_path.exists():
            detail = (completed.stderr or completed.stdout or "Document generator failed.").strip()
            raise RuntimeError(detail[-1200:])
        return output_path
    finally:
        input_path.unlink(missing_ok=True)
