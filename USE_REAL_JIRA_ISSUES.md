# 🎯 Switch From Dummy Data to Real REB3 Issues

## Problem

Right now you're seeing **dummy TEST data** (TEST-101, TEST-102, etc.) instead of **real REB3 issues**.

Filters show no data because dummy data has no sprints/versions/components.

---

## Solution: Fetch Real REB3 Issues

### Step 1: Run the Fetch Script

```powershell
cd C:\SymphonyProjects\automation-dashboard
.\fetch-real-reb3-issues.ps1
```

**The script will:**
- Ask for your Jira credentials
- Query real Jira for REB3 issues
- Save to `data/jira.json` (replaces dummy data)
- Populate filters with real sprint/version data

### Step 2: Start Dashboard

After script completes:

```bash
python server.py
```

### Step 3: Open Dashboard

Go to http://localhost:6060

Click **[Generate Test Cases]** → Now you should see:

```
✓ REB3-101, REB3-102, REB3-103... (REAL ISSUES!)
✓ Sprint dropdown populated
✓ Fix Version dropdown populated
✓ Issue Type dropdown populated
✓ Status dropdown populated
```

---

## Complete Workflow

```
1. Run: .\fetch-real-reb3-issues.ps1
   └─ Queries Jira for REB3 issues
   └─ Saves to data/jira.json
   
2. Run: python server.py
   └─ Starts dashboard
   
3. Open: http://localhost:6060
   └─ Click [Generate Test Cases]
   └─ Select 5 REB3 issues (NOT TEST-XXX!)
   └─ Click [Generate]
   
4. Approve scenarios
   └─ Click [✓ Approve]
   
5. Sync to Jira
   └─ Click [🔗 Sync to Jira]
   
6. Verify in Jira
   └─ Child issues appear under REB3-101, etc.
```

---

## What Gets Fetched

```
Query: All REB3 issues
Includes:
├─ Issue key (REB3-XXX)
├─ Summary (title)
├─ Issue type (Story, Task, etc.)
├─ Status (To Do, In Progress, etc.)
├─ Priority (High, Medium, Low)
├─ Sprint information
├─ Fix version information
├─ Components
└─ Assignee information

Stored in: data/jira.json
```

---

## Troubleshooting

### Script Says "Invalid credentials"

**Fix:**
1. Check Jira email is correct
2. Verify API token (not password!)
3. Get new token: https://id.atlassian.com/manage-profile/security/api-tokens
4. Try again

### Script Says "No REB3 issues found"

**Fix:**
1. Verify you have access to REB3 project
2. Check: https://retech.atlassian.net/projects/REB3
3. Verify there are issues in REB3 project
4. Ask Jira admin for project access

### Dashboard Still Shows TEST Issues

**Fix:**
1. Did fetch script complete successfully? (Look for ✓ SUCCESS message)
2. Refresh browser (Ctrl+R)
3. Check `data/jira.json` file
   - Should contain "REB3" in issue keys
   - Should NOT contain "TEST"

---

## Verify It Worked

After running fetch script, check:

### ✓ File Contents
```powershell
$data = Get-Content data/jira.json | ConvertFrom-Json
$data.issues | Select-Object -First 3 key, summary

# Should show:
# key    summary
# ---    -------
# REB3-101    ...
# REB3-102    ...
```

### ✓ Issue Count
```powershell
$data = Get-Content data/jira.json | ConvertFrom-Json
$data.issues.count

# Should be > 0 (number of REB3 issues)
```

### ✓ Filter Data
```powershell
$data = Get-Content data/jira.json | ConvertFrom-Json
$data.filterOptions

# Should have:
# - projects: ["REB3"]
# - fixVersions: [...versions...]
# - types: [...issue types...]
```

---

## One-Command Quick Start

```powershell
# 1. Fetch real issues
.\fetch-real-reb3-issues.ps1

# 2. Start server (when script finishes)
python server.py

# 3. Open http://localhost:6060 in browser
# 4. Click [Generate Test Cases]
# 5. Now see REB3 issues (not TEST)!
```

---

## What Happens Inside

```
1. Your credentials passed to Jira API
   └─ POST /rest/api/3/search/jql
   └─ Query: project = "REB3"
   
2. Jira returns all REB3 issues with details
   
3. Script processes response
   └─ Extracts: key, summary, type, status, priority, sprint, version
   └─ Formats for dashboard
   
4. Saves to data/jira.json
   
5. Dashboard loads from data/jira.json
   └─ Populates issue list
   └─ Populates filter dropdowns
   └─ Ready for test generation
```

---

## Data Flow Diagram

```
Before:
┌─────────────────────────────────────┐
│ Dummy Data (TEST-101, TEST-102...)  │
│ in data/jira.json                   │
└──────────────┬──────────────────────┘
               │
               ↓
        Dashboard shows
        dummy issues only

After Running Script:
┌─────────────────────────────────────┐
│ Real Jira Data (REB3-101, REB3-102) │
│ Fetched and saved to data/jira.json │
└──────────────┬──────────────────────┘
               │
               ↓
        Dashboard shows
        REAL REB3 issues
```

---

## FAQ

**Q: Do I need to run fetch script every time?**
A: No, only once. After first run, `data/jira.json` has real data until you replace it.

**Q: Can I use the script to update issues?**
A: Yes, run it again anytime to refresh the issue list.

**Q: Does this change the workflow?**
A: No, everything else works the same. Just real data instead of dummy data.

**Q: What if I want to go back to dummy data?**
A: The dummy data was committed to git. Run: `git checkout data/jira.json`

**Q: Can I fetch issues from different project?**
A: Modify the script line: `$env:JIRA_PROJECT_KEY = "YOUR_PROJECT"`

**Q: How long does fetching take?**
A: Usually 5-10 seconds. Depends on number of issues.

---

## Next Steps

1. Run: `.\fetch-real-reb3-issues.ps1`
2. Wait for ✓ SUCCESS message
3. Run: `python server.py`
4. Open: http://localhost:6060
5. Click [Generate Test Cases]
6. Verify you see REB3 issues (not TEST)
7. Continue with normal workflow

---

## Summary

```
Current problem:
├─ Showing TEST-101, TEST-102 (dummy data)
├─ No sprint/version data in filters
└─ Not using real Jira

Solution:
├─ Run fetch script
├─ Fetches real REB3 issues
├─ Saves to data/jira.json
└─ Dashboard now shows REAL issues

Result:
├─ REB3-101, REB3-102, etc. appear
├─ Filters populated with real data
├─ Can generate scenarios for real issues
├─ Sync creates child issues in real Jira
└─ Complete end-to-end workflow!
```

Ready? Run:

```powershell
.\fetch-real-reb3-issues.ps1
```

