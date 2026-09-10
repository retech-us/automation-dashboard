# Test Jira Connection
# This will verify if your Jira credentials work

Write-Host "Testing Jira Connection..." -ForegroundColor Cyan

# Get credentials
$jiraBaseUrl = Read-Host "Jira Base URL (e.g., https://retech.atlassian.net)"
$jiraEmail = Read-Host "Jira Email (e.g., your-email@company.com)"
$jiraToken = Read-Host "Jira API Token" -AsSecureString

# Convert to plain text
$jiraTokenPlain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToCoTaskMemUnicode($jiraToken))

# Test 1: Authenticate
Write-Host "`n[TEST 1] Testing Authentication..." -ForegroundColor Yellow

$auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${jiraEmail}:${jiraTokenPlain}"))
$headers = @{
    'Authorization' = "Basic $auth"
    'Content-Type'  = 'application/json'
}

try {
    $url = "$jiraBaseUrl/rest/api/3/myself"
    Write-Host "URL: $url"
    $response = Invoke-RestMethod -Uri $url -Headers $headers -Method Get
    Write-Host "PASS: Authentication SUCCESSFUL!" -ForegroundColor Green
    Write-Host "  User: $($response.displayName)"
    Write-Host "  Email: $($response.emailAddress)"
} catch {
    Write-Host "FAIL: Authentication FAILED!" -ForegroundColor Red
    Write-Host "  Error: $($_.Exception.Message)"
    exit 1
}

# Test 2: Access REB3 Project
Write-Host "`n[TEST 2] Checking REB3 Project Access..." -ForegroundColor Yellow

try {
    $url = "$jiraBaseUrl/rest/api/3/project/REB3"
    Write-Host "URL: $url"
    $response = Invoke-RestMethod -Uri $url -Headers $headers -Method Get
    Write-Host "PASS: REB3 Project FOUND!" -ForegroundColor Green
    Write-Host "  Project: $($response.name)"
    Write-Host "  Key: $($response.key)"
} catch {
    Write-Host "FAIL: REB3 Project NOT FOUND or NO ACCESS!" -ForegroundColor Red
    Write-Host "  Error: $($_.Exception.Message)"
    Write-Host "  Make sure you have access to REB3 project"
    exit 1
}

# Test 3: Fetch REB3 Issues (using v2 API for compatibility)
Write-Host "`n[TEST 3] Fetching REB3 Issues..." -ForegroundColor Yellow

try {
    $jql = "project = REB3 ORDER BY updated DESC"
    $url = "$jiraBaseUrl/rest/api/2/search"
    $body = @{
        jql = $jql
        maxResults = 10
        fields = @("key", "summary", "status", "issuetype", "priority")
    } | ConvertTo-Json

    Write-Host "URL: $url"
    Write-Host "Method: POST with JSON body (v2 API)"
    $response = Invoke-RestMethod -Uri $url -Headers $headers -Method Post -Body $body

    $issueCount = $response.issues.Count
    Write-Host "PASS: REB3 Issues FOUND!" -ForegroundColor Green
    Write-Host "  Total in Jira: $($response.total)"
    Write-Host "  Fetched: $issueCount"

    if ($issueCount -gt 0) {
        Write-Host "`n  First 5 issues:" -ForegroundColor Cyan
        $response.issues | Select-Object -First 5 | ForEach-Object {
            Write-Host "    - $($_.key): $($_.fields.summary)"
        }
    } else {
        Write-Host "FAIL: No issues found in REB3!" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "FAIL: Error fetching issues!" -ForegroundColor Red
    Write-Host "  Error: $($_.Exception.Message)"
    exit 1
}

Write-Host "`n=====================================================================" -ForegroundColor Green
Write-Host "PASS: ALL TESTS PASSED!" -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Green
Write-Host "Your Jira credentials are valid!" -ForegroundColor Green
Write-Host "You have access to REB3 project!" -ForegroundColor Green
Write-Host "REB3 has $($response.total) issues!" -ForegroundColor Green
Write-Host "`nNow run: .\fetch-real-reb3-issues.ps1" -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Green
