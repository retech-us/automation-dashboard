# Troubleshooting: Child Issues Not Appearing in Jira

**Problem:** After syncing, child issues don't appear under REB3-101 in Jira

---

## Step 1: Check Sync Status in Database

### Connect to Database

```bash
psql -U automation_user -d automation_dashboard -h localhost
```

### Query Sync Status

```sql
SELECT 
    scenario_id,
    title,
    jira_child_issue_key,
    jira_sync_status,
    status,
    jira_last_sync_at
FROM test_scenarios
WHERE jira_issue_key = 'REB3-101'
ORDER BY created_at DESC;
```

### What to Look For

**Case 1: jira_sync_status = 'pending' ⚠️**
```
scenario_id | jira_child_issue_key | jira_sync_status | status
────────────┼──────────────────────┼──────────────────┼─────────
uuid-1      | NULL                 | pending          | approved
uuid-2      | NULL                 | pending          | approved
```

**Problem:** Sync button was never clicked or didn't execute  
**Solution:** Click "Sync to Jira" button again in UI

---

**Case 2: jira_sync_status = 'failed' ❌**
```
scenario_id | jira_child_issue_key | jira_sync_status | status
────────────┼──────────────────────┼──────────────────┼─────────
uuid-1      | NULL                 | failed           | approved
uuid-2      | NULL                 | failed           | approved
```

**Problem:** Sync tried but failed  
**Solution:** Check error logs (see Step 2)

---

**Case 3: jira_sync_status = 'synced' ✅ but not in Jira ⚠️**
```
scenario_id | jira_child_issue_key | jira_sync_status | status
────────────┼──────────────────────┼──────────────────┼─────────
uuid-1      | REB3-102             | synced           | approved
uuid-2      | REB3-103             | synced           | approved
```

**Problem:** Database says synced but Jira shows nothing  
**Solution:** Check Jira permissions (see Step 5)

---

## Step 2: Check Sync Errors

### Query Sync History

```sql
SELECT 
    sync_id,
    scenario_id,
    sync_type,
    sync_status,
    error_message,
    synced_at
FROM sync_history
WHERE sync_direction = 'to_jira'
ORDER BY synced_at DESC
LIMIT 20;
```

### Common Error Messages

**Error: "401 Unauthorized"**
```
Problem: Jira API token is invalid or expired
Solution: 
  1. Generate new API token in Jira
  2. Re-enter credentials in dashboard
  3. Try sync again
```

**Error: "404 Not Found"**
```
Problem: Parent issue REB3-101 doesn't exist
Solution:
  1. Verify issue exists: https://retech.atlassian.net/browse/REB3-101
  2. Check spelling (case-sensitive: REB3 not reb3)
  3. Verify user has access to issue
```

**Error: "429 Too Many Requests"**
```
Problem: Jira rate limit hit (300 requests/minute)
Solution:
  1. Wait 1-2 minutes
  2. Try syncing again
  3. Or sync fewer scenarios at once
```

**Error: "403 Forbidden"**
```
Problem: User doesn't have permission to create child issues
Solution:
  1. Check project permissions in Jira
  2. Ask Jira admin for Create Child Issue permission
  3. Test with different user if available
```

**Error: "Invalid JQL query"**
```
Problem: Issue key format wrong
Solution:
  1. Verify issue format: PROJECT-NUMBER (e.g., REB3-101)
  2. Check project key matches (REB3, not REB-3)
```

### Check Application Logs

```bash
# View sync errors
tail -100 logs/app.log | grep -i "sync\|error\|failed"

# Check for Jira API errors
grep -i "jira.*error\|401\|404\|429" logs/app.log

# View last 50 lines
tail -50 logs/app.log
```

---

## Step 3: Verify Jira Credentials

### Check Credentials in Database

```sql
SELECT 
    user_email,
    jira_base_url,
    jira_email,
    session_expiry,
    created_at
FROM sessions
ORDER BY created_at DESC
LIMIT 1;
```

### Expected Values

```
user_email: user@company.com
jira_base_url: https://retech.atlassian.net
jira_email: user@company.com  (or your Jira email)
session_expiry: 2026-09-10 12:00:00  (should be in future)
```

### Test Jira API Connection

```bash
# Test with curl
curl -u jira_email:api_token \
  "https://retech.atlassian.net/rest/api/3/myself" \
  -H "Content-Type: application/json"

# Expected response:
# {
#   "self": "...",
#   "accountId": "...",
#   "emailAddress": "user@company.com",
#   "displayName": "User Name"
# }
```

### If Curl Fails

**Error: 401 Unauthorized**
```bash
# Solution: Check API token format
# API token should be: xxxxxxxxxxxxxxxxxxxx (20+ chars)
# Email should be: user@company.com (not username)

# Generate new token:
# 1. Go to: https://id.atlassian.com/manage-profile/security/api-tokens
# 2. Click "Create API token"
# 3. Copy the token
# 4. Use in dashboard credentials dialog
```

**Error: 404 Not Found**
```bash
# Solution: Check Jira URL
# Should be: https://retech.atlassian.net
# NOT: https://retech.jira.com or similar

# Verify correct URL by checking:
# 1. Browser address bar (what you see when logged in)
# 2. Base URL should match exactly
```

---

## Step 4: Manually Test Child Issue Creation

### Via Jira API

```bash
# First, verify parent exists
curl -u email@company.com:token \
  "https://retech.atlassian.net/rest/api/3/issues/REB3-101" \
  -H "Content-Type: application/json"

# Then try creating child issue manually
curl -X POST \
  -u email@company.com:token \
  "https://retech.atlassian.net/rest/api/3/issues" \
  -H "Content-Type: application/json" \
  -d '{
    "fields": {
      "project": {"key": "REB3"},
      "parent": {"key": "REB3-101"},
      "summary": "Test Child Issue",
      "description": "Manual test from API",
      "issuetype": {"name": "Story"}
    }
  }'
```

### Expected Response

```json
{
  "id": "12345",
  "key": "REB3-102",
  "self": "https://retech.atlassian.net/rest/api/3/issues/REB3-102"
}
```

**If this succeeds:** Your Jira API credentials work!  
**If this fails:** Fix the error first before trying from dashboard

---

## Step 5: Check Jira Permissions

### Required Permissions

To create child issues, you need:
- ✅ "Create Issue" permission
- ✅ "Link Issue" permission (for parent-child link)
- ✅ Access to the REB3 project
- ✅ View permission on REB3-101

### Verify in Jira

1. **Go to Project Settings**
   ```
   https://retech.atlassian.net/projects/REB3/settings
   ```

2. **Check Your Permissions**
   ```
   Settings → People → Your Role
   Should include: Create Issue, Edit Issue, Link Issue
   ```

3. **Check Issue Type Restrictions**
   ```
   Settings → Issue Types → Story
   Can you create Story issues? ✅
   ```

4. **Check Project Permissions**
   ```
   Settings → Permission Scheme
   Your role should have "Create Issue" permission
   ```

### If Permissions Missing

**Solution:** Ask Jira admin to grant you:
- Create Issue
- Link Issue
- Browse Projects (REB3)
- Create Child Issues (if restricted)

---

## Step 6: Verify Issue Hierarchy

### Check Parent Issue Configuration

1. **Open REB3-101 in Jira**
   ```
   https://retech.atlassian.net/browse/REB3-101
   ```

2. **Look for:**
   ```
   Issue Type: ✅ Epic, Story, or Task (not Bug, which can't have children)
   Child issues section: Usually near top or bottom
   Add child issue button: Should be clickable
   ```

3. **If Not Visible:**
   ```
   Problem: This issue type can't have children
   Solution: Use different issue type or check Jira configuration
   ```

### Check Jira Issue Type Hierarchy

```bash
# Query Jira to see if issue type allows children
curl -u email@company.com:token \
  "https://retech.atlassian.net/rest/api/3/issuetypes" \
  -H "Content-Type: application/json" | jq '.[].name'

# Should include: Epic, Story, or Task (types that support children)
```

---

## Step 7: Debug from Dashboard

### Run Test Sync

1. **Go to Dashboard**
   ```
   http://localhost:6060
   ```

2. **Generate Test Cases**
   - Click "Generate Test Cases"
   - Enter credentials
   - Select issue
   - Click "Generate"

3. **Monitor Logs**
   ```bash
   # In separate terminal, watch logs in real-time
   tail -f logs/app.log | grep -i sync
   ```

4. **Click Sync Button**
   - Click "🔗 Sync to Jira" button
   - Watch for progress bar
   - Watch for results display
   - Check logs for errors

5. **Check Results**
   ```
   Should show:
   ✓ Successful: N
   ✗ Failed: 0
   
   If Failed > 0: Check error message
   ```

---

## Step 8: Enable Debug Mode

### Increase Logging

**Edit `scripts/generate-test-cases.py`:**
```python
# Around line 30, change:
logger.setLevel(logging.INFO)

# To:
logger.setLevel(logging.DEBUG)
```

**Edit `sync/jira_sync.py`:**
```python
# Around line 15, change:
logger = logging.getLogger(__name__)

# To add debug:
logger.setLevel(logging.DEBUG)
```

### Run with Debug

```bash
# Set debug environment variable
export LOG_LEVEL=DEBUG

# Start server
python server.py

# Now logs will show detailed Jira API calls
```

### Check Debug Logs

```bash
grep -i "jira.*request\|jira.*response\|create.*child" logs/app.log
```

---

## Complete Diagnostic Script

Run this to collect all diagnostic data:

```bash
#!/bin/bash

echo "=== SYNC STATUS ==="
psql -U automation_user -d automation_dashboard -c \
  "SELECT COUNT(*) as total, 
          COUNT(CASE WHEN jira_sync_status='synced' THEN 1 END) as synced,
          COUNT(CASE WHEN jira_sync_status='pending' THEN 1 END) as pending,
          COUNT(CASE WHEN jira_sync_status='failed' THEN 1 END) as failed
   FROM test_scenarios WHERE jira_issue_key='REB3-101';"

echo -e "\n=== SYNC ERRORS ==="
psql -U automation_user -d automation_dashboard -c \
  "SELECT error_message, COUNT(*) 
   FROM sync_history 
   WHERE sync_direction='to_jira' AND sync_status='failed'
   GROUP BY error_message;"

echo -e "\n=== RECENT LOGS ==="
tail -50 logs/app.log | grep -i "jira\|sync\|error"

echo -e "\n=== TEST JIRA CONNECTION ==="
curl -s -u email@company.com:token \
  "https://retech.atlassian.net/rest/api/3/myself" \
  | jq '.displayName, .emailAddress'

echo -e "\n=== CHECK CHILD ISSUES VIA API ==="
curl -s -u email@company.com:token \
  "https://retech.atlassian.net/rest/api/3/issues/REB3-101/children" \
  | jq '.[]?.key'
```

---

## Quick Fix Checklist

- [ ] **Check sync status in database** → Is it "pending" or "failed"?
- [ ] **Check sync errors** → Any error messages?
- [ ] **Verify Jira credentials** → Are they valid?
- [ ] **Test API connection** → Can you reach Jira?
- [ ] **Check permissions** → Do you have Create Issue permission?
- [ ] **Verify issue type** → Can this issue type have children?
- [ ] **Check logs** → Are there error messages?
- [ ] **Re-run sync** → Click "Sync to Jira" button again

---

## Most Common Issues & Solutions

### Issue 1: "Sync Status = Pending"
```
Cause: Sync button never clicked or didn't process
Fix: Click "🔗 Sync to Jira" button in UI again
```

### Issue 2: "401 Unauthorized Error"
```
Cause: Invalid Jira API token
Fix: Generate new token and re-enter credentials
```

### Issue 3: "404 Not Found"
```
Cause: REB3-101 doesn't exist
Fix: Use correct issue key that exists in Jira
```

### Issue 4: "403 Forbidden"
```
Cause: Missing Create Issue permission
Fix: Ask Jira admin to grant permission
```

### Issue 5: "No Error, but Still No Child Issues"
```
Cause: Permissions or issue type restrictions
Fix: 
  1. Verify issue type can have children
  2. Check Jira project permissions
  3. Try manual API call to verify
```

---

## Next Steps After Diagnosis

### If Database Shows "synced"

```bash
# 1. Verify child issue exists in Jira
curl -u email@company.com:token \
  "https://retech.atlassian.net/rest/api/3/issues/REB3-102"

# 2. Verify parent-child link
curl -u email@company.com:token \
  "https://retech.atlassian.net/rest/api/3/issues/REB3-101/children"

# 3. Check Jira UI directly
# Browse to: https://retech.atlassian.net/browse/REB3-101
```

### If Database Shows "failed"

```bash
# 1. Check error message
psql -U automation_user -d automation_dashboard -c \
  "SELECT error_message FROM sync_history 
   WHERE sync_status='failed' ORDER BY synced_at DESC LIMIT 5;"

# 2. Fix the underlying issue:
#    - Invalid token? Generate new one
#    - Missing permission? Request from admin
#    - Wrong issue? Use different parent

# 3. Try sync again
```

---

## Success Criteria

✅ When it's working, you should see:

```
1. Frontend UI shows: 🔗 Child issue link (clickable)
2. Database shows: jira_sync_status = 'synced'
3. Database shows: jira_child_issue_key = 'REB3-102' (actual key)
4. Jira UI shows: Child issue in REB3-101 details page
5. Child issue contains: Formatted scenario details
```

---

## Still Not Working?

1. **Run diagnostic script above** ↑
2. **Share output of:**
   - Database sync status query
   - Sync error messages
   - Recent log lines (with email redacted)
3. **I can help diagnose further**

---

## Support

- **Logs location:** `logs/app.log`
- **Database:** `psql -U automation_user -d automation_dashboard`
- **Jira URL:** https://retech.atlassian.net
- **API token:** Generate at https://id.atlassian.com/manage-profile/security/api-tokens
