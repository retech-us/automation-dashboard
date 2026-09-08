# Local Testing with Test Passkey

## Quick Start

### 1️⃣ Generate Mock Data (One Command)

```bash
python3 test-local.py
```

**Output:**
```
✓ Passkey: test
✓ Level: full
✓ Purpose: For local development and testing
✓ Mock data saved to: data/jira.json
✓ 5 test issues created
```

### 2️⃣ Start Local Server

```bash
python3 server.py
```

**Output:**
```
✓ Server running on: http://localhost:6060
✓ Dashboard available at: http://localhost:6060/index.html
```

### 3️⃣ Open Dashboard & Login

```
http://localhost:6060
```

**At the login screen, enter one of these passkeys:**
- `RetechQA2026!` (Retech QA team)
- `SymphonyQA2026!` (Symphony AI QA team)

**You'll then see:**
- ✅ 5 mock Jira issues (TEST-101, TEST-102, etc.)
- ✅ All dashboard features working
- ✅ Mock data for testing
- ✅ No real API calls needed

---

## Available Test Passkeys

### `test` (Default - Recommended)
```bash
python3 test-local.py --passkey test
```
- **Level:** Full access
- **Purpose:** Local development and testing
- **Features:** All features enabled

### `demo`
```bash
python3 test-local.py --passkey demo
```
- **Level:** Read-only
- **Purpose:** Demo/presentation purposes
- **Features:** Limited to read operations

### `ci-test`
```bash
python3 test-local.py --passkey ci-test
```
- **Level:** Full access
- **Purpose:** CI/CD testing
- **Features:** Full access for automated tests

---

## Test Passkey Usage

### Generate Mock Jira Data
```bash
# Generate 5 mock issues (default)
python3 test-local.py

# Generate 10 mock issues
python3 test-local.py --issue-count 10

# Use different passkey
python3 test-local.py --passkey demo
```

### Generate Mock Jira + Test Cases
```bash
python3 test-local.py --generate-test-cases
```

**Creates:**
- `data/jira.json` - 5 mock Jira issues
- `data/test-cases.json` - Mock BDD test cases

### List Available Passkeys
```bash
python3 test-local.py --list-passkeys
```

**Output:**
```
test
  Test Passkey
  For local development and testing

demo
  Demo Passkey
  For demo/presentation purposes

ci-test
  CI Test Passkey
  For CI/CD testing
```

---

## Complete Workflow

### Setup (First Time)

```bash
# 1. Generate mock data with test passkey
python3 test-local.py --generate-test-cases

# Output shows:
# ✓ Passkey: test
# ✓ Mock data saved to: data/jira.json
# ✓ 5 test issues created
# ✓ Mock test cases saved to: data/test-cases.json
# ✓ 2 BDD scenarios created
```

### Development (Daily)

```bash
# Terminal 1: Start local server
python3 server.py

# Terminal 2: Edit code and refresh browser
# Edit files in assets/js/, assets/css/, etc.
# Refresh browser (Ctrl+R) to see changes

# Terminal 3: Run tests (if doing Phase 1)
pytest tests/ -v
```

### Testing

```bash
# View mock data
cat data/jira.json | jq .

# View mock test cases
cat data/test-cases.json | jq .

# Verify in browser
# Open: http://localhost:6060
# Should show mock Jira issues and test cases
```

---

## Test Credentials

When using test passkey, these credentials are available:

```
jira_base_url: https://test-domain.atlassian.net
jira_user_email: test@example.com
jira_api_token: test-jira-token-12345
anthropic_api_key: sk-ant-test-key-12345
environment: test
mode: local
```

**⚠️ Note:** These are NOT real credentials. They're for testing only.

---

## Mock Data Format

### Mock Jira Issues
```json
{
  "issues": [
    {
      "key": "TEST-101",
      "summary": "Test Issue 1: Sample Requirement",
      "description": "This is a test issue for local development...",
      "fields": {
        "issuetype": { "name": "Story" },
        "status": { "name": "In Progress" },
        "attachment": []
      }
    }
  ],
  "status": "mock",
  "lastUpdated": "2026-09-08T10:00:00Z",
  "source": "local_testing"
}
```

### Mock Test Cases
```json
{
  "testCases": [
    {
      "issueKey": "TEST-101",
      "summary": "Test Issue 1: Sample Requirement",
      "scenarios": [
        {
          "id": "SC-001",
          "title": "Valid test scenario",
          "type": "positive",
          "preconditions": ["Given system is in test mode"],
          "steps": [...]
        }
      ]
    }
  ],
  "source": "local_testing"
}
```

---

## Development During Phase 1

### Day 1-2: Testing Jira Integration

```bash
# Generate mock Jira data
python3 test-local.py --issue-count 10

# Start server
python3 server.py

# Run tests
pytest tests/test_jira_integration.py -v

# Browser: http://localhost:6060
# See mock issues displayed
```

### Day 3-4: Testing Claude Integration

```bash
# Generate mock data + test cases
python3 test-local.py --generate-test-cases

# Start server
python3 server.py

# Run tests
pytest tests/test_claude_integration.py -v

# Browser: http://localhost:6060
# See mock test cases displayed
```

### Day 5: Testing UI & Deployment

```bash
# Everything is ready
python3 server.py

# Test dashboard features
# Verify local development works
# Then push to GitHub for auto-deployment
```

---

## Troubleshooting

### "Invalid passkey" error

```bash
# List available passkeys
python3 test-local.py --list-passkeys

# Use correct passkey
python3 test-local.py --passkey test
```

### "No data showing in dashboard"

```bash
# Regenerate mock data
python3 test-local.py

# Clear browser cache
# Hard refresh: Ctrl+Shift+R (Windows/Linux)
#              Cmd+Shift+R (macOS)

# Verify files exist
ls -la data/jira.json
ls -la data/test-cases.json
```

### "Port 6060 already in use"

```bash
# Kill previous server
# macOS/Linux:
lsof -i :6060
kill -9 <PID>

# Windows:
netstat -ano | findstr :6060
taskkill /PID <PID> /F
```

---

## Features with Test Passkey

✅ Generate mock Jira issues  
✅ Generate mock test cases  
✅ Test dashboard UI  
✅ Test filtering & search  
✅ Test charts & visualizations  
✅ Test modal dialogs  
✅ Test API responses  
✅ Test error handling  
✅ Run full test suite  
✅ No real API calls needed  
✅ No credentials needed  
✅ Zero external dependencies  

---

## Environment Variables

### Using Test Passkey Explicitly

```bash
# Set passkey in environment
export LOCAL_PASSKEY='test'

# Or use environment mode
export ENVIRONMENT='development'

# Then run testing tool
python3 test-local.py
```

### Override Passkey

```bash
# Command line override
python3 test-local.py --passkey demo
```

---

## Switching Between Real and Test

### With Test Data (Development)
```bash
python3 test-local.py
python3 server.py
# Open: http://localhost:6060
# Uses mock data
```

### With Real Data (Testing)
```bash
# Fetch real Jira data
export JIRA_BASE_URL="https://your-domain.atlassian.net"
export JIRA_USER_EMAIL="your-email@company.com"
export JIRA_API_TOKEN="your-token"
python3 scripts/fetch-jira.py

# Start server
python3 server.py
# Open: http://localhost:6060
# Uses real data
```

---

## Test Passkey Security

⚠️ **Important:**

- Test passkeys are **FOR DEVELOPMENT ONLY**
- They are **NOT** real credentials
- They are **PUBLIC** (hardcoded in repository)
- They **CANNOT** access real APIs
- Use only on **localhost**
- Do **NOT** use in production

---

## Examples

### Example 1: Quick Testing

```bash
# Setup takes 10 seconds
$ python3 test-local.py
$ python3 server.py

# Visit: http://localhost:6060
# Done! Dashboard ready for testing
```

### Example 2: Testing During Phase 1

```bash
# Terminal 1: Generate data
python3 test-local.py --generate-test-cases

# Terminal 2: Start server
python3 server.py

# Terminal 3: Run tests
pytest tests/ -v

# Browser: http://localhost:6060
# Edit code and refresh to test
```

### Example 3: Demo/Presentation

```bash
# Use demo passkey
python3 test-local.py --passkey demo

# Start server
python3 server.py

# Open: http://localhost:6060
# Ready for demo!
```

---

## Next Steps

1. ✅ Run: `python3 test-local.py`
2. ✅ Start: `python3 server.py`
3. ✅ Open: `http://localhost:6060`
4. ✅ Develop: Edit files and refresh
5. ✅ Test: Run pytest during Phase 1
6. ✅ Deploy: Push to GitHub

---

**Local Testing Ready! 🚀**

Start with one command:
```bash
python3 test-local.py
```

Then:
```bash
python3 server.py
```

Then open:
```
http://localhost:6060
```

Happy testing! 🎯
