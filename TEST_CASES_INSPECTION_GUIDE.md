# Where to Inspect Created Test Cases

**Complete guide to finding and viewing generated test cases**

---

## Overview

Test cases are stored and accessible in **4 different locations**:

```
1. 📱 Frontend UI (ScenarioManager)
   └─ Real-time display, approval workflow
   
2. 🗄️ PostgreSQL Database
   └─ Persistent storage, audit trail
   
3. 🎯 Jira Cloud (Child Issues)
   └─ Synced scenarios as subtasks
   
4. 📄 JSON Files (Local)
   └─ Fallback for testing, exports
```

---

## 1. Frontend UI (Easiest - Real-Time) ✅

### View in Dashboard
```
1. Open http://localhost:6060
2. Click "Generate Test Cases" button
3. Enter credentials
4. Select Jira issue
5. Click "Generate"
6. Scroll down to "Test Scenarios" panel
```

### What You See
```
┌─────────────────────────────────────┐
│ 🧪 Test Scenarios                   │
├─────────────────────────────────────┤
│ Filter: [Approved] [Pending Sync] [Synced] │
│                                     │
│ [✓] Scenario 1 - Positive           │
│ └─ Priority: High                   │
│ └─ Preconditions: [1 item]          │
│ └─ Steps: [3 steps]                 │
│ └─ Expected Result: User is logged  │
│ └─ Tags: [smoke] [auth]             │
│ [✓ Approve] [✗ Reject] [🔗 Sync]  │
│                                     │
│ [✓] Scenario 2 - Negative           │
│ └─ [Similar details...]             │
│                                     │
└─────────────────────────────────────┘
```

### Features
- ✅ View all scenario details
- ✅ Approve/Reject scenarios
- ✅ Sync to Jira button
- ✅ Status badges (draft, approved, synced)
- ✅ Real-time updates
- ✅ Filter by status
- ✅ Jira links (when synced)

### Best For
- Quick review during generation
- Approval workflow
- Immediate feedback
- Testing the UI

---

## 2. PostgreSQL Database (Most Comprehensive) ✅

### Access Database

**Connect to PostgreSQL:**
```bash
psql -U automation_user -d automation_dashboard -h localhost
```

### Query Test Scenarios

**View all scenarios:**
```sql
SELECT 
    scenario_id,
    title,
    scenario_type,
    status,
    jira_child_issue_key,
    created_at
FROM test_scenarios
ORDER BY created_at DESC
LIMIT 20;
```

**Output:**
```
                scenario_id                 |              title               | scenario_type | status   | jira_child_issue_key | created_at
────────────────────────────────────────────┼──────────────────────────────────┼───────────────┼──────────┼──────────────────────┼──────────────────────
 660f9511-f40c-52e5-b827-557766551111       | User can login with credentials  | positive      | approved | REB3-102             | 2026-09-10 10:00:00
 770g0612-g51d-63f6-c938-668877552222       | User fails with invalid password | negative      | draft    |                      | 2026-09-10 10:00:05
 880h1723-h62e-74g7-d049-779988663333       | Edge case: SQL injection attempt | edge-case     | rejected | REB3-103             | 2026-09-10 10:00:10
```

### View Full Scenario Details

**Get complete scenario data:**
```sql
SELECT 
    scenario_id,
    title,
    scenario_type,
    priority,
    status,
    preconditions,
    steps,
    expected_result,
    automation_hint,
    tags,
    jira_child_issue_key,
    jira_sync_status,
    approved_by,
    approved_at,
    rejection_reason
FROM test_scenarios
WHERE scenario_id = '660f9511-f40c-52e5-b827-557766551111';
```

**Output (formatted):**
```
scenario_id: 660f9511-f40c-52e5-b827-557766551111
title: User can login with credentials
scenario_type: positive
priority: high
status: approved
preconditions: ["User is on login page", "Browser has cookies enabled"]
steps: [
  {"step": 1, "action": "Enter valid email"},
  {"step": 2, "action": "Enter valid password"},
  {"step": 3, "action": "Click login button"}
]
expected_result: User is logged in and redirected to dashboard
automation_hint: Use Selenium WebDriver for automation
tags: ["smoke", "authentication"]
jira_child_issue_key: REB3-102
jira_sync_status: synced
approved_by: reviewer@example.com
approved_at: 2026-09-10 10:00:00
rejection_reason: NULL
```

### View by Generation

**View all scenarios for a specific generation:**
```sql
SELECT 
    s.title,
    s.scenario_type,
    s.status,
    s.jira_sync_status,
    g.generation_status,
    g.total_scenarios,
    g.successful_scenarios
FROM test_scenarios s
JOIN test_case_generations g ON s.generation_id = g.generation_id
WHERE g.jira_issue_key = 'REB3-101'
ORDER BY s.scenario_number;
```

### View Approval Workflow

**Who approved what and when:**
```sql
SELECT 
    s.title,
    s.approved_by,
    s.approved_at,
    sh.sync_type,
    sh.sync_status,
    sh.synced_at
FROM test_scenarios s
LEFT JOIN sync_history sh ON s.scenario_id = sh.scenario_id
WHERE s.status = 'approved'
ORDER BY s.approved_at DESC;
```

### View Sync History (Audit Trail)

**Complete audit of all changes:**
```sql
SELECT 
    sh.scenario_id,
    sh.sync_direction,
    sh.sync_type,
    sh.sync_status,
    sh.error_message,
    sh.synced_by,
    sh.synced_at
FROM sync_history sh
ORDER BY sh.synced_at DESC
LIMIT 50;
```

**Output:**
```
scenario_id | sync_direction | sync_type | sync_status | error_message | synced_by       | synced_at
────────────┼────────────────┼───────────┼─────────────┼───────────────┼─────────────────┼──────────────────────
660f9511... | to_jira        | create    | success     | NULL          | sync-engine     | 2026-09-10 10:05:00
660f9511... | internal       | approve   | success     | NULL          | reviewer@ex.com | 2026-09-10 10:03:00
770g0612... | internal       | reject    | success     | NULL          | reviewer@ex.com | 2026-09-10 10:04:00
```

### Export to CSV/JSON

**Export scenarios to CSV:**
```bash
psql -U automation_user -d automation_dashboard -h localhost \
  -c "COPY (SELECT title, scenario_type, status, jira_child_issue_key FROM test_scenarios) TO STDOUT WITH CSV HEADER;" \
  > scenarios.csv
```

**Export to JSON:**
```sql
COPY (
  SELECT json_agg(row_to_json(test_scenarios))
  FROM test_scenarios
  WHERE created_at > NOW() - INTERVAL '1 day'
) TO STDOUT;
```

### Best For
- Complete data review
- Historical tracking
- Audit trails
- Reporting and analytics
- Backup and recovery

---

## 3. Jira Cloud (If Synced) ✅

### Find Child Issues in Jira

**Step 1: Open Parent Issue**
```
1. Go to https://retech.atlassian.net
2. Search for issue: REB3-101
3. Click to open the issue
```

**Step 2: View Child Issues**
```
In the issue detail page, scroll to "Child issues" section:

Child issues (5)
├─ REB3-102 - User can login with credentials
├─ REB3-103 - User fails with invalid password
├─ REB3-104 - Edge case: SQL injection attempt
├─ REB3-105 - Session timeout scenario
└─ REB3-106 - Concurrent login attempts
```

### View Test Case Details in Jira

**Click on any child issue (e.g., REB3-102):**
```
Issue: REB3-102
Type: Story
Status: To Do
Assignee: Unassigned
Priority: High

Description:
*Scenario:* User can login with credentials
*Type:* positive
*Priority:* high

*Preconditions:*
  1. User is on login page
  2. Browser has cookies enabled

*Steps:*
  1. Enter valid email
  2. Enter valid password
  3. Click login button

*Expected Result:* User is logged in and redirected to dashboard

*Automation:* Use Selenium WebDriver for automation

*Tags:* smoke, authentication
```

### View Sync History in Comments

**In Jira issue comments (if enabled):**
```
Automation Dashboard Bot - Today 10:05 AM
✓ Synced from test case generation REB3-101
  Generation ID: uuid-123...
  Scenario ID: uuid-456...
  Sync Status: Complete
  Timestamp: 2026-09-10 10:05:00 UTC
```

### Query Jira API Directly

**List all child issues for a parent:**
```bash
curl -u email@company.com:token \
  "https://retech.atlassian.net/rest/api/3/issues/REB3-101/children"
```

**Get specific child issue:**
```bash
curl -u email@company.com:token \
  "https://retech.atlassian.net/rest/api/3/issues/REB3-102" \
  | jq '.'
```

### Best For
- Team collaboration (Jira is shared)
- Sprint planning
- Test execution tracking
- Linking to other Jira issues
- Integration with CI/CD pipelines

---

## 4. JSON Files (Fallback) ✅

### File Locations

**Test cases JSON:**
```
data/test-cases.json
```

**Jira issues JSON (mock):**
```
data/jira.json
```

### View Test Cases File

**Read the JSON file:**
```bash
cat data/test-cases.json | jq '.'
```

**Pretty print (formatted):**
```bash
cat data/test-cases.json | jq '.' | less
```

### Format

**Example structure:**
```json
{
  "testCases": [
    {
      "issueKey": "REB3-101",
      "scenarios": [
        {
          "id": "scenario-1",
          "title": "User can login with credentials",
          "type": "positive",
          "priority": "high",
          "preconditions": [
            "User is on login page",
            "Browser has cookies enabled"
          ],
          "steps": [
            {"step": 1, "action": "Enter valid email"},
            {"step": 2, "action": "Enter valid password"},
            {"step": 3, "action": "Click login button"}
          ],
          "expectedResult": "User is logged in and redirected to dashboard",
          "automationHint": "Use Selenium WebDriver for automation",
          "tags": ["smoke", "authentication"]
        }
      ]
    }
  ],
  "totalIssues": 1
}
```

### Best For
- Testing without database
- Local development
- Portable data export
- Version control (if needed)
- Integration testing

---

## Quick Comparison

| Feature | Frontend | Database | Jira | JSON |
|---------|----------|----------|------|------|
| **View Details** | ✅ Yes | ✅ Complete | ✅ Limited | ✅ Limited |
| **Approve/Reject** | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **Sync to Jira** | ✅ Yes | ❌ No | ❌ Yes | ❌ No |
| **Audit Trail** | ❌ No | ✅ Yes | ✅ Comments | ❌ No |
| **Real-time** | ✅ Yes | ✅ Instant | ✅ Instant | ❌ Static |
| **Export** | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes |
| **Search** | ❌ No | ✅ SQL | ✅ JQL | ❌ No |
| **Persist** | ❌ Session | ✅ Forever | ✅ Forever | ❌ File |

---

## Recommended Inspection Workflow

### Step 1: Immediate Review (UI)
```
1. After generation completes
2. Scroll to "Test Scenarios" panel
3. Review scenario details
4. Approve/Reject as needed
```

### Step 2: Database Verification
```bash
psql -U automation_user -d automation_dashboard
SELECT COUNT(*) FROM test_scenarios;
SELECT * FROM test_scenarios LIMIT 5;
```

### Step 3: Jira Sync Check
```
1. Click "Sync to Jira" button
2. Open parent issue in Jira
3. Verify child issues created
4. Review scenario details in child issues
```

### Step 4: Audit Trail Review
```bash
# In psql:
SELECT * FROM sync_history ORDER BY synced_at DESC LIMIT 20;
```

---

## Troubleshooting: Where are my test cases?

### I don't see scenarios in the UI

**Solution 1: Refresh page**
```bash
# Hard refresh browser
Ctrl+Shift+R  (Windows/Linux)
Cmd+Shift+R   (Mac)
```

**Solution 2: Check database**
```sql
SELECT COUNT(*) FROM test_scenarios;
-- Should be > 0
```

**Solution 3: Check logs**
```bash
tail -f logs/app.log | grep -i scenario
```

### Scenarios exist but not in Jira

**Solution 1: Check sync status**
```sql
SELECT jira_sync_status, COUNT(*) 
FROM test_scenarios 
GROUP BY jira_sync_status;
-- Should show "synced" scenarios
```

**Solution 2: Click "Sync to Jira" button**
```
1. In frontend UI
2. Click "🔗 Sync to Jira" button
3. Verify results
```

**Solution 3: Check error logs**
```bash
grep -i "sync.*error\|failed.*sync" logs/app.log
```

### Database shows scenarios but UI doesn't

**Solution 1: Clear browser cache**
```javascript
// In browser console
localStorage.clear()
sessionStorage.clear()
location.reload()
```

**Solution 2: Check generation ID**
```sql
SELECT generation_id FROM test_scenarios LIMIT 1;
-- Should be UUID, not NULL
```

---

## Export/Extract Test Cases

### Export to CSV
```bash
psql -U automation_user -d automation_dashboard \
  -c "\COPY test_scenarios(title, scenario_type, status, expected_result) TO 'export.csv' WITH CSV HEADER"

# Opens: export.csv
```

### Export to Excel (via CSV)
```bash
# 1. Export to CSV
psql -U automation_user -d automation_dashboard \
  -c "\COPY (SELECT title, scenario_type, priority, status, expected_result, automation_hint FROM test_scenarios) TO STDOUT WITH CSV HEADER" \
  > scenarios.csv

# 2. Open in Excel
open scenarios.csv  (Mac)
# or
start scenarios.csv (Windows)
```

### Export as Gherkin (.feature)
```bash
# Query scenarios and format as Gherkin
psql -U automation_user -d automation_dashboard -c "
SELECT 
  'Feature: ' || (SELECT summary FROM jira_issues WHERE key = 'REB3-101') || E'\n' ||
  'Scenario: ' || title || E'\n' ||
  'Given ' || preconditions[1] || E'\n' ||
  'When ' || steps[1]->>'action' || E'\n' ||
  'Then ' || expected_result
FROM test_scenarios
WHERE jira_issue_key = 'REB3-101';
" > features.gherkin
```

### Export to JSON
```bash
psql -U automation_user -d automation_dashboard -c "
SELECT json_pretty(json_agg(row_to_json(t)))
FROM test_scenarios t;
" > scenarios.json
```

---

## Best Practices

### For Manual Testing
1. ✅ Use **Frontend UI** for approval workflow
2. ✅ Use **Jira child issues** for team visibility
3. ✅ Use **Database** for audit trail

### For Automation
1. ✅ Extract from **Database** via SQL
2. ✅ Format as **Gherkin** (.feature files)
3. ✅ Integrate with **CI/CD pipeline**

### For Reporting
1. ✅ Query **Database** for statistics
2. ✅ Export to **CSV/Excel** for analysis
3. ✅ View **Jira dashboard** for team metrics

### For Debugging
1. ✅ Check **logs/app.log** for errors
2. ✅ Query **sync_history** for audit trail
3. ✅ Review **Jira comments** for sync status

---

## Summary

**You can inspect test cases in 4 ways:**

| Location | Purpose | Command |
|----------|---------|---------|
| **🎯 Jira** | Team collaboration | Open browser to retech.atlassian.net |
| **📱 UI** | Quick review | Scroll to "Test Scenarios" panel |
| **🗄️ Database** | Complete audit | `psql` + SQL queries |
| **📄 JSON** | Local export | `cat data/test-cases.json` |

**Recommended: Use all 4 together for complete visibility!**
