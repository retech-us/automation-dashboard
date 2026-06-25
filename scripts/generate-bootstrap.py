#!/usr/bin/env python3
"""Bake latest repo snapshots into assets/bootstrap.js for instant, cache-safe load."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT = ROOT / "assets" / "bootstrap.js"
VERSION = "8"


def main() -> None:
    snapshots: dict = {}
    for path in sorted(DATA_DIR.glob("*.json")):
        try:
            snapshots[path.stem] = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

    payload = json.dumps({"version": VERSION, "snapshots": snapshots}, separators=(",", ":"))
    OUT.write_text(
        f"/* generated — do not edit */\n"
        f"window.DASHBOARD_VERSION = {json.dumps(VERSION)};\n"
        f"window.DASHBOARD_SNAPSHOTS = {payload};\n",
        encoding="utf-8",
    )
    print(f"✅ bootstrap.js written ({len(snapshots)} repos, version {VERSION})")


if __name__ == "__main__":
    main()
