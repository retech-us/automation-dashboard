# 🚀 Local Testing with Real REB3 Jira Tickets

Complete guide to test the entire workflow locally using **actual Jira tickets** from REB3 project.

---

## Overview

You will:
1. ✅ Enter Jira credentials in the dashboard
2. ✅ Fetch/select 5 real REB3 issues
3. ✅ Generate test scenarios using Claude AI
4. ✅ Approve scenarios in the modal
5. ✅ Sync back to Jira
6. ✅ Verify child issues appear in real Jira tickets

---

## Prerequisites

Make sure you have:
- ✅ Jira credentials (email + API token)
- ✅ Access to REB3 project
- ✅ Permission to create child issues in REB3
- ✅ Claude API key (or OpenAI key)
- ✅ Dashboard running locally

### Get Your Credentials

**Jira API Token:**
```
1. Go to: https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Copy the token
4. Use in dashboard credentials dialog
```

**Claude API Key:**
```
1. Go to: https://console.anthropic.com/
2. Navigate to API keys
3. Create or copy your key
4. Use in dashboard credentials dialog
```

---

## Method 1: Using Dashboard UI (Easiest) 🎯

### Step 1: Start the Dashboard

```bash
cd C:\SymphonyProjects\automation-dashboard
python server.py
```

Then open: http://localhost:6060

### Step 2: Enter Credentials

Click the **"Generate Test Cases"** button

Fill in the credentials dialog:
```
Jira Configuration:
├─ Jira Base URL: https://retech.atlassian.net
├─ Jira Email: your-email@company.com
├─ Jira API Token: [paste from https://id.atlassian.com/...]

AI Provider:
├─ Select: Claude (or OpenAI)
├─ API Key: [paste your key]

Session Duration: 4 hours
```

Click **[Verify Credentials]** → Should see ✓

### Step 3: Select REB3 Issues

After credentials verified, you'll see "Step 1: Select Issues"

```
Filter by:
├─ Sprint: [select if needed]
├─ Fix Version: [select if needed]
├─ Issue Type: Story / Task
├─ Status: All

Search: [leave empty to see all]

Select 5 issues from REB3:
├─ ☑ REB3-101 - Login Feature
├─ ☑ REB3-102 - User Profile
├─ ☑ REB3-103 - Payment Processing
├─ ☑ REB3-104 - Security Validation
├─ ☑ REB3-105 - API Integration
```

Or click **"Select All"** checkbox for all available issues

### Step 4: Generate Test Cases

Click **[Generate]** button

**Progress will show:**
```
Progress: 0% - Initializing test case generation for 5 issue(s)...
Progress: 10% - Validating credentials...
Progress: 20% - Sending request to server...
Progress: 50% - Processing results...
Progress: 90% - Finalizing...
Progress: 100% - Complete!
```

### Step 5: Approve Scenarios in Modal

After generation, preview modal appears with scenarios:

```
GENERATED SCENARIOS PREVIEW

REB3-101: Login Feature
├─ positive: Successfully validate first acceptance criterion...
│  Priority: P1 • Category: functional
│  [👁️ View Details] [✓ Approve] [✗ Reject]
│
├─ negative: User fails with invalid credentials
│  Priority: P2 • Category: security
│  [👁️ View Details] [✓ Approve] [✗ Reject]
│
└─ edge-case: Session timeout after 30 minutes
   Priority: P3 • Category: performance
   [👁️ View Details] [✓ Approve] [✗ Reject]

[+3 more scenarios...]
```

**For each scenario you want to sync:**
```
Click [✓ Approve]
├─ Button turns gray
├─ [✗ Reject] re-enabled
└─ Status saved
```

### Step 6: Close Modal & See Approval Panel

```
Click [Close] button
    ↓
Scroll down page
    ↓
"🧪 Test Scenarios" panel appears with:
├─ ✓ Approved scenarios (green badge)
├─ ✗ Rejected scenarios (red badge)
└─ 🔗 Sync to Jira (3) button
```

### Step 7: Sync to Jira

```
Click "🔗 Sync to Jira (3)" button
    ↓
Confirmation modal:
"Ready to sync 3 approved scenario(s) to Jira"
├─ REB3-101 - Login Feature
├─ REB3-102 - User Profile
└─ REB3-103 - Payment Processing

Click [🔗 Sync Now]
    ↓
Progress bar: "Syncing... (0/3)"
    ↓
Success! "✓ Successfully synced 3 scenario(s) to Jira!"

Created Issues:
├─ REB3-201 → View in Jira
├─ REB3-202 → View in Jira
└─ REB3-203 → View in Jira
```

### Step 8: Verify in Jira

Open each parent issue in Jira and check "Child issues" section:

**Example:**
```
https://retech.atlassian.net/browse/REB3-101

Child issues (3)
├─ REB3-201 - Successfully validate first acceptance criterion...
├─ REB3-202 - User fails with invalid credentials
└─ REB3-203 - Session timeout after 30 minutes
```

Click each child issue to verify:
- ✅ Full scenario details in description
- ✅ Steps formatted correctly
- ✅ Expected result included
- ✅ Automation hints present
- ✅ Tags applied

---

## Method 2: CLI - Fetch Issues First (Optional)

If you want to fetch and inspect REB3 issues before generating:

### Fetch REB3 Issues

```bash
cd C:\SymphonyProjects\automation-dashboard

# Set environment variables
$env:JIRA_BASE_URL = "https://retech.atlassian.net"
$env:JIRA_USER_EMAIL = "your-email@company.com"
$env:JIRA_API_TOKEN = "your-token-here"
$env:JIRA_PROJECT_KEY = "REB3"

# Run fetch script
python scripts/fetch-jira.py

# Output saved to: data/jira.json
```

This will:
```
✓ Authenticate with Jira
✓ Query all REB3 issues
✓ Save to data/jira.json
✓ Now available in dashboard UI
```

### Inspect Fetched Issues

```bash
# View issues in PowerShell
$issues = Get-Content data/jira.json | ConvertFrom-Json
$issues.issues | Select-Object -First 5 | Format-Table key, summary, status, priority

# Or in Python
python -c "import json; data=json.load(open('data/jira.json')); print(f'Found {len(data[\"issues\"])} issues')"
```

---

## Method 3: Input Specific Issue IDs

If you want to test with **specific 5 issue IDs**, use the dashboard:

### In Credentials Dialog

After clicking "Generate Test Cases" button:

```
Step 1: Select Issues

Instead of browsing list, type in search box:
[Search: REB3-101]

Or manually select:
├─ ☑ REB3-101
├─ ☑ REB3-102
├─ ☑ REB3-103
├─ ☑ REB3-104
├─ ☑ REB3-105

Then click [Generate]
```

---

## Testing Checklist

### ✅ Pre-Generation
- [ ] Dashboard is running (`python server.py`)
- [ ] Jira credentials are valid
- [ ] Can access https://retech.atlassian.net
- [ ] Have at least 5 REB3 issues in Jira
- [ ] Have create/link child issue permission

### ✅ During Generation
- [ ] Credentials verified successfully
- [ ] Issues loaded from Jira
- [ ] Can select 5 REB3 issues
- [ ] Generation progress bar shows 0% → 100%
- [ ] No errors in generation output

### ✅ During Approval
- [ ] Preview modal shows scenarios
- [ ] Can click [✓ Approve] on scenarios
- [ ] Buttons change state (gray/disabled)
- [ ] Modal closes properly
- [ ] Approval panel appears below

### ✅ During Sync
- [ ] Sync button appears with count: "(3)" or similar
- [ ] Can open sync confirmation modal
- [ ] Progress bar shows during sync
- [ ] Success message appears
- [ ] Issue links are clickable

### ✅ Post-Sync Verification
- [ ] Open parent issue in Jira
- [ ] Child issues appear in "Child issues" section
- [ ] Child issue titles match scenario titles
- [ ] Child issue descriptions contain full scenario details
- [ ] Click child issue → Full scenario visible
- [ ] Sync status shows "✓ Synced" in panel

---

## Troubleshooting

### Issue: "Invalid credentials" error

**Solution:**
```
1. Verify Jira credentials:
   - Go to https://retech.atlassian.net (login successful?)
   - Check API token at https://id.atlassian.com/manage-profile/security/api-tokens
   - Token should be 20+ characters
   
2. Verify Claude API key:
   - Go to https://console.anthropic.com/
   - Copy fresh API key
   - Paste in dashboard
   
3. Re-enter in dashboard:
   - Click [Generate Test Cases]
   - Fill all fields
   - Click [Verify Credentials]
```

### Issue: "No REB3 issues found"

**Solution:**
```
1. Check if issues exist:
   - Go to https://retech.atlassian.net/projects/REB3
   - Should see list of issues
   
2. Verify search in dashboard:
   - Don't filter by status/sprint if empty
   - Leave filters blank, click [Generate]
   
3. Use JQL to query directly:
   - Set JIRA_JQL environment variable
   - Restart server
```

### Issue: "Sync failed: 401 Unauthorized"

**Solution:**
```
Your Jira credentials expired or invalid during sync.

Fix:
1. Re-enter credentials in dashboard
2. Or refresh API token:
   - https://id.atlassian.com/manage-profile/security/api-tokens
   - Delete old token
   - Create new one
   - Use in dashboard

3. Retry sync
```

### Issue: "Sync failed: 403 Forbidden"

**Solution:**
```
Missing permissions to create child issues.

Fix:
1. Ask Jira admin for:
   - "Create Issue" permission
   - "Link Issue" permission
   - "Create Child Issue" permission
   
2. Or use different Jira user with higher permissions

3. Retry sync
```

### Issue: "Child issues not appearing in Jira"

**Solution:**
```
Sync reported success but issues not in Jira.

Debug steps:
1. Check database:
   psql -U automation_user -d automation_dashboard
   
   SELECT title, jira_child_issue_key, jira_sync_status 
   FROM test_scenarios 
   WHERE jira_issue_key = 'REB3-101';
   
   - Should show: jira_child_issue_key = 'REB3-202' (not NULL)
   - Should show: jira_sync_status = 'synced'

2. If database shows synced, but Jira doesn't show issues:
   - Check if issue key exists:
     curl -u email:token https://retech.atlassian.net/rest/api/3/issues/REB3-202
   - Check parent-child link:
     curl -u email:token https://retech.atlassian.net/rest/api/3/issues/REB3-101
   
3. Verify issue type can have children:
   - Parent issue type (REB3-101) must be Epic/Story/Task
   - Not Bug or other restricted types
```

---

## Monitoring During Test

### Terminal Output

Watch the server terminal for logs:

```bash
# Should see:
✓ TestCaseGenerator initialized
✓ Button added to #jira-header-actions
✓ Valid session found - opening generator modal
✓ Jira issues loaded successfully
Progress: 10% - Validating credentials...
Progress: 50% - Processing results...
✓ Generation Complete!
✓ Scenarios-generated event dispatched
✓ Panel inserted after modal
✓ Displaying 3 scenarios
✓ Sync complete: 3/3
```

### Browser Console (F12)

Check browser console for errors:

```javascript
// Should see:
📋 ScenarioManager: Initializing
✓ Panel inserted after modal
📋 Displaying 3 scenarios
✓ Sync complete: 3/3
✓ Successfully synced 3 scenario(s) to Jira!

// Should NOT see:
❌ Uncaught ReferenceError
❌ Failed to load
❌ 404 Not Found
```

### Database Check

Verify data was saved:

```bash
psql -U automation_user -d automation_dashboard

# Check test scenarios were created
SELECT COUNT(*) as total_scenarios FROM test_scenarios;

# Check sync history
SELECT sync_status, COUNT(*) as count 
FROM sync_history 
GROUP BY sync_status;

# Check specific generation
SELECT 
  s.title, 
  s.status, 
  s.jira_child_issue_key,
  s.jira_sync_status
FROM test_scenarios s
WHERE s.jira_issue_key = 'REB3-101'
ORDER BY s.created_at DESC;
```

---

## Expected Results

After successful test, you should see:

### In Dashboard
- ✅ Generation completes successfully
- ✅ Scenarios appear in preview modal
- ✅ Can approve/reject scenarios
- ✅ Approval panel shows preserved status
- ✅ Sync button works
- ✅ Success message with issue links
- ✅ Synced scenarios removed from panel

### In Jira
- ✅ Parent issue (REB3-101) has child issues
- ✅ Child issues contain full scenario details
- ✅ Each child issue is a "Story" type
- ✅ Child issues tagged with "test-scenario"
- ✅ Child issue descriptions are formatted correctly
- ✅ Preconditions, steps, expected results visible

### In Database
- ✅ `test_scenarios` table has new records
- ✅ `status` = 'approved' or 'rejected'
- ✅ `jira_child_issue_key` = 'REB3-202' (actual keys)
- ✅ `jira_sync_status` = 'synced'
- ✅ `sync_history` has audit trail

---

## Next Steps After Test

### If Everything Works ✅
```
1. Commit changes: git add -A && git commit -m "test: verified end-to-end sync with real Jira"
2. Create PR for code review
3. Deploy to staging
4. Run additional tests
5. Move to production
```

### If Issues Found ❌
```
1. Check error messages carefully
2. Try again with different issue
3. Check database for partial sync
4. Review logs (scripts/logs/generate-test-cases.log)
5. Fix issue in code
6. Test again
```

---

## Performance Expectations

- Generation time: ~2-5 seconds per issue
- For 5 issues: ~30 seconds total
- Sync time: ~1-2 seconds per scenario
- For 3 scenarios: ~5 seconds total
- Total workflow: ~1 minute start to finish

---

## Real-World Scenario Example

**Testing with actual REB3 issues:**

```
1. User opens http://localhost:6060
2. Clicks [Generate Test Cases]
3. Enters real Jira credentials for retech.atlassian.net
4. Sees 50 REB3 issues in list
5. Selects REB3-101, REB3-102, REB3-103, REB3-104, REB3-105
6. Clicks [Generate]
7. System queries Jira for issue details
8. Claude AI generates ~3-5 scenarios per issue = ~15 scenarios total
9. Modal shows all scenarios with [Approve]/[Reject] buttons
10. User approves 12 scenarios, rejects 3 scenarios
11. Closes modal
12. Scrolls down, sees approval panel with status preserved
13. Clicks [🔗 Sync to Jira (12)]
14. Confirmation: "Ready to sync 12 approved scenario(s)"
15. System creates 12 child issues in Jira
16. Success: "✓ Successfully synced 12 scenario(s) to Jira!"
17. Opens https://retech.atlassian.net/browse/REB3-101
18. Child issues section shows:
    - REB3-201, REB3-202, REB3-203, etc. (12 total)
19. Clicks REB3-201 → Sees full scenario details
20. Status shows "To Do" (ready for testing team)
```

---

## Support

If you encounter issues:

1. **Check browser console** (F12) for errors
2. **Check terminal output** for server logs
3. **Check database** (psql commands above)
4. **Review troubleshooting section** above
5. **Check documentation**: TROUBLESHOOTING_JIRA_SYNC.md

