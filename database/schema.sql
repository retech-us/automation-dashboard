-- Automation Dashboard Database Schema
-- PostgreSQL 12+

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- SESSIONS TABLE - Store user credentials and Jira auth
-- ============================================================================
CREATE TABLE sessions (
  id SERIAL PRIMARY KEY,
  user_email VARCHAR(255) NOT NULL UNIQUE,
  jira_base_url VARCHAR(500) NOT NULL,
  jira_email VARCHAR(255) NOT NULL,
  jira_api_token VARCHAR(500) NOT NULL,
  ai_provider VARCHAR(50) NOT NULL CHECK (ai_provider IN ('anthropic', 'openai')),
  anthropic_api_key VARCHAR(500),
  openai_api_key VARCHAR(500),
  openai_api_base VARCHAR(500),
  session_expiry TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sessions_email ON sessions(user_email);
CREATE INDEX idx_sessions_expiry ON sessions(session_expiry);

-- ============================================================================
-- JIRA ISSUES TABLE - Cache Jira issues
-- ============================================================================
CREATE TABLE jira_issues (
  id SERIAL PRIMARY KEY,
  jira_instance_url VARCHAR(500) NOT NULL,
  issue_key VARCHAR(50) NOT NULL,
  summary VARCHAR(500) NOT NULL,
  description TEXT,
  issue_type VARCHAR(100),
  status VARCHAR(100),
  priority VARCHAR(50),
  acceptance_criteria JSONB,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(jira_instance_url, issue_key)
);

CREATE INDEX idx_jira_issues_key ON jira_issues(issue_key);
CREATE INDEX idx_jira_issues_instance ON jira_issues(jira_instance_url);

-- ============================================================================
-- TEST CASE GENERATIONS TABLE - Master generation records
-- ============================================================================
CREATE TABLE test_case_generations (
  id SERIAL PRIMARY KEY,
  generation_id UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  user_email VARCHAR(255) NOT NULL REFERENCES sessions(user_email) ON DELETE CASCADE,
  jira_issue_key VARCHAR(50) NOT NULL,
  jira_instance_url VARCHAR(500) NOT NULL,
  ai_provider VARCHAR(50) NOT NULL,
  ai_model VARCHAR(100) NOT NULL,
  generation_status VARCHAR(50) DEFAULT 'completed' CHECK (generation_status IN ('pending', 'generating', 'completed', 'failed')),
  total_scenarios INTEGER DEFAULT 0,
  successful_scenarios INTEGER DEFAULT 0,
  failed_scenarios INTEGER DEFAULT 0,
  generation_notes TEXT,
  temperature FLOAT DEFAULT 0.3,
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (jira_instance_url, jira_issue_key) REFERENCES jira_issues(jira_instance_url, issue_key) ON DELETE CASCADE
);

CREATE INDEX idx_generations_user ON test_case_generations(user_email);
CREATE INDEX idx_generations_status ON test_case_generations(generation_status);
CREATE INDEX idx_generations_issue ON test_case_generations(jira_issue_key);

-- ============================================================================
-- TEST SCENARIOS TABLE - Individual test cases
-- ============================================================================
CREATE TABLE test_scenarios (
  id SERIAL PRIMARY KEY,
  scenario_id UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
  generation_id UUID NOT NULL REFERENCES test_case_generations(generation_id) ON DELETE CASCADE,
  jira_issue_key VARCHAR(50) NOT NULL,
  jira_instance_url VARCHAR(500) NOT NULL,
  scenario_number INTEGER,
  title VARCHAR(500) NOT NULL,
  scenario_type VARCHAR(50) NOT NULL CHECK (scenario_type IN ('positive', 'negative', 'edge-case')),
  category VARCHAR(100),
  priority VARCHAR(50),
  preconditions JSONB,
  steps JSONB,
  expected_result TEXT,
  automation_hint TEXT,
  tags JSONB,
  coverage JSONB,

  -- Jira Integration
  jira_child_issue_key VARCHAR(50),
  jira_child_issue_url VARCHAR(500),
  jira_sync_status VARCHAR(50) DEFAULT 'pending' CHECK (jira_sync_status IN ('pending', 'synced', 'failed')),
  jira_last_sync_at TIMESTAMP,

  -- Approval/Validation
  status VARCHAR(50) DEFAULT 'draft' CHECK (status IN ('draft', 'approved', 'rejected', 'in_progress', 'passed', 'failed')),
  approved_by VARCHAR(255),
  approved_at TIMESTAMP,
  rejection_reason TEXT,

  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (jira_instance_url, jira_issue_key) REFERENCES jira_issues(jira_instance_url, issue_key) ON DELETE CASCADE
);

CREATE INDEX idx_scenarios_generation ON test_scenarios(generation_id);
CREATE INDEX idx_scenarios_issue ON test_scenarios(jira_issue_key);
CREATE INDEX idx_scenarios_sync ON test_scenarios(jira_sync_status);
CREATE INDEX idx_scenarios_status ON test_scenarios(status);
CREATE INDEX idx_scenarios_jira_child ON test_scenarios(jira_child_issue_key);

-- ============================================================================
-- SYNC HISTORY TABLE - Audit trail for all changes
-- ============================================================================
CREATE TABLE sync_history (
  id SERIAL PRIMARY KEY,
  scenario_id UUID REFERENCES test_scenarios(scenario_id) ON DELETE CASCADE,
  sync_direction VARCHAR(50) CHECK (sync_direction IN ('to_jira', 'from_jira', 'internal')),
  sync_type VARCHAR(100) CHECK (sync_type IN ('create', 'update', 'delete', 'approve', 'reject', 'sync')),
  previous_state JSONB,
  new_state JSONB,
  sync_status VARCHAR(50) CHECK (sync_status IN ('success', 'failed')),
  error_message TEXT,
  synced_by VARCHAR(255),
  synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sync_history_scenario ON sync_history(scenario_id);
CREATE INDEX idx_sync_history_timestamp ON sync_history(synced_at);

-- ============================================================================
-- ACCEPTANCE CRITERIA COVERAGE TABLE - Map scenarios to AC
-- ============================================================================
CREATE TABLE acceptance_criteria_coverage (
  id SERIAL PRIMARY KEY,
  scenario_id UUID REFERENCES test_scenarios(scenario_id) ON DELETE CASCADE,
  jira_issue_key VARCHAR(50) NOT NULL,
  ac_number VARCHAR(10),
  ac_text TEXT,
  coverage_status VARCHAR(50) DEFAULT 'covered' CHECK (coverage_status IN ('covered', 'partial', 'not_covered')),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ac_coverage_scenario ON acceptance_criteria_coverage(scenario_id);
CREATE INDEX idx_ac_coverage_issue ON acceptance_criteria_coverage(jira_issue_key);

-- ============================================================================
-- PROJECT SETTINGS TABLE - Project-wide configuration
-- ============================================================================
CREATE TABLE project_settings (
  id SERIAL PRIMARY KEY,
  jira_instance_url VARCHAR(500) NOT NULL UNIQUE,
  project_key VARCHAR(50),
  parent_issue_key VARCHAR(50),
  test_case_issue_type VARCHAR(50) DEFAULT 'Story',
  auto_approve_enabled BOOLEAN DEFAULT false,
  auto_sync_enabled BOOLEAN DEFAULT true,
  notification_enabled BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- CUSTOM JIRA FIELDS MAPPING TABLE
-- ============================================================================
CREATE TABLE jira_custom_fields (
  id SERIAL PRIMARY KEY,
  jira_instance_url VARCHAR(500) NOT NULL,
  field_key VARCHAR(100) NOT NULL,
  field_id VARCHAR(100) NOT NULL,
  field_name VARCHAR(255) NOT NULL,
  field_type VARCHAR(50),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(jira_instance_url, field_key)
);

-- ============================================================================
-- SUMMARY VIEW - Quick statistics
-- ============================================================================
CREATE VIEW generation_summary AS
SELECT
  gen.user_email,
  COUNT(DISTINCT gen.generation_id) as total_generations,
  COUNT(DISTINCT ts.scenario_id) as total_scenarios,
  COUNT(DISTINCT CASE WHEN ts.status = 'approved' THEN ts.scenario_id END) as approved_scenarios,
  COUNT(DISTINCT CASE WHEN ts.jira_sync_status = 'synced' THEN ts.scenario_id END) as synced_scenarios,
  MAX(gen.created_at) as last_generation
FROM test_case_generations gen
LEFT JOIN test_scenarios ts ON gen.generation_id = ts.generation_id
GROUP BY gen.user_email;

-- ============================================================================
-- SYNC STATISTICS VIEW
-- ============================================================================
CREATE VIEW sync_statistics AS
SELECT
  DATE(synced_at) as sync_date,
  sync_direction,
  sync_type,
  sync_status,
  COUNT(*) as count
FROM sync_history
GROUP BY DATE(synced_at), sync_direction, sync_type, sync_status;

-- ============================================================================
-- COVERAGE SUMMARY VIEW
-- ============================================================================
CREATE VIEW coverage_summary AS
SELECT
  jira_issue_key,
  COUNT(DISTINCT ac_number) as total_ac,
  COUNT(DISTINCT CASE WHEN coverage_status = 'covered' THEN scenario_id END) as covered_ac,
  COUNT(DISTINCT CASE WHEN coverage_status = 'partial' THEN scenario_id END) as partial_ac,
  COUNT(DISTINCT CASE WHEN coverage_status = 'not_covered' THEN scenario_id END) as uncovered_ac
FROM acceptance_criteria_coverage
GROUP BY jira_issue_key;

-- ============================================================================
-- Seed data - Default project settings
-- ============================================================================
INSERT INTO project_settings (jira_instance_url, project_key)
VALUES ('https://retech.atlassian.net', 'REB3')
ON CONFLICT (jira_instance_url) DO NOTHING;
