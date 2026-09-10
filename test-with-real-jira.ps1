# Quick Start: Test with Real REB3 Jira Issues
# =============================================
# This script helps you quickly test the complete workflow
# with actual Jira tickets from REB3 project

Write-Host "
╔════════════════════════════════════════════════════════════════════╗
║          Test Automation Dashboard - Real Jira Testing             ║
║                        Quick Start Guide                           ║
╚════════════════════════════════════════════════════════════════════╝
" -ForegroundColor Cyan

# Step 1: Collect Jira Credentials
Write-Host "`n[STEP 1] Enter Your Jira Credentials" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

$jiraBaseUrl = Read-Host "Jira Base URL (e.g., https://retech.atlassian.net)"
$jiraEmail = Read-Host "Jira Email (e.g., your-email@company.com)"
$jiraToken = Read-Host "Jira API Token (from https://id.atlassian.com/manage-profile/security/api-tokens)" -AsSecureString

# Convert secure string to plain text for environment variable
$jiraTokenPlain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToCoTaskMemUnicode($jiraToken))

# Step 2: Collect Claude API Key
Write-Host "`n[STEP 2] Enter Your AI Provider Key" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

Write-Host "Choose AI Provider:" -ForegroundColor Cyan
Write-Host "  1) Claude (Anthropic) - Recommended" -ForegroundColor Green
Write-Host "  2) OpenAI (GPT)" -ForegroundColor Blue
$aiChoice = Read-Host "Enter your choice (1 or 2)"

if ($aiChoice -eq "2") {
    $aiProvider = "openai"
    $apiKey = Read-Host "OpenAI API Key (from https://platform.openai.com/api-keys)"
    $env:OPENAI_API_KEY = $apiKey
    Write-Host "✓ OpenAI configured" -ForegroundColor Green
} else {
    $aiProvider = "anthropic"
    $apiKey = Read-Host "Claude API Key (from https://console.anthropic.com/)"
    $env:ANTHROPIC_API_KEY = $apiKey
    Write-Host "✓ Claude configured" -ForegroundColor Green
}

# Step 3: Set Environment Variables
Write-Host "`n[STEP 3] Setting Environment Variables" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

$env:JIRA_BASE_URL = $jiraBaseUrl
$env:JIRA_USER_EMAIL = $jiraEmail
$env:JIRA_API_TOKEN = $jiraTokenPlain
$env:JIRA_PROJECT_KEY = "REB3"

Write-Host "✓ JIRA_BASE_URL: $jiraBaseUrl" -ForegroundColor Green
Write-Host "✓ JIRA_USER_EMAIL: $jiraEmail" -ForegroundColor Green
Write-Host "✓ JIRA_API_TOKEN: [SET]" -ForegroundColor Green
Write-Host "✓ JIRA_PROJECT_KEY: REB3" -ForegroundColor Green

# Step 4: Verify Directory
Write-Host "`n[STEP 4] Verifying Project Directory" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not (Test-Path "$scriptDir\server.py")) {
    Write-Host "❌ server.py not found in $scriptDir" -ForegroundColor Red
    Write-Host "Make sure you run this script from the project root directory" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ Project directory verified" -ForegroundColor Green
Write-Host "✓ Location: $scriptDir" -ForegroundColor Green

# Step 5: Test Jira Connection
Write-Host "`n[STEP 5] Testing Jira Connection" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

Write-Host "Connecting to Jira..." -ForegroundColor Cyan

# Create a temporary Python script to test connection
$testScript = @"
import sys
import base64
import urllib.request
import urllib.error
import json

base_url = """$jiraBaseUrl"""
email = """$jiraEmail"""
token = """$jiraTokenPlain"""

try:
    credentials = f"{email}:{token}"
    encoded = base64.b64encode(credentials.encode()).decode()

    headers = {
        'Authorization': f'Basic {encoded}',
        'Content-Type': 'application/json'
    }

    # Test 1: Authenticate
    url = f"{base_url}/rest/api/3/myself"
    req = urllib.request.Request(url, headers=headers)

    with urllib.request.urlopen(req, timeout=10) as response:
        data = json.loads(response.read().decode('utf-8'))
        print(f"✓ Authentication successful")
        print(f"✓ User: {data.get('displayName')}")
        print(f"✓ Email: {data.get('emailAddress')}")

    # Test 2: Access REB3 project
    url = f"{base_url}/rest/api/3/project/REB3"
    req = urllib.request.Request(url, headers=headers)

    with urllib.request.urlopen(req, timeout=10) as response:
        data = json.loads(response.read().decode('utf-8'))
        print(f"✓ REB3 Project Access: OK")
        print(f"✓ Project: {data.get('name')}")

    # Test 3: Fetch issues
    jql = "project = REB3 ORDER BY updated DESC"
    url = f"{base_url}/rest/api/3/search?jql={urllib.parse.quote(jql)}&maxResults=5"
    req = urllib.request.Request(url, headers=headers)

    with urllib.request.urlopen(req, timeout=10) as response:
        data = json.loads(response.read().decode('utf-8'))
        issues = data.get('issues', [])
        print(f"✓ REB3 Issues Found: {len(issues)}")
        if issues:
            for issue in issues[:3]:
                print(f"  - {issue['key']}: {issue['fields']['summary'][:60]}")

    print(f"\\n✓✓✓ All tests passed! Ready to generate test cases.\\n")
    sys.exit(0)

except urllib.error.HTTPError as e:
    error_msg = e.read().decode('utf-8')
    if "401" in str(e):
        print(f"❌ Authentication failed (401 Unauthorized)")
        print(f"   Check your Jira email and API token")
    elif "403" in str(e):
        print(f"❌ Permission denied (403 Forbidden)")
        print(f"   You may not have access to REB3 project")
    elif "404" in str(e):
        print(f"❌ Not found (404)")
        print(f"   Check your Jira Base URL")
    else:
        print(f"❌ HTTP {e.code}: {error_msg}")
    sys.exit(1)

except Exception as e:
    print(f"❌ Connection failed: {e}")
    print(f"   Check your Jira Base URL and network connection")
    sys.exit(1)
"@

# Save and run test script
$testScriptPath = "$scriptDir\__test_jira_connection.py"
Set-Content -Path $testScriptPath -Value $testScript

try {
    $output = & python $testScriptPath 2>&1
    Write-Host $output -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to test connection: $_" -ForegroundColor Red
    exit 1
} finally {
    Remove-Item $testScriptPath -ErrorAction SilentlyContinue
}

# Step 6: Start Server
Write-Host "`n[STEP 6] Starting Dashboard Server" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

Write-Host "Starting server on http://localhost:6060" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop server" -ForegroundColor Yellow

Write-Host "`n╔════════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                        READY TO TEST!                              ║" -ForegroundColor Green
Write-Host "║                                                                    ║" -ForegroundColor Green
Write-Host "║  1. Open http://localhost:6060 in your browser                    ║" -ForegroundColor Green
Write-Host "║  2. Click [Generate Test Cases] button                            ║" -ForegroundColor Green
Write-Host "║  3. Credentials already set, click [Verify]                       ║" -ForegroundColor Green
Write-Host "║  4. Select 5 REB3 issues                                          ║" -ForegroundColor Green
Write-Host "║  5. Click [Generate]                                             ║" -ForegroundColor Green
Write-Host "║  6. Approve scenarios in modal                                    ║" -ForegroundColor Green
Write-Host "║  7. Click [Sync to Jira]                                          ║" -ForegroundColor Green
Write-Host "║  8. Check Jira for child issues                                   ║" -ForegroundColor Green
Write-Host "║                                                                    ║" -ForegroundColor Green
Write-Host "║  For detailed instructions, see:                                  ║" -ForegroundColor Green
Write-Host "║  → LOCAL_TESTING_WITH_REAL_JIRA.md                                ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════════════╝" -ForegroundColor Green

# Start server
Set-Location $scriptDir
python server.py
