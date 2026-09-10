# ⚡ Quick Start: Test with Real REB3 Jira Tickets

## Fastest Way to Test End-to-End (5 minutes)

---

## 🎯 The Quick Path

### 1️⃣ **Get Your Credentials** (2 min)

**Jira API Token:**
- Go to: https://id.atlassian.com/manage-profile/security/api-tokens
- Click "Create API token"
- Copy it (you'll paste it in step 3)

**Claude API Key:**
- Go to: https://console.anthropic.com/
- Copy your API key

### 2️⃣ **Run the Quick Start Script** (1 min)

```powershell
cd C:\SymphonyProjects\automation-dashboard
.\test-with-real-jira.ps1
```

**The script will:**
- Ask for your Jira credentials
- Ask for your Claude API key
- Test the connection
- Start the server on http://localhost:6060
- Tell you what to do next

### 3️⃣ **Test in Browser** (2 min)

Open http://localhost:6060 and:

```
1. Click [⚡ Generate Test Cases]
2. Verify Credentials (already filled!)
3. Select 5 REB3 issues
4. Click [Generate]
   ↓ Wait for scenarios to appear
5. Click [✓ Approve] on scenarios you like
6. Close modal
7. Scroll down → See approval panel
8. Click [🔗 Sync to Jira (N)]
   ↓ Watch progress bar
9. See success message ✓
10. Click link to view in Jira
```

---

## 📋 What You'll See

### In Dashboard
```
✓ Scenarios load from REAL REB3 issues
✓ Approve/Reject buttons work
✓ Status preserved after modal close
✓ Sync button appears with count
✓ Success message with Jira links
✓ Synced scenarios removed
```

### In Jira
```
https://retech.atlassian.net/browse/REB3-101

Child issues (3)
├─ REB3-201 - Successfully validate first acceptance criterion
├─ REB3-202 - User fails with invalid credentials  
└─ REB3-203 - Session timeout scenario

👉 Click any child issue to see full test scenario details
```

---

## 🛠️ Manual Setup (If Script Fails)

### Option A: PowerShell Terminal

```powershell
# Set credentials
$env:JIRA_BASE_URL = "https://retech.atlassian.net"
$env:JIRA_USER_EMAIL = "your-email@company.com"
$env:JIRA_API_TOKEN = "your-api-token-here"
$env:JIRA_PROJECT_KEY = "REB3"
$env:ANTHROPIC_API_KEY = "your-claude-key-here"

# Start server
cd C:\SymphonyProjects\automation-dashboard
python server.py
```

### Option B: Create .env File

```bash
# .env file
JIRA_BASE_URL=https://retech.atlassian.net
JIRA_USER_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-api-token-here
JIRA_PROJECT_KEY=REB3
ANTHROPIC_API_KEY=your-claude-key-here
```

Then:
```bash
python server.py
```

---

## ✅ Success Indicators

### ✓ Credentials Test Passes
```
✓ Authentication successful
✓ User: Your Name
✓ Email: your-email@company.com
✓ REB3 Project Access: OK
✓ REB3 Issues Found: 50+
```

### ✓ Generation Works
```
Progress: 0% - Initializing...
Progress: 50% - Processing results...
Progress: 100% - Complete!

Generated 15 test scenarios for 5 REB3 issues
```

### ✓ Sync Works
```
Ready to sync 12 approved scenario(s) to Jira
Syncing... (3/12)
✓ Successfully synced 12 scenario(s) to Jira!

Created Issues:
├─ REB3-201 → View in Jira
├─ REB3-202 → View in Jira
└─ REB3-203 → View in Jira
```

### ✓ Jira Shows Child Issues
```
https://retech.atlassian.net/browse/REB3-101

Child issues (3)
✓ REB3-201
✓ REB3-202
✓ REB3-203
```

---

## ❌ Common Issues & Fixes

| Problem | Fix |
|---------|-----|
| "Invalid credentials" | Check Jira email & API token at https://id.atlassian.com/ |
| "No REB3 issues found" | Verify you have access to REB3 project |
| "403 Forbidden" | Ask Jira admin for "Create Child Issue" permission |
| "Child issues not in Jira" | Wait a few seconds, refresh Jira page |
| Script won't run | Run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned` |

---

## 📚 Detailed Docs

- **Full Testing Guide:** `LOCAL_TESTING_WITH_REAL_JIRA.md`
- **Workflow Summary:** `SYNC_WORKFLOW_COMPLETE.md`
- **Troubleshooting:** `TROUBLESHOOTING_JIRA_SYNC.md`

---

## 🚀 Next Steps

### After Successful Test

1. **Verify Everything Works**
   - Generate scenarios ✓
   - Approve scenarios ✓
   - Sync to Jira ✓
   - Child issues appear ✓

2. **Commit Your Test**
   ```bash
   git add -A
   git commit -m "test: verified end-to-end sync with real REB3 issues"
   ```

3. **Share Results**
   - Take screenshot of child issues in Jira
   - Share with team
   - Plan production deployment

---

## 💡 Pro Tips

### Tip 1: Use Chrome DevTools
```
F12 → Console tab
├─ Monitors real-time events
├─ Shows sync progress
└─ Catches any errors early
```

### Tip 2: Monitor Database
```powershell
# In another terminal, watch database changes
psql -U automation_user -d automation_dashboard

SELECT COUNT(*) FROM test_scenarios;  # Should increase
```

### Tip 3: Check Server Logs
```bash
# Terminal running server shows:
✓ Credentials verified
✓ Jira issues loaded
✓ Generation started
✓ Sync completed
```

### Tip 4: Test with Different Issue Counts
```
First test: 1 issue (fast, verify flow works)
Second test: 3 issues (verify multi-scenario)
Third test: 5 issues (full test, verify sync for many)
```

---

## 🎉 What Success Looks Like

**Complete workflow working:**
```
1. Dashboard generates scenarios from REAL REB3 issues ✓
2. Scenarios shown in preview modal ✓
3. User approves/rejects scenarios ✓
4. Status preserved when modal closes ✓
5. Approval panel shows with correct state ✓
6. Sync button creates child issues in actual Jira ✓
7. Child issues appear in parent ticket ✓
8. Full scenario details visible in each child issue ✓
```

**Time from start to finish: ~1 minute**

**Confidence level: 95%+**

---

## 📞 Support

If something doesn't work:

1. **Check console errors** (F12 in browser)
2. **Check server logs** (terminal running server.py)
3. **Read troubleshooting** (TROUBLESHOOTING_JIRA_SYNC.md)
4. **Verify credentials** (retest with curl or Postman)
5. **Check database** (psql queries)

---

## 🎯 TL;DR

```bash
# 1. Get credentials (2 min)
# - Jira token: https://id.atlassian.com/...
# - Claude key: https://console.anthropic.com/

# 2. Run quick start (1 min)
cd C:\SymphonyProjects\automation-dashboard
.\test-with-real-jira.ps1

# 3. Test in browser (2 min)
# - http://localhost:6060
# - Click [Generate Test Cases]
# - Select 5 REB3 issues
# - Approve scenarios
# - Sync to Jira

# 4. Verify in Jira (instant)
# - https://retech.atlassian.net/browse/REB3-101
# - Check child issues appeared
# - Click to verify details
```

**Total time: ~5 minutes**

---

Ready? Start with: `.\test-with-real-jira.ps1`

