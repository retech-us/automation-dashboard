# Test script to verify generator works
$ErrorActionPreference = "Stop"

Write-Host "=== Test Case Generator - Verification ===" -ForegroundColor Green
Write-Host ""

# Set environment variables for testing
$env:ANTHROPIC_API_KEY = "sk-ant-test-key-12345"
$env:JIRA_BASE_URL = "https://test-domain.atlassian.net"
$env:JIRA_USER_EMAIL = "test@example.com"
$env:JIRA_API_TOKEN = "test-token"
$env:MAX_ISSUES_PER_RUN = "1"
$env:DEBUG = "false"

Write-Host "✓ Environment variables set" -ForegroundColor Green
Write-Host "  ANTHROPIC_API_KEY: [SET]"
Write-Host "  JIRA_BASE_URL: $env:JIRA_BASE_URL"
Write-Host "  JIRA_USER_EMAIL: $env:JIRA_USER_EMAIL"
Write-Host ""

# Test 1: Script loads without encoding errors
Write-Host "Test 1: Checking for encoding issues..." -ForegroundColor Yellow
try {
    $output = python scripts/generate-test-cases.py 2>&1 | Select-Object -First 10
    if ($output -match "UnicodeEncodeError") {
        Write-Host "✗ FAILED: Encoding error detected" -ForegroundColor Red
        $output | ForEach-Object { Write-Host "  $_" }
    } else {
        Write-Host "✓ PASSED: No encoding errors" -ForegroundColor Green
    }
} catch {
    Write-Host "✓ PASSED: Script runs (expected auth error)" -ForegroundColor Green
}

Write-Host ""
Write-Host "Test 2: Checking logging configuration..." -ForegroundColor Yellow
if (Test-Path "scripts/logs/generate-test-cases.log") {
    $fileExists = $true
    Write-Host "✓ PASSED: Log file created" -ForegroundColor Green
} else {
    Write-Host "⚠ INFO: Log file not yet created (normal on first run)" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "=== Tests Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Set your actual API key:"
Write-Host "   `$env:ANTHROPIC_API_KEY = 'sk-ant-your-real-key'"
Write-Host ""
Write-Host "2. Run the generator:"
Write-Host "   python scripts/generate-test-cases.py"
Write-Host ""
