# 🧪 Dry-Run Testing Guide

**Test sync workflow without modifying Jira - Perfect for safe testing!**

---

## What is Dry-Run Mode?

**Dry-run mode simulates the entire sync workflow WITHOUT actually modifying anything in Jira:**

✅ **No issues created** - Simulated only
✅ **No links created** - Simulated only
✅ **No QC counter incremented** - Stays the same
✅ **No custom fields updated** - Simulated only
✅ **No Jira API calls** - All mocked
✅ **100% Safe** - Zero risk to production data

---

## Quick Start (2 Minutes)

### Step 1: Start Dashboard & Jira Plugin

```powershell
# Terminal 1: Dashboard Server
cd C:\SymphonyProjects\automation-dashboard
python server.py

# Terminal 2: Jira Plugin
cd jira-plugin
forge tunnel
```

### Step 2: Open Dashboard

```
Open: http://localhost:5000
```

### Step 3: Enable Dry-Run Mode

**Look for the toggle in TOP-RIGHT corner:**

```
🧪 Test Mode
○ LIVE → [Enable]

Click: [Enable]
```

**Should show:**

```
🧪 Test Mode
✓ DRY-RUN ← ✓ Success!
```

### Step 4: Test Sync

**In dashboard:**

1. Go to **⚡ Generate Test Cases** tab
2. **Generate** scenarios from REB3 issue
3. **Approve** one scenario
4. **Watch console** for dry-run logs

**Console output:**

```
[DRY-RUN] Would create issue: REB3-20608 - Test Case Title
[DRY-RUN] Would link REB3-20607 → REB3-20608
[DRY-RUN] Would update field on REB3-20607
[DRY-RUN] Would increment QC counter: 99 → 100
```

### Step 5: View Preview

**Click:** [Preview] button

**Shows:**

```
🧪 Dry-Run Preview

Summary
📝 Total actions: 4
✨ Issues to create: 1
🔗 Links to create: 1
📋 Fields to update: 1

Issues to Create
┌─────────────────────────────┐
│ REB3-20608                  │
│ [TC: QC-100] Test Case...   │
└─────────────────────────────┘

Links to Create
┌─────────────────────────────┐
│ REB3-20607 → REB3-20608    │
│ Type: relates to            │
└─────────────────────────────┘
```

---

## Full Workflow

### Phase 1: Enable Dry-Run

```
Top-right corner:
🧪 Test Mode  [Enable]
              ↓
🧪 Test Mode  [Disable]  [Preview]
✓ DRY-RUN
```

**Console output:**
```
✓ DRY-RUN MODE ENABLED - No changes will be made to Jira
📝 All sync operations will be simulated only
⚠️ DRY-RUN MODE: No actual changes will be made to Jira
```

### Phase 2: Generate & Approve

**Generate test cases:**
```
1. Go to ⚡ Generate Test Cases tab
2. Select REB3 issue (e.g., REB3-20607)
3. Click [Generate]
4. Scenarios appear: ✓ Displaying 5 scenarios
```

**Approve one scenario:**
```
1. Click [✓ Approve] button
2. Shows: "✓ Approved! Syncing to Jira..."
3. Auto-syncs (in dry-run mode)
```

**Watch console:**
```
Console (F12):
  [DRY-RUN] Would create issue: REB3-20608 - My Test Case
  [DRY-RUN] Would link REB3-20607 → REB3-20608
  [DRY-RUN] Would update field on REB3-20607
  [DRY-RUN] Would increment QC counter: 99 → 100
```

### Phase 3: View Preview

**Click [Preview] button:**
```
Shows modal with:
  - What issues would be created
  - How many scenarios would sync
  - What QC numbers would be used
  - What links would be created
```

### Phase 4: Verify Jira Untouched

**Open your live Jira:**
```
https://your-company.atlassian.net/browse/REB3-20607

Expected:
✓ NO new issues created
✓ NO new links added
✓ NO custom field updated
✓ Everything unchanged

Because: Dry-run mode simulated only!
```

---

## What Dry-Run Shows

### Console Logs

Every action that WOULD happen:

```
[DRY-RUN] Would create issue: REB3-20608 - [TC: QC-100] Test Case
[DRY-RUN] Would link REB3-20607 → REB3-20608
[DRY-RUN] Would update field on REB3-20607
[DRY-RUN] Would increment QC counter: 99 → 100
```

### Preview Modal

**When you click [Preview]:**

```
🧪 Dry-Run Preview

⚠️ DRY-RUN MODE: No actual changes will be made to Jira

Summary
  📝 Total actions: 4
  ✨ Issues to create: 1
  🔗 Links to create: 1
  📋 Fields to update: 1

Issues to Create
  Key: REB3-20608
  Summary: [TC: QC-100] Test Case Title
  Type: Test Case
  Project: REB3

Links to Create
  From: REB3-20607
  To: REB3-20608
  Type: relates to

Fields to Update
  Issue: REB3-20607
  Field: Inhouse TC Generator
  Action: Append
  Content: • [QC-100] [REB3-20608] - synced
```

---

## Testing Scenarios

### Scenario 1: Single Test Case

**Steps:**
1. Enable dry-run
2. Generate 1 test case
3. Approve it
4. View preview

**Expected:**
```
Issues to create: 1
Links to create: 1
QC number: QC-100
Jira: No changes
```

### Scenario 2: Multiple Test Cases

**Steps:**
1. Enable dry-run
2. Generate 3 test cases
3. Approve all 3
4. View preview

**Expected:**
```
Total actions: 12
Issues to create: 3
Links to create: 3
QC numbers: QC-100, QC-101, QC-102
Jira: No changes
```

### Scenario 3: Mixed Approvals

**Steps:**
1. Enable dry-run
2. Generate 5 test cases
3. Approve only 2
4. Reject 1
5. Leave 2 as draft
6. View preview

**Expected:**
```
Total actions: 8 (only approved get synced)
Issues to create: 2
Links to create: 2
Jira: No changes
```

---

## How to Disable Dry-Run

**When ready for real sync:**

```
Click: [Disable] button

Top-right shows:
🧪 Test Mode
○ LIVE  ← Back to live mode

Now syncs will actually modify Jira!
```

**Console confirms:**
```
✓ Dry-run mode disabled - Back to live Jira sync
```

---

## Common Testing Patterns

### Test 1: Verify QC Numbering

```
1. Enable dry-run
2. Approve 5 scenarios
3. View preview
4. Check QC numbers: QC-100, QC-101, QC-102, QC-103, QC-104
5. Verify counter incremented correctly
```

### Test 2: Verify Field Updates

```
1. Enable dry-run
2. Approve 1 scenario for REB3-20607
3. View preview
4. Verify custom field would be updated on REB3-20607
5. Check Jira - no actual update happened
```

### Test 3: Verify Linking

```
1. Enable dry-run
2. Approve 2 scenarios for REB3-20607
3. View preview
4. Verify links:
   - REB3-20607 → REB3-20608
   - REB3-20607 → REB3-20609
5. Check Jira - no actual links created
```

### Test 4: Verify Issue Details

```
1. Enable dry-run
2. Generate and approve
3. View preview
4. Verify issue summary: [TC: QC-100] Test Case Title
5. Verify issue type: Test Case
6. Verify project: REB3
```

---

## Troubleshooting

### Dry-run button not visible

```
1. Refresh page (Ctrl+R)
2. Check console (F12) for errors
3. Ensure server is running
```

### Preview button disabled

```
1. Make sure dry-run is ENABLED
2. Make sure you approved at least 1 scenario
3. Try clicking [Preview] again
```

### No dry-run logs in console

```
1. Open console (F12)
2. Make sure console is showing "All" messages
3. Approve a scenario
4. Should see [DRY-RUN] logs
```

### Preview shows "no actions"

```
1. Generate and approve scenarios first
2. Preview only shows approved scenarios
3. Try approving more than 0
```

---

## Verifying Safety

**After testing with dry-run:**

### Check Dashboard Data
```
✓ Test cases created in database
✓ Scenarios stored in sessionStorage
✓ QC counter still at 99 (not incremented)
```

### Check Jira Data
```
✓ NO new issues
✓ NO new links
✓ NO custom field updates
✓ Everything unchanged
```

### Check Logs
```
✓ All [DRY-RUN] prefixed
✓ No actual API calls shown
✓ Mocked responses only
```

---

## Dry-Run API Endpoints

For developers, these endpoints are available:

### Enable Dry-Run
```bash
POST /api/dry-run/enable

Response:
{
  "status": "enabled",
  "mode": "DRY-RUN",
  "message": "Dry-run mode enabled..."
}
```

### Check Status
```bash
GET /api/dry-run/status

Response:
{
  "dry_run_enabled": true,
  "mode": "DRY-RUN",
  "current_qc_number": 99
}
```

### Get Preview
```bash
GET /api/dry-run/preview

Response:
{
  "mode": "DRY-RUN",
  "summary": {...},
  "details": {...},
  "actions_log": [...]
}
```

### Disable Dry-Run
```bash
POST /api/dry-run/disable

Response:
{
  "status": "disabled",
  "mode": "LIVE"
}
```

---

## Next Steps

### After Testing Passes

1. **Disable dry-run:**
   ```
   Click [Disable] button
   ```

2. **Test with small dataset:**
   ```
   Approve 1 scenario only
   Verify in Jira it was created
   ```

3. **Test complete workflow:**
   ```
   Generate → Approve → Sync → Check Jira
   ```

4. **Deploy plugin:**
   ```
   forge deploy
   ```

---

## FAQ

**Q: Will dry-run mode break anything?**
A: No! It only simulates - zero changes to Jira.

**Q: Can I switch modes anytime?**
A: Yes! Click Enable/Disable anytime.

**Q: What if I approve during dry-run?**
A: Simulated only - Jira untouched.

**Q: How do I see all actions?**
A: Click [Preview] button or check console (F12).

**Q: Is data lost when disabling?**
A: No, preview data stays until new sync.

**Q: Can I test plugin with dry-run?**
A: Yes! Plugin works in dry-run mode too.

---

## Summary

| Aspect | Dry-Run | Live |
|--------|---------|------|
| **Creates issues** | ❌ Simulates | ✅ Real |
| **Updates Jira** | ❌ No | ✅ Yes |
| **Increments counter** | ❌ No | ✅ Yes |
| **Shows preview** | ✅ Yes | ✅ Yes |
| **Risk level** | 🟢 None | 🔴 High |
| **Best for** | Testing | Production |

---

**Ready to test safely? Enable dry-run mode and start approving scenarios!** 🧪✨
