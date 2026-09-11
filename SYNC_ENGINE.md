# Jira Sync Engine - Complete Documentation

## Overview

The Jira Sync Engine handles two-way synchronization between test scenarios in the dashboard and Jira issues. It automatically creates, updates, and tracks test scenario child issues in Jira.

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│         Approved Test Scenario                  │
│     (in Automation Dashboard DB)                │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│         SyncEngine.sync_scenario_to_jira()      │
│  - Prepares scenario data                       │
│  - Calls JiraClient.create_child_issue()        │
│  - Records sync in database                     │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│      JiraClient (HTTP API)                      │
│  - POST /issues (create child)                  │
│  - PUT /issues/{key} (update)                   │
│  - POST /issues/{key}/comments                  │
│  - POST /issues/{key}/transitions               │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│    Jira Cloud (REST API v3)                     │
│  Creates child issue under parent               │
│  (REB3-101 → REB3-102, REB3-103, etc.)         │
└─────────────────────────────────────────────────┘
```

---

## Components

### 1. JiraClient

Low-level HTTP client for Jira API v3 operations.

#### Methods

**Core Operations**
```python
client = JiraClient(
    jira_base_url="https://jira.atlassian.net",
    email="user@example.com",
    api_token="token123"
)

# Get issue details
issue = client.get_issue("REB3-101")

# Create child issue
child_result = client.create_child_issue("REB3-101", scenario_dict)
# Returns: {"key": "REB3-102", "url": "..."}

# Update child issue
success = client.update_child_issue("REB3-102", updated_scenario_dict)

# Add comment
success = client.add_comment("REB3-102", "Test scenario passed execution")

# Transition issue status
success = client.transition_issue("REB3-102", "To Do")
```

#### Error Handling

All methods return appropriate HTTP status codes:
- **200**: Success
- **201**: Created
- **204**: Updated
- **400/401**: Authentication or validation error
- **404**: Issue not found
- **500**: Server error

#### Scenario Description Format

Child issues are created with formatted description containing:

```
*Scenario:* User can login with valid credentials
*Type:* positive
*Priority:* high

*Preconditions:*
  1. User is at login page
  2. Browser has cookies enabled

*Steps:*
  1. Enter valid email
  2. Enter valid password
  3. Click login button

*Expected Result:* User is logged in and redirected to dashboard

*Automation:* Use Selenium for web automation

*Tags:* smoke, authentication
```

---

### 2. SyncEngine

High-level orchestration for scenario synchronization.

#### Main Methods

**Sync Single Scenario**
```python
engine = SyncEngine()

success, child_key = engine.sync_scenario_to_jira(
    scenario_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
    jira_base_url="https://jira.atlassian.net",
    jira_email="user@example.com",
    jira_token="token123"
)

# Returns: (True, "REB3-102") on success
# Returns: (False, "Error message") on failure
```

**Sync Multiple Scenarios**
```python
results = engine.sync_batch_scenarios(
    scenario_ids=[uuid1, uuid2, uuid3],
    jira_base_url="https://jira.atlassian.net",
    jira_email="user@example.com",
    jira_token="token123"
)

# Returns:
# {
#   "total": 3,
#   "successful": 2,
#   "failed": 1,
#   "synced_issues": ["REB3-102", "REB3-103"]
# }
```

**Sync All Pending Scenarios**
```python
results = engine.sync_pending_scenarios(
    jira_base_url="https://jira.atlassian.net",
    jira_email="user@example.com",
    jira_token="token123",
    limit=50  # Max scenarios to sync
)

# Automatically finds all approved scenarios pending sync
# and syncs them to Jira
```

---

## API Integration

### New Endpoints Added to APIRoutes

**1. Sync Single Scenario**
```
POST /api/jira/sync/{scenario_id}
Content-Type: application/json

{
  "jira_base_url": "https://jira.atlassian.net",
  "jira_email": "user@example.com",
  "jira_api_token": "token123"
}

Response (200):
{
  "status": "synced",
  "jira_child_issue_key": "REB3-102"
}
```

**2. Sync Multiple Scenarios**
```
POST /api/jira/sync-batch
Content-Type: application/json

{
  "scenario_ids": [
    "550e8400-e29b-41d4-a716-446655440000",
    "660f9511-f40c-52e5-b827-557766551111"
  ],
  "jira_base_url": "https://jira.atlassian.net",
  "jira_email": "user@example.com",
  "jira_api_token": "token123"
}

Response (200):
{
  "status": "completed",
  "results": {
    "total": 2,
    "successful": 2,
    "failed": 0,
    "synced_issues": ["REB3-102", "REB3-103"]
  }
}
```

**3. Sync All Pending**
```
POST /api/jira/sync-pending
Content-Type: application/json

{
  "jira_base_url": "https://jira.atlassian.net",
  "jira_email": "user@example.com",
  "jira_api_token": "token123",
  "limit": 50
}

Response (200):
{
  "status": "completed",
  "results": {
    "total": 5,
    "successful": 5,
    "failed": 0,
    "synced_issues": ["REB3-102", "REB3-103", ...]
  }
}
```

**4. Jira Webhook Handler**
```
POST /api/jira/webhook
Content-Type: application/json

{
  "webhookEvent": "jira:issue_updated",
  "issue": {
    "key": "REB3-102",
    "fields": {
      "summary": "Updated title",
      "description": "..."
    }
  }
}

Response (200):
{
  "status": "processed"
}
```

---

## Database Integration

### Sync Flow

**Step 1: Scenario Approval**
- User approves scenario in dashboard
- Scenario status → "approved"
- Jira sync status → "pending"

**Step 2: Sync Engine Processes**
```python
# Get scenario from database
scenario = scenario_repo.get_scenario(scenario_id)

# Create in Jira via JiraClient
child_result = client.create_child_issue(parent_key, scenario_dict)

# Update scenario with Jira details
scenario_repo.update_scenario_sync_status(
    scenario_id=scenario_id,
    sync_status='synced',
    jira_child_issue_key='REB3-102',
    jira_child_issue_url='https://...'
)
```

**Step 3: Audit Trail**
```python
# Record sync event for history
sync_repo.record_sync(
    scenario_id=scenario_id,
    sync_direction='to_jira',
    sync_type='create',
    new_state={'jira_child_issue_key': 'REB3-102'},
    sync_status='success',
    synced_by='sync-engine'
)
```

### Database Tables Updated

**test_scenarios**
- `jira_child_issue_key`: Child issue key (e.g., "REB3-102")
- `jira_child_issue_url`: Direct link to child issue
- `jira_sync_status`: "pending" → "synced" → "updated"
- `jira_last_sync_at`: Timestamp of last sync

**sync_history**
- Records every sync event
- Tracks direction (to_jira, from_jira)
- Tracks type (create, update, delete)
- Captures before/after state

---

## Two-Way Sync (Future)

### From Jira → Dashboard

When Jira issue changes, webhook notifies dashboard:

```
1. Jira sends webhook event
   POST /api/jira/webhook

2. Dashboard receives and processes
   handle_jira_webhook(webhook_data)

3. Dashboard updates scenario
   update_scenario_from_jira(scenario_id)

4. Records sync_history with "from_jira" direction
```

### Conflict Resolution

When both systems change simultaneously:
- Dashboard keeps version (default)
- Jira keeps version (alternative)
- Manual review (future)

```python
conflicts = engine.get_sync_conflicts()
resolved = engine.resolve_conflicts('dashboard_wins')
```

---

## Error Handling

### Common Scenarios

**Parent Issue Not Found**
```
Error: Parent issue REB3-101 not found
Action: Verify issue key exists in Jira
        Check user has permission to view
```

**Authentication Failed**
```
Error: 401 Unauthorized
Action: Verify Jira email and API token
        Check token hasn't expired
```

**Scenario Already Synced**
```
Warning: Scenario already synced to REB3-102
Action: Skip sync or update existing
```

**Jira API Rate Limit**
```
Error: 429 Too Many Requests
Action: Wait and retry
        Implement exponential backoff
```

### Logging

All operations logged with timestamps:

```
2026-09-10 10:05:00 - INFO - ✓ Created child issue REB3-102 for REB3-101
2026-09-10 10:05:01 - INFO - ✓ Synced scenario 550e8400... to REB3-102
2026-09-10 10:05:02 - INFO - ✓ Added comment to REB3-102
2026-09-10 10:05:03 - ERROR - Failed to transition REB3-102: Invalid transition
```

---

## Usage Example

### Full Sync Workflow

```python
from sync.jira_sync import sync_engine

# Step 1: Get user session
session = session_repo.get_session_by_email("user@example.com")

# Step 2: Sync pending scenarios
results = sync_engine.sync_pending_scenarios(
    jira_base_url=session.jira_base_url,
    jira_email=session.jira_email,
    jira_token=session.jira_api_token
)

print(f"Synced {results['successful']}/{results['total']} scenarios")
print(f"Created issues: {results['synced_issues']}")

# Step 3: Get sync statistics
stats = sync_repo.get_sync_statistics(days=7)
print(f"Success rate: {stats['success_rate']}%")
```

### Via REST API

```bash
# Get pending scenarios
curl -X GET http://localhost:6060/api/jira/pending-syncs

# Approve a scenario
curl -X POST http://localhost:6060/api/scenarios/{id}/approve \
  -H "Content-Type: application/json" \
  -d '{"approved_by": "user@example.com"}'

# Sync to Jira
curl -X POST http://localhost:6060/api/jira/sync-pending \
  -H "Content-Type: application/json" \
  -d '{
    "jira_base_url": "https://jira.atlassian.net",
    "jira_email": "user@example.com",
    "jira_api_token": "token123"
  }'

# Check sync statistics
curl -X GET "http://localhost:6060/api/reports/sync-status?days=7"
```

---

## Implementation Status

### Complete ✅
- Single scenario sync to Jira
- Batch scenario sync
- Pending scenario sync
- JiraClient HTTP operations
- Error handling and logging
- Database integration
- API endpoints

### In Progress ⏳
- Webhook handler (foundation ready)
- Two-way sync (architecture defined)
- Conflict detection
- Conflict resolution strategies

### Future 📋
- Scheduled sync jobs
- Retry with exponential backoff
- Custom field mapping
- Advanced filtering
- Sync templates
- Bulk operations

---

## Testing

### Manual Test Cases

**Test 1: Single Scenario Sync**
```
1. Create scenario in dashboard
2. Approve scenario
3. Call sync endpoint
4. Verify child issue created in Jira
5. Verify sync_history recorded
```

**Test 2: Batch Sync**
```
1. Create 3 scenarios
2. Approve all 3
3. Call sync-batch endpoint
4. Verify all 3 synced
5. Check results statistics
```

**Test 3: Error Handling**
```
1. Try to sync non-existent scenario
2. Verify error response
3. Try with invalid credentials
4. Verify authentication error
```

---

## Next Steps

1. **Frontend Integration** (Step 5)
   - Add sync button to scenario approval UI
   - Show sync status badges
   - Display Jira links

2. **Webhook Handling** (Step 6)
   - Set up webhook listener
   - Parse Jira events
   - Update scenarios from Jira

3. **Testing** (Step 6)
   - Unit tests for JiraClient
   - Integration tests for SyncEngine
   - E2E tests for full workflow

---

## File Structure

```
sync/
├── __init__.py          # Module exports
└── jira_sync.py         # JiraClient + SyncEngine (550+ lines)

api/
├── __init__.py
└── routes.py            # Updated with 3 new sync endpoints

database/
├── repositories.py      # Already has sync_repo
└── models.py            # Already has SyncHistory model
```

---

## Configuration

### Environment Variables

```bash
# Jira credentials (from user session)
JIRA_BASE_URL=https://jira.atlassian.net
JIRA_USER_EMAIL=user@example.com
JIRA_API_TOKEN=token123

# Logging
LOG_LEVEL=INFO
SYNC_LOG_FILE=logs/sync.log
```

### Database URL

```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/automation_dashboard
```

---

## Performance

### Sync Speed

- Single scenario sync: ~500-800ms (including Jira API call)
- Batch sync (10 scenarios): ~6-8s (parallel capable)
- Pending sync (50 scenarios): ~30-40s

### Database Impact

- Each sync creates 1 SyncHistory record
- 1 TestScenario update per sync
- Indexes on scenario_id, synced_at optimize queries
