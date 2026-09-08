# Phase 1 - Quick Start Guide 🚀

**Status:** ✅ Complete | **Tests:** 25/25 passing | **Ready:** Production

---

## 5-Minute Setup

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Set Environment Variables

**Option A: Use Test Credentials (for demo)**
```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-test-key-12345"
$env:JIRA_BASE_URL = "https://test-domain.atlassian.net"
$env:JIRA_USER_EMAIL = "test@example.com"
$env:JIRA_API_TOKEN = "test-token"
```

**Option B: Use Real Credentials**
```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-your-real-key"
$env:JIRA_BASE_URL = "https://your-domain.atlassian.net"
$env:JIRA_USER_EMAIL = "your-email@company.com"
$env:JIRA_API_TOKEN = "your-jira-token"
```

### Step 3: Generate Mock Data
```bash
python test-local.py
# Output: ✓ 5 test issues created in data/jira.json
```

### Step 4: Start Dashboard
```bash
python server.py
# Opens on http://localhost:6060
```

### Step 5: Login & Generate

1. Open browser: http://localhost:6060
2. Login with: `RetechQA2026!` or `SymphonyQA2026!`
3. Click: **⚡ Generate Test Cases** (top right)
4. Select: Test issues you want
5. Click: **Generate**
6. Wait: 1-2 minutes for Claude to generate scenarios
7. View: BDD test cases in results!

---

## What You'll See

### Dashboard Header
```
🎯 Quality at a glance v16
[Refresh] [⚡ Generate Test Cases] [🌙 Light] [🔒 Lock] [Export pack]
```

### Generate Modal - Step 1: Select
```
✅ TEST-101: Sample Requirement (Task)
✅ TEST-102: Sample Requirement (Story)
✅ TEST-103: Sample Requirement (Task)
✅ TEST-104: Sample Requirement (Story)
✅ TEST-105: Sample Requirement (Task)

Selected: 5/5 issues
```

### Generate Modal - Step 2: Progress
```
Progress: ████████░░ 80%

Status:
  Issues Processed: 3/5
  Scenarios Generated: 15
  API Provider: Claude
  Estimated Time: ~1 minute
```

### Generate Modal - Step 3: Results
```
Generation Complete! ✨

Total Scenarios:     25
Successful:          5
Failed:              0

Sample Scenarios:
• [positive] User logs in with valid credentials (P1)
• [negative] Invalid password shows error message (P1)
• [edge-case] Login with special characters (P2)
• ... and more
```

---

## Verify Installation

```bash
# Run all tests
pytest tests/ -v

# Expected: 25 tests passing
# ✅ 9 Jira integration tests
# ✅ 16 Claude integration tests
```

---

## Folder Structure

```
automation-dashboard/
├── scripts/
│   ├── generate-test-cases.py    ← Main generator
│   ├── prompts/bdd-generation.txt ← Claude prompt
│   ├── local_auth.py              ← Test auth
│   └── utils.py                   ← Helpers
├── assets/
│   ├── js/test-case-generator.js  ← Modal UI
│   └── css/test-case-generator.css ← Styling
├── data/
│   ├── jira.json                  ← Mock issues
│   └── test-cases.json            ← Generated results
├── tests/
│   ├── test_jira_integration.py    ← 9 tests
│   ├── test_claude_integration.py  ← 16 tests
│   └── conftest.py                ← Fixtures
├── docs/                          ← 9 guides
├── server.py                      ← HTTP server
├── index.html                     ← Dashboard
└── requirements.txt               ← Dependencies
```

---

## Common Issues

### "No AI provider configured"
```powershell
# Set your API key
$env:ANTHROPIC_API_KEY = "sk-ant-your-key"

# OR use OpenAI
$env:OPENAI_API_KEY = "sk-your-key"
```

### "Port 6060 already in use"
```powershell
# Windows: Kill process on port 6060
Get-Process | Where-Object { $_.Port -eq 6060 } | Stop-Process -Force

# Or change port in server.py:
# PORT = 6061
```

### "UnicodeEncodeError" (Windows)
```powershell
# Already fixed! Script handles UTF-8 encoding on Windows
# If still issues, check Python version:
python --version  # Should be 3.8+
```

### "Jira issues not loading"
```bash
# Regenerate mock data
python test-local.py

# Or refresh browser (Ctrl+Shift+R)
```

---

## API Endpoints

Test with curl:

```bash
# Get Jira issues
curl http://localhost:6060/api/jira-issues

# Trigger generation
curl -X POST http://localhost:6060/api/generate-test-cases \
  -H "Content-Type: application/json" \
  -d '{"issueKeys": ["TEST-101"]}'

# Get results
curl http://localhost:6060/api/test-cases
```

---

## Documentation Files

| File | Purpose |
|------|---------|
| `PHASE1_IMPLEMENTATION_COMPLETE.md` | Full Phase 1 summary |
| `docs/DASHBOARD_TEST_CASE_GENERATION.md` | User guide |
| `docs/AI_PROVIDER_SETUP.md` | AI provider configuration |
| `TESTING_LOCALLY.md` | Local testing guide |
| `WINDOWS_QUICK_START.md` | Windows-specific setup |
| `docs/LOCAL_DEVELOPMENT.md` | Dev environment guide |

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Escape` | Close modal |
| `Ctrl+R` | Refresh dashboard |
| `Ctrl+Shift+R` | Hard refresh (clear cache) |
| `F12` | Open DevTools |

---

## Next Steps

### For Testing
1. ✅ Run full test suite: `pytest tests/ -v`
2. ✅ Test in dashboard: Click "⚡ Generate Test Cases"
3. ✅ Verify mock data: Check `data/test-cases.json`
4. ✅ Check logs: `scripts/logs/generate-test-cases.log`

### For Deployment
1. Set production environment variables
2. Update `.env` (not committed to git)
3. Run: `python server.py`
4. Monitor logs and API usage
5. Set up CI/CD pipeline

### For Development
1. Read `docs/LOCAL_DEVELOPMENT.md`
2. Create feature branches from `jira_changes`
3. Run tests before committing
4. Update documentation

---

## Support

### Check Logs
```bash
# Python server logs (console output)
python server.py  # Watch for errors

# Test case generation logs
type scripts/logs/generate-test-cases.log

# Browser console (F12)
# Look for JavaScript errors
```

### Run Tests
```bash
# All tests
pytest tests/ -v

# Specific test
pytest tests/test_jira_integration.py -v

# With coverage
pytest tests/ --cov=scripts
```

### Debug Mode
```powershell
$env:DEBUG = "true"
python scripts/generate-test-cases.py  # Verbose output
```

---

## Performance Tips

- **Fewer issues = Faster generation**
  - 5 issues: ~1-2 min
  - 10 issues: ~2-4 min
  - 20+ issues: ~5+ min

- **Use Claude (default) - it's faster than GPT-4**

- **Close browser tabs** to free up resources

- **Run during off-peak hours** for consistent performance

---

## File Sizes

| Component | Size | Type |
|-----------|------|------|
| `generate-test-cases.py` | 681 lines | Python |
| `test-case-generator.js` | 330 lines | JavaScript |
| `test-case-generator.css` | 500 lines | CSS |
| Tests | 25 tests | pytest |
| Documentation | 9 files | Markdown |
| **Total** | **~1,500 lines** | Code |

---

## Summary

✅ **Backend:** Jira → Claude/OpenAI → JSON  
✅ **Frontend:** Dashboard modal UI with real-time progress  
✅ **Testing:** 25 tests, 100% passing  
✅ **Docs:** Comprehensive guides for every use case  
✅ **Windows:** UTF-8 encoding fully supported  

**Everything is ready!** Start using it now. 🎉

---

## Questions?

1. **Setup issues?** → Read `TESTING_LOCALLY.md` or `WINDOWS_QUICK_START.md`
2. **How to use?** → Read `docs/DASHBOARD_TEST_CASE_GENERATION.md`
3. **Which AI provider?** → Read `docs/AI_PROVIDER_SETUP.md`
4. **Want OpenAI?** → Read `docs/OPENAI_SUPPORT.md`
5. **Development?** → Read `docs/LOCAL_DEVELOPMENT.md`

---

**Ready to generate amazing test cases?** Let's go! 🚀
