#!/usr/bin/env python3
"""Inline ir-report-export.js into existing IR HTML reports (no external script dependency)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mobile-backend-integration-tests"))

from core.ir_export_script import ensure_ir_export_inline  # noqa: E402

PATTERNS = (
    "Intelligent Reset Action Count",
    "Intelligent Reset State Transition",
    "Intelligent Reset E2E Audit",
    "Action Count & Resumption Audit",
    "State Transition & Validation Dashboard",
    "E2E Audit & Bi-Directional Trace",
)


def is_ir_report(path: Path, content: str) -> bool:
    name = path.name
    if not (
        name.startswith("IR_")
        or name == "test_report.html"
        or "State_Transition" in name
        or "E2E_Audit" in name
    ):
        return False
    return any(p in content for p in PATTERNS)


def patch_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if not is_ir_report(path, text):
        return False
    updated = ensure_ir_export_inline(text)
    if updated == text:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def main() -> int:
    patched = 0
    for path in ROOT.rglob("*.html"):
        if "node_modules" in path.parts:
            continue
        try:
            if patch_file(path):
                patched += 1
                print(f"✅ {path.relative_to(ROOT)}")
        except OSError as exc:
            print(f"⚠️  {path}: {exc}", file=sys.stderr)
    print(f"📊 Patched {patched} report(s) with inline Excel export")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
