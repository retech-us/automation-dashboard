# Automation Dashboard - API Endpoints (Step 3)

Complete REST API reference for test case generation, scenarios, and Jira synchronization.

---

## Base URL

```
http://localhost:6060/api
```

---

## 1. Session Management

### Create Session
```
POST /api/sessions
Content-Type: application/json

{
  "user_email": "user@example.com",
  "jira_base_url": "https://jira.atlassian.net",
  "jira_email": "jira@example.com",
  "jira_api_token": "token_value",
  "ai_provider": "anthropic",
  "anthropic_api_key": "sk-ant-...",
  "session_hours": 4
}

Response (201):
{
  "status": "success",
  "session": {
    "user_email": "user@example.com",
    "expires_at": "2026-09-10T12:00:00",
    "created_at": "2026-09-10T08:00:00"
  }
}
```

### Get Session
```
GET /api/sessions/{email}

Response (200):
{
  "user_email": "user@example.com",
  "expires_at": "2026-09-10T12:00:00",
  "is_valid": true
}
```

### Refresh Session
```
POST /api/sessions/refresh
Content-Type: application/json

{
  "user_email": "user@example.com",
  "hours": 4
}

Response (200):
{
  "status": "refreshed",
  "hours": 4
}
```

---

## 2. Test Case Generation

### Create Generation
```
POST /api/generations
Content-Type: application/json

{
  "user_email": "user@example.com",
  "jira_issue_key": "REB3-101",
  "jira_instance_url": "https://jira.atlassian.net",
  "ai_provider": "anthropic",
  "ai_model": "claude-3-sonnet-20240229",
  "temperature": 0.3
}

Response (201):
{
  "status": "created",
  "generation_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2026-09-10T10:00:00"
}
```

### Get Generation
```
GET /api/generations/{generation_id}

Response (200):
{
  "generation_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_email": "user@example.com",
  "jira_issue_key": "REB3-101",
  "status": "completed",
  "total_scenarios": 5,
  "successful_scenarios": 5,
  "failed_scenarios": 0,
  "created_at": "2026-09-10T10:00:00",
  "completed_at": "2026-09-10T10:05:00"
}
```

### List User Generations
```
GET /api/generations/user/{email}?limit=50

Response (200):
{
  "generations": [
    {
      "generation_id": "550e8400-e29b-41d4-a716-446655440000",
      "jira_issue_key": "REB3-101",
      "status": "completed",
      "total_scenarios": 5,
      "created_at": "2026-09-10T10:00:00"
    }
  ],
  "total": 1
}
```

### Update Generation Status
```
PUT /api/generations/{generation_id}/status
Content-Type: application/json

{
  "status": "completed",
  "notes": "Generation successful with 5 scenarios"
}

Response (200):
{
  "status": "updated",
  "generation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Delete Generation
```
DELETE /api/generations/{generation_id}

Response (200):
{
  "status": "deleted"
}
```

---

## 3. Scenario Management

### Create Scenario
```
POST /api/scenarios
Content-Type: application/json

{
  "generation_id": "550e8400-e29b-41d4-a716-446655440000",
  "jira_issue_key": "REB3-101",
  "jira_instance_url": "https://jira.atlassian.net",
  "title": "User can login with valid credentials",
  "scenario_type": "positive",
  "category": "authentication",
  "priority": "high",
  "preconditions": ["User is at login page"],
  "steps": [
    {"step": 1, "action": "Enter valid email"},
    {"step": 2, "action": "Enter valid password"},
    {"step": 3, "action": "Click login button"}
  ],
  "expected_result": "User is logged in and redirected to dashboard",
  "automation_hint": "Use Selenium for web automation",
  "tags": ["smoke", "authentication"],
  "scenario_number": 1
}

Response (201):
{
  "status": "created",
  "scenario_id": "660f9511-f40c-52e5-b827-557766551111",
  "created_at": "2026-09-10T10:00:00"
}
```

### Get Scenario
```
GET /api/scenarios/{scenario_id}

Response (200):
{
  "scenario_id": "660f9511-f40c-52e5-b827-557766551111",
  "title": "User can login with valid credentials",
  "scenario_type": "positive",
  "status": "draft",
  "jira_sync_status": "pending",
  "jira_child_issue_key": null,
  "preconditions": ["User is at login page"],
  "steps": [...],
  "expected_result": "User is logged in and redirected to dashboard",
  "approved_by": null,
  "approved_at": null,
  "created_at": "2026-09-10T10:00:00"
}
```

### List Scenarios for Issue
```
GET /api/scenarios/issue/{jira_issue_key}?limit=100

Response (200):
{
  "scenarios": [
    {
      "scenario_id": "660f9511-f40c-52e5-b827-557766551111",
      "title": "User can login with valid credentials",
      "scenario_type": "positive",
      "status": "draft",
      "jira_sync_status": "pending",
      "created_at": "2026-09-10T10:00:00"
    }
  ],
  "total": 1
}
```

### Approve Scenario
```
POST /api/scenarios/{scenario_id}/approve
Content-Type: application/json

{
  "approved_by": "reviewer@example.com"
}

Response (200):
{
  "status": "approved"
}
```

### Reject Scenario
```
POST /api/scenarios/{scenario_id}/reject
Content-Type: application/json

{
  "reason": "Scenario needs more detailed steps",
  "rejected_by": "reviewer@example.com"
}

Response (200):
{
  "status": "rejected"
}
```

### Update Scenario
```
PUT /api/scenarios/{scenario_id}
Content-Type: application/json

{
  "title": "Updated title",
  "steps": [...],
  "expected_result": "Updated result"
}

Response (200):
{
  "status": "updated"
}
```

### Delete Scenario
```
DELETE /api/scenarios/{scenario_id}

Response (200):
{
  "status": "deleted"
}
```

---

## 4. Jira Synchronization

### Get Sync History
```
GET /api/scenarios/{scenario_id}/history?limit=50

Response (200):
{
  "history": [
    {
      "sync_type": "create",
      "sync_direction": "to_jira",
      "status": "success",
      "error": null,
      "synced_at": "2026-09-10T10:05:00",
      "synced_by": "admin@example.com"
    }
  ],
  "total": 1
}
```

### Get Pending Syncs
```
GET /api/jira/pending-syncs?limit=100

Response (200):
{
  "pending_scenarios": [
    {
      "scenario_id": "660f9511-f40c-52e5-b827-557766551111",
      "title": "User can login with valid credentials",
      "jira_issue_key": "REB3-101",
      "status": "approved",
      "created_at": "2026-09-10T10:00:00"
    }
  ],
  "total": 1
}
```

### Sync Scenario to Jira
```
POST /api/jira/sync/{scenario_id}
Content-Type: application/json

{
  "jira_child_issue_key": "REB3-102",
  "jira_child_issue_url": "https://jira.atlassian.net/browse/REB3-102",
  "synced_by": "admin@example.com"
}

Response (200):
{
  "status": "synced",
  "jira_child_issue_key": "REB3-102"
}
```

---

## 5. Analytics & Reporting

### Get Coverage Report
```
GET /api/reports/coverage?jira_instance_url=https://jira.atlassian.net

Response (200):
{
  "coverage_summary": {
    "total_issues": 10,
    "covered_issues": 7,
    "partial_coverage": 2,
    "uncovered_issues": 1
  },
  "by_issue": [
    {
      "jira_issue_key": "REB3-101",
      "total_scenarios": 5,
      "acceptance_criteria": 3,
      "coverage_percentage": 100
    }
  ]
}
```

### Get Sync Statistics
```
GET /api/reports/sync-status?days=30

Response (200):
{
  "statistics": {
    "total": 50,
    "successful": 48,
    "failed": 2,
    "success_rate": 96.0,
    "period_days": 30
  },
  "period_days": 30
}
```

### Get Generation History
```
GET /api/reports/generations?user_email=user@example.com&limit=50

Response (200):
{
  "generations": [
    {
      "generation_id": "550e8400-e29b-41d4-a716-446655440000",
      "user_email": "user@example.com",
      "jira_issue_key": "REB3-101",
      "status": "completed",
      "total_scenarios": 5,
      "successful_scenarios": 5,
      "failed_scenarios": 0,
      "created_at": "2026-09-10T10:00:00"
    }
  ],
  "total": 1
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "error": "Missing required fields"
}
```

### 404 Not Found
```json
{
  "error": "Scenario not found"
}
```

### 500 Internal Server Error
```json
{
  "error": "Error message details"
}
```

---

## Status Codes

| Code | Meaning |
|------|---------|
| 200 | OK - Request successful |
| 201 | Created - Resource created |
| 400 | Bad Request - Invalid input |
| 404 | Not Found - Resource doesn't exist |
| 500 | Server Error - Internal error |

---

## Workflow Example

```
1. Create Session
   POST /api/sessions
   → Returns: session with user_email

2. Create Generation
   POST /api/generations
   → Returns: generation_id

3. Create Scenarios (loop)
   POST /api/scenarios
   → Returns: scenario_id

4. Review Scenarios
   GET /api/scenarios/{scenario_id}

5. Approve/Reject
   POST /api/scenarios/{scenario_id}/approve
   OR
   POST /api/scenarios/{scenario_id}/reject

6. Sync to Jira
   POST /api/jira/sync/{scenario_id}

7. Track Progress
   GET /api/reports/sync-status
```

---

## Integration Notes

All endpoints return JSON responses with proper HTTP status codes. The API uses:
- **Authentication**: Session-based via user_email in requests
- **Pagination**: Limit parameter (default 50, max 100)
- **Timestamps**: ISO 8601 format (UTC)
- **IDs**: UUIDs for generation_id and scenario_id

See `database/repositories.py` for underlying implementation details.
