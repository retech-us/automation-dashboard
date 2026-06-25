#!/usr/bin/env python3
"""Fetch latest run summaries — Allure widgets (live) + run-summary.json (failures)."""

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
        "environment_url": "https://retech-us.github.io/retech-web-automation/widgets/environment.json",
        "executors_url": "https://retech-us.github.io/retech-web-automation/widgets/executors.json",
        "repo_name": "retech-us/retech-web-automation",
    },
    "mobile-ios": {
        "report_url": "https://retech-us.github.io/retech-mobile-automation/ios/",
        "ci_url": "https://github.com/retech-us/retech-mobile-automation/actions",
        "summary_url": "https://retech-us.github.io/retech-mobile-automation/run-summary.json",
        "widget_url": "https://retech-us.github.io/retech-mobile-automation/ios/widgets/summary.json",
        "environment_url": "https://retech-us.github.io/retech-mobile-automation/ios/widgets/environment.json",
        "executors_url": "https://retech-us.github.io/retech-mobile-automation/ios/widgets/executors.json",
        "repo_name": "retech-us/retech-mobile-automation",
        "platform": "iOS",
        "default_environment": "Alpha app",
    },
    "mobile-android": {
        "report_url": "https://retech-us.github.io/retech-mobile-automation/android/",
        "ci_url": "https://github.com/retech-us/retech-mobile-automation/actions",
        "summary_url": "https://retech-us.github.io/retech-mobile-automation/run-summary.json",
        "widget_url": "https://retech-us.github.io/retech-mobile-automation/android/widgets/summary.json",
        "environment_url": "https://retech-us.github.io/retech-mobile-automation/android/widgets/environment.json",
        "executors_url": "https://retech-us.github.io/retech-mobile-automation/android/widgets/executors.json",
        "repo_name": "retech-us/retech-mobile-automation",
        "platform": "Android",
        "default_environment": "Alpha app",
    },
    "api": {
        "report_url": "https://retech-us.github.io/retech-api-automation/",
        "ci_url": "https://github.com/retech-us/retech-api-automation/actions",
        "summary_url": "https://retech-us.github.io/retech-api-automation/run-summary.json",
        "widget_url": "https://retech-us.github.io/retech-api-automation/widgets/summary.json",
        "environment_url": "https://retech-us.github.io/retech-api-automation/widgets/environment.json",
        "executors_url": "https://retech-us.github.io/retech-api-automation/widgets/executors.json",
        "repo_name": "retech-us/retech-api-automation",
    },
}


def fetch_json(url: str):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "automation-dashboard/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, ValueError):
        return None


def format_app_environment(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None
    if normalized.endswith(" app"):
        return normalized[0].upper() + normalized[1:]
    return normalized[0].upper() + normalized[1:] + " app"


def resolve_environment(env_meta: dict, cfg: dict) -> str | None:
    if cfg.get("default_environment"):
        raw = env_meta.get("environment") or env_meta.get("instance")
        if raw:
            return format_app_environment(str(raw))
        return cfg.get("default_environment")
    return env_meta.get("environment") or env_meta.get("instance")


def parse_environment(widget: list | None) -> dict:
    if not widget:
        return {}
    lookup = {}
    for item in widget:
        name = item.get("name", "")
        values = item.get("values") or []
        if values:
            lookup[name] = values[0]
    return {
        "branch": lookup.get("Branch") or lookup.get("Git Branch"),
        "commit": lookup.get("Commit.SHA") or lookup.get("Commit"),
        "environment": (
            lookup.get("Environment")
            or lookup.get("Test Environment")
            or lookup.get("Instance")
        ),
        "instance": lookup.get("Instance"),
        "baseUrl": lookup.get("Base URL"),
        "browser": lookup.get("Browser"),
        "workflow": lookup.get("Workflow"),
    }


def compute_rates(summary: dict) -> dict:
    s = summary.get("summary") or {}
    total = int(s.get("total") or 0)
    passed = int(s.get("passed") or 0)
    failed = int(s.get("failed") or 0) + int(s.get("broken") or 0)
    skipped = int(s.get("skipped") or 0)
    if total == 0:
        return {"passPct": 0, "failPct": 0, "skipPct": 0}
    return {
        "passPct": round((passed / total) * 100, 1),
        "failPct": round((failed / total) * 100, 1),
        "skipPct": round((skipped / total) * 100, 1),
    }


def from_widget(repo_id: str, widget: dict, cfg: dict) -> dict:
    stats = widget.get("statistic") or {}
    failed = int(stats.get("failed", 0))
    broken = int(stats.get("broken", 0))
    passed = int(stats.get("passed", 0))
    skipped = int(stats.get("skipped", 0))
    total = int(stats.get("total", 0))
    time_info = widget.get("time") or {}
    stop = time_info.get("stop")
    finished = (
        datetime.fromtimestamp(stop / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if stop
        else datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    status = "failed" if failed + broken > 0 else ("passed" if total > 0 else "unknown")
    payload = {
        "schemaVersion": "1.0",
        "repo": repo_id,
        "repoName": cfg["repo_name"],
        "repository": cfg["repo_name"],
        "status": status,
        "suite": "regression",
        "finishedAt": finished,
        "durationMs": int(time_info.get("duration", 0)),
        "summary": {"total": total, "passed": passed, "failed": failed, "broken": broken, "skipped": skipped},
        "reportUrl": cfg["report_url"],
        "ciRunUrl": cfg["ci_url"],
        "topFailures": [],
        "failureCategories": {},
        "dataSource": "allure-report",
        "reportName": widget.get("reportName"),
    }
    payload["rates"] = compute_rates(payload)
    return payload


def enrich(payload: dict, cfg: dict, env_meta: dict, executors, run_summary: dict | None) -> dict:
    if env_meta.get("branch"):
        payload["branch"] = env_meta["branch"]
    if env_meta.get("commit"):
        payload["commit"] = env_meta["commit"]
    resolved = resolve_environment(env_meta, cfg)
    if resolved:
        payload["environment"] = resolved
    if env_meta.get("instance"):
        payload["instance"] = env_meta["instance"]
    if env_meta.get("baseUrl"):
        payload["baseUrl"] = env_meta["baseUrl"]
    if env_meta.get("browser"):
        payload["browser"] = env_meta["browser"]
    if env_meta.get("workflow"):
        payload["workflow"] = env_meta["workflow"]

    if isinstance(executors, list) and executors:
        ex = executors[0]
        if ex.get("buildUrl"):
            payload["ciRunUrl"] = ex["buildUrl"]
        if ex.get("buildName") and not payload.get("workflow"):
            payload["workflow"] = ex["buildName"]

    if run_summary:
        if not payload.get("branch") and run_summary.get("branch"):
            payload["branch"] = run_summary["branch"]
        if not payload.get("commit") and run_summary.get("commit"):
            payload["commit"] = run_summary["commit"]
        if run_summary.get("topFailures"):
            payload["topFailures"] = run_summary["topFailures"]
        if run_summary.get("failureCategories"):
            payload["failureCategories"] = run_summary["failureCategories"]
        if run_summary.get("runId"):
            payload["runId"] = run_summary["runId"]
        if run_summary.get("ciRunUrl") and not executors:
            payload["ciRunUrl"] = run_summary["ciRunUrl"]

    payload["rates"] = compute_rates(payload)
    return payload


def placeholder(repo_id: str, cfg: dict) -> dict:
    return {
        "schemaVersion": "1.0",
        "repo": repo_id,
        "repoName": cfg["repo_name"],
        "status": "unknown",
        "summary": {"total": 0, "passed": 0, "failed": 0, "broken": 0, "skipped": 0},
        "rates": {"passPct": 0, "failPct": 0, "skipPct": 0},
        "reportUrl": cfg["report_url"],
        "ciRunUrl": cfg["ci_url"],
        "topFailures": [],
        "failureCategories": {},
        "dataSource": "unavailable",
    }


def fetch_repo(repo_id: str) -> dict:
    cfg = REPOS[repo_id]
    widget = fetch_json(cfg["widget_url"])
    run_summary = fetch_json(cfg["summary_url"])
    executors = fetch_json(cfg["executors_url"])

    env_meta = parse_environment(fetch_json(cfg["environment_url"]))

    if widget and widget.get("statistic"):
        payload = from_widget(repo_id, widget, cfg)
    elif run_summary and run_summary.get("repo"):
        payload = dict(run_summary)
        payload["dataSource"] = "run-summary.json"
        payload["rates"] = compute_rates(payload)
    else:
        return placeholder(repo_id, cfg)

    if cfg.get("platform"):
        payload["platform"] = cfg["platform"]

    return enrich(payload, cfg, env_meta, executors, run_summary if run_summary and run_summary.get("repo") else None)


def main() -> int:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data")
    out_dir.mkdir(parents=True, exist_ok=True)
    for repo_id in REPOS:
        payload = fetch_repo(repo_id)
        path = out_dir / f"{repo_id}.json"
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
        rates = payload.get("rates", {})
        print(
            f"✅ {repo_id}: {rates.get('passPct', 0)}% pass | "
            f"env={payload.get('environment', '—')} branch={payload.get('branch', '—')}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
