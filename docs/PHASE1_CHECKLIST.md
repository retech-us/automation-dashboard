# Phase 1 Pre-Implementation Checklist

## Prerequisites Verification

Before starting Phase 1 development, verify all Phase 0 items are complete:

### Environment Setup
- [ ] Python 3.9+ installed: `python3 --version`
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] All packages verified:
  - [ ] `python3 -c "import anthropic; print('✓ anthropic')"`
  - [ ] `python3 -c "import pdfplumber; print('✓ pdfplumber')"`
  - [ ] `python3 -c "import docx; print('✓ python-docx')"`
  - [ ] `python3 -c "import pytest; print('✓ pytest')"`
  - [ ] `python3 -c "import responses; print('✓ responses')"`

### Jira Configuration
- [ ] Jira API token generated: https://id.atlassian.com/manage/api-tokens
- [ ] Jira base URL identified: `https://your-domain.atlassian.net`
- [ ] Jira credentials working:
  ```bash
  export JIRA_BASE_URL="..."
  export JIRA_USER_EMAIL="..."
  export JIRA_API_TOKEN="..."
  python3 scripts/generate-test-cases.py  # Should validate config
  ```

### Anthropic API Configuration
- [ ] Anthropic API key generated: https://console.anthropic.com/account/keys
- [ ] Anthropic credentials working:
  ```bash
  export ANTHROPIC_API_KEY="sk-ant-..."
  python3 << 'EOF'
  from anthropic import Anthropic
  client = Anthropic(api_key="sk-ant-...")
  print("✓ Anthropic API accessible")
  EOF
  ```

### GitHub Secrets
- [ ] `ANTHROPIC_API_KEY` added to GitHub Secrets
- [ ] Other Jira secrets verified (JIRA_BASE_URL, JIRA_USER_EMAIL, JIRA_API_TOKEN)

### Repository Setup
- [ ] `.env.example` reviewed and documented
- [ ] `.gitignore` updated to exclude `.env`
- [ ] `requirements.txt` ready with all dependencies
- [ ] Test structure created (tests/conftest.py, test files)
- [ ] Script skeleton ready (scripts/generate-test-cases.py)

---

## Code Review Before Starting

### Script Skeleton Review
- [ ] Read `scripts/generate-test-cases.py` skeleton
- [ ] Understand class structure:
  - [ ] ConfigManager (configuration)
  - [ ] JiraClient (Jira API)
  - [ ] AttachmentParser (PDF/DOCX)
  - [ ] PreconditionExtractor (AC extraction)
  - [ ] BDDGenerator (Claude AI)
  - [ ] PIISanitizer (security)
  - [ ] TestCaseGenerator (orchestrator)

### Utilities Review
- [ ] Review `scripts/utils.py` for helper functions
  - [ ] JSONValidator (scenario validation)
  - [ ] PreconditionFormatter (formatting)
  - [ ] AcceptanceCriteriaExtractor (AC extraction)
  - [ ] MarkdownExporter (markdown output)
  - [ ] CostTracker (cost calculation)

### Prompt Review
- [ ] Review `scripts/prompts/bdd-generation.txt`
- [ ] Understand expected input/output format
- [ ] Note JSON structure requirements

### Test Structure Review
- [ ] Review `tests/conftest.py` fixtures
- [ ] Review `tests/test_bdd_generator.py` test placeholders
- [ ] Review `tests/test_integration.py` test placeholders

---

## Implementation Plan Review

- [ ] Read `docs/PHASE1_IMPLEMENTATION.md` completely
- [ ] Understand day-by-day breakdown
- [ ] Note critical implementation paths
- [ ] Understand success criteria
- [ ] Identify any blockers or dependencies

---

## Development Environment Setup

### IDE Setup
- [ ] IDE of choice installed and configured
- [ ] Python interpreter configured (use venv or system Python 3.9+)
- [ ] Git configured for commits:
  ```bash
  git config user.name "Your Name"
  git config user.email "your-email@company.com"
  ```

### Local Testing Setup
- [ ] Create `.env` file from `.env.example` with real credentials:
  ```bash
  cp .env.example .env
  # Edit .env with real values
  ```
- [ ] Test script runs locally:
  ```bash
  python3 scripts/generate-test-cases.py
  # Should validate config and exit cleanly
  ```

### Git Workflow
- [ ] Create feature branch for Phase 1:
  ```bash
  git checkout -b phase-1/test-case-creator-mvp
  ```
- [ ] Verify you can push to branch (test with dummy commit)

---

## Team Coordination

### Communication
- [ ] Notify team Phase 1 starting
- [ ] Share link to Phase 1 implementation guide
- [ ] Set up daily standup (if doing team work)
- [ ] Identify point person for questions

### Review Process
- [ ] Identify code reviewer(s) for PRs
- [ ] Schedule security review (Day 5, before merge)
- [ ] Schedule user acceptance testing (UAT)

---

## Phase 1 Day-by-Day Readiness

### Day 1: Jira Integration
- [ ] Ready to implement `JiraClient.fetch_issues()`
- [ ] Understand Jira API v3 `/search/jql` endpoint
- [ ] Have test Jira project identified (REB3?)
- [ ] Ready to write unit tests for Jira integration

### Day 2-3: Claude Integration
- [ ] Understand Claude API calling patterns
- [ ] Understand JSON response parsing
- [ ] Ready to implement precondition extraction
- [ ] Ready to implement scenario validation
- [ ] BDD prompt template reviewed and understood

### Day 4: Output & Storage
- [ ] Understand JSON file writing to `data/test-cases.json`
- [ ] Understand Jira attachment API
- [ ] Ready to implement markdown exporter
- [ ] Understand cost tracking

### Day 5: UI & Workflow
- [ ] Understand GitHub Actions YAML
- [ ] Ready to create modal UI component
- [ ] Ready to integrate with existing Jira tab
- [ ] Ready for end-to-end testing

---

## Critical Decision Points

### Model Selection
- [ ] Confirm using `claude-3-5-sonnet-20241022` as primary model
- [ ] Understand cost: ~$0.003 per 1K input tokens, $0.015 per 1K output tokens
- [ ] OK with ~$0.03-0.05 cost per issue for test generation?

### Storage Strategy
- [ ] Confirm using `data/test-cases.json` for main storage
- [ ] OK with git-versioned storage (vs. database)?
- [ ] Plan for append-only history in Phase 2?

### Jira Attachment
- [ ] OK with attaching test cases to Jira issues?
- [ ] Confirm test attachment format (markdown + JSON)?
- [ ] Confirm notification required when test cases attached?

---

## Known Issues & Workarounds

| Issue | Workaround | Timeline |
|-------|-----------|----------|
| Attachment parsing timeout | 3s timeout + fallback to description | Day 1 |
| PII in Jira issues | Sanitize before Claude call | Day 2 |
| Claude non-deterministic output | Validate structure not content | Day 2 |
| Large Jira instances (10k+ issues) | Max 50 issues/run, add filtering | Day 1 |
| Rate limiting | Exponential backoff + queue | Day 4 |

---

## Success Metrics (Track These)

By end of Phase 1, you should have:

### Code Metrics
- [ ] ≥80% test coverage (pytest --cov)
- [ ] 0 linting errors (if using linter)
- [ ] All tests passing locally
- [ ] Zero regressions in existing Jira integration

### Functional Metrics
- [ ] ≥3 valid BDD scenarios per Jira issue
- [ ] 50-issue batch completes in <3 minutes
- [ ] 100% PII removal verification
- [ ] Test cases successfully attached to Jira
- [ ] Modal UI displays results correctly

### Quality Metrics
- [ ] User feedback on scenario quality (ask early testers)
- [ ] Cost per issue tracked and logged
- [ ] Zero uncaught exceptions in logs
- [ ] Clear error messages for failures

### Documentation Metrics
- [ ] All public methods have docstrings
- [ ] README updated with plugin info
- [ ] Phase 1 results documented
- [ ] No TODOs left in Phase 1 code

---

## Git Commit Strategy

Plan your commits by day:

**Day 1 Commits:**
```
feat: Implement Jira issue fetching with pagination
feat: Implement safe attachment downloading with size/timeout limits
test: Add unit tests for Jira client
```

**Day 2-3 Commits:**
```
feat: Implement precondition extraction from issue content
feat: Implement BDD scenario generation with Claude
feat: Add PII redaction for sensitive data
test: Add integration tests for Claude API
```

**Day 4 Commits:**
```
feat: Implement JSON output formatting
feat: Implement Jira attachment posting
feat: Add markdown exporter for test cases
feat: Add cost tracking and reporting
```

**Day 5 Commits:**
```
feat: Update GitHub Actions workflow for test generation
feat: Create modal UI component for test case display
feat: Integrate with Jira tracker tab
feat: Add end-to-end tests and documentation
```

**Final Commit:**
```
feat: Phase 1 MVP complete - Test Case Creator plugin
- Fetches Jira issues and attachments
- Generates BDD scenarios with Claude AI
- Attaches results to Jira issues
- Integrates with dashboard
```

---

## File Checklist (What Should Exist After Phase 0)

After Phase 0, these files should exist:

✅ **Created Files:**
- [ ] `requirements.txt` (dependencies)
- [ ] `tests/conftest.py` (pytest fixtures)
- [ ] `tests/test_bdd_generator.py` (unit tests)
- [ ] `tests/test_integration.py` (integration tests)
- [ ] `scripts/generate-test-cases.py` (main script skeleton)
- [ ] `scripts/utils.py` (utility functions)
- [ ] `scripts/prompts/bdd-generation.txt` (Claude prompt)
- [ ] `.env.example` (env vars template)
- [ ] `docs/PHASE0_SETUP.md` (setup guide)
- [ ] `docs/PHASE1_IMPLEMENTATION.md` (this plan)
- [ ] `memory/plugin_architecture_requirements.md` (architecture notes)
- [ ] `memory/phase0_completion.md` (Phase 0 summary)

✅ **Modified Files:**
- [ ] `.gitignore` (added .env and Python excludes)

❓ **Files to Create in Phase 1:**
- [ ] `.github/workflows/update-dashboard.yml` (modify with new step)
- [ ] `assets/js/test-case-creator-ui.js` (modal UI)
- [ ] `tests/test_jira_integration.py` (Jira integration tests)
- [ ] `tests/test_claude_integration.py` (Claude integration tests)
- [ ] `tests/test_end_to_end.py` (E2E tests)

---

## Ready? Let's Go! 🚀

Once you've checked all the boxes above:

1. **Create feature branch:**
   ```bash
   git checkout -b phase-1/test-case-creator-mvp
   ```

2. **Start Day 1 implementation:**
   - Read `docs/PHASE1_IMPLEMENTATION.md` Day 1 section
   - Implement `JiraClient.fetch_issues()`
   - Write unit tests
   - Commit and push

3. **Daily progress:**
   - Update this checklist as you complete items
   - Check off completed tasks
   - Note any blockers
   - Commit daily

4. **End of Phase 1:**
   - All items checked
   - All tests passing
   - PR ready for review
   - Ready for security audit

---

**Status:** Phase 0 ✅ Complete  
**Next:** Phase 1 Ready to Begin  
**Timeline:** 5-7 days

Let's build this! 🎯
