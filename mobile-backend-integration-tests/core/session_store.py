"""Keep instance sign-ins across runner restarts.

Only bearer tokens are stored, never credentials, and the file is written with
owner-only permissions and a short lifetime so a forgotten token cannot be
reused indefinitely.
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, Optional

SCHEMA_VERSION = 1
DEFAULT_MAX_AGE_SECONDS = 12 * 60 * 60


def _clean(tokens: Dict[str, str]) -> Dict[str, str]:
    return {
        str(url): str(token)
        for url, token in (tokens or {}).items()
        if str(url or "").strip() and str(token or "").strip()
    }


def save_tokens(path: Path, tokens: Dict[str, str], now: Optional[float] = None) -> None:
    """Write tokens for reuse, or remove the file when there is nothing to keep."""
    path = Path(path)
    usable = _clean(tokens)
    if not usable:
        path.unlink(missing_ok=True)
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "schema_version": SCHEMA_VERSION,
        "saved_at": float(now if now is not None else time.time()),
        "tokens": usable,
    }

    temporary = path.with_suffix(path.suffix + ".tmp")
    # Create with 0600 from the start so the token is never briefly world-readable.
    handle = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(handle, "w", encoding="utf-8") as stream:
        json.dump(document, stream)
    os.replace(temporary, path)
    os.chmod(path, 0o600)


def load_tokens(
    path: Path,
    now: Optional[float] = None,
    max_age_seconds: float = DEFAULT_MAX_AGE_SECONDS,
) -> Dict[str, str]:
    """Return still-fresh tokens; a missing or unreadable file simply means none."""
    path = Path(path)
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(document, dict):
        return {}

    saved_at = document.get("saved_at")
    if not isinstance(saved_at, (int, float)):
        return {}
    moment = float(now if now is not None else time.time())
    if moment - float(saved_at) > max_age_seconds:
        return {}

    tokens = document.get("tokens")
    return _clean(tokens) if isinstance(tokens, dict) else {}
