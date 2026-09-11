# Phase 0: Test Case Creator Plugin - Setup Guide

## Overview

Phase 0 prepares the development environment for the Test Case Creator plugin. This includes installing dependencies, configuring credentials, and setting up the test suite.

**Timeline:** 2-3 days  
**Status:** ✅ In Progress

---

## Prerequisites

- Python 3.9 or higher
- Git
- GitHub repository access (for adding secrets)
- Jira Cloud account with API access
- Anthropic API key

---

## Step 1: Install Python Dependencies

### 1.1 Create requirements.txt

✅ **Already created:** `requirements.txt`

This file includes:
- `anthropic>=0.35.0` - Claude API
- `pdfplumber>=0.9.0` - PDF parsing
- `python-docx>=0.8.11` - DOCX parsing
- `pytest>=7.4.0` - Testing framework
- `responses>=0.23.0` - HTTP mocking

### 1.2 Install Dependencies

```bash
# Navigate to project root
cd /path/to/automation-dashboard

# Install all dependencies
pip install -r requirements.txt

# Verify installation
python3 -c "import anthropic; print(f'Anthropic SDK v{anthropic.__version__}')"
python3 -c "import pdfplumber; print('pdfplumber OK')"
python3 -c "import docx; print('python-docx OK')"
pip show pytest
```

**Expected Output:**
```
Anthropic SDK v0.35.1
pdfplumber OK
python-docx OK
Name: pytest
Version: 7.4.0
...
```

### 1.3 Create logs directory

```bash
mkdir -p scripts/logs
```

---

## Step 2: Configure Jira API Credentials

### 2.1 Generate Jira API Token

1. Go to **Atlassian Account Settings**: https://id.atlassian.com/manage/api-tokens
2. Click **Create API token**
3. Give it a name: `Test Case Creator Plugin`
4. Click **Create**
5. Copy the generated token (you'll only see it once)

### 2.2 Find Your Jira Base URL

Format: `https://your-domain.atlassian.net`

Example: `https://retech.atlassian.net`

### 2.3 Verify Jira Access (Local Testing)

```bash
# Set temporary environment variables
export JIRA_BASE_URL="https://your-domain.atlassian.net"
export JIRA_USER_EMAIL="your-email@company.com"
export JIRA_API_TOKEN="your-api-token-here"

# Test Jira connectivity
python3 -c "
import os
import json
import base64
import urllib.request

base_url = os.getenv('JIRA_BASE_URL')
email = os.getenv('JIRA_USER_EMAIL')
token = os.getenv('JIRA_API_TOKEN')

credentials = f'{email}:{token}'
encoded = base64.b64encode(credentials.encode()).decode()
headers = {'Authorization': f'Basic {encoded}', 'Content-Type': 'application/json'}

try:
    req = urllib.request.Request(f'{base_url}/rest/api/3/myself', headers=headers)
    with urllib.request.urlopen(req, timeout=5) as response:
        user = json.loads(response.read())
        print(f'✓ Jira auth OK: {user[\"displayName\"]}')
except Exception as e:
    print(f'✗ Jira auth failed: {e}')
"
```

**Expected Output:**
```
✓ Jira auth OK: Your Name
```

---

## Step 3: Configure Anthropic API Credentials

### 3.1 Get Your Anthropic API Key

1. Go to **Anthropic Console**: https://console.anthropic.com/account/keys
2. Click **Create Key**
3. Copy the generated API key

### 3.2 Verify Claude API Access (Local Testing)

```bash
# Set temporary environment variable
export ANTHROPIC_API_KEY="sk-ant-your-key-here"

# Test Claude connectivity
python3 << 'EOF'
import os
from anthropic import Anthropic

api_key = os.getenv('ANTHROPIC_API_KEY')
if not api_key:
    print("✗ ANTHROPIC_API_KEY not set")
    exit(1)

try:
    client = Anthropic(api_key=api_key)
    
    # Make a simple test request
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=100,
        messages=[
            {"role": "user", "content": "Say 'Test successful' in one word."}
        ]
    )
    
    response_text = message.content[0].text
    if "successful" in response_text.lower() or "success" in response_text.lower():
        print(f"✓ Claude API OK: {response_text}")
    else:
        print(f"✓ Claude API OK (Response: {response_text})")
except Exception as e:
    print(f"✗ Claude API failed: {e}")
EOF
```

**Expected Output:**
```
✓ Claude API OK: Test successful
```

---

## Step 4: Configure GitHub Secrets

### 4.1 Add Secrets to GitHub Repository

These secrets will be used by GitHub Actions when running the workflow.

1. Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions**

2. Add the following secrets (click **New repository secret**):

   - **ANTHROPIC_API_KEY**
     - Value: Your Anthropic API key
     - Name: `ANTHROPIC_API_KEY`
   
   - **JIRA_BASE_URL** (if not already set)
     - Value: `https://your-domain.atlassian.net`
     - Name: `JIRA_BASE_URL`
   
   - **JIRA_USER_EMAIL** (if not already set)
     - Value: Your email address
     - Name: `JIRA_USER_EMAIL`
   
   - **JIRA_API_TOKEN** (if not already set)
     - Value: Your Jira API token
     - Name: `JIRA_API_TOKEN`

### 4.2 Verify Secrets Configuration

```bash
# List configured secrets (via GitHub CLI)
gh secret list --repo owner/automation-dashboard

# Expected output:
# ANTHROPIC_API_KEY  ****
# JIRA_API_TOKEN     ****
# JIRA_BASE_URL      https://your-domain.atlassian.net
# JIRA_USER_EMAIL    user@company.com
```

---

## Step 5: Set Up Test Suite

### 5.1 Test Structure Overview

The test suite is organized in `/tests/` directory:

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── test_bdd_generator.py    # Unit tests for scenario generation
├── test_integration.py      # Integration tests with mocked APIs
└── ...
```

✅ **Already created:**
- `tests/conftest.py` - Pytest fixtures and configuration
- `tests/test_bdd_generator.py` - Placeholder unit tests
- `tests/test_integration.py` - Placeholder integration tests

### 5.2 Run Tests

```bash
# Run all tests with coverage report
pytest tests/ -v --cov=scripts --cov-report=html

# Run specific test file
pytest tests/test_bdd_generator.py -v

# Run tests with debugging output
pytest tests/ -v -s

# Run only integration tests
pytest tests/test_integration.py -v
```

### 5.3 View Coverage Report

```bash
# Generate and open HTML coverage report
pytest tests/ --cov=scripts --cov-report=html
open htmlcov/index.html  # macOS
# or
start htmlcov/index.html  # Windows
```

---

## Step 6: Verify Script Structure

### 6.1 Main Script Location

✅ **Already created:** `scripts/generate-test-cases.py`

This is the main entry point for test case generation. It includes:
- Configuration management
- Jira API client
- Claude AI integration (Phase 1 implementation)
- Error handling and logging

### 6.2 Test the Script Structure

```bash
# Make script executable (Unix/Linux/macOS)
chmod +x scripts/generate-test-cases.py

# Test script imports and basic structure
python3 -c "
import sys
sys.path.insert(0, '.')
import scripts.generate_test_cases as gen

# Verify classes exist
print('✓ ConfigManager imported')
print('✓ JiraClient imported')
print('✓ BDDGenerator imported')
print('✓ TestCaseGenerator imported')
"
```

### 6.3 Run Script in Validation Mode (No Generation Yet)

```bash
# Set environment variables
export JIRA_BASE_URL="https://your-domain.atlassian.net"
export JIRA_USER_EMAIL="your-email@company.com"
export JIRA_API_TOKEN="your-jira-token"
export ANTHROPIC_API_KEY="sk-ant-your-key"

# Run script (will validate config but not generate yet)
python3 scripts/generate-test-cases.py
```

**Expected Output (Phase 0):**
```
============================================================
Test Case Creator - BDD Scenario Generator
============================================================
2026-09-08 14:00:00 - root - INFO - Configuration validated successfully
2026-09-08 14:00:01 - root - INFO - ✓ Jira auth OK: Your Name
2026-09-08 14:00:02 - root - INFO - Fetching issues (max 50)...
2026-09-08 14:00:02 - root - INFO - Found 0 issues to process (Phase 1 implementation pending)
```

---

## Step 7: Create Logs Directory

```bash
# Create logs directory
mkdir -p scripts/logs

# Verify logs directory exists
ls -la scripts/logs/
```

---

## Step 8: Local Environment Setup (.env file - Optional)

For local development, you can create a `.env` file to avoid setting env vars each time:

```bash
# Create .env file (DO NOT COMMIT THIS FILE!)
cat > .env << 'EOF'
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_USER_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-jira-token
ANTHROPIC_API_KEY=sk-ant-your-key
TEST_CASE_CREATOR_ENABLED=true
GENERATION_MODEL=claude-3-5-sonnet-20241022
DEBUG=false
EOF

# Add to .gitignore (keep secrets out of git)
echo ".env" >> .gitignore

# Load .env variables for testing
set -a
source .env
set +a
python3 scripts/generate-test-cases.py
```

---

## Step 9: Documentation Review

✅ **Already created:**
- `docs/PHASE0_SETUP.md` - This file
- Comments in `scripts/generate-test-cases.py` with Phase 1 implementation placeholders

---

## Checklist - Phase 0 Complete

Use this checklist to verify Phase 0 setup is complete:

```
DEPENDENCIES & INSTALLATION:
  [ ] requirements.txt created with all dependencies
  [ ] pip install -r requirements.txt successful
  [ ] All packages verified to be installed
  [ ] scripts/logs/ directory created

JIRA CREDENTIALS:
  [ ] Jira API token generated (https://id.atlassian.com/manage/api-tokens)
  [ ] Jira base URL identified (https://your-domain.atlassian.net)
  [ ] Local test confirms Jira connectivity works
  [ ] Jira credentials added to GitHub Secrets

ANTHROPIC CREDENTIALS:
  [ ] Anthropic API key generated (https://console.anthropic.com/account/keys)
  [ ] Local test confirms Claude API connectivity works
  [ ] ANTHROPIC_API_KEY added to GitHub Secrets

TEST SUITE:
  [ ] tests/conftest.py created with fixtures
  [ ] tests/test_bdd_generator.py created (placeholders)
  [ ] tests/test_integration.py created (placeholders)
  [ ] pytest installed and working
  [ ] Tests run successfully (pytest tests/ -v)

SCRIPT SKELETON:
  [ ] scripts/generate-test-cases.py created
  [ ] Script structure verified (classes, imports)
  [ ] Script runs in validation mode
  [ ] Logging configured

DOCUMENTATION:
  [ ] PHASE0_SETUP.md (this file) created
  [ ] Code comments added for Phase 1 implementation
  [ ] .env.example created (if using .env)
  [ ] Updated .gitignore to exclude .env

READY FOR PHASE 1:
  [ ] All Phase 0 items checked
  [ ] Team reviewed findings from pre-implementation audit
  [ ] Approved go/no-go decision received
  [ ] Phase 1 development timeline confirmed
```

---

## Troubleshooting

### Problem: Jira API authentication fails

**Symptoms:**
```
✗ Jira auth failed: HTTP Error 401
```

**Solutions:**
1. Verify Jira API token is not expired (tokens don't auto-expire, but check Atlassian account)
2. Ensure email is correct (use email associated with your Jira account)
3. Verify JIRA_BASE_URL format: `https://your-domain.atlassian.net` (no trailing slash)
4. Check that your Jira user has sufficient permissions to read issues

### Problem: Claude API authentication fails

**Symptoms:**
```
✗ Claude API failed: Error 401 Unauthorized
```

**Solutions:**
1. Verify API key is correct (copy from https://console.anthropic.com/account/keys)
2. Check API key hasn't been revoked in Anthropic console
3. Ensure no extra spaces in API key
4. Try a simple test request:
   ```bash
   curl https://api.anthropic.com/v1/messages \
     -H "x-api-key: sk-ant-your-key" \
     -H "anthropic-version: 2023-06-01"
   ```

### Problem: Tests fail to import fixtures

**Symptoms:**
```
ImportError: No module named 'conftest'
```

**Solutions:**
1. Ensure `tests/conftest.py` exists
2. Run pytest from project root: `pytest tests/ -v`
3. Verify `__init__.py` not needed (pytest auto-discovers conftest.py)

### Problem: pdfplumber or python-docx installation fails

**Symptoms:**
```
ERROR: Could not find a version that satisfies the requirement pdfplumber>=0.9.0
```

**Solutions:**
1. Update pip: `pip install --upgrade pip`
2. Try installing with specific version: `pip install pdfplumber==0.9.0`
3. On macOS, may need to install Poppler: `brew install poppler`
4. On Ubuntu/Debian: `sudo apt-get install libpoppler-cpp-dev`

---

## Next Steps: Phase 1 Development

Once Phase 0 is complete and approved:

1. **Day 1:** Implement Jira issue fetcher + attachment downloader
2. **Day 2-3:** Implement Claude prompt engineering + BDD generation
3. **Day 4:** Implement output formatting + file storage
4. **Day 5:** Create modal UI + documentation

See `docs/IMPLEMENTATION_ROADMAP.md` for detailed Phase 1 plan.

---

## Security Notes

⚠️ **IMPORTANT:**

1. **Never commit `.env` file** - It contains secrets
2. **API keys are sensitive** - Treat like passwords
3. **GitHub Secrets masking:**
   - GitHub auto-masks known secrets in logs
   - Always use `logger.debug()` for sensitive values (not `print()`)
   - Never log full API key or tokens
4. **PII in Jira:**
   - Jira issues may contain personal information
   - Phase 1 will implement sanitization before sending to Claude
5. **Attachment security:**
   - Validate file types and sizes (Phase 1)
   - Never execute attachment content
   - Use subprocess sandbox for parsing (Phase 1)

---

## Additional Resources

- **Jira API Docs:** https://developer.atlassian.com/cloud/jira/rest/v3/
- **Anthropic API Docs:** https://docs.anthropic.com/
- **Pytest Docs:** https://docs.pytest.org/
- **pdfplumber Docs:** https://github.com/jsvine/pdfplumber
- **python-docx Docs:** https://python-docx.readthedocs.io/

---

**Phase 0 Status:** ✅ SETUP COMPLETE

Next: Proceed to Phase 1 - MVP Implementation
