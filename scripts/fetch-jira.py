#!/usr/bin/env python3
"""
Fetch live Jira defects and quality metrics for the Store Intell QA Automation Dashboard.
Runs via GitHub Actions on scheduled cron or manual workflow dispatch.
"""

import os
import sys
import json
import base64
import datetime
import urllib.request
import urllib.parse
import urllib.error

JIRA_BASE_URL = os.environ.get("JIRA_BASE_URL", "").rstrip("/")
JIRA_USER_EMAIL = os.environ.get("JIRA_USER_EMAIL", "")
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN", "")
JIRA_PROJECT_KEY = os.environ.get("JIRA_PROJECT_KEY", "")
JIRA_CUSTOM_JQL = os.environ.get("JIRA_JQL", "")

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "jira.json")


def get_mock_data():
    """Fallback sample data when live Jira credentials are not present."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return {
        "status": "sample",
        "lastUpdated": now,
        "jiraUrl": JIRA_BASE_URL or "https://your-domain.atlassian.net",
        "projectKey": JIRA_PROJECT_KEY or "STORE",
        "summary": {
            "totalDefects": 18,
            "openDefects": 11,
            "blockers": 2,
            "inProgress": 4,
            "inQa": 3,
            "resolvedThisWeek": 7,
            "defectDensity": "0.14 defect/test"
        },
        "byPriority": {
            "Highest": 2,
            "High": 5,
            "Medium": 8,
            "Low": 3
        },
        "byComponent": {
            "Web Portal": 6,
            "Mobile iOS": 4,
            "Mobile Android": 3,
            "API Backend": 5
        },
        "byStatus": {
            "Open": 4,
            "In Progress": 4,
            "In QA / Review": 3,
            "Done / Closed": 7
        },
        "issues": [
            {
                "key": f"{JIRA_PROJECT_KEY or 'STORE'}-1042",
                "summary": "Realogram shelf scanner crash on iOS 18 beta during wide-angle capture",
                "status": "In Progress",
                "statusCategory": "indeterminate",
                "priority": "Highest",
                "component": "Mobile iOS",
                "assignee": "Alex Rivera",
                "assigneeAvatar": "https://avatar-management--avatars.us-west-2.prod.public.atl-paas.net/default-avatar.png",
                "reporter": "Automation Bot",
                "created": "2026-08-16T09:14:00.000Z",
                "updated": "2026-08-17T06:30:00.000Z",
                "labels": ["automation-failure", "flaky-triage", "p0-blocker"],
                "url": f"{JIRA_BASE_URL or 'https://your-domain.atlassian.net'}/browse/{JIRA_PROJECT_KEY or 'STORE'}-1042"
            },
            {
                "key": f"{JIRA_PROJECT_KEY or 'STORE'}-1039",
                "summary": "Price tag OCR validation endpoint returns HTTP 504 gateway timeout under load",
                "status": "Open",
                "statusCategory": "new",
                "priority": "Highest",
                "component": "API Backend",
                "assignee": "Devin Kumar",
                "assigneeAvatar": "https://avatar-management--avatars.us-west-2.prod.public.atl-paas.net/default-avatar.png",
                "reporter": "API Regression Suite",
                "created": "2026-08-15T14:22:00.000Z",
                "updated": "2026-08-16T11:15:00.000Z",
                "labels": ["perf-regression", "p0-blocker"],
                "url": f"{JIRA_BASE_URL or 'https://your-domain.atlassian.net'}/browse/{JIRA_PROJECT_KEY or 'STORE'}-1039"
            },
            {
                "key": f"{JIRA_PROJECT_KEY or 'STORE'}-1035",
                "summary": "Product approval review modal layout overflows on resolution 1366x768",
                "status": "In QA / Review",
                "statusCategory": "indeterminate",
                "priority": "High",
                "component": "Web Portal",
                "assignee": "Sarah Chen",
                "assigneeAvatar": "https://avatar-management--avatars.us-west-2.prod.public.atl-paas.net/default-avatar.png",
                "reporter": "Visual SmartUI",
                "created": "2026-08-14T16:05:00.000Z",
                "updated": "2026-08-17T04:20:00.000Z",
                "labels": ["smartui-diff", "frontend"],
                "url": f"{JIRA_BASE_URL or 'https://your-domain.atlassian.net'}/browse/{JIRA_PROJECT_KEY or 'STORE'}-1035"
            },
            {
                "key": f"{JIRA_PROJECT_KEY or 'STORE'}-1028",
                "summary": "Store associate barcode scanning fails to register consecutive rapid scans",
                "status": "In Progress",
                "statusCategory": "indeterminate",
                "priority": "High",
                "component": "Mobile Android",
                "assignee": "Marcus Vance",
                "assigneeAvatar": "https://avatar-management--avatars.us-west-2.prod.public.atl-paas.net/default-avatar.png",
                "reporter": "Marcus Vance",
                "created": "2026-08-13T11:40:00.000Z",
                "updated": "2026-08-16T15:10:00.000Z",
                "labels": ["android-appium"],
                "url": f"{JIRA_BASE_URL or 'https://your-domain.atlassian.net'}/browse/{JIRA_PROJECT_KEY or 'STORE'}-1028"
            },
            {
                "key": f"{JIRA_PROJECT_KEY or 'STORE'}-1022",
                "summary": "Bulk CSV import silently ignores rows with special UTF-8 characters",
                "status": "Open",
                "statusCategory": "new",
                "priority": "Medium",
                "component": "Web Portal",
                "assignee": "Unassigned",
                "assigneeAvatar": None,
                "reporter": "Elena Rostova",
                "created": "2026-08-12T10:18:00.000Z",
                "updated": "2026-08-15T08:45:00.000Z",
                "labels": ["data-pipeline"],
                "url": f"{JIRA_BASE_URL or 'https://your-domain.atlassian.net'}/browse/{JIRA_PROJECT_KEY or 'STORE'}-1022"
            },
            {
                "key": f"{JIRA_PROJECT_KEY or 'STORE'}-1018",
                "summary": "Session timeout redirect loses user's draft task state",
                "status": "Done / Closed",
                "statusCategory": "done",
                "priority": "Medium",
                "component": "Web Portal",
                "assignee": "Sarah Chen",
                "assigneeAvatar": "https://avatar-management--avatars.us-west-2.prod.public.atl-paas.net/default-avatar.png",
                "reporter": "Devin Kumar",
                "created": "2026-08-10T08:00:00.000Z",
                "updated": "2026-08-16T18:00:00.000Z",
                "labels": ["auth-ux"],
                "url": f"{JIRA_BASE_URL or 'https://your-domain.atlassian.net'}/browse/{JIRA_PROJECT_KEY or 'STORE'}-1018"
            }
        ]
    }


def fetch_jira_live():
    if not (JIRA_BASE_URL and JIRA_USER_EMAIL and JIRA_API_TOKEN):
        print("[Jira Fetcher] Missing Jira credentials. Using fallback sample dataset.")
        return get_mock_data()

    # Build JQL query
    if JIRA_CUSTOM_JQL:
        jql = JIRA_CUSTOM_JQL
    elif JIRA_PROJECT_KEY:
        jql = f'project = "{JIRA_PROJECT_KEY}" AND (issuetype in (Bug, Defect, Incident) OR type in (Bug, Defect)) ORDER BY priority DESC, created DESC'
    else:
        jql = 'issuetype in (Bug, Defect) ORDER BY priority DESC, created DESC'

    print(f"[Jira Fetcher] Querying Jira: {JIRA_BASE_URL} with JQL: {jql}")

    # Build search URL
    params = {
        "jql": jql,
        "maxResults": 100,
        "fields": "summary,status,priority,components,assignee,reporter,created,updated,labels,issuetype"
    }
    query_string = urllib.parse.urlencode(params)
    api_url = f"{JIRA_BASE_URL}/rest/api/3/search?{query_string}"

    auth_str = f"{JIRA_USER_EMAIL}:{JIRA_API_TOKEN}"
    b64_auth = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")

    headers = {
        "Authorization": f"Basic {b64_auth}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "StoreIntell-QADashboard/1.0"
    }

    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # Fallback to API v2 if v3 is not supported
        if e.code == 404 or e.code == 400:
            print(f"[Jira Fetcher] API v3 failed ({e.code}), falling back to API v2...")
            api_url_v2 = f"{JIRA_BASE_URL}/rest/api/2/search?{query_string}"
            req_v2 = urllib.request.Request(api_url_v2, headers=headers)
            with urllib.request.urlopen(req_v2, timeout=30) as resp_v2:
                data = json.loads(resp_v2.read().decode("utf-8"))
        else:
            print(f"[Jira Fetcher] HTTP Error {e.code}: {e.read().decode('utf-8')}")
            raise

    raw_issues = data.get("issues", [])
    print(f"[Jira Fetcher] Retrieved {len(raw_issues)} issues from Jira.")

    issues = []
    by_priority = {"Highest": 0, "High": 0, "Medium": 0, "Low": 0, "Lowest": 0}
    by_component = {}
    by_status = {}

    open_count = 0
    in_prog_count = 0
    in_qa_count = 0
    done_count = 0
    blocker_count = 0

    now = datetime.datetime.now(datetime.timezone.utc)
    seven_days_ago = now - datetime.timedelta(days=7)
    resolved_this_week = 0

    for item in raw_issues:
        fields = item.get("fields", {})
        key = item.get("key", "")
        summary = fields.get("summary", "No summary")
        
        status_obj = fields.get("status") or {}
        status_name = status_obj.get("name", "Unknown")
        status_category = status_obj.get("statusCategory", {}).get("key", "new") # new, indeterminate, done

        priority_obj = fields.get("priority") or {}
        priority_name = priority_obj.get("name", "Medium")

        # Normalize priority
        if priority_name in by_priority:
            by_priority[priority_name] += 1
        else:
            by_priority[priority_name] = by_priority.get(priority_name, 0) + 1

        if priority_name in ["Highest", "Blocker", "P0", "P1"]:
            blocker_count += 1

        # Component
        components = fields.get("components") or []
        comp_name = components[0].get("name", "General") if components else "General"
        by_component[comp_name] = by_component.get(comp_name, 0) + 1

        # Status counts
        by_status[status_name] = by_status.get(status_name, 0) + 1
        if status_category == "done":
            done_count += 1
            # Check resolved time
            updated_str = fields.get("updated", "")
            if updated_str:
                try:
                    updated_dt = datetime.datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
                    if updated_dt >= seven_days_ago:
                        resolved_this_week += 1
                except Exception:
                    pass
        elif "qa" in status_name.lower() or "review" in status_name.lower() or "testing" in status_name.lower():
            in_qa_count += 1
        elif status_category == "indeterminate" or "progress" in status_name.lower() or "dev" in status_name.lower():
            in_prog_count += 1
        else:
            open_count += 1

        # Assignee
        assignee_obj = fields.get("assignee")
        assignee_name = assignee_obj.get("displayName", "Unassigned") if assignee_obj else "Unassigned"
        assignee_avatar = assignee_obj.get("avatarUrls", {}).get("48x48") if assignee_obj else None

        # Reporter
        reporter_obj = fields.get("reporter")
        reporter_name = reporter_obj.get("displayName", "Unknown") if reporter_obj else "Unknown"

        issues.append({
            "key": key,
            "summary": summary,
            "status": status_name,
            "statusCategory": status_category,
            "priority": priority_name,
            "component": comp_name,
            "assignee": assignee_name,
            "assigneeAvatar": assignee_avatar,
            "reporter": reporter_name,
            "created": fields.get("created", ""),
            "updated": fields.get("updated", ""),
            "labels": fields.get("labels", []),
            "url": f"{JIRA_BASE_URL}/browse/{key}"
        })

    return {
        "status": "live",
        "lastUpdated": now.isoformat(),
        "jiraUrl": JIRA_BASE_URL,
        "projectKey": JIRA_PROJECT_KEY,
        "summary": {
            "totalDefects": len(issues),
            "openDefects": open_count,
            "blockers": blocker_count,
            "inProgress": in_prog_count,
            "inQa": in_qa_count,
            "resolvedThisWeek": resolved_this_week,
            "resolvedTotal": done_count
        },
        "byPriority": by_priority,
        "byComponent": by_component,
        "byStatus": by_status,
        "issues": issues
    }


def main():
    try:
        data = fetch_jira_live()
    except Exception as err:
        print(f"[Jira Fetcher] Error fetching Jira data ({err}). Generating fallback mock dataset.")
        data = get_mock_data()
        data["lastError"] = str(err)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"[Jira Fetcher] Successfully written Jira data to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
