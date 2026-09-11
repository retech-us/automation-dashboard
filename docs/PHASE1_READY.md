# Phase 1 Ready - Test Case Creator Plugin MVP

## 🎯 Status: READY TO BEGIN

**Phase 0 Completion:** ✅ 100%  
**Phase 1 Status:** 🟢 **READY TO START**  
**Date Prepared:** 2026-09-08  
**Timeline:** 5-7 days (Sep 9 - Sep 15)

---

## 📊 What's Complete (Phase 0)

### ✅ Foundation
- All Python dependencies specified (requirements.txt)
- Script skeleton with all classes defined (generate-test-cases.py)
- Test framework set up with fixtures (tests/conftest.py + test files)
- Utility functions ready (scripts/utils.py)
- Comprehensive documentation

### ✅ Configuration
- Jira credentials setup and tested locally
- Anthropic API key generated and verified
- GitHub Secrets ready for CI/CD
- Environment variables documented (.env.example)

### ✅ Security
- PII redaction class created (PIISanitizer)
- Token handling patterns established
- Attachment safety patterns defined
- .gitignore configured to protect secrets

### ✅ Documentation
- PHASE0_SETUP.md (620 lines) - Setup guide
- PHASE1_IMPLEMENTATION.md (500+ lines) - Day-by-day breakdown
- PHASE1_CHECKLIST.md (400+ lines) - Pre-implementation checklist
- Inline code comments with Phase 1 TODOs
- BDD prompt template documented

---

## 🚀 What to Implement (Phase 1)

### Day 1: Jira Integration
**Duration:** ~4-6 hours  
**Tasks:**
- Implement `JiraClient.fetch_issues()` - Query Jira API with JQL
- Implement `JiraClient.download_attachment()` - Safe file download
- Add `_api_call()` helper method - API abstraction
- Write 5-8 unit tests with mocking
- Local testing with real Jira instance

**Deliverable:** Fetch and download Jira issues + attachments  
**Success Criteria:** Can retrieve 50 issues with attachments in <10s

---

### Day 2-3: Claude Integration & BDD Generation
**Duration:** ~8-12 hours  
**Tasks:**
- Implement `PreconditionExtractor.extract()` - Parse AC, description
- Implement `BDDGenerator.generate_scenarios()` - Call Claude API
- Implement `_validate_scenario()` - Verify JSON structure
- Implement PII redaction in production
- Write 10-15 integration tests (mocked Claude)
- Test prompt quality with sample issues

**Deliverable:** Generate BDD scenarios from Jira issues  
**Success Criteria:** ≥3 valid scenarios per issue, 0 PII leakage

---

### Day 4: Output & File Storage
**Duration:** ~4-6 hours  
**Tasks:**
- Implement `_save_results()` - Write JSON + history
- Implement `_attach_to_jira()` - Post attachments to Jira
- Implement markdown converter - Export to markdown
- Add cost tracking - Log API usage + cost
- Write file I/O tests

**Deliverable:** Save and share test cases  
**Success Criteria:** Files written correctly, attached to Jira

---

### Day 5: GitHub Actions & UI
**Duration:** ~6-8 hours  
**Tasks:**
- Update `.github/workflows/update-dashboard.yml` - Add generation step
- Create modal UI component - HTML + JS
- Integrate with Jira tab - Add button + logic
- Write end-to-end tests - Full pipeline
- Deploy to staging + test

**Deliverable:** Automated generation + user interface  
**Success Criteria:** Workflow runs, modal displays results

---

## 📋 What's Ready to Use

### Code Templates
```
✅ scripts/generate-test-cases.py - 416 lines, all classes defined
✅ scripts/utils.py - 350+ lines, utility functions
✅ scripts/prompts/bdd-generation.txt - Claude prompt template
✅ tests/conftest.py - Pytest fixtures ready
```

### Documentation
```
✅ docs/PHASE1_IMPLEMENTATION.md - Detailed day-by-day guide
✅ docs/PHASE1_CHECKLIST.md - Pre-implementation checklist
✅ docs/PHASE0_SETUP.md - Environment setup (Phase 0)
✅ Code comments with Phase 1 TODOs
```

### Helper Functions
```
✅ JSONValidator - Validate BDD scenario structure
✅ PreconditionFormatter - Format preconditions
✅ AcceptanceCriteriaExtractor - Extract AC from issues
✅ MarkdownExporter - Convert scenarios to markdown
✅ CostTracker - Calculate API costs
```

---

## 🎯 Quick Start (5 Minutes)

### 1. Prepare Environment
```bash
cd /path/to/automation-dashboard

# Install dependencies
pip install -r requirements.txt

# Verify Jira credentials
export JIRA_BASE_URL="https://your-domain.atlassian.net"
export JIRA_USER_EMAIL="your-email@company.com"
export JIRA_API_TOKEN="your-token"
export ANTHROPIC_API_KEY="sk-ant-your-key"

# Test script skeleton
python3 scripts/generate-test-cases.py
# Should output: "Configuration validated successfully"
```

### 2. Create Feature Branch
```bash
git checkout -b phase-1/test-case-creator-mvp
git push -u origin phase-1/test-case-creator-mvp
```

### 3. Start Day 1
```bash
# Read Phase 1 implementation guide
cat docs/PHASE1_IMPLEMENTATION.md | head -100

# Start with Jira integration
# - Implement JiraClient.fetch_issues()
# - Follow TODOs in script skeleton
# - Write tests as you code
```

---

## 📊 Metrics to Track

### Code Quality
- [ ] Test coverage: ≥80% (track with pytest --cov)
- [ ] Linting: 0 errors (if using ruff/flake8)
- [ ] Type hints: Complete (Python 3.9+ style)
- [ ] Docstrings: All public methods documented

### Functionality
- [ ] Issues fetched: ≥50 per run
- [ ] Attachment handling: 100% success rate on <10MB files
- [ ] Scenario generation: ≥3 per issue (average)
- [ ] PII redaction: 100% (manual spot-check)
- [ ] Jira attachment: 100% success rate
- [ ] Cost per issue: <$0.05 (track in logs)

### Performance
- [ ] Batch time (50 issues): <3 minutes
- [ ] Time per issue: 3-5 seconds
- [ ] API response time: <2s per call
- [ ] File I/O: <500ms

### Quality
- [ ] Test coverage: ≥80%
- [ ] Integration tests: ≥10
- [ ] Regression tests: 0 failures
- [ ] Manual testing: 5+ real issues
- [ ] User feedback: Positive (ask early users)

---

## 🔐 Security Checklist (Day 5)

Before merging Phase 1:

- [ ] **PII Redaction**: Verify no emails/IPs/secrets in Claude calls
  ```bash
  grep -r "example.com\|@company.com" data/
  # Should return 0 results
  ```

- [ ] **Token Security**: Verify tokens not logged
  ```bash
  grep -r "JIRA_API_TOKEN\|ANTHROPIC_API_KEY" scripts/
  # Should only see in config, not in logs
  ```

- [ ] **Attachment Validation**: Verify size/timeout limits enforced
  - [ ] Files >10MB rejected
  - [ ] Download timeout 5s enforced
  - [ ] Only PDF/DOCX accepted

- [ ] **Error Handling**: Graceful failures
  - [ ] No stack traces in user output
  - [ ] Errors logged with context
  - [ ] Plugin continues on individual issue failures

- [ ] **GitHub Secrets**: Verified configured
  - [ ] ANTHROPIC_API_KEY in secrets
  - [ ] Jira secrets still present
  - [ ] No hardcoded keys in code

---

## 🧪 Testing Strategy

### Unit Tests (Day 1-2)
```python
# tests/test_jira_integration.py
test_fetch_issues_success()
test_fetch_issues_empty()
test_download_attachment_success()
test_download_attachment_size_limit()
test_download_attachment_timeout()
test_api_call_auth_failure()

# tests/test_claude_integration.py
test_generate_scenarios_success()
test_generate_scenarios_validation()
test_precondition_extraction()
test_pii_redaction()

# tests/test_output.py
test_save_results_json()
test_attach_to_jira()
test_markdown_export()
test_cost_calculation()
```

### Integration Tests (Day 3-4)
```python
# tests/test_integration.py
test_full_pipeline_with_mocked_apis()
test_pipeline_error_recovery()
test_pipeline_rate_limiting()
test_jira_attachment_workflow()
```

### E2E Tests (Day 5)
```python
# tests/test_end_to_end.py
test_full_pipeline_real_jira_mocked_claude()
test_plugin_disabled_mode()
test_github_actions_workflow()
test_regression_jira_integration()
```

### Manual Testing (Day 5)
```bash
# Test with real Jira issues
python3 scripts/generate-test-cases.py

# Verify:
# - Issues fetched from Jira
# - Test cases generated
# - Results saved to data/test-cases.json
# - Results attached to Jira issues
# - Modal displays correctly
# - Dashboard still works
```

---

## 📝 Commit Strategy

**One commit per day** following this pattern:

```
Day 1:
git commit -m "feat: Implement Jira fetching and attachment parsing

- Add JiraClient.fetch_issues() with JQL pagination
- Add JiraClient.download_attachment() with safety limits
- Add _api_call() helper for Jira API
- Add unit tests for Jira integration
- Verified with real Jira instance (REB3 project)"

Day 2-3:
git commit -m "feat: Implement Claude BDD scenario generation

- Add PreconditionExtractor.extract() from issue content
- Add BDDGenerator.generate_scenarios() with Claude API
- Add scenario validation with JSONValidator
- Add PII redaction for sensitive data
- Add integration tests with mocked Claude
- Verified scenario quality with 5 sample issues"

Day 4:
git commit -m "feat: Implement test case output formatting

- Add JSON output to data/test-cases.json
- Add history logging to data/history/
- Add Jira attachment posting
- Add markdown export for readability
- Add cost tracking and reporting
- All file I/O tests passing"

Day 5:
git commit -m "feat: Add GitHub Actions workflow and UI

- Update .github/workflows/update-dashboard.yml
- Create modal UI component for test case display
- Integrate with Jira tracker tab
- Add end-to-end tests
- Deployed to staging and verified
- Phase 1 MVP complete"
```

---

## ⚠️ Potential Blockers & Solutions

| Blocker | Solution | Fallback |
|---------|----------|----------|
| Jira API auth fails | Verify token expiry, check permissions | Use staging Jira instance |
| Claude API rate limit | Implement backoff, throttle to 10/min | Use Haiku model (cheaper) |
| PDF parsing timeout | 3s timeout + subprocess rlimit | Skip attachments, use description |
| Large Jira instance | Filter query, limit to 50/run | Use project-specific query |
| GitHub Actions fails | Verify secrets, check logs | Test locally first |
| PII redaction misses | Manual review of first 10 issues | Add more patterns |

---

## 🎓 Learning Resources

### Jira API
- https://developer.atlassian.com/cloud/jira/rest/v3/
- JQL syntax: https://www.atlassian.com/software/jira/guides/jql

### Claude/Anthropic
- https://docs.anthropic.com/
- API reference: https://docs.anthropic.com/reference
- Model IDs: https://docs.anthropic.com/en/docs/about/models/overview

### BDD/Gherkin
- https://cucumber.io/docs/gherkin/
- https://en.wikipedia.org/wiki/Behavior-driven_development

### Testing
- Pytest: https://docs.pytest.org/
- responses: https://github.com/getsentry/responses
- pytest-cov: https://pytest-cov.readthedocs.io/

---

## 📞 Support & Escalation

### Questions During Development
- Refer to: `docs/PHASE1_IMPLEMENTATION.md` (detailed guide)
- Check: Code comments with "TODO Phase 1"
- Review: `scripts/utils.py` (helper functions)

### Blockers
1. First: Check PHASE1_IMPLEMENTATION.md "Known Constraints"
2. Then: Review error logs in `scripts/logs/`
3. Finally: Escalate to team lead with:
   - Specific error message
   - What you tried
   - Code snippet
   - Expected vs actual

### Security Questions
- Email: it.support@symphonyai.com (per org guidelines)
- Also consult: Section "Security Checklist"

---

## ✅ Final Readiness Check

Before you start, verify:

```bash
# Dependencies installed
pip show anthropic pdfplumber python-docx pytest responses

# Jira credentials work
python3 scripts/generate-test-cases.py
# Should say: "Configuration validated successfully"

# Git branch created
git branch | grep phase-1

# Files exist
ls -la docs/PHASE1_*.md
ls -la scripts/utils.py
ls -la tests/conftest.py
ls -la scripts/prompts/bdd-generation.txt

# Ready to code
echo "✅ Phase 1 Ready to Begin"
```

---

## 🚀 Let's Begin!

**You are fully prepared for Phase 1 implementation.**

### Next Steps:
1. ✅ Verify checklist above
2. ✅ Create feature branch
3. ✅ Start with Day 1 (Jira integration)
4. ✅ Reference `docs/PHASE1_IMPLEMENTATION.md` for detailed tasks
5. ✅ Commit daily and push
6. ✅ Track metrics in spreadsheet or notes
7. ✅ Prepare PR at end of Day 5

---

## 📊 Summary

| Aspect | Status | Details |
|--------|--------|---------|
| **Planning** | ✅ Complete | 5-day breakdown, success criteria defined |
| **Foundation** | ✅ Complete | All classes, fixtures, utilities ready |
| **Documentation** | ✅ Complete | 1,500+ lines, examples provided |
| **Security** | ✅ Complete | PII redaction, token handling patterns |
| **Testing** | ✅ Ready | Test framework set up, placeholders ready |
| **Environment** | ✅ Ready | Dependencies, credentials verified |
| **Go/No-Go** | 🟢 **GO** | All prerequisites met, ready to proceed |

---

**Phase 0:** ✅ Complete  
**Phase 1:** 🟢 **READY TO START**  
**Timeline:** 5-7 days  
**Status:** 🚀 **LET'S BUILD THIS**

---

*Phase 1 MVP: Test Case Creator Plugin*  
*Generating intelligent BDD scenarios with Claude AI*  
*Automated. Secure. Ready to ship.*
