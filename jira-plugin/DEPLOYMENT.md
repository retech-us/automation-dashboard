# Jira Plugin Deployment Guide

Complete instructions for testing and deploying the Inhouse TC Generator plugin.

## Part 1: Local Development (30 minutes)

### Step 1: Install Dependencies

```powershell
cd C:\SymphonyProjects\automation-dashboard\jira-plugin

npm install
```

### Step 2: Run Local Tunnel

```powershell
forge tunnel

# Output:
# Tunnel running at: https://your-tunnel-url
# Keep this terminal open!
```

### Step 3: Test in Jira

In a **new terminal**:

```powershell
# Go to your Jira instance
# https://your-company.atlassian.net

# Navigate to any issue (e.g., REB3-20607)

# The panel should appear on the right sidebar
# Title: "🧪 Inhouse TC Generator"
```

### Step 4: Verify It Works

1. **Open issue with test cases:**
   - Generate test cases using our dashboard
   - Approve them (they sync to Jira)
   - Open the parent REB3 issue in Jira

2. **Check the panel:**
   - Should see: "🧪 Inhouse TC Generator"
   - Should list all generated test cases
   - Should show: `[QC-100]`, `[QC-101]`, etc.
   - Click refresh button to reload

3. **Test interactions:**
   - Click "View in Jira" link
   - Should open test case issue
   - Click refresh button
   - Should update the list

### Step 5: Troubleshooting Local

**Panel not showing?**
```powershell
# 1. Check tunnel is running
# 2. Hard refresh Jira (Ctrl+Shift+R)
# 3. Check browser console for errors (F12)
# 4. Check tunnel terminal for errors
```

**Test cases not loading?**
```powershell
# 1. Verify issue has linked test cases
# 2. Check issue links are type "relates to"
# 3. Verify test case titles have [TC: QC-100] format
# 4. Check console logs
```

**Performance issues?**
```powershell
# 1. Clear browser cache
# 2. Restart forge tunnel
# 3. Restart Jira
```

---

## Part 2: Production Deployment (5 minutes)

### Step 1: Build the App

```powershell
cd C:\SymphonyProjects\automation-dashboard\jira-plugin

forge build

# Output: ✓ Built
```

### Step 2: Deploy to Jira Cloud

```powershell
forge deploy

# Output:
# ✓ App deployed
# App ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

### Step 3: Install in Your Jira

**Option A: Automatic (Recommended)**

After deployment, Forge usually prompts:
```
Install app? (Y/n)
```

Press `y` to auto-install.

**Option B: Manual Installation**

1. Go to your Jira instance
2. **Settings (⚙️) → Apps → Manage apps**
3. Find **"Inhouse TC Generator"**
4. Click **"Install"**

### Step 4: Configure for Project

1. Go to **Project Settings** (for REB3 project)
2. Find **"Inhouse TC Generator"** section
3. Enable for project
4. Choose issue types: **"Test Case"**
5. Save

### Step 5: Verify Production

1. Open any REB3 issue with linked test cases
2. Panel should appear on right sidebar
3. Test all interactions
4. Check mobile view (if needed)

---

## Part 3: Updates & Maintenance

### Updating the Plugin

**After code changes:**

```powershell
# 1. Make your changes
# 2. Rebuild
forge build

# 3. Deploy
forge deploy

# 4. Jira automatically updates
# (No reinstall needed)
```

### Viewing Deployment History

```powershell
forge deployments
```

### Rolling Back

```powershell
# List versions
forge deployments

# Revert to previous
forge deploy --restore <version-id>
```

### Viewing Logs

```powershell
# Stream logs
forge logs --tail

# View logs for specific date
forge logs --since=2026-09-10
```

---

## Part 4: Publishing to Marketplace (Optional)

### Prerequisites

- ✓ Plugin is tested and working
- ✓ You have Atlassian account
- ✓ You own or manage the app

### Publication Steps

1. **Prepare Listing**
   ```
   Create: screenshots, description, pricing
   ```

2. **Submit to Marketplace**
   ```
   forge marketplace:submit
   ```

3. **Atlassian Reviews**
   ```
   Typically: 5-7 business days
   ```

4. **Published!**
   ```
   Users can install from:
   Jira Settings → Find new apps → "Inhouse TC Generator"
   ```

### Pricing

- **Free tier:** No revenue
- **Paid tier:** You set price
- **Revenue share:** Atlassian takes 30%
- **Payout:** Monthly to registered account

---

## Part 5: Monitoring & Support

### Monitor Usage

```powershell
# Check health
forge health

# View analytics (if enabled)
forge analytics
```

### Troubleshooting in Production

**Panel not showing:**
```
1. Check: Is issue type "Test Case"?
2. Check: Does issue have linked test cases?
3. Check: Are links type "relates to"?
```

**Performance slow:**
```
1. Check: How many linked issues?
2. Optimize: Fetch only needed fields
3. Cache: Recent results in localStorage
```

**Users reporting errors:**
```
# Check logs
forge logs

# View stack traces
forge logs --tail --since=1h
```

---

## Part 6: Development Best Practices

### Code Quality

```powershell
# Lint code
npm run lint

# Format code
npm run format

# Run tests
npm test
```

### Version Control

```bash
git add jira-plugin/
git commit -m "feat: Add/update Jira plugin

- Updated panel UI
- Fixed test case loading
- Added refresh functionality"
```

### Documentation

Update docs when changing:
- UI/layout
- API integrations
- Manifest configuration
- Permission requirements

---

## Complete Checklist

### Before Deployment
- [ ] Code complete
- [ ] Local tunnel tested
- [ ] All interactions work
- [ ] No console errors
- [ ] Responsive design tested
- [ ] Performance acceptable

### After Deployment
- [ ] Can view in Jira
- [ ] Panel appears correctly
- [ ] Test cases load
- [ ] Links work
- [ ] Refresh button works
- [ ] Mobile friendly

### For Production Release
- [ ] Tested with real data
- [ ] Performance tested (50+ test cases)
- [ ] Error handling works
- [ ] Logs are clean
- [ ] Documentation updated
- [ ] Team trained

---

## Quick Commands Reference

```powershell
# Development
forge tunnel                    # Local development
forge build                     # Build locally
forge logs --tail             # Stream logs

# Deployment
forge deploy                    # Deploy to cloud
forge deployments              # View history
forge install                  # Install in Jira

# Maintenance
forge health                    # Check app health
forge logout                    # Sign out
forge list                      # List your apps
```

---

## Support & Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Tunnel not connecting | Check internet, try different port |
| Panel won't load | Clear cache, hard refresh (Ctrl+Shift+R) |
| Test cases empty | Verify issue links, check format |
| Performance slow | Optimize API calls, add pagination |
| Deploy fails | Check Node version, clear cache |

### Resources

- **Forge Docs:** https://developer.atlassian.com/platform/forge/
- **Jira API:** https://developer.atlassian.com/cloud/jira/rest/v3/
- **Community:** https://community.atlassian.com/
- **Support:** dev-support@atlassian.com

---

## Next Steps

1. **Local Testing:** Run `forge tunnel` and test in Jira
2. **Deployment:** Run `forge deploy`
3. **Configuration:** Enable in project settings
4. **Monitoring:** Check logs and usage
5. **Iteration:** Update based on feedback

**Questions? Check the docs folder or contact support!**

**Ready? Start with:** `forge tunnel`
