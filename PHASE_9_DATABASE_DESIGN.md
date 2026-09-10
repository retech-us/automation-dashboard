# Phase 9: Database Storage + Full Jira Sync

## Overview
Store test cases in PostgreSQL and create/update child issues in Jira for each scenario, with two-way synchronization.

---

## Database Schema

### PostgreSQL Tables

```sql
-- Users/Sessions
CREATE TABLE sessions (
  id SERIAL PRIMARY KEY,
  user_email VARCHAR(255) NOT NULL UNIQUE,
  jira_base_url VARCHAR(500) NOT NULL,
  jira_email VARCHAR(255) NOT NULL,
  jira_api_token VARCHAR(500) NOT NULL,
  ai_provider VARCHAR(50) NOT NULL, -- 'anthropic' or 'openai'
  anthropic_api_key VARCHAR(500),
  openai_api_key VARCHAR(500),
  openai_api_base VARCHAR(500),
  session_expiry TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Jira Issues (Cached)
CREATE TABLE jira_issues (
  id SERIAL PRIMARY KEY,
  jira_instance_url VARCHAR(500) NOT NULL,
  issue_key VARCHAR(50) NOT NULL,
  summary VARCHAR(500) NOT NULL,
  description TEXT,
  issue_type VARCHAR(100),
  status VARCHAR(100),
  priority VARCHAR(50),
  acceptance_criteria JSONB, -- Parsed AC from description
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(jira_instance_url, issue_key)
);

-- Test Case Generations (Master Record)
CREATE TABLE test_case_generations (
  id SERIAL PRIMARY KEY,
  generation_id UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  user_email VARCHAR(255) NOT NULL REFERENCES sessions(user_email),
  jira_issue_key VARCHAR(50) NOT NULL,
  jira_instance_url VARCHAR(500) NOT NULL,
  ai_provider VARCHAR(50) NOT NULL,
  ai_model VARCHAR(100) NOT NULL,
  generation_status VARCHAR(50), -- 'pending', 'generating', 'completed', 'failed'
  total_scenarios INTEGER,
  successful_scenarios INTEGER,
  failed_scenarios INTEGER,
  generation_notes TEXT,
  temperature FLOAT,
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (jira_instance_url, jira_issue_key) REFERENCES jira_issues(jira_instance_url, issue_key)
);

-- Test Scenarios (Individual Test Cases)
CREATE TABLE test_scenarios (
  id SERIAL PRIMARY KEY,
  scenario_id UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  generation_id UUID NOT NULL REFERENCES test_case_generations(generation_id) ON DELETE CASCADE,
  jira_issue_key VARCHAR(50) NOT NULL,
  jira_instance_url VARCHAR(500) NOT NULL,
  scenario_number INTEGER, -- SC-001, SC-002, etc
  title VARCHAR(500) NOT NULL,
  scenario_type VARCHAR(50) NOT NULL, -- 'positive', 'negative', 'edge-case'
  category VARCHAR(100),
  priority VARCHAR(50),
  preconditions JSONB, -- Array of precondition strings
  steps JSONB, -- Array of {stepNumber, action, expectedResult}
  expected_result TEXT,
  automation_hint TEXT,
  tags JSONB, -- Array of tags: @positive, @smoke, @critical
  coverage JSONB, -- Array of acceptance criteria covered
  
  -- Jira Integration
  jira_child_issue_key VARCHAR(50), -- Child issue created in Jira
  jira_child_issue_url VARCHAR(500),
  jira_sync_status VARCHAR(50), -- 'pending', 'synced', 'failed'
  jira_last_sync_at TIMESTAMP,
  
  -- Approval/Validation
  status VARCHAR(50) DEFAULT 'draft', -- 'draft', 'approved', 'rejected', 'in_progress'
  approved_by VARCHAR(255),
  approved_at TIMESTAMP,
  rejection_reason TEXT,
  
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (jira_instance_url, jira_issue_key) REFERENCES jira_issues(jira_instance_url, issue_key)
);

-- Sync History (Audit Trail)
CREATE TABLE sync_history (
  id SERIAL PRIMARY KEY,
  scenario_id UUID REFERENCES test_scenarios(scenario_id) ON DELETE CASCADE,
  sync_direction VARCHAR(50), -- 'to_jira', 'from_jira'
  sync_type VARCHAR(100), -- 'create', 'update', 'delete', 'approve', 'reject'
  previous_state JSONB, -- Before state
  new_state JSONB, -- After state
  sync_status VARCHAR(50), -- 'success', 'failed'
  error_message TEXT,
  synced_by VARCHAR(255),
  synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Acceptance Criteria Mapping
CREATE TABLE acceptance_criteria_coverage (
  id SERIAL PRIMARY KEY,
  scenario_id UUID REFERENCES test_scenarios(scenario_id) ON DELETE CASCADE,
  jira_issue_key VARCHAR(50) NOT NULL,
  ac_number VARCHAR(10), -- AC1, AC2, AC3, etc
  ac_text TEXT,
  coverage_status VARCHAR(50), -- 'covered', 'partial', 'not_covered'
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Team/Project Settings
CREATE TABLE project_settings (
  id SERIAL PRIMARY KEY,
  jira_instance_url VARCHAR(500) NOT NULL UNIQUE,
  project_key VARCHAR(50),
  parent_issue_key VARCHAR(50), -- Epic or parent issue for test case stories
  test_case_issue_type VARCHAR(50) DEFAULT 'Story', -- Issue type for test scenarios
  auto_approve_enabled BOOLEAN DEFAULT false,
  auto_sync_enabled BOOLEAN DEFAULT true,
  notification_enabled BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for Performance
CREATE INDEX idx_jira_issues_key ON jira_issues(issue_key);
CREATE INDEX idx_test_generations_user ON test_case_generations(user_email);
CREATE INDEX idx_test_generations_status ON test_case_generations(generation_status);
CREATE INDEX idx_test_scenarios_jira_issue ON test_scenarios(jira_issue_key);
CREATE INDEX idx_test_scenarios_sync_status ON test_scenarios(jira_sync_status);
CREATE INDEX idx_test_scenarios_approval ON test_scenarios(status);
CREATE INDEX idx_sync_history_scenario ON sync_history(scenario_id);
```

---

## API Endpoints (New/Updated)

### Database Setup
```
POST /api/db/init
- Initialize database schema
- Run migrations
- Set default settings
```

### Generation Management
```
GET /api/generations
- Query: user_email, jira_issue_key, status, limit, offset
- List all test case generations with filters

GET /api/generations/{generation_id}
- Get full generation details with all scenarios

POST /api/generations/{generation_id}/approve
- Approve all scenarios in a generation
- Triggers Jira sync

DELETE /api/generations/{generation_id}
- Delete generation and all associated scenarios
```

### Scenario Management
```
GET /api/scenarios/{scenario_id}
- Get specific scenario details
- Include sync status and Jira link

PUT /api/scenarios/{scenario_id}
- Update scenario (title, steps, etc)
- Triggers Jira sync if approved

DELETE /api/scenarios/{scenario_id}
- Delete scenario
- Delete Jira child issue (if exists)

POST /api/scenarios/{scenario_id}/approve
- Approve single scenario
- Creates/updates Jira child issue

POST /api/scenarios/{scenario_id}/reject
- Reject scenario with reason
- Removes from Jira

POST /api/scenarios/{scenario_id}/sync-to-jira
- Manually trigger sync to Jira
- Create or update child issue
```

### Jira Integration Endpoints
```
POST /api/jira/sync-all
- Sync all pending scenarios to Jira
- Create child issues for each approved scenario

GET /api/jira/issues/{issue_key}/scenarios
- Get all test scenarios for an issue
- Include Jira child issue links

GET /api/jira/child-issue/{child_issue_key}
- Get scenario from Jira child issue key
- Retrieve linked scenario data

POST /api/jira/webhook
- Webhook handler for Jira updates
- Two-way sync trigger
- Update scenario if child issue updated
```

### Reporting/Analytics
```
GET /api/reports/coverage
- Test scenario coverage by issue
- Which acceptance criteria covered

GET /api/reports/sync-status
- Sync success/failure statistics
- Pending syncs

GET /api/reports/generations-history
- Historical generations data
- Trends and metrics
```

---

## Jira Integration Architecture

### Child Issue Template

**Parent Issue (from Jira):**
```
REB3-123: Implement user authentication
├─ AC1: User can login with email/password
├─ AC2: User stays logged in with session token
└─ AC3: User can logout and session clears
```

**Child Issues Created:**
```
REB3-123-SC-001: [TEST] Verify user can login with valid credentials
- Type: Sub-task (or Story in test project)
- Parent: REB3-123
- Description: Generated from scenario
- Labels: @smoke, @critical, @positive
- Custom Fields:
  - Test Type: Positive
  - Scenario ID: <UUID>
  - Coverage: AC1
  - Automation Hint: Selenium code
  - Status: Draft/Approved/Rejected

REB3-123-SC-002: [TEST] Verify login fails with invalid password
- Similar structure...

REB3-123-SC-003: [TEST] Verify session expires after 24 hours
- Similar structure...
```

### Sync Flow Diagram

```
DASHBOARD                          BACKEND                           JIRA
┌─────────────────┐              ┌──────────────┐              ┌──────────────┐
│ Generate        │──POST────────>│ Generate     │              │              │
│ Test Cases      │  (credentials)│ Test Cases   │              │              │
└─────────────────┘              │ (AI API)     │              │              │
                                 │              │              │              │
                                 │ Store in DB  │              │              │
                                 └──────┬───────┘              │              │
                                        │                      │              │
                  ┌─────────────────────┘                      │              │
                  │                                            │              │
            POST /approve              (POST)                 │              │
          ┌──────────────────────────────────────────┐        │              │
          │ For each approved scenario:              │        │              │
          │ 1. Create Jira child issue ─────────────────────>│ Create       │
          │ 2. Link to parent issue                 │        │ Sub-task     │
          │ 3. Set custom fields                    │        │              │
          │ 4. Store child_issue_key in DB          │        │              │
          │ 5. Mark sync_status = 'synced'          │        │              │
          └──────────────────────────────────────────┘        │              │
                                                              │              │
          (OPTIONAL: 2-WAY SYNC)                            │              │
                                                              │              │
          Webhook from Jira ────────────────────────────────>│ Listen       │
          (Issue updated/closed)                             │ (webhook)    │
                  │                                           │              │
                  │<──────────────(PUT)─────────────────────────              │
                  │ Update scenario status                    │              │
                  │ (based on child issue status)             │              │
                  ▼                                           │              │
          Dashboard reflects                                 │              │
          Jira changes                                       │              │
```

---

## Implementation Steps

### Step 1: Database Setup (2-3 hours)
```bash
# 1. Install PostgreSQL
# 2. Create database
createdb automation_dashboard

# 3. Run schema creation script
psql automation_dashboard < schema.sql

# 4. Create migration system (Alembic/Flyway)
# 5. Test connections
```

### Step 2: Backend Database Layer (3-4 hours)
```python
# Create models (SQLAlchemy)
- Session model
- JiraIssue model
- TestCaseGeneration model
- TestScenario model
- SyncHistory model
- AcceptanceCriteria model

# Create repository/DAO layer
- SessionRepo (CRUD)
- GenerationRepo (CRUD + queries)
- ScenarioRepo (CRUD + queries)
- SyncRepo (tracking)

# Create database connection manager
- Connection pooling
- Migration runner
- Transaction management
```

### Step 3: Jira API Extension (2-3 hours)
```python
# Extend JiraClient class
- create_child_issue() - Create test scenario as Jira issue
- update_child_issue() - Update existing child issue
- delete_child_issue() - Delete child issue
- get_child_issues() - Get all test scenarios for an issue
- setup_webhook() - Register webhook for two-way sync
- parse_child_issue_update() - Handle webhook updates
```

### Step 4: API Endpoints (3-4 hours)
```python
# Update server.py
- Add database endpoints
- Implement scenario CRUD
- Implement approval workflow
- Implement Jira sync logic
- Add webhook handler
```

### Step 5: Frontend Integration (4-5 hours)
```javascript
// Update test-case-generator.js
- Add database scenario loading
- Add scenario approval UI
- Add Jira link display
- Add sync status tracking
- Add two-way sync updates

// Create new components
- Scenario review modal
- Approval workflow UI
- Jira link browser
- Sync history viewer
```

### Step 6: Sync Logic (2-3 hours)
```python
# Create sync engine
- Auto-sync after approval
- Manual sync trigger
- Webhook handler
- Two-way sync resolver
- Conflict resolution
- Error recovery
```

---

## Data Flow Examples

### Example 1: Generate → Approve → Sync to Jira

```
1. User selects REB3-123 issue
2. Clicks "Generate Test Cases"
3. AI generates 6 scenarios
4. Scenarios stored in DB with status='draft'
5. Results shown in dashboard

6. User reviews scenarios in dashboard
7. Clicks "Approve All"
   - Each scenario: status='approved'
   - Triggers sync_to_jira for each

8. For each scenario:
   - Create Jira sub-task
   - Link to REB3-123
   - Set description (Given/When/Then)
   - Set labels (@positive, @smoke, etc)
   - Set custom field "Coverage": AC1
   - Store child_issue_key: REB3-123-SC-001
   - Record in sync_history

9. Dashboard shows:
   - Scenario title with Jira link ✓
   - Sync status: "Synced"
   - Child issue: REB3-123-SC-001
```

### Example 2: Jira Child Issue Status Changes

```
1. User opens Jira
2. Finds REB3-123-SC-001 (test scenario)
3. Changes status: Draft → In Progress
4. Jira sends webhook to dashboard

5. Dashboard webhook handler:
   - Receives REB3-123-SC-001 status change
   - Looks up scenario in DB by jira_child_issue_key
   - Updates scenario: status='in_progress'
   - Records in sync_history

6. Dashboard refreshes:
   - Shows scenario status changed ✓
   - Timeline shows: "Updated from Jira"
   - Keeps data in sync
```

### Example 3: Update Scenario After Approval

```
1. Scenario is already approved and synced
2. User edits scenario in dashboard
   - Changes title
   - Modifies test steps
   - Adds new precondition

3. On save:
   - Updates scenario in DB
   - Records previous_state in sync_history
   - Triggers sync_to_jira

4. Jira child issue updated:
   - Description updated with new Given/When/Then
   - Modification tracked in Jira activity

5. Two-way sync:
   - If user also modified in Jira (conflict)
   - Merge logic determines which takes priority
   - Log conflict resolution
```

---

## Configuration Schema

### project_settings table
```json
{
  "jira_instance_url": "https://retech.atlassian.net",
  "project_key": "REB3",
  "parent_issue_key": "REB3-1000",  // Epic for all test scenarios
  "test_case_issue_type": "Story",   // or "Sub-task"
  "auto_approve_enabled": false,
  "auto_sync_enabled": true,
  "notification_enabled": true
}
```

### Jira Custom Fields Setup (Required)
```
Custom Fields to create in Jira:
1. "Test Scenario Type" (Select): positive, negative, edge-case
2. "Scenario ID" (Text): UUID for linking
3. "Coverage" (Multi-select): AC1, AC2, AC3, etc
4. "Automation Hint" (Text): Selenium/Cypress code
5. "Test Category" (Select): functional, security, performance, etc
6. "Related Acceptance Criteria" (Link Issue): Link to parent AC
```

---

## Migration Strategy

### Database Initialization
```sql
-- 1. Run schema.sql (creates all tables)
-- 2. Run seed.sql (initial data)
-- 3. Migrate existing test-cases.json data
--    INSERT INTO test_case_generations (...)
--    SELECT * FROM json_data...
```

### Code Changes Timeline

**Week 1:**
- Day 1-2: Database schema + connection setup
- Day 3: Repository/DAO layer
- Day 4-5: Jira sync logic

**Week 2:**
- Day 1-2: API endpoints
- Day 3-4: Frontend integration
- Day 5: Testing + deployment

---

## Security & Considerations

### Data Protection
```
1. Encrypt sensitive fields:
   - jira_api_token → AES-256
   - anthropic_api_key → AES-256
   - openai_api_key → AES-256

2. Access Control:
   - Session-based authentication
   - User can only see their own generations
   - Admin can see all

3. Audit Trail:
   - Every change logged in sync_history
   - Who made change, when, what changed
```

### Error Handling
```
1. Jira sync failures:
   - Mark as 'failed'
   - Log error reason
   - Allow retry

2. Webhook failures:
   - Implement retry logic
   - Queue failed syncs
   - Notify admin

3. Conflict resolution:
   - Dashboard version takes priority (configurable)
   - Or Jira version takes priority
   - Or manual review required
```

---

## Performance Optimizations

```sql
-- Indexes created (see schema above)
-- Connection pooling: 10-20 connections
-- Query caching for frequently accessed data
-- Pagination: default 50, max 500 scenarios per page

-- Timeline queries optimized for:
- User email lookup: O(1)
- Issue key lookup: O(1)
- Sync status queries: O(n)
- Scenario retrieval: O(1)
```

---

## Testing Strategy

### Unit Tests
- Repository layer CRUD operations
- Sync logic (create/update/delete)
- Conflict resolution
- Data validation

### Integration Tests
- End-to-end flow: generate → approve → sync
- Jira API integration
- Two-way sync webhook
- Database transactions

### Load Tests
- 1000+ concurrent users
- 10000+ test scenarios
- Sync performance under load

---

## Deployment Checklist

- [ ] PostgreSQL installed and running
- [ ] Database schema created
- [ ] Connection pooling configured
- [ ] Jira custom fields created
- [ ] Webhook URL registered in Jira
- [ ] Encryption keys configured
- [ ] Backup strategy in place
- [ ] Monitoring/alerting set up
- [ ] Documentation updated
- [ ] Team trained on new workflow

