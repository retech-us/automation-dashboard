#!/usr/bin/env python3
"""Fetch latest run summaries — Allure widgets (live) + run-summary.json (failures)."""

from __future__ import annotations

import json
import re
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
        "github_workflow_hint": "Java CI",
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
        "aggregate_batches": True,
        "github_workflow_hint": "Mobile Tests",
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
        "aggregate_batches": True,
        "github_workflow_hint": "Mobile Tests",
    },
    "api": {
        "report_url": "https://retech-us.github.io/retech-api-automation/",
        "ci_url": "https://github.com/retech-us/retech-api-automation/actions",
        "summary_url": "https://retech-us.github.io/retech-api-automation/run-summary.json",
        "widget_url": "https://retech-us.github.io/retech-api-automation/widgets/summary.json",
        "environment_url": "https://retech-us.github.io/retech-api-automation/widgets/environment.json",
        "executors_url": "https://retech-us.github.io/retech-api-automation/widgets/executors.json",
        "repo_name": "retech-us/retech-api-automation",
        "github_workflow_hint": "API",
    },
}


def fetch_json(url: str):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "automation-dashboard/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, ValueError):
        return None


def parse_environment(widget: list | None) -> dict:
    if not widget:
        return {}
    lookup = {}
    for item in widget:
        name = item.get("name", "")
        values = item.get("values") or []
        if values:
            lookup[name] = values[0]
    ci = lookup.get("CI") == "true" or str(lookup.get("Environment", "")).lower() == "ci"
    instance = lookup.get("Instance")
    base_url = lookup.get("Base URL", "")
    if not instance and base_url:
        match = re.search(r"https?://([^.]+)\.", base_url, re.I)
        if match:
            instance = match.group(1)
    return {
        "branch": lookup.get("Branch") or lookup.get("Git Branch"),
        "commit": lookup.get("Commit.SHA") or lookup.get("Commit"),
        "environment": "CI" if ci else lookup.get("Environment"),
        "instance": instance,
        "baseUrl": base_url or None,
        "browser": lookup.get("Browser"),
        "workflow": lookup.get("Workflow"),
        "app": lookup.get("App"),
        "appName": lookup.get("APP Name") or lookup.get("App Name"),
        "appVersion": lookup.get("App Version"),
        "targetEnvironment": lookup.get("Test Environment"),
        "osName": lookup.get("OS Name") or lookup.get("OS"),
    }


def fetch_github_run(repo_name: str, workflow_hint: str) -> dict | None:
    import os

    url = f"https://api.github.com/repos/{repo_name}/actions/runs?per_page=20&status=completed"
    headers = {"User-Agent": "automation-dashboard/1.0", "Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, ValueError):
        return None
    for run in data.get("workflow_runs") or []:
        name = run.get("name") or ""
        if workflow_hint.lower() not in name.lower():
            continue
        if "pages build" in name.lower():
            continue
        return {
            "branch": run.get("head_branch"),
            "commit": (run.get("head_sha") or "")[:7],
            "ciRunUrl": run.get("html_url"),
            "workflow": name,
            "runNumber": run.get("run_number"),
            "runId": str(run.get("id") or ""),
            "finishedAt": run.get("updated_at"),
        }
    return None


def summarize_history_trend(trend: list | None) -> list[dict]:
    if not isinstance(trend, list):
        return []
    rows = []
    for entry in trend:
        data = entry.get("data") or {}
        total = int(data.get("total") or 0)
        if total <= 0:
            continue
        passed = int(data.get("passed") or 0)
        failed = int(data.get("failed") or 0) + int(data.get("broken") or 0)
        rows.append({
            "passPct": round((passed / total) * 100, 1),
            "total": total,
            "failed": failed,
        })
        if len(rows) >= 6:
            break
    return rows


def merge_widgets(widgets: list[dict]) -> dict | None:
    totals = {"total": 0, "passed": 0, "failed": 0, "broken": 0, "skipped": 0}
    stop = 0
    start = float("inf")
    for widget in widgets:
        stats = widget.get("statistic") or {}
        if not stats.get("total"):
            continue
        totals["total"] += int(stats.get("total", 0))
        totals["passed"] += int(stats.get("passed", 0))
        totals["failed"] += int(stats.get("failed", 0))
        totals["broken"] += int(stats.get("broken", 0))
        totals["skipped"] += int(stats.get("skipped", 0))
        time_info = widget.get("time") or {}
        if time_info.get("stop"):
            stop = max(stop, int(time_info["stop"]))
        if time_info.get("start"):
            start = min(start, int(time_info["start"]))
    if totals["total"] == 0:
        return None
    return {
        "reportName": "Aggregated Allure Report",
        "statistic": totals,
        "time": {
            "start": None if start == float("inf") else start,
            "stop": stop or None,
            "duration": (stop - start) if stop and start != float("inf") else 0,
        },
    }


def fetch_mobile_widget(cfg: dict) -> dict | None:
    primary = fetch_json(cfg["widget_url"])
    if primary and (primary.get("statistic") or {}).get("total", 0) > 0:
        return primary
    widgets = []
    if primary and primary.get("statistic"):
        widgets.append(primary)
    for batch in range(1, 6):
        widget = fetch_json(f"{cfg['report_url']}batch-{batch}/widgets/summary.json")
        if widget and (widget.get("statistic") or {}).get("total", 0) > 0:
            widgets.append(widget)
    return merge_widgets(widgets) or primary


def latest_from_history_trend(trend: list | None) -> dict | None:
    if not trend:
        return None
    for entry in trend:
        data = entry.get("data") or {}
        if int(data.get("total") or 0) > 0:
            return data
    return None


def compute_counts(summary: dict) -> dict:
    s = summary.get("summary") or {}
    total = int(s.get("total") or 0)
    passed = int(s.get("passed") or 0)
    review = int(s.get("failed") or 0) + int(s.get("broken") or 0)
    skipped = int(s.get("skipped") or 0)
    return {"total": total, "passed": passed, "review": review, "skipped": skipped}


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
    payload = {
        "schemaVersion": "1.0",
        "repo": repo_id,
        "repoName": cfg["repo_name"],
        "repository": cfg["repo_name"],
        "status": "unknown" if total == 0 else ("active" if failed + broken > 0 else "stable"),
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
    payload["counts"] = compute_counts(payload)
    return payload


def from_run_summary(repo_id: str, run_summary: dict, cfg: dict) -> dict:
    payload = dict(run_summary)
    payload["repo"] = repo_id
    payload["reportUrl"] = run_summary.get("reportUrl") or cfg["report_url"]
    payload["ciRunUrl"] = run_summary.get("ciRunUrl") or cfg["ci_url"]
    payload["dataSource"] = "run-summary.json"
    payload["counts"] = compute_counts(payload)
    return payload


def resolve_best_payload(
    repo_id: str,
    cfg: dict,
    widget: dict | None,
    history_trend: list | None,
    run_summary: dict | None,
    cached: dict | None,
) -> dict:
    candidates: list[tuple[int, dict]] = []

    def rank(payload: dict, score: int) -> None:
        candidates.append((score, payload))

    stats = (widget or {}).get("statistic") or {}
    if int(stats.get("total") or 0) > 0:
        rank(from_widget(repo_id, widget, cfg), 1000 + int(stats["total"]))
    if run_summary and int((run_summary.get("summary") or {}).get("total") or 0) > 0:
        rank(from_run_summary(repo_id, run_summary, cfg), 900 + int(run_summary["summary"]["total"]))
    trend_stats = latest_from_history_trend(history_trend)
    if trend_stats:
        payload = from_widget(repo_id, {"statistic": trend_stats, "time": {}, "reportName": "Allure Report"}, cfg)
        payload["dataSource"] = "allure-history-trend"
        payload["lastAvailable"] = True
        rank(payload, 800 + int(trend_stats["total"]))
    if cached and int((cached.get("summary") or {}).get("total") or 0) > 0:
        bundled_score = 950 if cached.get("dataSource") and cached.get("dataSource") != "unavailable" else 750
        cached_payload = dict(cached)
        rank(cached_payload, bundled_score + int(cached["summary"]["total"]))
    if widget and widget.get("statistic"):
        rank(from_widget(repo_id, widget, cfg), 50)

    if not candidates:
        return placeholder(repo_id, cfg)
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def placeholder(repo_id: str, cfg: dict) -> dict:
    return {
        "schemaVersion": "1.0",
        "repo": repo_id,
        "repoName": cfg["repo_name"],
        "status": "unknown",
        "summary": {"total": 0, "passed": 0, "failed": 0, "broken": 0, "skipped": 0},
        "counts": {"total": 0, "passed": 0, "review": 0, "skipped": 0},
        "reportUrl": cfg["report_url"],
        "ciRunUrl": cfg["ci_url"],
        "topFailures": [],
        "failureCategories": {},
        "dataSource": "unavailable",
    }


def enrich(payload: dict, cfg: dict, env_meta: dict, executors, run_summary: dict | None) -> dict:
    if env_meta.get("branch"):
        payload["branch"] = env_meta["branch"]
    if env_meta.get("commit"):
        payload["commit"] = env_meta["commit"]
    if env_meta.get("environment"):
        payload["environment"] = env_meta["environment"]
    if env_meta.get("instance"):
        payload["instance"] = env_meta["instance"]
    if env_meta.get("baseUrl"):
        payload["baseUrl"] = env_meta["baseUrl"]
    if env_meta.get("browser"):
        payload["browser"] = env_meta["browser"]
    if env_meta.get("workflow"):
        payload["workflow"] = env_meta["workflow"]
    if env_meta.get("app"):
        payload["app"] = env_meta["app"]
    if env_meta.get("appName"):
        payload["appName"] = env_meta["appName"]
    if env_meta.get("appVersion"):
        payload["appVersion"] = env_meta["appVersion"]
    if env_meta.get("targetEnvironment"):
        payload["targetEnvironment"] = env_meta["targetEnvironment"]
    if env_meta.get("osName"):
        payload["osName"] = env_meta["osName"]

    if isinstance(executors, list) and executors:
        ex = executors[0]
        if ex.get("buildUrl"):
            payload["ciRunUrl"] = ex["buildUrl"]
            if not payload.get("environment") and "github.com" in ex["buildUrl"]:
                payload["environment"] = "CI"
        if ex.get("buildName") and not payload.get("workflow"):
            payload["workflow"] = ex["buildName"]

    if run_summary:
        if not payload.get("branch") and run_summary.get("branch"):
            payload["branch"] = run_summary["branch"]
        if not payload.get("commit") and run_summary.get("commit"):
            payload["commit"] = run_summary["commit"]
        if not payload.get("environment") and run_summary.get("environment"):
            env = str(run_summary["environment"])
            if env.lower() == "ci":
                payload["environment"] = "CI"
        if not payload.get("instance") and run_summary.get("instance"):
            payload["instance"] = run_summary["instance"]
        if run_summary.get("topFailures"):
            payload["topFailures"] = run_summary["topFailures"]
        if run_summary.get("failureCategories"):
            payload["failureCategories"] = run_summary["failureCategories"]
        if run_summary.get("runId"):
            payload["runId"] = run_summary["runId"]
        if run_summary.get("ciRunUrl"):
            payload["ciRunUrl"] = run_summary["ciRunUrl"]

    if not payload.get("environment") and "github.com" in str(payload.get("ciRunUrl", "")):
        payload["environment"] = "CI"

    payload["counts"] = compute_counts(payload)
    return payload


def enrich_github(payload: dict, cfg: dict) -> dict:
    hint = cfg.get("github_workflow_hint")
    if not hint:
        return payload
    gh = fetch_github_run(cfg["repo_name"], hint)
    if not gh:
        return payload
    if not payload.get("branch") and gh.get("branch"):
        payload["branch"] = gh["branch"]
    if not payload.get("commit") and gh.get("commit"):
        payload["commit"] = gh["commit"]
    if gh.get("ciRunUrl"):
        payload["ciRunUrl"] = gh["ciRunUrl"]
    if not payload.get("workflow") and gh.get("workflow"):
        payload["workflow"] = gh["workflow"]
    if not payload.get("runId") and gh.get("runId"):
        payload["runId"] = gh["runId"]
    if gh.get("runNumber"):
        payload["runNumber"] = gh["runNumber"]
    if (not payload.get("finishedAt") or payload.get("durationMs", 0) == 0) and gh.get("finishedAt"):
        payload["finishedAt"] = gh["finishedAt"]
    return payload


def fetch_repo(repo_id: str, out_dir: Path) -> dict:
    cfg = REPOS[repo_id]
    cached_path = out_dir / f"{repo_id}.json"
    cached = None
    if cached_path.exists():
        try:
            cached = json.loads(cached_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            cached = None

    run_summary = fetch_json(cfg["summary_url"])
    executors = fetch_json(cfg["executors_url"])
    env_meta = parse_environment(fetch_json(cfg["environment_url"]))
    history_trend = fetch_json(f"{cfg['report_url']}widgets/history-trend.json")

    if cfg.get("aggregate_batches"):
        widget = fetch_mobile_widget(cfg)
    else:
        widget = fetch_json(cfg["widget_url"])

    payload = resolve_best_payload(repo_id, cfg, widget, history_trend, run_summary, cached)
    payload["historyTrend"] = summarize_history_trend(history_trend)

    if cfg.get("platform"):
        payload["platform"] = cfg["platform"]

    summary_for_enrich = run_summary if run_summary and (run_summary.get("repo") or run_summary.get("summary")) else None
    payload = enrich(payload, cfg, env_meta, executors, summary_for_enrich)
    return enrich_github(payload, cfg)


def main() -> int:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data")
    out_dir.mkdir(parents=True, exist_ok=True)
    for repo_id in REPOS:
        payload = fetch_repo(repo_id, out_dir)
        path = out_dir / f"{repo_id}.json"
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
        counts = payload.get("counts", {})
        source = payload.get("dataSource", "—")
        print(
            f"✅ {repo_id}: {counts.get('total', 0)} tests ({source}) | "
            f"env={payload.get('environment', '—')} instance={payload.get('instance', '—')}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
