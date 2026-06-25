#!/usr/bin/env python3
"""Fetch run summaries for dashboard — run-summary.json with Allure widget fallback."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPOS = {
    "web": {
        "report_url": "https://retech-us.github.io/retech-web-automation/",
        "ci_url": "https://github.com/retech-us/retech-web-automation/actions",
        "summary_url": "https://retech-us.github.io/retech-web-automation/run-summary.json",
        "widget_url": "https://retech-us.github.io/retech-web-automation/widgets/summary.json",
        "repo_name": "retech-us/retech-web-automation",
    },
    "mobile": {
        "report_url": "https://retech-us.github.io/retech-mobile-automation/",
        "ci_url": "https://github.com/retech-us/retech-mobile-automation/actions",
        "summary_url": "https://retech-us.github.io/retech-mobile-automation/run-summary.json",
        "widget_url": "https://retech-us.github.io/retech-mobile-automation/widgets/summary.json",
        "repo_name": "retech-us/retech-mobile-automation",
    },
    "api": {
        "report_url": "https://retech-us.github.io/retech-api-automation/",
        "ci_url": "https://github.com/retech-us/retech-api-automation/actions",
        "summary_url": "https://retech-us.github.io/retech-api-automation/run-summary.json",
        "widget_url": "https://retech-us.github.io/retech-api-automation/widgets/summary.json",
        "repo_name": "retech-us/retech-api-automation",
    },
}


def fetch_json(url: str) -> dict | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "automation-dashboard/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None


def from_widget(repo_id: str, widget: dict, cfg: dict) -> dict:
    stats = widget.get("statistic") or {}
    failed = int(stats.get("failed", 0))
    broken = int(stats.get("broken", 0))
    passed = int(stats.get("passed", 0))
    skipped = int(stats.get("skipped", 0))
    total = int(stats.get("total", 0))
    time_info = widget.get("time") or {}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    status = "failed" if failed + broken > 0 else ("passed" if total > 0 else "unknown")
    return {
        "schemaVersion": "1.0",
        "repo": repo_id,
        "repoName": cfg["repo_name"],
        "repository": cfg["repo_name"],
        "status": status,
        "environment": "staging",
        "suite": "regression",
        "finishedAt": now,
        "durationMs": int(time_info.get("duration", 0)),
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "broken": broken,
            "skipped": skipped,
        },
        "reportUrl": cfg["report_url"],
        "ciRunUrl": cfg["ci_url"],
        "topFailures": [],
        "failureCategories": {},
        "dataSource": "allure-widget-fallback",
        "reportName": widget.get("reportName"),
    }


def placeholder(repo_id: str, cfg: dict) -> dict:
    return {
        "schemaVersion": "1.0",
        "repo": repo_id,
        "repoName": cfg["repo_name"],
        "status": "unknown",
        "summary": {"total": 0, "passed": 0, "failed": 0, "broken": 0, "skipped": 0},
        "reportUrl": cfg["report_url"],
        "ciRunUrl": cfg["ci_url"],
        "topFailures": [],
        "dataSource": "unavailable",
    }


def fetch_repo(repo_id: str) -> dict:
    cfg = REPOS[repo_id]
    summary = fetch_json(cfg["summary_url"])
    if summary and summary.get("repo"):
        summary["dataSource"] = "run-summary.json"
        return summary
    widget = fetch_json(cfg["widget_url"])
    if widget and widget.get("statistic"):
        return from_widget(repo_id, widget, cfg)
    return placeholder(repo_id, cfg)


def main() -> int:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data")
    out_dir.mkdir(parents=True, exist_ok=True)
    for repo_id in REPOS:
        payload = fetch_repo(repo_id)
        path = out_dir / f"{repo_id}.json"
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
        src = payload.get("dataSource", "?")
        total = payload.get("summary", {}).get("total", 0)
        print(f"✅ {repo_id}: {payload.get('status')} total={total} source={src}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
