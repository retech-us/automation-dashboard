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
    project_key = JIRA_PROJECT_KEY or "STORE"
    
    issues = [
        {
            "key": f"{project_key}-1042",
            "summary": "Realogram shelf scanner crash on iOS 18 beta during wide-angle capture",
            "project": "Store Intelligence Mobile",
            "projectKey": project_key,
            "fixVersion": "v16.3.0",
            "type": "Bug",
            "status": "In Progress",
            "statusCategory": "indeterminate",
            "priority": "Highest",
            "component": "Mobile iOS",
            "assignee": "Alex Rivera",
            "assigneeAvatar": "https://avatar-management--avatars.us-west-2.prod.public.atl-paas.net/default-avatar.png",
            "tester": "Elena Rostova",
            "reporter": "Automation Bot",
            "created": "2026-08-16T09:14:00.000Z",
            "updated": "2026-08-17T06:30:00.000Z",
            "labels": ["automation-failure", "flaky-triage", "p0-blocker"],
            "url": f"{JIRA_BASE_URL or 'https://your-domain.atlassian.net'}/browse/{project_key}-1042"
        },
        {
            "key": f"{project_key}-1039",
            "summary": "Price tag OCR validation endpoint returns HTTP 504 gateway timeout under load",
            "project": "Store Intelligence Backend",
            "projectKey": project_key,
            "fixVersion": "v16.2.1",
            "type": "Defect",
            "status": "Open",
            "statusCategory": "new",
            "priority": "Highest",
            "component": "API Backend",
            "assignee": "Devin Kumar",
            "assigneeAvatar": "https://avatar-management--avatars.us-west-2.prod.public.atl-paas.net/default-avatar.png",
            "tester": "Vipin Nair",
            "reporter": "API Regression Suite",
            "created": "2026-08-15T14:22:00.000Z",
            "updated": "2026-08-16T11:15:00.000Z",
            "labels": ["perf-regression", "p0-blocker"],
            "url": f"{JIRA_BASE_URL or 'https://your-domain.atlassian.net'}/browse/{project_key}-1039"
        },
        {
            "key": f"{project_key}-1035",
            "summary": "Product approval review modal layout overflows on resolution 1366x768",
            "project": "Store Intelligence Web",
            "projectKey": project_key,
            "fixVersion": "v16.2.0",
            "type": "Bug",
            "status": "In QA / Review",
            "statusCategory": "indeterminate",
            "priority": "High",
            "component": "Web Portal",
            "assignee": "Sarah Chen",
            "assigneeAvatar": "https://avatar-management--avatars.us-west-2.prod.public.atl-paas.net/default-avatar.png",
            "tester": "Vipin Nair",
            "reporter": "Visual SmartUI",
            "created": "2026-08-14T16:05:00.000Z",
            "updated": "2026-08-17T04:20:00.000Z",
            "labels": ["smartui-diff", "frontend"],
            "url": f"{JIRA_BASE_URL or 'https://your-domain.atlassian.net'}/browse/{project_key}-1035"
        },
        {
            "key": f"{project_key}-1028",
            "summary": "Store associate barcode scanning fails to register consecutive rapid scans",
            "project": "Store Intelligence Mobile",
            "projectKey": project_key,
            "fixVersion": "v16.3.0",
            "type": "Bug",
            "status": "In Progress",
            "statusCategory": "indeterminate",
            "priority": "High",
            "component": "Mobile Android",
            "assignee": "Marcus Vance",
            "assigneeAvatar": "https://avatar-management--avatars.us-west-2.prod.public.atl-paas.net/default-avatar.png",
            "tester": "Marcus Vance",
            "reporter": "Marcus Vance",
            "created": "2026-08-13T11:40:00.000Z",
            "updated": "2026-08-16T15:10:00.000Z",
            "labels": ["android-appium"],
            "url": f"{JIRA_BASE_URL or 'https://your-domain.atlassian.net'}/browse/{project_key}-1028"
        },
        {
            "key": f"{project_key}-1022",
            "summary": "Bulk CSV import silently ignores rows with special UTF-8 characters",
            "project": "Store Intelligence Web",
            "projectKey": project_key,
            "fixVersion": "v16.2.0",
            "type": "Defect",
            "status": "Open",
            "statusCategory": "new",
            "priority": "Medium",
            "component": "Web Portal",
            "assignee": "Unassigned",
            "assigneeAvatar": None,
            "tester": "Elena Rostova",
            "reporter": "Elena Rostova",
            "created": "2026-08-12T10:18:00.000Z",
            "updated": "2026-08-15T08:45:00.000Z",
            "labels": ["data-pipeline"],
            "url": f"{JIRA_BASE_URL or 'https://your-domain.atlassian.net'}/browse/{project_key}-1022"
        },
        {
            "key": f"{project_key}-1018",
            "summary": "Session timeout redirect loses user's draft task state",
            "project": "Store Intelligence Web",
            "projectKey": project_key,
            "fixVersion": "v16.1.0",
            "type": "Bug",
            "status": "Done / Closed",
            "statusCategory": "done",
            "priority": "Medium",
            "component": "Web Portal",
            "assignee": "Sarah Chen",
            "assigneeAvatar": "https://avatar-management--avatars.us-west-2.prod.public.atl-paas.net/default-avatar.png",
            "tester": "Devin Kumar",
            "reporter": "Devin Kumar",
            "created": "2026-08-10T08:00:00.000Z",
            "updated": "2026-08-16T18:00:00.000Z",
            "labels": ["auth-ux"],
            "url": f"{JIRA_BASE_URL or 'https://your-domain.atlassian.net'}/browse/{project_key}-1018"
        }
    ]

    return {
        "status": "sample",
        "lastUpdated": now,
        "jiraUrl": JIRA_BASE_URL or "https://your-domain.atlassian.net",
        "projectKey": project_key,
        "summary": {
            "totalDefects": len(issues),
            "openDefects": sum(1 for i in issues if i["statusCategory"] == "new"),
            "blockers": sum(1 for i in issues if i["priority"] in ["Highest", "Blocker", "P0"]),
            "inProgress": sum(1 for i in issues if i["statusCategory"] == "indeterminate" and "qa" not in i["status"].lower()),
            "inQa": sum(1 for i in issues if "qa" in i["status"].lower() or "review" in i["status"].lower()),
            "resolvedThisWeek": sum(1 for i in issues if i["statusCategory"] == "done"),
            "defectDensity": "0.14 defect/test"
        },
        "byPriority": {
            "Highest": 2,
            "High": 2,
            "Medium": 2,
            "Low": 0
        },
        "byComponent": {
            "Web Portal": 3,
            "Mobile iOS": 1,
            "Mobile Android": 1,
            "API Backend": 1
        },
        "byStatus": {
            "Open": 2,
            "In Progress": 2,
            "In QA / Review": 1,
            "Done / Closed": 1
        },
        "filterOptions": {
            "projects": sorted(list(set(i["project"] for i in issues))),
            "fixVersions": sorted(list(set(i["fixVersion"] for i in issues))),
            "types": sorted(list(set(i["type"] for i in issues))),
            "assignees": sorted(list(set(i["assignee"] for i in issues))),
            "testers": sorted(list(set(i["tester"] for i in issues)))
        },
        "issues": issues
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

    # Build search URL with all relevant fields
    params = {
        "jql": jql,
        "maxResults": 100,
        "fields": "summary,status,priority,components,assignee,reporter,created,updated,labels,issuetype,project,fixVersions"
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
        if e.code in (400, 404):
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

    projects_set = set()
    fix_versions_set = set()
    types_set = set()
    assignees_set = set()
    testers_set = set()

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

        # Project
        proj_obj = fields.get("project") or {}
        project_name = proj_obj.get("name") or proj_obj.get("key") or JIRA_PROJECT_KEY or "Main Project"
        proj_key = proj_obj.get("key") or JIRA_PROJECT_KEY or "PROJ"
        projects_set.add(project_name)

        # Fix Versions
        fix_vers = fields.get("fixVersions") or []
        fix_ver_name = fix_vers[0].get("name") if fix_vers else "Unversioned"
        fix_versions_set.add(fix_ver_name)

        # Issue Type
        issue_type_obj = fields.get("issuetype") or {}
        issue_type = issue_type_obj.get("name", "Bug")
        types_set.add(issue_type)

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
        assignees_set.add(assignee_name)

        # Tester / Reporter
        # Check if custom tester field or reporter exists
        reporter_obj = fields.get("reporter")
        tester_name = reporter_obj.get("displayName", "Unknown") if reporter_obj else "Unknown"
        # Check customfield for tester/QA if available
        for k, v in fields.items():
            if k.startswith("customfield_") and isinstance(v, dict) and "displayName" in v:
                if any(term in k.lower() for term in ["tester", "qa", "verified"]):
                    tester_name = v.get("displayName", tester_name)
        testers_set.add(tester_name)

        issues.append({
            "key": key,
            "summary": summary,
            "project": project_name,
            "projectKey": proj_key,
            "fixVersion": fix_ver_name,
            "type": issue_type,
            "status": status_name,
            "statusCategory": status_category,
            "priority": priority_name,
            "component": comp_name,
            "assignee": assignee_name,
            "assigneeAvatar": assignee_avatar,
            "tester": tester_name,
            "reporter": reporter_obj.get("displayName", "Unknown") if reporter_obj else "Unknown",
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
        "filterOptions": {
            "projects": sorted(list(projects_set)),
            "fixVersions": sorted(list(fix_versions_set)),
            "types": sorted(list(types_set)),
            "assignees": sorted(list(assignees_set)),
            "testers": sorted(list(testers_set))
        },
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
