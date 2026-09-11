"""Inline Intelligent Reset report Excel export script for self-contained HTML."""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_JS_PATH = _REPO_ROOT / "assets" / "js" / "ir-report-export.js"
_EXTERNAL_TAG_RE = re.compile(
    r'<script\s+src="(?:\.\./)*assets/js/ir-report-export\.js"\s*></script>\s*',
    re.IGNORECASE,
)


def get_ir_export_script() -> str:
    return _JS_PATH.read_text(encoding="utf-8")


def ir_export_inline_script_tag() -> str:
    return f"<script>\n{get_ir_export_script()}\n</script>"


def ensure_ir_export_inline(html: str) -> str:
    """Replace external ir-report-export.js refs with inline script; append if missing."""
    tag = ir_export_inline_script_tag()
    if _EXTERNAL_TAG_RE.search(html):
        return _EXTERNAL_TAG_RE.sub(lambda _m: tag + "\n", html, count=1)
    if "__irExportReady" in html:
        return html
    if "</body>" in html:
        return html.replace("</body>", tag + "\n</body>", 1)
    return html + "\n" + tag
