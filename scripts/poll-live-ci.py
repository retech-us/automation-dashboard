#!/usr/bin/env python3
"""
Live Test Execution Daemon for Automation Dashboard.
Runs on EC2 backend to monitor GitHub Actions in real time and update data/live-status.json.
"""

import os
import sys
import time
import json
import urllib.request
import urllib.error
import subprocess
from datetime import datetime

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE_STATUS_FILE = os.path.join(BASE_DIR, "data", "live-status.json")

REPOS = [
    {"key": "web", "label": "Web Automation", "icon": "🌐", "repo": "retech-us/retech-web-automation", "workflow_hint": "Java CI"},
    {"key": "api", "label": "API Automation", "icon": "🔌", "repo": "retech-us/retech-api-automation", "workflow_hint": "API"},
    {"key": "mobile-ios", "label": "iOS Mobile", "icon": "🍎", "repo": "retech-us/retech-mobile-automation", "workflow_hint": "Mobile Tests"},
    {"key": "mobile-android", "label": "Android Mobile", "icon": "🤖", "repo": "retech-us/retech-mobile-automation", "workflow_hint": "Mobile Tests"}
]


def load_env_file():
    env_file = os.path.join(BASE_DIR, ".env")
    if os.path.isfile(env_file):
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    if k and not os.environ.get(k):
                        os.environ[k] = v


def make_github_request(url, token=""):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Automation-Dashboard-LiveDaemon/1.0"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_live_job_logs(repo, job_id, token=""):
    if not token:
        return []
    url = f"https://api.github.com/repos/{repo}/actions/jobs/{job_id}/logs"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Automation-Dashboard-LiveDaemon/1.0",
        "Authorization": f"Bearer {token}"
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            text = resp.read().decode("utf-8", errors="ignore")
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            return lines[-50:] if len(lines) > 50 else lines
    except Exception:
        return []


def parse_progress_from_logs(logs):
    total = 0
    completed = 0
    passed = 0
    failed = 0
    skipped = 0
    current_test = "Running test step..."

    for line in reversed(logs):
        if "[QA_LIVE_PROGRESS]" in line:
            try:
                json_str = line.split("[QA_LIVE_PROGRESS]", 1)[1].strip()
                data = json.loads(json_str)
                total = int(data.get("total", 0))
                completed = int(data.get("completed", 0))
                passed = int(data.get("passed", 0))
                failed = int(data.get("failed", 0))
                skipped = int(data.get("skipped", 0))
                current_test = data.get("currentTest") or data.get("details") or current_test
                break
            except Exception:
                pass

    return {
        "total": total,
        "completed": completed,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "currentTest": current_test
    }


def read_current_live_status():
    if os.path.isfile(LIVE_STATUS_FILE):
        try:
            with open(LIVE_STATUS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"updatedAt": datetime.utcnow().isoformat() + "Z", "status": "IDLE", "activeRuns": 0}


def check_and_update():
    load_env_file()
    token = os.environ.get("GITHUB_TOKEN", "").strip()

    status_data = read_current_live_status()
    active_count = 0
    any_run_changed = False

    for cfg in REPOS:
        repo_key = cfg["key"]
        repo_name = cfg["repo"]
        workflow_hint = cfg["workflow_hint"]

        try:
            url = f"https://api.github.com/repos/{repo_name}/actions/runs?status=in_progress&per_page=3"
            data = make_github_request(url, token=token)
            runs = data.get("workflow_runs", [])

            matching_run = None
            for r in runs:
                name = r.get("name", "")
                if workflow_hint.lower() in name.lower():
                    matching_run = r
                    break

            if matching_run:
                active_count += 1
                run_id = matching_run.get("id")
                created_at = matching_run.get("created_at")

                # Fetch running job
                jobs_url = f"https://api.github.com/repos/{repo_name}/actions/runs/{run_id}/jobs"
                jobs_data = make_github_request(jobs_url, token=token)
                jobs = jobs_data.get("jobs", [])
                running_job = next((j for j in jobs if j.get("status") == "in_progress"), jobs[0] if jobs else {})
                job_id = running_job.get("id")
                job_steps = running_job.get("steps", [])

                logs = fetch_live_job_logs(repo_name, job_id, token=token) if job_id else []
                progress = parse_progress_from_logs(logs)

                total = progress["total"]
                completed = progress["completed"]
                passed = progress["passed"]
                failed = progress["failed"]
                skipped = progress["skipped"]
                current_test = progress["currentTest"]

                if total == 0 and job_steps:
                    completed_steps = len([s for s in job_steps if s.get("status") == "completed"])
                    total_steps = max(len(job_steps), 1)
                    percent = round((completed_steps / total_steps) * 100, 1)
                    current_test = next((s.get("name") for s in job_steps if s.get("status") == "in_progress"), "Running test step...")
                else:
                    percent = round((completed / total) * 100, 1) if total > 0 else 0.0

                eta_seconds = 0
                if total > 0 and completed > 0 and created_at:
                    try:
                        start_time = datetime.fromisoformat(created_at.replace("Z", "+00:00")).timestamp()
                        elapsed = max(1, time.time() - start_time)
                        avg_sec = elapsed / completed
                        remaining = total - completed
                        eta_seconds = max(0, int(remaining * avg_sec))
                    except Exception:
                        eta_seconds = (total - completed) * 2

                status_data[repo_key] = {
                    "status": "RUNNING",
                    "runId": run_id,
                    "runNumber": matching_run.get("run_number"),
                    "workflowName": matching_run.get("name"),
                    "htmlUrl": matching_run.get("html_url"),
                    "currentTest": current_test,
                    "total": total,
                    "completed": completed,
                    "passed": passed,
                    "failed": failed,
                    "skipped": skipped,
                    "percent": percent,
                    "etaSeconds": eta_seconds,
                    "createdAt": created_at,
                    "recentLogs": logs[-30:]
                }
                any_run_changed = True
            else:
                # If was running previously, mark as completed
                existing = status_data.get(repo_key, {})
                if existing.get("status") == "RUNNING":
                    existing["status"] = "COMPLETED"
                    existing["percent"] = 100.0
                    existing["etaSeconds"] = 0
                    existing["currentTest"] = "Execution completed"
                    status_data[repo_key] = existing
                    any_run_changed = True

        except Exception as err:
            # Handle rate limit or network glitch gracefully
            pass

    status_data["updatedAt"] = datetime.utcnow().isoformat() + "Z"
    status_data["status"] = "RUNNING" if active_count > 0 else "IDLE"
    status_data["activeRuns"] = active_count

    # Write to live-status.json
    os.makedirs(os.path.dirname(LIVE_STATUS_FILE), exist_ok=True)
    temp_file = LIVE_STATUS_FILE + ".tmp"
    with open(temp_file, "w") as f:
        json.dump(status_data, f, indent=2)
    os.replace(temp_file, LIVE_STATUS_FILE)

    if any_run_changed:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Live CI Status Updated: {active_count} active run(s)")


def main():
    load_env_file()
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    print("=" * 60)
    print("⚡ Automation Dashboard Live CI Daemon Starting...")
    print(f"📁 Monitored Repositories: {len(REPOS)}")
    print(f"🔑 GitHub Token: {'Configured (' + str(len(token)) + ' chars)' if token else 'NOT SET (Rate-limited to 60 req/hr)'}")
    print(f"📄 Target File: {LIVE_STATUS_FILE}")
    print("=" * 60)

    while True:
        try:
            check_and_update()
        except Exception as e:
            print(f"[Error in poller cycle]: {e}")
        time.sleep(5)


if __name__ == "__main__":
    main()
