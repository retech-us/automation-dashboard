#!/usr/bin/env python3
"""Inject shared ir-report-export.js into existing IR HTML reports."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_MARKER = "ir-report-export.js"
PATTERNS = (
    "Intelligent Reset Action Count",
    "Intelligent Reset State Transition",
    "Action Count & Resumption Audit",
    "State Transition & Validation Dashboard",
)


def asset_href(html_path: Path) -> str:
    rel = html_path.relative_to(ROOT)
    depth = len(rel.parts) - 1
    return ("../" * depth) + "assets/js/ir-report-export.js"


def needs_patch(text: str) -> bool:
    if SCRIPT_MARKER in text:
        return False
    return any(p in text for p in PATTERNS)


def patch_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if not needs_patch(text):
        return False
    tag = f'<script src="{asset_href(path)}"></script>\n'
    if "</body>" in text:
        text = text.replace("</body>", tag + "</body>", 1)
    else:
        text += "\n" + tag
    path.write_text(text, encoding="utf-8")
    return True


def main() -> int:
    patched = 0
    for path in ROOT.rglob("*.html"):
        if "node_modules" in path.parts:
            continue
        name = path.name
        if not (
            name.startswith("IR_")
            or name == "test_report.html"
            or "State_Transition" in name
            or "E2E_Audit" in name
        ):
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if not any(p in content for p in PATTERNS):
            continue
        if patch_file(path):
            patched += 1
            print(f"✅ {path.relative_to(ROOT)}")
    print(f"📊 Patched {patched} report(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
