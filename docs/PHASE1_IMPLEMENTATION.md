# Phase 1: Test Case Creator Plugin - MVP Implementation Guide

## Overview

Phase 1 builds the complete MVP (Minimum Viable Product) for the Test Case Creator plugin. This includes:
- Jira data fetching + attachment parsing
- Claude AI BDD scenario generation
- JSON output + Jira attachment
- GitHub Actions workflow integration
- Modal UI for displaying results

**Timeline:** 5-7 days  
**Status:** Ready to Start

---

## Day 1: Jira Integration (Fetching & Attachments)

### Objectives
- ✅ Fetch Jira issues with rich metadata
- ✅ Download and cache attachments
- ✅ Implement safe attachment handling

### Tasks

#### 1.1 Implement `JiraClient.fetch_issues()`

```python
# Location: scripts/generate-test-cases.py, class JiraClient

def fetch_issues(self, limit: int = 50, jql: str = None) -> List[Dict[str, Any]]:
    """
    Fetch Jira issues for test case generation.
    
    Args:
        limit: Max issues to fetch (default 50)
        jql: Custom JQL query (optional)
    
    Returns:
        List of issue dictionaries with key, summary, description, attachments
    
    Fetches fields: key, summary, description, issuetype, status, attachment
    """
    # TODO Phase 1:
    # 1. Build JQL query if not provided
    #    - Default: "type in (Story, Task) AND project = {PROJECT_KEY}"
    #    - Filter: Only issues with description
    # 2. POST to /rest/api/3/search/jql
    # 3. Paginate through results (max 100 per page)
    # 4. Extract required fields
    # 5. Return list of issues
    
    # Pseudo-code:
    # jql = jql or f"type in (Story, Task) AND project = REB3 ORDER BY updated DESC"
    # issues = []
    # start_at = 0
    # while len(issues) < limit:
    #     response = self._api_call("POST", "/rest/api/3/search/jql", {
    #         "jql": jql,
    #         "startAt": start_at,
    #         "maxResults": 100,
    #         "fields": ["key", "summary", "description", "issuetype", "status", "attachment"]
    #     })
    #     issues.extend(response.get("issues", []))
    #     if len(response.get("issues", [])) < 100:
    #         break
    #     start_at += 100
    # return issues[:limit]
```

#### 1.2 Implement `JiraClient.download_attachment()`

```python
# Location: scripts/generate-test-cases.py, class JiraClient

def download_attachment(self, attachment_url: str) -> Optional[bytes]:
    """
    Download attachment safely with size/timeout limits.
    
    Args:
        attachment_url: URL to attachment (from Jira)
    
    Returns:
        File content as bytes, or None if download fails/exceeds limits
    
    Safety checks:
    - Max file size: 10MB (configurable)
    - Timeout: 5 seconds
    - Validates content-length header
    """
    # TODO Phase 1:
    # 1. Check content-length header BEFORE downloading
    # 2. If > max_attachment_mb, return None with warning
    # 3. Download with timeout
    # 4. If actual size > limit, return None
    # 5. Catch network errors gracefully
    # 6. Log with masked URL (no credentials)
    
    # Pseudo-code:
    # try:
    #     req = urllib.request.Request(attachment_url, headers=self.auth_header)
    #     with urllib.request.urlopen(req, timeout=5) as response:
    #         size = int(response.headers.get('content-length', 0))
    #         if size > self.config.max_attachment_mb * 1024 * 1024:
    #             logger.warning(f"Attachment too large: {size} bytes")
    #             return None
    #         data = response.read(self.config.max_attachment_mb * 1024 * 1024 + 1)
    #         if len(data) > self.config.max_attachment_mb * 1024 * 1024:
    #             logger.warning("Attachment download exceeded size limit")
    #             return None
    #         return data
    # except Exception as e:
    #     logger.warning(f"Attachment download failed: {e}")
    #     return None
```

#### 1.3 Add API Helper Method

```python
# Location: scripts/generate-test-cases.py, class JiraClient

def _api_call(self, method: str, endpoint: str, data: Dict = None) -> Dict[str, Any]:
    """
    Make API call to Jira with error handling.
    
    Args:
        method: HTTP method (GET, POST)
        endpoint: API endpoint (e.g., /rest/api/3/search/jql)
        data: Request payload for POST
    
    Returns:
        Response JSON
    
    Raises:
        urllib.error.HTTPError on API errors
    """
    # TODO Phase 1:
    # 1. Build full URL
    # 2. Prepare request with auth header
    # 3. Handle JSON payload for POST
    # 4. Parse response
    # 5. Log API calls (masked)
    # 6. Handle rate limiting (return error for caller to handle)
```

#### 1.4 Write Unit Tests

**File:** `tests/test_jira_integration.py` (new)

```python
@responses.activate
def test_fetch_issues_success(mock_jira_base_url):
    """Test successful issue fetch"""
    # Mock endpoint, verify call parameters, assert results

@responses.activate
def test_fetch_issues_empty_result(mock_jira_base_url):
    """Test handling of empty results"""

@responses.activate
def test_download_attachment_success(mock_jira_base_url):
    """Test attachment download"""

def test_download_attachment_size_limit(mock_jira_base_url):
    """Test rejection of oversized attachments"""

def test_download_attachment_timeout(mock_jira_base_url):
    """Test timeout handling"""
```

---

## Day 2-3: Claude AI Integration & BDD Generation

### Objectives
- ✅ Implement precondition extraction
- ✅ Create Claude prompts for BDD generation
- ✅ Implement BDD scenario generation
- ✅ Handle attachments in prompts

### Tasks

#### 2.1 Implement `PreconditionExtractor.extract()`

```python
# Location: scripts/generate-test-cases.py, class PreconditionExtractor

@staticmethod
def extract(issue: Dict[str, Any], attachment_content: Optional[str] = None) -> List[str]:
    """
    Extract preconditions from issue content.
    
    Looks for patterns in:
    1. Description field (Given/Given...)
    2. Acceptance Criteria (AC1, AC2, etc.)
    3. Attachment content (from PDF/DOCX)
    
    Returns:
        List of precondition strings (ready for BDD "Given" statements)
    """
    # TODO Phase 1:
    # 1. Parse description for keywords: "must be", "should be", "requires", "configured", "enabled"
    # 2. Extract bullet points from description
    # 3. Parse AC field for configuration requirements
    # 4. Extract from attachment content (if provided)
    # 5. Deduplicate and format as "Given X is Y" statements
    # 6. Return ordered list (most important first)
    
    # Example preconditions:
    # [
    #   "Given barcode scanner module is initialized",
    #   "And multi-store feature flag is enabled",
    #   "And API authentication with JWT token is available",
    #   "And database schema includes store_id field"
    # ]
```

#### 2.2 Create Claude Prompt Template

**File:** `scripts/prompts/bdd-generation.txt` (new)

```
# System Prompt for BDD Scenario Generation

You are an expert QA engineer specializing in Behavior-Driven Development (BDD).

Your task is to generate comprehensive BDD test scenarios in Gherkin format for Jira issues.

## Input
You will receive:
1. Issue Summary: High-level requirement
2. Issue Description: Detailed requirements
3. Acceptance Criteria: Specific acceptance criteria
4. Preconditions: System/setup requirements
5. Optional: Attachment content (requirements, API specs, etc.)

## Output Format
Generate valid BDD scenarios as JSON array with this structure:
[
  {
    "id": "SC-001",
    "title": "Clear, specific scenario title",
    "type": "positive|negative|edge-case",
    "category": "functional|validation|performance|security",
    "priority": "P1|P2|P3",
    "preconditions": ["Given condition 1", "And condition 2"],
    "steps": [
      {"step": 1, "action": "When user does X", "expected": "Then system does Y"},
      {"step": 2, "action": "When user does Z", "expected": "Then result is A"}
    ],
    "expectedResult": "Final outcome description",
    "automationHint": "Framework-specific automation tips (Selenium, WebDriver, etc.)",
    "coverage": ["AC1", "AC2"]
  }
]

## Requirements

1. **Scenario Variety**: Generate mix of positive, negative, and edge case scenarios
2. **Acceptance Criteria Mapping**: Each scenario must map to 1+ acceptance criteria
3. **BDD Format**: Strictly follow Given-When-Then structure
4. **Clarity**: Scenarios must be understandable by both technical and non-technical stakeholders
5. **Automation Ready**: Include Selenium/WebDriver hints for test automation
6. **Completeness**: Each scenario must have preconditions, steps, and expected results

## Scenario Types

- **Positive**: Happy path - system works as intended
- **Negative**: Error handling - system rejects invalid input
- **Edge Case**: Boundary conditions, unusual scenarios

## Priority Mapping

- P1: Critical path, directly maps to AC
- P2: Important but less critical
- P3: Nice to have, edge case coverage

## Example

Input Issue:
  Summary: "User login with email and password"
  Description: "Users can log in using email and password credentials..."
  AC: "User sees dashboard on valid login, error on invalid login"

Output Scenario:
  {
    "id": "SC-001",
    "title": "User successfully logs in with valid credentials",
    "type": "positive",
    "category": "functional",
    "priority": "P1",
    "preconditions": [
      "Given user account exists in database",
      "And user is on login page"
    ],
    "steps": [
      {"step": 1, "action": "When user enters valid email", "expected": "Email field populated"},
      {"step": 2, "action": "When user enters valid password", "expected": "Password field populated"},
      {"step": 3, "action": "When user clicks 'Login' button", "expected": "Request sent to backend"}
    ],
    "expectedResult": "User is logged in and redirected to dashboard",
    "automationHint": "Selenium: Use WebDriverWait, find elements by ID (email_input, password_input, login_btn)",
    "coverage": ["AC1"]
  }

## Important Rules

1. **PII Redaction**: Never include actual passwords, API keys, or sensitive URLs in scenarios
2. **Real-World**: Base scenarios on actual issue requirements, not generic templates
3. **No Assumptions**: Don't invent requirements not stated in issue
4. **Validation**: All JSON must be valid and parseable
5. **Language**: Use clear, professional English
6. **Completeness**: Provide 3-5 scenarios per issue (positive 2-3, negative 1-2, edge case 1)

Generate ONLY valid JSON array. No markdown, no code blocks, just JSON.
```

#### 2.3 Implement `BDDGenerator.generate_scenarios()`

```python
# Location: scripts/generate-test-cases.py, class BDDGenerator

def generate_scenarios(
    self,
    issue: Dict[str, Any],
    preconditions: List[str],
    test_types: List[str] = None
) -> List[Dict[str, Any]]:
    """
    Generate BDD scenarios using Claude AI.
    
    Args:
        issue: Jira issue data
        preconditions: Extracted preconditions
        test_types: Test types to generate (default: positive, negative, e2e)
    
    Returns:
        List of validated BDD scenario dicts
    """
    # TODO Phase 1:
    # 1. Import anthropic SDK
    # 2. Sanitize issue content (remove PII)
    # 3. Build prompt with issue details + preconditions
    # 4. Call Claude with test_types preference
    # 5. Parse JSON response
    # 6. Validate each scenario against schema
    # 7. Return validated scenarios
    
    # Pseudo-code:
    # from anthropic import Anthropic
    # client = Anthropic(api_key=self.config.anthropic_api_key)
    # 
    # prompt = f"""
    # Issue Summary: {issue['summary']}
    # Description: {PIISanitizer.sanitize(issue['description'])}
    # Acceptance Criteria: {self._extract_ac(issue)}
    # Preconditions: {', '.join(preconditions)}
    # Test Types Requested: {', '.join(test_types or ['positive', 'negative', 'e2e'])}
    # 
    # Generate BDD scenarios...
    # """
    # 
    # response = client.messages.create(
    #     model=self.config.model,
    #     max_tokens=2000,
    #     messages=[{"role": "user", "content": prompt}]
    # )
    # 
    # response_text = response.content[0].text
    # scenarios = json.loads(response_text)
    # validated = [s for s in scenarios if self._validate_scenario(s)]
    # return validated
```

#### 2.4 Implement Scenario Validation

```python
# Location: scripts/generate-test-cases.py, class BDDGenerator

@staticmethod
def _validate_scenario(scenario: Dict[str, Any]) -> bool:
    """
    Validate BDD scenario structure and content.
    
    Checks:
    - Required fields present
    - Preconditions start with "Given" or "And"
    - Steps have action and expected
    - Expected result is meaningful (>20 chars)
    - Priority is valid
    """
    # TODO Phase 1:
    # 1. Check required fields: id, title, type, preconditions, steps, expectedResult
    # 2. Validate precondition format
    # 3. Validate steps structure
    # 4. Validate priority value
    # 5. Return True if all valid, False otherwise
```

#### 2.5 Write Tests

**File:** `tests/test_claude_integration.py` (new)

```python
@patch('anthropic.Anthropic')
def test_generate_scenarios_success(mock_claude, mock_jira_issue):
    """Test successful scenario generation"""

@patch('anthropic.Anthropic')
def test_generate_scenarios_validation(mock_claude):
    """Test scenario validation"""

def test_precondition_extraction_from_description():
    """Test extracting preconditions from description"""

def test_precondition_extraction_from_ac():
    """Test extracting from acceptance criteria"""

def test_pii_redaction_before_claude(mock_issue_with_pii):
    """Test PII is redacted before Claude call"""
```

---

## Day 4: Output Formatting & File Storage

### Objectives
- ✅ Implement JSON output formatting
- ✅ Implement Jira attachment posting
- ✅ Implement history logging
- ✅ Add cost tracking

### Tasks

#### 4.1 Implement `TestCaseGenerator._save_results()`

```python
# Location: scripts/generate-test-cases.py, class TestCaseGenerator

def _save_results(self, results: Dict[str, Any]):
    """
    Save generated test cases to multiple locations.
    
    Outputs:
    1. data/test-cases.json - Main output (versioned in git)
    2. data/history/test-cases-{date}.jsonl - Append-only history
    3. Attach to Jira issues as markdown + JSON files
    """
    # TODO Phase 1:
    # 1. Validate results JSON structure
    # 2. Write to data/test-cases.json
    # 3. Append to data/history/test-cases-{YYYY-MM-DD}.jsonl
    # 4. For each issue, call _attach_to_jira()
    # 5. Log summary statistics
    # 6. Handle write errors gracefully
```

#### 4.2 Implement Jira Attachment

```python
# Location: scripts/generate-test-cases.py, class TestCaseGenerator

def _attach_to_jira(self, issue_key: str, test_cases: List[Dict]) -> bool:
    """
    Attach generated test cases to Jira issue.
    
    Attachments:
    1. Markdown file (human-readable)
    2. JSON file (programmatic access)
    
    Also adds comment with summary.
    """
    # TODO Phase 1:
    # 1. Convert test_cases to markdown (.md file)
    # 2. Convert test_cases to JSON (.json file)
    # 3. POST markdown as attachment via Jira API
    # 4. POST JSON as attachment
    # 5. Add comment: "Test cases generated by Claude AI on [date]"
    # 6. Return success/failure
```

#### 4.3 Create Markdown Converter

```python
# Location: scripts/generate-test-cases.py, new function or class

def convert_scenarios_to_markdown(scenarios: List[Dict], issue_summary: str) -> str:
    """
    Convert BDD scenarios to human-readable markdown.
    
    Format:
    # Test Cases for [Issue Summary]
    
    ## Scenario 1: [Title]
    **Type:** Positive  
    **Priority:** P1
    
    ### Preconditions
    - Given X
    - And Y
    
    ### Steps
    1. When user does A
       Expected: System shows B
    
    ### Expected Result
    User sees dashboard
    
    ### Automation Hint
    Selenium: Use WebDriver...
    """
    # TODO Phase 1: Generate markdown format
```

#### 4.4 Add Cost Tracking

```python
# Location: scripts/generate-test-cases.py, add to output

# Track Claude API usage for cost monitoring:
# {
#   "timestamp": "2026-09-08T14:00:00Z",
#   "tokenUsage": {
#     "input": 1500,
#     "output": 800,
#     "model": "claude-3-5-sonnet-20241022"
#   },
#   "estimatedCost": 0.0045,  # (1500 * 0.003 + 800 * 0.015) / 1000
#   "totalCost": 0.0891  # Running total
# }
```

---

## Day 5: GitHub Actions & UI Integration

### Objectives
- ✅ Update GitHub Actions workflow
- ✅ Create modal UI component
- ✅ Integrate with dashboard

### Tasks

#### 5.1 Update GitHub Actions Workflow

**File:** `.github/workflows/update-dashboard.yml` (modify)

```yaml
- name: Generate Test Cases (Test Case Creator Plugin)
  if: github.event_name == 'push' || github.event_name == 'schedule'
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
    JIRA_BASE_URL: ${{ secrets.JIRA_BASE_URL }}
    JIRA_USER_EMAIL: ${{ secrets.JIRA_USER_EMAIL }}
    JIRA_API_TOKEN: ${{ secrets.JIRA_API_TOKEN }}
    TEST_CASE_CREATOR_ENABLED: 'true'
    DEBUG: 'false'
  run: |
    python3 scripts/generate-test-cases.py
  timeout-minutes: 5
  continue-on-error: true  # Don't fail entire workflow if generation fails
```

#### 5.2 Create Modal UI Component

**File:** `assets/js/test-case-creator-ui.js` (new)

```javascript
// Test Case Creator Modal UI Component
class TestCaseCreatorModal {
  constructor() {
    this.modal = null;
    this.isOpen = false;
    this.testCases = [];
  }

  // TODO Phase 1:
  // 1. Create modal HTML structure
  // 2. Implement issue selector (search, filter)
  // 3. Implement test type checkboxes
  // 4. Show results in tabs (Summary, Detailed, JSON)
  // 5. Add download/attach buttons
  // 6. Handle loading state + errors

  open() { /* Show modal */ }
  close() { /* Hide modal */ }
  loadTestCases(issueKey) { /* Load from data/test-cases.json */ }
  displaySummary() { /* Show summary stats */ }
  displayDetailed() { /* List all scenarios */ }
  downloadJSON() { /* Download JSON file */ }
  attachToJira() { /* Call backend to attach */ }
}
```

#### 5.3 Integrate with Jira Tab

**File:** `assets/js/jira-tracker.js` (enhance)

```javascript
// Add button to Jira header
const generateTestCasesBtn = document.createElement('button');
generateTestCasesBtn.id = 'generate-test-cases-btn';
generateTestCasesBtn.className = 'btn btn-primary';
generateTestCasesBtn.textContent = '🎯 Generate Test Cases';
generateTestCasesBtn.onclick = () => {
  const testCaseCreator = new TestCaseCreatorModal();
  testCaseCreator.open();
};

// TODO Phase 1:
// 1. Add button to existing Jira tab header
// 2. Only show if plugin enabled in settings
// 3. Handle click to open modal
// 4. Refresh test cases after generation
```

#### 5.4 Write E2E Tests

**File:** `tests/test_end_to_end.py` (new)

```python
def test_full_pipeline_with_mock_jira_and_claude():
    """Test complete pipeline: Jira → Claude → JSON → Attach"""
    # Mock Jira API
    # Mock Claude API
    # Run test case generator
    # Verify output files created
    # Verify Jira attachment called
    # Verify no errors logged

def test_plugin_disabled_mode():
    """Test plugin respects disable flag"""

def test_rate_limiting():
    """Test pipeline respects rate limits"""

def test_error_recovery():
    """Test pipeline continues on individual failures"""
```

---

## Phase 1 Checklist

### Development
- [ ] **Day 1: Jira Integration**
  - [ ] Implement `JiraClient.fetch_issues()`
  - [ ] Implement `JiraClient.download_attachment()`
  - [ ] Add `_api_call()` helper
  - [ ] Write unit tests (conftest fixtures)
  - [ ] Test against real Jira (staging)

- [ ] **Day 2-3: Claude Integration**
  - [ ] Implement `PreconditionExtractor.extract()`
  - [ ] Create BDD prompt template
  - [ ] Implement `BDDGenerator.generate_scenarios()`
  - [ ] Implement scenario validation
  - [ ] Implement PII redaction in production code
  - [ ] Write integration tests with mocked Claude
  - [ ] Test prompt quality (run against sample issues)

- [ ] **Day 4: Output & Storage**
  - [ ] Implement `_save_results()` (JSON + history)
  - [ ] Implement Jira attachment (`_attach_to_jira()`)
  - [ ] Create markdown converter
  - [ ] Add cost tracking
  - [ ] Write file I/O tests

- [ ] **Day 5: Deployment & UI**
  - [ ] Update GitHub Actions workflow
  - [ ] Create modal UI (HTML + JS)
  - [ ] Integrate with Jira tab
  - [ ] Write E2E tests
  - [ ] Deploy to staging
  - [ ] Full regression testing

### Testing & QA
- [ ] Unit tests ≥80% coverage
- [ ] Integration tests (mocked APIs)
- [ ] E2E tests (full pipeline)
- [ ] Manual testing on 5+ real Jira issues
- [ ] Security review (PII, tokens, attachments)
- [ ] Performance testing (batch generation timing)
- [ ] Regression testing (existing Jira integration)

### Documentation
- [ ] Code comments on all public methods
- [ ] Update README with plugin info
- [ ] Create PHASE1_RESULTS.md (findings, metrics)
- [ ] Document any deviations from plan

### Deployment
- [ ] GitHub Actions workflow tested
- [ ] Secrets validated in GitHub
- [ ] Soft launch on test project (REB3)
- [ ] Monitor logs for errors
- [ ] Get user feedback
- [ ] Proceed to Phase 2 (optimization)

---

## Success Criteria (MVP)

✅ Generate ≥3 valid BDD scenarios per issue  
✅ Handle missing/incomplete descriptions gracefully  
✅ Complete 50-issue batch in <3 minutes  
✅ Zero PII leakage to Claude API  
✅ Attach results to Jira with markdown + JSON  
✅ ≥80% test coverage  
✅ Zero regressions in existing Jira integration  
✅ GitHub Actions workflow runs successfully  
✅ Modal UI displays results correctly  
✅ Cost tracking enabled  

---

## Critical Implementation Paths

### Path 1: Jira Data Flow
```
Jira API → fetch_issues() 
        → download_attachments()
        → Parse PDFs/DOCX
        → Extract preconditions
        → Ready for Claude
```

### Path 2: Claude Generation
```
Jira data + Prompt → Claude API
                  → Parse JSON response
                  → Validate scenarios
                  → Cost tracking
```

### Path 3: Output Flow
```
Validated scenarios → JSON file (git-versioned)
                   → History (append-only)
                   → Jira attachment (markdown + JSON)
                   → Dashboard display (modal UI)
```

---

## Known Constraints & Workarounds

| Constraint | Workaround |
|-----------|-----------|
| Claude response may be non-deterministic | Validate structure, not exact content; use temperature=0.3 for consistency |
| Large PDF parsing timeout | Implement 3s timeout + fallback to description only |
| Jira API rate limit | Max 50 issues/run; implement exponential backoff |
| PII in Jira | Sanitize before Claude; remove from output |
| Test case quality varies | Include human review workflow (Phase 2) |

---

## Commit Strategy

Suggested git commits (one per day):

```
Day 1: feat: Implement Jira issue fetching and attachment parsing
Day 2: feat: Implement Claude BDD scenario generation with PII redaction
Day 3: feat: Add precondition extraction and validation
Day 4: feat: Implement test case output formatting and Jira attachment
Day 5: feat: Add GitHub Actions workflow and modal UI; Phase 1 MVP complete
```

---

## Phase 2 Preparation

Don't implement Phase 2 items yet, but keep in mind:

- [ ] Parallel Claude requests (batch_size=5)
- [ ] Haiku model for simple issues
- [ ] Prompt caching (90% cost reduction)
- [ ] Append-only history migration
- [ ] Human review workflow before attachment
- [ ] Performance benchmarking
- [ ] Multi-team support

---

**Next Action:** Begin Day 1 implementation

Review this plan with your team, then start with Jira integration on Day 1.
