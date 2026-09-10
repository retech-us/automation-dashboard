# Fetch Real REB3 Issues from Jira
# ================================
# This script fetches REAL REB3 issues and saves them to data/jira.json
# Run this BEFORE testing in the dashboard

Write-Host "
╔════════════════════════════════════════════════════════════════╗
║         Fetch Real REB3 Issues from Jira                       ║
╚════════════════════════════════════════════════════════════════╝
" -ForegroundColor Cyan

# Collect Jira Credentials
Write-Host "`n[STEP 1] Enter Your Jira Credentials" -ForegroundColor Yellow

$jiraBaseUrl = Read-Host "Jira Base URL (e.g., https://retech.atlassian.net)"
$jiraEmail = Read-Host "Jira Email (e.g., your-email@company.com)"
$jiraToken = Read-Host "Jira API Token" -AsSecureString

# Convert secure string to plain text
$jiraTokenPlain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToCoTaskMemUnicode($jiraToken))

# Set environment variables
$env:JIRA_BASE_URL = $jiraBaseUrl
$env:JIRA_USER_EMAIL = $jiraEmail
$env:JIRA_API_TOKEN = $jiraTokenPlain
$env:JIRA_PROJECT_KEY = "REB3"

Write-Host "`n✓ Credentials set" -ForegroundColor Green

# Run fetch script
Write-Host "`n[STEP 2] Fetching Real REB3 Issues..." -ForegroundColor Yellow

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

python scripts/fetch-jira.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║                   ✓ SUCCESS!                                   ║" -ForegroundColor Green
    Write-Host "║                                                                ║" -ForegroundColor Green
    Write-Host "║  Real REB3 issues have been fetched and saved to:             ║" -ForegroundColor Green
    Write-Host "║  → data/jira.json                                             ║" -ForegroundColor Green
    Write-Host "║                                                                ║" -ForegroundColor Green
    Write-Host "║  Now when you open the dashboard:                            ║" -ForegroundColor Green
    Write-Host "║  1. http://localhost:6060                                     ║" -ForegroundColor Green
    Write-Host "║  2. Click [Generate Test Cases]                               ║" -ForegroundColor Green
    Write-Host "║  3. You'll see REAL REB3-XXX issues (not TEST-XXX)            ║" -ForegroundColor Green
    Write-Host "║  4. Filters will have data!                                   ║" -ForegroundColor Green
    Write-Host "║                                                                ║" -ForegroundColor Green
    Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Green

    Write-Host "`nNext step: Start the dashboard with real Jira data" -ForegroundColor Cyan
    Write-Host "Command: python server.py" -ForegroundColor Yellow
} else {
    Write-Host "`n❌ Failed to fetch Jira issues" -ForegroundColor Red
    Write-Host "Check credentials and try again" -ForegroundColor Yellow
}
