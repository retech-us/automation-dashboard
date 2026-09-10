# Phase 6: Fix Jira Connector (CRITICAL BLOCKER)

## Problem Statement
Jira API integration is failing - test case generation returns 0 issues despite:
- Valid credentials being entered in dialog
- Credentials passing to server
- Server passing to Python subprocess
- Python script connecting to Jira endpoint

---

## Debugging Checklist

### Step 1: Check Credential Flow (5 minutes)

**Frontend (Browser Console):**
```javascript
// Check if credentials are captured
console.log(window.credentialsManager.getSession());

// Expected output:
{
  jira_base_url: "https://retech.atlassian.net",
  jira_user_email: "gautam@retechlabs.com",
  jira_api_token: "ATATT...",
  ai_provider: "openai",
  openai_api_key: "sk-...",
  created_at: "...",
  expires_at: "..."
}
```

**Backend (Check logs):**
```bash
tail -50 C:/SymphonyProjects/automation-dashboard/scripts/logs/generate-test-cases.log

# Look for:
# "JIRA_BASE_URL: https://retech.atlassian.net" ✓
# "JIRA_USER_EMAIL: gautam@retechlabs.com" ✓
# "JIRA_API_TOKEN: SET" ✓
# "Testing Jira connection to: ..." 
# If you DON'T see these, credentials aren't passing
```

---

### Step 2: Test Jira Connection Manually (10 minutes)

**Test with curl:**
```bash
# 1. Create Basic Auth header
EMAIL="gautam@retechlabs.com"
TOKEN="your_actual_jira_token_here"
AUTH=$(echo -n "$EMAIL:$TOKEN" | base64)

# 2. Test /myself endpoint
curl -X GET \
  -H "Authorization: Basic $AUTH" \
  -H "Content-Type: application/json" \
  "https://retech.atlassian.net/rest/api/3/myself"

# Expected response (200 OK):
{
  "self": "https://retech.atlassian.net/rest/api/3/user?accountId=...",
  "accountId": "...",
  "emailAddress": "gautam@retechlabs.com",
  "displayName": "Gautam Chakraborty",
  ...
}

# If 401: Authentication failed (wrong email or token)
# If 404: URL is wrong (not Jira Cloud)
# If connection refused: Network issue
```

**Test Jira API with Python:**
```python
import base64
import urllib.request
import json

email = "gautam@retechlabs.com"
token = "your_actual_jira_token"
url = "https://retech.atlassian.net/rest/api/3/myself"

credentials = f"{email}:{token}"
encoded = base64.b64encode(credentials.encode()).decode()

headers = {
    "Authorization": f"Basic {encoded}",
    "Content-Type": "application/json"
}

try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=5) as response:
        data = json.loads(response.read())
        print(f"✓ Success! User: {data.get('displayName')}")
except Exception as e:
    print(f"✗ Error: {e}")
    print(f"  Error type: {type(e).__name__}")
```

---

### Step 3: Verify Jira Instance Type (5 minutes)

Jira Cloud vs Jira Server APIs are different!

```bash
# Check if it's Jira Cloud (Atlassian Cloud)
# URL should be: https://{instance}.atlassian.net/

# Test cloud-specific endpoint
curl "https://retech.atlassian.net/rest/api/3/myself" \
  -H "Authorization: Basic $AUTH"

# If this works → It's Jira Cloud ✓
# If "endpoint not found" → It's Jira Server ✗ (use /rest/api/2 instead)
```

---

### Step 4: Check Issue Existence (5 minutes)

```bash
# Once /myself works, test JQL query
# List all issues of type Story or Task
curl "https://retech.atlassian.net/rest/api/3/search/jql?jql=type%20in%20(Story,Task)%20ORDER%20BY%20updated%20DESC&maxResults=10" \
  -H "Authorization: Basic $AUTH"

# Expected response:
{
  "expand": "...",
  "startAt": 0,
  "maxResults": 10,
  "total": 5,  // ← How many issues found?
  "issues": [
    {
      "key": "REB3-123",
      "fields": {
        "summary": "...",
        ...
      }
    }
  ]
}

# If total=0: No issues match the query
# If issues array empty: Check permissions
# If error: Check JQL syntax
```

---

### Step 5: Check TEST-101 Specifically (5 minutes)

```bash
# Search for TEST-101 specifically
curl "https://retech.atlassian.net/rest/api/3/search/jql?jql=key=TEST-101" \
  -H "Authorization: Basic $AUTH"

# Result options:
# 1. ✓ Found: Returns TEST-101 issue (good, should work)
# 2. ✗ Not found: total=0 (TEST-101 doesn't exist in real Jira)
#    → Use mock data fallback (already implemented)
# 3. ✗ Error: Permission denied (user can't see this issue)
#    → Check Jira permissions
# 4. ✗ 404: Endpoint doesn't exist (not Jira Cloud)
#    → Check Jira instance URL
```

---

## Common Issues & Fixes

### Issue 1: 401 Unauthorized
**Symptoms:**
- "Jira authentication failed: Invalid credentials"
- curl returns 401

**Causes & Fixes:**
```
1. Wrong Jira Token
   - Go to: https://id.atlassian.com/manage-profile/security/api-tokens
   - Generate new token (old one might be expired)
   - Copy exact token (no spaces)
   - Re-enter in dialog

2. Wrong Email
   - Use email registered with Atlassian
   - NOT the display name
   - Check: https://id.atlassian.com/account

3. Base64 Encoding Issue
   - Test: echo -n "email:token" | base64
   - Should not have newlines
   - Our code handles this, but good to verify

4. Token Expired
   - Jira tokens expire after 90 days of inactivity
   - Generate new one
```

### Issue 2: 404 Not Found
**Symptoms:**
- "Jira endpoint not found (404)"
- URL not found in Jira

**Causes & Fixes:**
```
1. Wrong Jira URL
   - Should be: https://instance.atlassian.net
   - NOT: https://instance.atlassian.net/jira
   - NOT: https://instance.atlassian.net/browse/

2. Using Jira Server instead of Cloud
   - Server uses: /rest/api/2/search
   - Cloud uses: /rest/api/3/search/jql
   - Check your Jira type

3. URL missing /rest/api/3 path
   - Verify in logs: "Testing Jira connection to: ..."
   - Should end with /rest/api/3/myself
```

### Issue 3: 0 Issues Returned
**Symptoms:**
- Auth succeeds (✓)
- But "Total issues fetched: 0"
- Mock data fallback activates

**Causes & Fixes:**
```
1. No issues in Jira instance
   - Create test issues first
   - Or use mock data (currently working)

2. Issues don't match JQL query
   - Query: "type in (Story, Task) ORDER BY updated DESC"
   - Your issues might be: Bug, Epic, etc.
   - Fix: Modify JQL in code
   - File: scripts/generate-test-cases.py, line ~206

3. Permission issue
   - User can't see issues
   - Check Jira permissions
   - Test with curl first

4. Project key filter
   - Jira might have issues in different project
   - Test without project filter first
   - Then add: "AND project = REB3"
```

### Issue 4: Connection Timeout
**Symptoms:**
- "Jira connectivity failed"
- Timeout after 5 seconds

**Causes & Fixes:**
```
1. Network issue
   - Test: ping retech.atlassian.net
   - Check firewall/proxy
   - Test from command line first

2. Jira instance down
   - Go to: https://retech.atlassian.net
   - Is it accessible in browser?

3. Timeout too short
   - Current timeout: 5 seconds
   - Increase to 10 seconds
   - File: scripts/generate-test-cases.py
   - Lines: 150, 181
```

---

## Step-by-Step Fix Procedure

### PHASE 1: Verify Basic Auth Works (15 minutes)

1. **Get actual Jira token:**
   - Go to: https://id.atlassian.com/manage-profile/security/api-tokens
   - Click "Create API token"
   - Copy token value
   - Store safely (don't commit to git!)

2. **Test with curl (in terminal):**
   ```bash
   # Replace with actual values
   export EMAIL="gautam@retechlabs.com"
   export TOKEN="your_token_here"
   
   curl -X GET \
     -H "Authorization: Basic $(echo -n $EMAIL:$TOKEN | base64)" \
     "https://retech.atlassian.net/rest/api/3/myself"
   ```
   
3. **If this works:** ✓ Continue to Phase 2
4. **If this fails:** Fix auth first (see "Common Issues & Fixes" above)

---

### PHASE 2: Test Issue Listing (10 minutes)

1. **List all issues:**
   ```bash
   curl -X GET \
     -H "Authorization: Basic $(echo -n $EMAIL:$TOKEN | base64)" \
     "https://retech.atlassian.net/rest/api/3/search/jql?jql=type%20in%20(Story,Task)&maxResults=5"
   ```

2. **Check response:**
   - Look for: `"total": X` 
   - If X > 0: Issues exist ✓
   - If X = 0: No issues in Jira (use mock data)

3. **If you want to use real Jira:**
   - Create test issues in Jira first
   - Or modify the JQL query to match your issues

---

### PHASE 3: Test Dashboard Flow (10 minutes)

1. **Clear logs:**
   ```bash
   rm C:/SymphonyProjects/automation-dashboard/scripts/logs/generate-test-cases.log
   # Or just open it and delete contents
   ```

2. **Hard refresh dashboard:**
   - Ctrl+Shift+R

3. **Enter credentials in dialog:**
   - Email: gautam@retechlabs.com
   - Token: (your actual token from Phase 1)
   - AI Provider: OpenAI (or Claude if you have key)
   - Click "Save & Continue"

4. **Select TEST-101 and Generate:**
   - Click "Generate Test Cases" button
   - If dialog doesn't show, check browser console

5. **Check logs immediately:**
   ```bash
   tail -100 C:/SymphonyProjects/automation-dashboard/scripts/logs/generate-test-cases.log
   
   # Should show:
   # "JIRA_BASE_URL: https://retech.atlassian.net" ✓
   # "JIRA_USER_EMAIL: gautam@retechlabs.com" ✓
   # "Testing Jira connection to: ..." ✓
   # "✓ Jira auth OK: Gautam Chakraborty" ✓
   # "Fetching 1 specific issues: TEST-101" ✓
   # "✓ Total issues fetched: X" (should be ≥ 1 if TEST-101 exists)
   ```

6. **If issues are 0:**
   - Mock data fallback will load TEST-101 from data/jira.json
   - Generation should still work ✓

---

## Expected Success Flow

```
Dashboard Credentials Dialog
  ↓ (User enters token)
Browser Console
  ✓ Session saved with expiry
  ✓ Dialog closes
  ↓
Generator Modal Opens
  ↓ (User selects TEST-101)
Backend /api/generate-test-cases
  ↓
Python Script Starts
  ✓ "Environment validated"
  ✓ "Testing Jira connection to: ..."
  ✓ "✓ Jira auth OK: Gautam Chakraborty"
  ✓ "Fetching 1 specific issues: TEST-101"
  ✓ "Total issues fetched: 1" (or 0 with fallback)
  ✓ "Configuration validated"
  ↓
AI Generation
  ✓ "Generating scenarios for TEST-101"
  ✓ "[1/1] Processing TEST-101: ..."
  ↓
Results
  ✓ "Successfully recovered JSON (6 scenarios recovered)"
  ✓ "Saved results to data/test-cases.json"
  ✓ "Summary: 1/1 successful"
  ↓
Dashboard Results
  ✓ Progress bar: 100%
  ✓ 6 test scenarios displayed
  ✓ "Generation Complete!"
```

---

## Testing Checkpoints

| Checkpoint | Expected Result | Status |
|------------|-----------------|--------|
| curl /myself | 200 OK + user data | ✓ or ✗ |
| curl /search | 200 OK + issues | ✓ or ✗ |
| Dialog opens | Form displays | ✓ or ✗ |
| Credentials saved | Session shows | ✓ or ✗ |
| Generator opens | Modal shows issues | ✓ or ✗ |
| Logs show auth | "✓ Jira auth OK" | ✓ or ✗ |
| Issues fetched | total ≥ 0 | ✓ or ✗ |
| Generation runs | AI starts | ✓ or ✗ |
| Results display | 6 scenarios shown | ✓ or ✗ |

---

## Next Steps After Fix

1. ✓ Verify end-to-end flow works
2. ✓ Confirm results appear in dashboard
3. ✓ Check that mock data fallback works
4. → Move to **Phase 9: Database Implementation**

