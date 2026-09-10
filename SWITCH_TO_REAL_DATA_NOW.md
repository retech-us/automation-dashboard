# ⚡ Quick Fix: Switch from Dummy to Real Data

## 🎯 Current Issue
You're seeing dummy **TEST-101, TEST-102** data instead of real **REB3-101, REB3-102** data.

## ✅ Solution (30 seconds)

### Step 1: Run Fetch Script
```powershell
cd C:\SymphonyProjects\automation-dashboard
.\fetch-real-reb3-issues.ps1
```

### Step 2: Enter Your Jira Credentials
```
Jira Base URL: https://retech.atlassian.net
Jira Email: your-email@company.com
Jira API Token: [from https://id.atlassian.com/manage-profile/security/api-tokens]
```

### Step 3: Wait for "SUCCESS" Message
```
✓ SUCCESS!
Real REB3 issues have been fetched and saved to: data/jira.json
```

### Step 4: Refresh Browser
```
Browser still open? Just press: Ctrl+R
```

### Step 5: Click Generate Button Again
Now you'll see **REB3-XXX** issues instead of TEST-XXX! ✓

---

## 📋 Why This Happens

```
data/jira.json contains the issue list
    ↓
On first startup → Contains DUMMY data (TEST-101, etc.)
    ↓
After running fetch script → Contains REAL data (REB3-101, etc.)
    ↓
Browser loads issues from data/jira.json
    ↓
Shows whatever is in the file!
```

---

## ✨ Complete Flow Now

```
1. Run: .\fetch-real-reb3-issues.ps1
   └─ Fetches real REB3 issues from Jira
   └─ Saves to data/jira.json
   
2. Refresh browser (Ctrl+R)
   └─ Dashboard reloads with real data
   
3. Click "⚡ Generate Test Cases" tab
   └─ Click [⚡ Generate Test Cases] button
   └─ NOW see REB3-101, REB3-102, etc.
   └─ Not TEST-101, TEST-102!
   
4. Select 5 REB3 issues
   └─ Click [Generate]
   └─ Generate scenarios from REAL issues
   
5. Approve and sync
   └─ Child issues created in real Jira!
```

---

## 🚀 Do This Now

Open PowerShell:

```powershell
cd C:\SymphonyProjects\automation-dashboard
.\fetch-real-reb3-issues.ps1
```

Takes ~30 seconds. After that, refresh browser and you're done! 🎉

