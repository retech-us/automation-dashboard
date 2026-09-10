# Debug Jira API directly
$jiraUrl = "https://retech.atlassian.net"
$email = "gautam@retechlabs.com"

Write-Host "Enter your API token:"
$token = Read-Host -AsSecureString
$tokenPlain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToCoTaskMemUnicode($token))

$auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${email}:${tokenPlain}"))

$headers = @{
    "Authorization" = "Basic $auth"
    "Content-Type" = "application/json"
}

$body = @{
    "jql" = "project = REB3"
    "maxResults" = 5
} | ConvertTo-Json

Write-Host "`n=== Testing /rest/api/3/search/jql endpoint ===" -ForegroundColor Cyan
Write-Host "URL: $jiraUrl/rest/api/3/search/jql" -ForegroundColor Yellow
Write-Host "Method: POST" -ForegroundColor Yellow
Write-Host "Body: $body" -ForegroundColor Yellow

try {
    $response = Invoke-WebRequest -Uri "$jiraUrl/rest/api/3/search/jql" `
        -Headers $headers `
        -Method Post `
        -Body $body `
        -ContentType "application/json" `
        -ErrorAction Stop

    Write-Host "`nSUCCESS!" -ForegroundColor Green
    Write-Host "Status: $($response.StatusCode)"
    $data = $response.Content | ConvertFrom-Json
    Write-Host "Issues found: $($data.total)"
    if ($data.issues) {
        Write-Host "`nFirst issue:"
        Write-Host "  Key: $($data.issues[0].key)"
        Write-Host "  Summary: $($data.issues[0].fields.summary)"
    }
} catch {
    Write-Host "`nFAIL!" -ForegroundColor Red
    Write-Host "Status Code: $($_.Exception.Response.StatusCode)" -ForegroundColor Red
    Write-Host "Status Description: $($_.Exception.Response.StatusDescription)" -ForegroundColor Red

    try {
        $errorBody = $_.Exception.Response.GetResponseStream()
        $reader = New-Object System.IO.StreamReader($errorBody)
        $errorText = $reader.ReadToEnd()
        Write-Host "`nError Response:" -ForegroundColor Yellow
        Write-Host $errorText
    } catch {
        Write-Host "Could not read error body"
    }
}
