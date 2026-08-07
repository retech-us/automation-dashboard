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
        "ai_usage_url": "https://retech-us.github.io/retech-web-automation/ai-usage.json",
        "widget_url": "https://retech-us.github.io/retech-web-automation/widgets/summary.json",
        "environment_url": "https://retech-us.github.io/retech-web-automation/widgets/environment.json",
        "executors_url": "https://retech-us.github.io/retech-web-automation/widgets/executors.json",
        "repo_name": "retech-us/retech-web-automation",
        "github_workflow_hint": "Java CI",
        "framework": "Web · TestNG + Selenium",
        "ai_capable": True,
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
        "framework": "Mobile · Appium",
        "ai_capable": True,
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
        "framework": "Mobile · Appium",
        "ai_capable": True,
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
        "framework": "API · REST Assured",
        "ai_capable": True,
    },
}


def fetch_json(url: str):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "automation-dashboard/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, ValueError):
        return None


def fetch_text(url: str) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "automation-dashboard/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError, ValueError, UnicodeDecodeError):
        return None


AI_ENV_KEYS = {
    "AI.TotalInvocations": "llmInvocations",
    "AI.SuccessfulHealings": "healsSucceeded",
    "AI.FailedHealings": "healsFailed",
    "AI.SkippedInvocations": "healsSkipped",
    "AI.HealSuccessRatePct": "healSuccessRatePct",
    "AI.EstimatedCostUsd": "estimatedCostUsd",
    "AI.EstimatedMinutesSaved": "estimatedMinutesSaved",
    "AI.AvgLatencyMs": "avgAiLatencyMs",
    "AI.ElementInteractions": "elementInteractions",
}

AI_TEST_NAME_HINTS = ("ai usage metrics", "ai usage")
AI_ATTACHMENT_NAMES = frozenset({
    "ai-usage.json",
    "ai-usage-summary.json",
    "ai-metrics.json",
    "ai-effectiveness-summary.json",
})


def _env_lookup(widget: list | None) -> dict[str, str]:
    lookup: dict[str, str] = {}
    if not widget:
        return lookup
    for item in widget:
        name = item.get("name", "")
        values = item.get("values") or []
        if values:
            lookup[name] = str(values[0])
    return lookup


def _parse_metric_value(raw: str) -> float:
    text = str(raw).strip().replace("%", "").replace(",", "")
    try:
        return float(text)
    except (TypeError, ValueError):
        return 0.0


def parse_ai_from_environment(widget: list | None) -> tuple[dict, dict]:
    lookup = _env_lookup(widget)
    summary: dict[str, float] = {}
    for env_key, dest in AI_ENV_KEYS.items():
        if env_key in lookup:
            summary[dest] = _parse_metric_value(lookup[env_key])
    meta = {
        "aiEnabled": lookup.get("SelfHeal.AI.Enabled"),
        "frameworkLabel": lookup.get("Framework") or lookup.get("Test.Framework"),
    }
    return summary, meta


def _has_ai_summary(summary: dict) -> bool:
    return any(_num(summary.get(k)) for k in (
        "llmInvocations", "healsSucceeded", "healsFailed",
        "elementInteractions", "estimatedCostUsd",
    ))


def _walk_allure_ai_tests(nodes: list | None, out: list[str]) -> None:
    for node in nodes or []:
        name = (node.get("name") or "").lower()
        uid = node.get("uid")
        children = node.get("children")
        if children:
            _walk_allure_ai_tests(children, out)
        elif uid and any(hint in name for hint in AI_TEST_NAME_HINTS):
            out.append(uid)


def fetch_ai_from_allure_attachment(report_url: str) -> dict | None:
    suites = fetch_json(f"{report_url.rstrip('/')}/data/suites.json")
    if not suites:
        return None
    uids: list[str] = []
    _walk_allure_ai_tests(suites.get("children"), uids)
    base = report_url.rstrip("/")
    for uid in uids:
        case = fetch_json(f"{base}/data/test-cases/{uid}.json")
        if not case:
            continue
        for att in case.get("attachments") or []:
            name = att.get("name") or ""
            if name not in AI_ATTACHMENT_NAMES:
                continue
            source = att.get("source")
            if not source:
                continue
            body = fetch_text(f"{base}/data/attachments/{source}")
            if not body:
                continue
            try:
                parsed = json.loads(body)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                if isinstance(parsed.get("summary"), dict):
                    return parsed
                return {"summary": parsed, "jobs": parsed.get("jobs") or []}
    return None


def fetch_ai_raw_for_repo(repo_id: str, cfg: dict) -> tuple[dict | None, str | None, dict]:
    """Return (raw metrics doc, source label, extra meta)."""
    meta: dict = {
        "framework": cfg.get("framework"),
        "aiCapable": bool(cfg.get("ai_capable")),
    }
    report_url = cfg.get("report_url", "").rstrip("/")

    for url, source in (
        (f"{report_url}/ai-usage.json", "allure-pages-json"),
        (cfg.get("ai_usage_url"), "ci-json"),
    ):
        if not url:
            continue
        raw = fetch_json(url)
        if isinstance(raw, dict) and (raw.get("summary") or _has_ai_summary(raw)):
            return raw, source, meta

    env_widget = fetch_json(cfg.get("environment_url"))
    env_summary, env_meta = parse_ai_from_environment(env_widget)
    if env_meta.get("aiEnabled") is not None:
        meta["aiEnabled"] = str(env_meta["aiEnabled"]).lower() == "true"
    if env_meta.get("frameworkLabel"):
        meta["frameworkLabel"] = env_meta["frameworkLabel"]
    if _has_ai_summary(env_summary):
        return {"summary": env_summary}, "allure-environment", meta

    att_raw = fetch_ai_from_allure_attachment(cfg.get("report_url", ""))
    if att_raw:
        return att_raw, "allure-attachment", meta

    if meta.get("aiEnabled"):
        return {"summary": {}}, "allure-environment", meta

    return None, None, meta


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
        if run_summary.get("jobs"):
            payload["jobs"] = run_summary["jobs"]
        if run_summary.get("runId"):
            payload["runId"] = run_summary["runId"]
        if run_summary.get("runNumber"):
            payload["runNumber"] = run_summary["runNumber"]
        if run_summary.get("ciRunUrl"):
            payload["ciRunUrl"] = run_summary["ciRunUrl"]

    if not payload.get("environment") and "github.com" in str(payload.get("ciRunUrl", "")):
        payload["environment"] = "CI"

    payload["counts"] = compute_counts(payload)
    return payload


def failures_from_behaviors(behaviors: dict | None, report_url: str, limit: int = 8) -> list[dict]:
    if not behaviors or not isinstance(behaviors.get("items"), list):
        return []
    rows: list[dict] = []
    for item in behaviors["items"]:
        stats = item.get("statistic") or {}
        failed = int(stats.get("failed") or 0)
        broken = int(stats.get("broken") or 0)
        if failed + broken <= 0:
            continue
        status = "failed" if failed > 0 else "broken"
        uid = item.get("uid")
        rows.append({
            "name": item.get("name") or "Unnamed feature",
            "status": status,
            "category": "assertion" if status == "failed" else "unknown",
            "feature": item.get("name"),
            "reason": f"{failed} failed · {broken} broken in feature",
            "reportUrl": f"{report_url}#behaviors/{uid}/" if uid else report_url,
            "_severity": failed * 10 + broken,
        })
    rows.sort(key=lambda row: row.get("_severity", 0), reverse=True)
    for row in rows:
        row.pop("_severity", None)
    return rows[:limit]


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
    payload = enrich_github(payload, cfg)
    behaviors = fetch_json(f"{cfg['report_url']}widgets/behaviors.json")
    if not payload.get("topFailures"):
        payload["topFailures"] = failures_from_behaviors(behaviors, cfg["report_url"])
    return payload


def main() -> int:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data")
    out_dir.mkdir(parents=True, exist_ok=True)
    payloads: dict[str, dict] = {}
    for repo_id in REPOS:
        payload = fetch_repo(repo_id, out_dir)
        path = out_dir / f"{repo_id}.json"
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
        payloads[repo_id] = payload
        counts = payload.get("counts", {})
        source = payload.get("dataSource", "—")
        print(
            f"✅ {repo_id}: {counts.get('total', 0)} tests ({source}) | "
            f"env={payload.get('environment', '—')} instance={payload.get('instance', '—')}"
        )
    append_automation_history(out_dir, payloads)
    fetch_ai_usage(out_dir, payloads)
    fetch_contributors(out_dir)
    return 0


REPO_LABELS = {
    "retech-us/retech-web-automation": "Web",
    "retech-us/retech-mobile-automation": "Mobile",
    "retech-us/retech-api-automation": "API",
}

BOT_LOGINS = frozenset({
    "dependabot", "dependabot-preview", "renovate", "renovate-bot",
    "github-actions", "github-actions-bot",
})


def _is_bot(login: str) -> bool:
    lower = login.lower()
    return lower in BOT_LOGINS or lower.endswith("[bot]") or lower.endswith("-bot")


def _github_api_request(url: str) -> tuple[object | None, str | None]:
    import os

    headers = {"User-Agent": "automation-dashboard/1.0", "Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            next_url = None
            link = resp.headers.get("Link")
            if link:
                for part in link.split(","):
                    if 'rel="next"' in part:
                        next_url = part.split(";")[0].strip().strip("<>")
                        break
            return body, next_url
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, ValueError):
        return None, None


def _fetch_repo_contributors(repo_name: str) -> list[dict]:
    contributors: list[dict] = []
    url = f"https://api.github.com/repos/{repo_name}/contributors?per_page=100&anon=1"
    while url:
        data, next_url = _github_api_request(url)
        if not isinstance(data, list):
            break
        contributors.extend(data)
        url = next_url
    return contributors


def _aggregate_contributors(repos_data: dict[str, list[dict]]) -> list[dict]:
    by_login: dict[str, dict] = {}
    for repo_name, contributors in repos_data.items():
        for entry in contributors:
            login = entry.get("login") or entry.get("name") or "anonymous"
            if _is_bot(str(login)):
                continue
            count = int(entry.get("contributions") or 0)
            if login not in by_login:
                by_login[login] = {
                    "login": login,
                    "name": entry.get("name"),
                    "avatarUrl": entry.get("avatar_url"),
                    "profileUrl": entry.get("html_url") or f"https://github.com/{login}",
                    "contributions": 0,
                    "repos": {},
                }
            by_login[login]["contributions"] += count
            by_login[login]["repos"][repo_name] = by_login[login]["repos"].get(repo_name, 0) + count

    ranked = sorted(by_login.values(), key=lambda row: row["contributions"], reverse=True)
    for index, row in enumerate(ranked, start=1):
        row["rank"] = index
    return ranked


def fetch_contributors(out_dir: Path) -> None:
    unique_repos: list[str] = []
    seen: set[str] = set()
    for cfg in REPOS.values():
        repo_name = cfg.get("repo_name")
        if repo_name and repo_name not in seen:
            seen.add(repo_name)
            unique_repos.append(repo_name)

    repos_data = {repo_name: _fetch_repo_contributors(repo_name) for repo_name in unique_repos}
    ranked = _aggregate_contributors(repos_data)

    doc = {
        "schemaVersion": "1.0",
        "updatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repos": [
            {
                "name": repo_name,
                "label": REPO_LABELS.get(repo_name, repo_name.split("/")[-1]),
                "url": f"https://github.com/{repo_name}",
                "contributorCount": len([
                    c for c in repos_data.get(repo_name, [])
                    if not _is_bot(str(c.get("login") or c.get("name") or ""))
                ]),
            }
            for repo_name in unique_repos
        ],
        "contributors": [
            {
                "rank": row["rank"],
                "login": row["login"],
                "name": row.get("name"),
                "avatarUrl": row.get("avatarUrl"),
                "profileUrl": row.get("profileUrl"),
                "contributions": row["contributions"],
                "repos": [
                    {
                        "name": repo_name,
                        "label": REPO_LABELS.get(repo_name, repo_name),
                        "contributions": count,
                    }
                    for repo_name, count in sorted(
                        row["repos"].items(),
                        key=lambda item: (-item[1], item[0]),
                    )
                ],
            }
            for row in ranked
        ],
        "totals": {
            "uniqueContributors": len(ranked),
            "totalContributions": sum(row["contributions"] for row in ranked),
        },
    }
    path = out_dir / "contributors.json"
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(
        f"👥 contributors: {doc['totals']['uniqueContributors']} people · "
        f"{doc['totals']['totalContributions']} commits → {path}"
    )


def _num(value, default: float = 0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_ai_usage(
    repo_id: str,
    cfg: dict,
    raw: dict | None,
    run_payload: dict | None,
    *,
    source: str | None = None,
    meta: dict | None = None,
) -> dict:
    """Map Allure / CI AI metrics to dashboard contract."""
    meta = meta or {}
    framework = meta.get("frameworkLabel") or cfg.get("framework") or repo_id
    base = {
        "repo": repo_id,
        "repoName": cfg.get("repo_name", repo_id),
        "framework": framework,
        "aiEnabled": meta.get("aiEnabled"),
        "aiCapable": meta.get("aiCapable", bool(cfg.get("ai_capable"))),
        "finishedAt": run_payload.get("finishedAt") if run_payload else None,
        "ciRunUrl": (run_payload or {}).get("ciRunUrl") or cfg.get("ci_url"),
        "reportUrl": cfg.get("report_url"),
    }

    if not raw:
        return {
            **base,
            "status": "pending",
            "summary": {},
            "jobs": [],
            "source": None,
            "note": "No AI metrics in Allure yet — publish via environment.properties or ai-usage.json attachment.",
        }

    summary_src = raw.get("summary") if isinstance(raw.get("summary"), dict) else raw
    merged = {
        "llmInvocations": _num(summary_src.get("llmInvocations") or summary_src.get("aiInvocations") or summary_src.get("llmDecisionCount")),
        "healsSucceeded": _num(summary_src.get("healsSucceeded") or summary_src.get("aiSuccessCount") or summary_src.get("healingSuccessCount")),
        "healsFailed": _num(summary_src.get("healsFailed") or summary_src.get("aiFailureCount") or summary_src.get("healingFailureCount")),
        "healsSkipped": _num(summary_src.get("healsSkipped") or summary_src.get("aiSkippedCount")),
        "healSuccessRatePct": _num(summary_src.get("healSuccessRatePct") or summary_src.get("aiSuccessRatePct") or summary_src.get("healingSuccessRatePct")),
        "elementInteractions": _num(summary_src.get("elementInteractions") or summary_src.get("totalElementInteractions")),
        "estimatedCostUsd": _num(summary_src.get("estimatedCostUsd") or summary_src.get("aiEstimatedCostDollars")),
        "estimatedMinutesSaved": _num(summary_src.get("estimatedMinutesSaved") or summary_src.get("aiEstimatedTimeSavedMinutes")),
        "avgAiLatencyMs": _num(summary_src.get("avgAiLatencyMs") or summary_src.get("aiAverageLatencyMs") or summary_src.get("avgTimeAddedByAiMs")),
        "learnedLocatorsCount": int(_num(summary_src.get("learnedLocatorsCount"))),
        "flakyQuarantineCount": int(_num(summary_src.get("flakyQuarantineCount"))),
    }
    if merged["healSuccessRatePct"] == 0 and merged["healsSucceeded"] + merged["healsFailed"] > 0:
        healed = merged["healsSucceeded"] + merged["healsFailed"]
        merged["healSuccessRatePct"] = round((merged["healsSucceeded"] / healed) * 100, 1)

    jobs = raw.get("jobs") if isinstance(raw.get("jobs"), list) else []
    has_metrics = _has_ai_summary(merged)
    status = "live" if has_metrics else ("enabled" if meta.get("aiEnabled") else "pending")
    note = None
    if status == "enabled":
        note = "AI enabled in Allure environment — run metrics will appear after the next CI publish."
    elif status == "pending":
        note = "No AI metrics in Allure yet — publish via environment.properties or ai-usage.json attachment."

    return {
        **base,
        "repo": raw.get("repo") or repo_id,
        "repoName": raw.get("repoName") or cfg.get("repo_name", repo_id),
        "status": status,
        "source": source,
        "finishedAt": raw.get("finishedAt") or base["finishedAt"],
        "ciRunUrl": raw.get("ciRunUrl") or base["ciRunUrl"],
        "runId": raw.get("runId") or (run_payload or {}).get("runId"),
        "summary": merged,
        "jobs": jobs,
        "topFailingLocators": raw.get("topFailingLocators") or summary_src.get("topFailingLocators") or summary_src.get("topFailingLocatorsFromAi") or {},
        "topHealedModules": raw.get("topHealedModules") or summary_src.get("mostHealedModules") or {},
        "topSkipReasons": raw.get("topSkipReasons") or summary_src.get("topAiSkipReasons") or {},
        "note": note,
    }


def aggregate_ai_totals(repos: dict[str, dict]) -> dict:
    totals = {
        "llmInvocations": 0,
        "healsSucceeded": 0,
        "healsFailed": 0,
        "healsSkipped": 0,
        "healSuccessRatePct": 0,
        "elementInteractions": 0,
        "estimatedCostUsd": 0,
        "estimatedMinutesSaved": 0,
        "avgAiLatencyMs": 0,
        "learnedLocatorsCount": 0,
        "flakyQuarantineCount": 0,
        "reposReporting": 0,
        "frameworksReporting": 0,
        "frameworksWithAiEnabled": 0,
    }
    latency_weight = 0
    for entry in repos.values():
        if entry.get("status") not in ("live", "enabled"):
            continue
        if entry.get("status") == "enabled":
            totals["frameworksWithAiEnabled"] += 1
        s = entry.get("summary") or {}
        if not any(_num(s.get(k)) for k in ("llmInvocations", "healsSucceeded", "elementInteractions")):
            continue
        totals["reposReporting"] += 1
        totals["frameworksReporting"] += 1
        for key in (
            "llmInvocations", "healsSucceeded", "healsFailed", "healsSkipped",
            "elementInteractions", "estimatedCostUsd", "estimatedMinutesSaved",
            "learnedLocatorsCount", "flakyQuarantineCount",
        ):
            totals[key] += _num(s.get(key))
        inv = _num(s.get("llmInvocations"))
        if inv > 0:
            latency_weight += inv
            totals["avgAiLatencyMs"] += _num(s.get("avgAiLatencyMs")) * inv
    if latency_weight > 0:
        totals["avgAiLatencyMs"] = round(totals["avgAiLatencyMs"] / latency_weight, 1)
    healed = totals["healsSucceeded"] + totals["healsFailed"]
    if healed > 0:
        totals["healSuccessRatePct"] = round((totals["healsSucceeded"] / healed) * 100, 1)
    totals["estimatedCostUsd"] = round(totals["estimatedCostUsd"], 4)
    totals["estimatedMinutesSaved"] = round(totals["estimatedMinutesSaved"], 1)
    return totals


def fetch_ai_usage(out_dir: Path, run_payloads: dict[str, dict]) -> None:
    repos: dict[str, dict] = {}
    for repo_id, cfg in REPOS.items():
        raw, source, meta = fetch_ai_raw_for_repo(repo_id, cfg)
        repos[repo_id] = normalize_ai_usage(
            repo_id, cfg, raw, run_payloads.get(repo_id), source=source, meta=meta,
        )

    doc = {
        "schemaVersion": "1.1",
        "updatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repos": repos,
        "totals": aggregate_ai_totals(repos),
    }
    path = out_dir / "ai-usage.json"
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    live = doc["totals"]["reposReporting"]
    enabled = doc["totals"]["frameworksWithAiEnabled"]
    inv = int(doc["totals"]["llmInvocations"])
    print(f"🤖 ai-usage: {live} live · {enabled} AI-enabled · {inv} LLM invocations → {path}")

def _point_from_payload(suite: str, payload: dict) -> dict | None:
    counts = payload.get("counts") or {}
    summary = payload.get("summary") or {}
    total = int(counts.get("total") or summary.get("total") or 0)
    if total <= 0:
        return None
    passed = int(counts.get("passed") or summary.get("passed") or 0)
    failed = int(counts.get("review") or (summary.get("failed", 0) + summary.get("broken", 0)))
    finished = payload.get("finishedAt")
    if finished:
        try:
            day = datetime.fromisoformat(finished.replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            day = datetime.now(timezone.utc).date().isoformat()
    else:
        day = datetime.now(timezone.utc).date().isoformat()
    return {
        "date": day,
        "suite": suite,
        "passPct": round((passed / total) * 100, 1),
        "total": total,
        "passed": passed,
        "failed": failed,
        "source": "ci-snapshot",
    }


def append_automation_history(out_dir: Path, payloads: dict[str, dict]) -> None:
    """Upsert today's (or run-day) pass-rate points for the trend graph."""
    history_dir = out_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    path = history_dir / "automation-trend.json"
    if path.exists():
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            doc = {"schemaVersion": "1.0", "points": []}
    else:
        doc = {"schemaVersion": "1.0", "points": []}

    points = list(doc.get("points") or [])
    index = {(p.get("suite"), p.get("date")): i for i, p in enumerate(points)}
    added = 0
    for suite, payload in payloads.items():
        point = _point_from_payload(suite, payload)
        if not point:
            continue
        key = (point["suite"], point["date"])
        if key in index:
            points[index[key]] = point
        else:
            points.append(point)
            index[key] = len(points) - 1
            added += 1

    points.sort(key=lambda p: (p.get("date") or "", p.get("suite") or ""))
    doc["points"] = points
    doc["updatedAt"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    doc["schemaVersion"] = "1.0"
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(f"📈 history: {len(points)} points ({added} new) → {path}")


if __name__ == "__main__":
    sys.exit(main())
