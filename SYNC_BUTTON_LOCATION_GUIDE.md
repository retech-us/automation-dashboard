# Where is the Sync Button? - Visual Guide

---

## 🎯 Quick Answer

**The Sync Button appears AFTER test generation completes**

```
Location: http://localhost:6060
           ↓
        [Generate Test Cases] button
           ↓ (click it)
        Enter Jira credentials
           ↓
        Select issue
           ↓
        Click "Generate"
           ↓
        WAIT FOR COMPLETION
           ↓
        SCROLL DOWN
           ↓
        📍 "🔗 Sync to Jira" button
```

---

## Step-by-Step Visual Guide

### Step 1: Click "Generate Test Cases" Button

**Location on page:**
```
http://localhost:6060
┌─────────────────────────────────────────────────┐
│ Header with buttons                              │
│ ┌─────────────────────────────────────────────┐ │
│ │ Refresh   [🔒 Lock] [Export] [Generate... 📍] │
│ └─────────────────────────────────────────────┘ │
│                                                  │
│ 📍 = Click this button                          │
└─────────────────────────────────────────────────┘
```

**Button Label:** `Generate Test Cases` (blue button, top right)

---

### Step 2: Credentials Dialog Opens

```
┌──────────────────────────────────────────────────┐
│ 🔐 Test Case Generation Credentials              │
├──────────────────────────────────────────────────┤
│                                                   │
│ Jira Configuration:                              │
│ ┌──────────────────────────────────────────────┐ │
│ │ Jira Base URL: https://retech.atlassian.net  │ │
│ └──────────────────────────────────────────────┘ │
│ ┌──────────────────────────────────────────────┐ │
│ │ Jira Email: user@company.com                 │ │
│ └──────────────────────────────────────────────┘ │
│ ┌──────────────────────────────────────────────┐ │
│ │ Jira API Token: ••••••••••••••••••••••••••  │ │
│ └──────────────────────────────────────────────┘ │
│                                                   │
│ AI Provider: [Claude ▼]                         │
│ ┌──────────────────────────────────────────────┐ │
│ │ API Key: sk-ant-••••••••••••••••••••••••••  │ │
│ └──────────────────────────────────────────────┘ │
│                                                   │
│ Session Duration: [4 hours ▼]                   │
│                                                   │
│ [Verify Credentials] [Close] [Generate]         │
└──────────────────────────────────────────────────┘
```

---

### Step 3: Fill Credentials & Generate

```
1. Enter Jira Base URL: https://retech.atlassian.net
2. Enter Jira Email: your-email@company.com
3. Enter Jira API Token: (get from: https://id.atlassian.com/manage-profile/security/api-tokens)
4. Select AI Provider: Claude or OpenAI
5. Enter API Key
6. Click "Generate" button
```

---

### Step 4: Test Case Generation In Progress

```
http://localhost:6060
┌─────────────────────────────────────────────────┐
│                                                  │
│ Generating test cases...                        │
│ ████████████░░░░░░░░ 60%                       │
│                                                  │
│ Fetching issues from Jira...                   │
│ Analyzing issue content...                      │
│ Generating test scenarios...                    │
│ Structuring results...                          │
│                                                  │
└─────────────────────────────────────────────────┘
```

**WAIT** for this to complete ⏳ (usually 10-30 seconds)

---

### Step 5: SCROLL DOWN After Generation Completes ⬇️

After generation completes, you will see:

```
http://localhost:6060 (SCROLL DOWN)
┌─────────────────────────────────────────────────┐
│ Generation Complete!                             │
│                                                  │
│ 5 test cases generated for REB3-101             │
│                                                  │
│ Test Cases Summary:                             │
│ ├─ Positive scenarios: 3                       │
│ ├─ Negative scenarios: 1                       │
│ └─ Edge cases: 1                               │
│                                                  │
└─────────────────────────────────────────────────┘

          ⬇️ SCROLL DOWN ⬇️

┌─────────────────────────────────────────────────┐
│ 🧪 Test Scenarios                               │
│ ┌─────────────────────────────────────────────┐ │
│ │ Panel Header with Controls:                 │ │
│ │ ┌─────────────────────────────────────────┐ │ │
│ │ │ 🔗 Sync to Jira (2)  🔄 Refresh       │ │ │
│ │ └─────────────────────────────────────────┘ │ │
│ │                                             │ │
│ │ 📍 = SYNC BUTTON IS HERE!                  │ │
│ │                                             │ │
│ └─────────────────────────────────────────────┘ │
│                                                  │
│ Filters: [Approved] [Pending Sync] [Synced]   │
│                                                  │
│ [✓] Scenario 1: User can login                │ │
│ [✓] Scenario 2: Invalid password              │ │
│ [✓] Scenario 3: SQL injection test            │ │
│                                                  │
└─────────────────────────────────────────────────┘
```

---

## 📍 WHERE IS THE SYNC BUTTON?

### Location Details

**Section:** Test Scenarios Panel  
**Subsection:** Panel Header (top-right)  
**Text:** `🔗 Sync to Jira (2)`  
**Color:** Blue button  
**Right next to:** Refresh button (🔄)  

### Visual Layout

```
┌──────────────────────────────────────────────────┐
│ 🧪 Test Scenarios                                │
├──────────────────────────────────────────────────┤
│ Panel Header                                     │
│ ┌────────────────────────────────────────────┐  │
│ │ Left side: "🧪 Test Scenarios"             │  │
│ │                                             │  │
│ │ Right side: Buttons:                       │  │
│ │ ┌──────────────┐  ┌──────────────┐       │  │
│ │ │ 🔗 Sync to   │  │ 🔄 Refresh   │       │  │
│ │ │   Jira (2)   │  │              │       │  │
│ │ └──────────────┘  └──────────────┘       │  │
│ │                                             │  │
│ │ 📍 = SYNC BUTTON IS HERE                  │  │
│ └────────────────────────────────────────────┘  │
│                                                  │
│ Filters: [Approved] [Pending Sync] [Synced]   │
│                                                  │
│ [Scenarios listed below...]                    │
└──────────────────────────────────────────────────┘
```

---

## 🎯 How to Click the Sync Button

### Option 1: Single Click (Simplest)
```
1. Scroll down to "Test Scenarios" panel
2. Find blue button: "🔗 Sync to Jira (2)"
3. Click it
4. Wait for popup with results
```

### Option 2: Click "🔗 Sync to Jira" Text
```
The whole button is clickable:
┌────────────────────┐
│ 🔗 Sync to Jira (2)│  ← Click anywhere in this box
└────────────────────┘
```

### Option 3: If You Don't See It
```
Problem: Can't find the sync button

Solutions:
1. Did generation complete? (Wait for it to finish)
   └─ Should show: "Generation Complete!"
   
2. Did you scroll down? (Scroll down in the page)
   └─ Sync button is in lower section
   
3. Is number in button > 0? (Check "(2)" in button)
   └─ If number is 0: All scenarios already synced
   
4. Browser zoom too high? (Try Ctrl+- to zoom out)
   └─ Page might be cut off on right side
   
5. Need to approve first? (Only approved sync to Jira)
   └─ Click [Approve] on scenarios first
```

---

## What the Sync Button Shows

### Before Syncing

```
🔗 Sync to Jira (2)
        ↑
    Pending sync count
    (number of approved scenarios waiting to sync)
```

### After Clicking (Progress)

```
⏳ Syncing... (0/2)

Progress bar appears
████░░░░░░ 50%
```

### After Completion

```
✓ Sync Complete!

Results displayed:
Successful: 2/2 ✅
Failed: 0 ✅

Created Issues:
├─ REB3-102
└─ REB3-103

Links to view in Jira (clickable)
```

---

## Important: Scenarios Must Be Approved First ⚠️

### Before Sync

Each scenario has action buttons:

```
[✓] Scenario 1: User login
├─ Priority: High
├─ Type: Positive
├─ Status: [Draft]
│
└─ Action Buttons:
   ┌──────────┐  ┌──────────┐  ┌──────────┐
   │ ✓ Approve│  │ ✗ Reject │  │ Sync     │
   │ Button   │  │ Button   │  │ Single   │
   └──────────┘  └──────────┘  └──────────┘
```

### Steps

1. **Click [✓ Approve]** on each scenario you want to sync
   ```
   Status changes: Draft → Approved
   Badge changes: "Draft" → "✓ Approved"
   ```

2. **Wait for all approvals to complete**

3. **Then click "🔗 Sync to Jira"** button at top of panel

---

## Complete Workflow

```
1. Click [Generate Test Cases] button
           ↓
2. Enter credentials in dialog
           ↓
3. Click [Generate]
           ↓
4. WAIT for generation to complete
           ↓
5. Scroll down to see "Test Scenarios" panel
           ↓
6. Click [✓ Approve] on scenarios you want to sync
           ↓
7. Click "🔗 Sync to Jira (N)" button
   (N = number of approved scenarios)
           ↓
8. Watch progress bar
           ↓
9. See results: "Created issues: REB3-102, REB3-103"
           ↓
10. Check Jira for child issues
    https://retech.atlassian.net/browse/REB3-101
```

---

## Troubleshooting: Sync Button Issues

### Issue 1: "Sync Button Doesn't Appear"

**Solutions:**
```
1. ✅ Did generation complete?
   └─ Wait until you see "Generation Complete!"

2. ✅ Did you scroll down?
   └─ Scroll past the summary to see scenarios

3. ✅ Is the page fully loaded?
   └─ Refresh page: Ctrl+R (Windows) or Cmd+R (Mac)

4. ✅ Are there scenarios to sync?
   └─ If 0 scenarios generated, button won't appear
```

### Issue 2: "Button Shows (0) - Nothing to Sync"

**Solutions:**
```
1. ✅ Are any scenarios approved?
   └─ Click [✓ Approve] on scenarios first

2. ✅ Are scenarios already synced?
   └─ Check jira_child_issue_key column (not NULL means already synced)

3. ✅ Were all scenarios rejected?
   └─ Re-generate or approve different scenarios
```

### Issue 3: "Sync Button is Disabled/Greyed Out"

**Solutions:**
```
1. ✅ Generation in progress?
   └─ Wait for "Generation Complete!"

2. ✅ Syncing already in progress?
   └─ Wait for previous sync to finish

3. ✅ Not enough scenarios approved?
   └─ Approve at least 1 scenario first
```

---

## Button Location Summary

| Question | Answer |
|----------|--------|
| **Where is sync button?** | Top-right of "Test Scenarios" panel |
| **When does it appear?** | After test generation completes |
| **What does it look like?** | Blue button with "🔗 Sync to Jira (N)" text |
| **What's the (N)?** | Number of approved scenarios pending sync |
| **How to make it clickable?** | Approve at least 1 scenario first |
| **What happens after click?** | Progress bar shows, child issues created in Jira |

---

## Quick Visual Map

```
http://localhost:6060 (full page view)

┌─────────────────────────────────────────────────────┐
│ TOP: Header with [Generate Test Cases] button       │
├─────────────────────────────────────────────────────┤
│                                                      │
│ MIDDLE: Test case summary (if generation done)      │
│ "5 test cases generated for REB3-101"              │
│                                                      │
├─────────────────────────────────────────────────────┤
│                                                      │
│ LOWER: "🧪 Test Scenarios" Panel                   │
│                                                      │
│ ┌──────────────────────────────────────────────┐   │
│ │ 🔗 Sync to Jira (2) 📍   🔄 Refresh         │   │
│ │                                               │   │
│ │ SYNC BUTTON IS HERE ↑                       │   │
│ └──────────────────────────────────────────────┘   │
│                                                      │
│ Filters: [Approved] [Pending] [Synced]            │
│                                                      │
│ [✓] Scenario 1...  [✓ Approve] [Sync]            │
│ [✓] Scenario 2...  [✓ Approve] [Sync]            │
│ [✓] Scenario 3...  [✓ Approve] [Sync]            │
│                                                      │
└─────────────────────────────────────────────────────┘
```

---

## ✅ You Found It!

Now you should be able to:
1. ✅ Find the "🔗 Sync to Jira" button
2. ✅ Approve scenarios first
3. ✅ Click the sync button
4. ✅ See child issues created in Jira

**Next:** If child issues still don't appear in Jira after syncing, check: `TROUBLESHOOTING_JIRA_SYNC.md`
