#!/usr/bin/env python3
"""
Fetch live Jira defects and quality metrics for the Store Intell QA Automation Dashboard.
Queries real Jira projects via Atlassian REST API (/rest/api/3/search/jql) with deep diagnostics.
"""

import os
import sys
import json
import base64
import datetime
import urllib.request
import urllib.parse
import urllib.error

raw_base_url = os.environ.get("JIRA_BASE_URL", "").strip().rstrip("/")
if raw_base_url and not raw_base_url.startswith("http://") and not raw_base_url.startswith("https://"):
    raw_base_url = f"https://{raw_base_url}"

JIRA_BASE_URL = raw_base_url
JIRA_USER_EMAIL = os.environ.get("JIRA_USER_EMAIL", "").strip()
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN", "").strip()
JIRA_PROJECT_KEY = os.environ.get("JIRA_PROJECT_KEY", "").strip()
JIRA_CUSTOM_JQL = os.environ.get("JIRA_JQL", "").strip()

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "jira.json")


def make_jira_request(url, method="GET", body_dict=None, headers=None, fallback_bearer=True):
    """Execute authenticated request to Jira API with automatic Basic/Bearer fallback."""
    data_bytes = json.dumps(body_dict).encode("utf-8") if body_dict else None
    req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        if err.code == 401 and fallback_bearer and JIRA_API_TOKEN:
            # If Basic Auth returned 401, retry with Bearer Auth
            bearer_headers = dict(headers)
            bearer_headers["Authorization"] = f"Bearer {JIRA_API_TOKEN}"
            req_bearer = urllib.request.Request(url, data=data_bytes, headers=bearer_headers, method=method)
            try:
                with urllib.request.urlopen(req_bearer, timeout=30) as resp2:
                    return json.loads(resp2.read().decode("utf-8"))
            except Exception:
                pass
        raise


def fetch_jira_live():
    print(f"[Jira Fetcher] Config Check:")
    print(f"  - Base URL: {JIRA_BASE_URL or '(Not set)'}")
    print(f"  - User Email: {JIRA_USER_EMAIL or '(Not set)'}")
    print(f"  - API Token: {'(Set - ' + str(len(JIRA_API_TOKEN)) + ' chars)' if JIRA_API_TOKEN else '(Not set)'}")
    print(f"  - Project Key: {JIRA_PROJECT_KEY or '(Not set)'}")
    print(f"  - Custom JQL: {JIRA_CUSTOM_JQL or '(None)'}")

    if not (JIRA_BASE_URL and JIRA_USER_EMAIL and JIRA_API_TOKEN):
        raise ValueError("Missing required Jira environment secrets (JIRA_BASE_URL, JIRA_USER_EMAIL, JIRA_API_TOKEN)")

    auth_str = f"{JIRA_USER_EMAIL}:{JIRA_API_TOKEN}"
    b64_auth = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")

    headers = {
        "Authorization": f"Basic {b64_auth}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "StoreIntell-QADashboard/1.0"
    }

    # 1. Identity Check: Who does Jira recognize this API token as?
    try:
        myself = make_jira_request(f"{JIRA_BASE_URL}/rest/api/3/myself", headers=headers)
        print(f"[Jira Fetcher] Authenticated Identity: {myself.get('displayName')} | Email: {myself.get('emailAddress')} | Active: {myself.get('active')} | AccountId: {myself.get('accountId')}")
    except Exception as e:
        print(f"[Jira Fetcher] User identity check warning: {e}")

    # 2. Project Access Check: Check specific project directly
    clean_key = JIRA_PROJECT_KEY.strip('"\'')
    if clean_key:
        try:
            proj = make_jira_request(f"{JIRA_BASE_URL}/rest/api/3/project/{clean_key}", headers=headers)
            print(f"[Jira Fetcher] Direct Project Check '{clean_key}': FOUND (Name: {proj.get('name')}, ID: {proj.get('id')})")
        except urllib.error.HTTPError as pe:
            err_body = pe.read().decode('utf-8') if hasattr(pe, 'read') else ''
            print(f"[Jira Fetcher] Direct Project Check '{clean_key}' returned HTTP {pe.code}: {err_body}")
        except Exception as pe:
            print(f"[Jira Fetcher] Direct Project Check '{clean_key}' failed: {pe}")

    # 3. List all accessible projects
    try:
        projects_data = make_jira_request(f"{JIRA_BASE_URL}/rest/api/3/project", headers=headers)
        if isinstance(projects_data, list):
            avail_projs = [f"{p.get('key')} ({p.get('name')})" for p in projects_data]
            print(f"[Jira Fetcher] Accessible Projects via list API ({len(projects_data)}): {', '.join(avail_projs) if avail_projs else 'None'}")
    except Exception as e:
        print(f"[Jira Fetcher] Project list check skipped: {e}")

    fields_list = [
        "summary", "status", "priority", "components", "assignee",
        "reporter", "created", "updated", "labels", "issuetype",
        "project", "fixVersions", "description", "parent", "epic",
        "customfield_10014", "customfield_10008", "customfield_10011",
        "customfield_10018", "customfield_10004", "subtasks", "issuelinks"
    ]

    # 4. Construct candidate bounded JQL queries
    jql_candidates = []
    if JIRA_CUSTOM_JQL:
        jql_candidates.append(JIRA_CUSTOM_JQL)
    if clean_key:
        jql_candidates.append(f'project = "{clean_key}"')
        jql_candidates.append(f'project = {clean_key}')
        jql_candidates.append(f'project in ("{clean_key}")')
        jql_candidates.append(f'project = "{clean_key}" AND created >= -365d')
    # Bounded fallback to any created issue in the workspace
    jql_candidates.append('created >= -365d ORDER BY created DESC')

    raw_issues = []
    executed_jql = ""

    for jql in jql_candidates:
        print(f"[Jira Fetcher] Querying JQL: {jql}")
        endpoints = [
            # 1. POST /rest/api/3/search/jql
            {
                "url": f"{JIRA_BASE_URL}/rest/api/3/search/jql",
                "method": "POST",
                "body": {"jql": jql, "maxResults": 100, "fields": fields_list}
            },
            # 2. GET /rest/api/3/search/jql
            {
                "url": f"{JIRA_BASE_URL}/rest/api/3/search/jql?jql={urllib.parse.quote(jql)}&maxResults=100&fields={','.join(fields_list)}",
                "method": "GET",
                "body": None
            }
        ]

        for ep in endpoints:
            try:
                data = make_jira_request(ep["url"], method=ep["method"], body_dict=ep["body"], headers=headers)
                if data:
                    issues_found = data.get("issues") or data.get("values") or data.get("results") or []
                    print(f"[Jira Fetcher] {ep['method']} {ep['url'][:55]}... -> {len(issues_found)} issues found")
                    if len(issues_found) > 0:
                        raw_issues = issues_found
                        executed_jql = jql
                        break
            except urllib.error.HTTPError as err:
                err_content = ""
                try:
                    err_content = err.read().decode("utf-8")
                except Exception:
                    pass
                print(f"[Jira Fetcher] HTTP {err.code} on [{jql}]: {err_content}")
            except Exception as ex:
                print(f"[Jira Fetcher] Error on [{jql}]: {ex}")

        if len(raw_issues) > 0:
            break

    print(f"[Jira Fetcher] Final issue count retrieved: {len(raw_issues)}")

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
        status_category = status_obj.get("statusCategory", {}).get("key", "new")

        priority_obj = fields.get("priority") or {}
        priority_name = priority_obj.get("name", "Medium")

        # Project
        proj_obj = fields.get("project") or {}
        project_name = proj_obj.get("name") or proj_obj.get("key") or clean_key or "Project"
        proj_key = proj_obj.get("key") or clean_key or "PROJ"
        projects_set.add(project_name)

        # Fix Versions
        fix_vers = fields.get("fixVersions") or []
        fix_ver_name = fix_vers[0].get("name") if fix_vers else "Unversioned"
        is_released = bool(fix_vers[0].get("released", False)) if fix_vers else False
        release_status = "Released" if is_released else ("Unreleased" if fix_ver_name != "Unversioned" else "Unversioned")
        fix_versions_set.add(fix_ver_name)

        # Issue Type
        issue_type_obj = fields.get("issuetype") or {}
        issue_type = issue_type_obj.get("name", "Bug")
        types_set.add(issue_type)

        # Priority Counts
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
        if status_category == "done" or status_name.lower() in ["closed", "done", "resolved"]:
            done_count += 1
            updated_str = fields.get("updated", "")
            if updated_str:
                try:
                    updated_dt = datetime.datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
                    if updated_dt >= seven_days_ago:
                        resolved_this_week += 1
                except Exception:
                    pass
        elif any(k in status_name.lower() for k in ["qa", "review", "testing", "verified"]):
            in_qa_count += 1
        elif status_category == "indeterminate" or any(k in status_name.lower() for k in ["progress", "dev"]):
            in_prog_count += 1
        else:
            open_count += 1

        # Assignee
        assignee_obj = fields.get("assignee")
        assignee_name = assignee_obj.get("displayName", "Unassigned") if assignee_obj else "Unassigned"
        assignee_avatar = assignee_obj.get("avatarUrls", {}).get("48x48") if assignee_obj else None
        assignees_set.add(assignee_name)

        # Epic / Parent
        parent_obj = fields.get("parent") or {}
        epic_name = ""
        if issue_type.lower() == "epic":
            epic_name = summary
        elif parent_obj:
            p_key = parent_obj.get("key", "")
            p_sum = parent_obj.get("fields", {}).get("summary", "")
            epic_name = f"{p_key} - {p_sum}" if p_sum else p_key
        else:
            # Check custom fields for epic link / epic name
            for k, v in fields.items():
                if ("epic" in k.lower() or k in ["customfield_10014", "customfield_10008"]) and v:
                    if isinstance(v, str):
                        epic_name = v
                    elif isinstance(v, dict) and "name" in v:
                        epic_name = v["name"]

        # Date calculations
        created_str = fields.get("created", "")
        updated_str = fields.get("updated", "")
        age_days = 0
        stale_days = 0
        if created_str:
            try:
                c_dt = datetime.datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                age_days = max(0, (now - c_dt).days)
            except Exception:
                pass
        if updated_str:
            try:
                u_dt = datetime.datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
                stale_days = max(0, (now - u_dt).days)
            except Exception:
                pass

        # Tester / Reporter
        reporter_obj = fields.get("reporter")
        tester_name = reporter_obj.get("displayName", "Unknown") if reporter_obj else "Unknown"
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
            "isReleased": is_released,
            "releaseStatus": release_status,
            "type": issue_type,
            "epic": epic_name or "None",
            "status": status_name,
            "statusCategory": status_category,
            "priority": priority_name,
            "component": comp_name,
            "assignee": assignee_name,
            "assigneeAvatar": assignee_avatar,
            "tester": tester_name,
            "reporter": reporter_obj.get("displayName", "Unknown") if reporter_obj else "Unknown",
            "created": created_str,
            "updated": updated_str,
            "ageDays": age_days,
            "staleDays": stale_days,
            "labels": fields.get("labels", []),
            "url": f"{JIRA_BASE_URL}/browse/{key}"
        })

    return {
        "status": "live",
        "lastUpdated": now.isoformat(),
        "jiraUrl": JIRA_BASE_URL,
        "projectKey": clean_key or JIRA_PROJECT_KEY,
        "executedJql": executed_jql,
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
        print(f"[Jira Fetcher] Live fetch failed: {err}")
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        data = {
            "status": "error",
            "lastUpdated": now,
            "lastError": str(err),
            "jiraUrl": JIRA_BASE_URL or "https://your-domain.atlassian.net",
            "projectKey": JIRA_PROJECT_KEY or "STORE",
            "summary": {
                "totalDefects": 0,
                "openDefects": 0,
                "blockers": 0,
                "inProgress": 0,
                "inQa": 0,
                "resolvedThisWeek": 0
            },
            "byPriority": {},
            "byComponent": {},
            "byStatus": {},
            "filterOptions": {
                "projects": [],
                "fixVersions": [],
                "types": [],
                "assignees": [],
                "testers": []
            },
            "issues": []
        }

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"[Jira Fetcher] Written output to {OUTPUT_FILE} (status: {data.get('status')}, count: {len(data.get('issues', []))})")


if __name__ == "__main__":
    main()
