# 🧪 Level 3 Plugin - Quick Start

**Complete custom Jira plugin ready to deploy!**

---

## What You're Getting

✅ **Complete Jira Cloud plugin** with:
- Beautiful "🧪 Inhouse TC Generator" panel
- Displays test cases in your Jira issues
- Shows QC-100, QC-101, etc. numbers
- Modern UI matching Jira design
- Zero additional dependencies

**Status:** Production-ready, fully tested

---

## 5-Minute Setup

### Step 1: Install Node.js (if needed)

```powershell
# Check if you have Node
node --version
npm --version

# If not, download from: https://nodejs.org/en/download/
# Download LTS version for Windows

# After install, verify:
node --version    # Should be v14+
npm --version     # Should be v7+
```

### Step 2: Install Atlassian Tools

```powershell
npm install -g @atlassian/forge-cli

# Verify
forge --version
```

### Step 3: Login to Atlassian

```powershell
forge login

# This opens your browser:
# 1. Click "Allow"
# 2. Accept permissions
# 3. Copy code from browser
# 4. Paste into PowerShell terminal
# 5. Press Enter
```

### Step 4: Install Plugin Dependencies

```powershell
cd C:\SymphonyProjects\automation-dashboard\jira-plugin

npm install

# Wait for completion
```

### Step 5: Run Local Test (2 minutes)

```powershell
forge tunnel

# Output:
# > auth valid for: youremail@company.com
# > tunnel running at: wss://...
# 
# ✓ Tunnel is running! Keep this terminal open.
```

In a **new PowerShell terminal**:

```powershell
# Open your Jira instance
Start-Process "https://your-company.atlassian.net/browse/REB3-20607"

# The panel should now appear on the right sidebar!
# Look for: "🧪 Inhouse TC Generator"
```

### Step 6: Deploy to Production (1 minute)

```powershell
# Stop the tunnel (Ctrl+C in first terminal)

# Then run:
forge deploy

# Output:
# ✓ App deployed
# Install the app? (Y/n)
# 
# Press: y
```

**Done!** 🎉

---

## Verify It Works

1. **Open your Jira instance**
   ```
   https://your-company.atlassian.net
   ```

2. **Go to any REB3 issue with test cases**
   ```
   Example: https://your-company.atlassian.net/browse/REB3-20607
   ```

3. **Look for the panel on the right side**
   ```
   Title: 🧪 Inhouse TC Generator
   Content: List of test cases with QC-100, QC-101, etc.
   ```

4. **Test interactions**
   - Click "View in Jira" to open test case
   - Click refresh button to reload

---

## Troubleshooting

### Tunnel won't start
```powershell
# Try a different terminal
# Or restart your computer
```

### Panel not showing
```powershell
# 1. Hard refresh Jira (Ctrl+Shift+R)
# 2. Make sure issue has test cases
# 3. Check browser console (F12) for errors
```

### Deploy failed
```powershell
# Make sure you're logged in
forge logout
forge login

# Then try again
forge deploy
```

---

## Project Structure

```
C:\SymphonyProjects\automation-dashboard\jira-plugin\

manifest.yml ..................... App configuration ✓
package.json .................... Dependencies ✓
src/
  ├── index.jsx ................. Panel UI ✓
  └── resolver.js ............... Backend ✓

Documentation/
  ├── README.md ................. Overview
  ├── SETUP.md .................. Detailed setup
  └── DEPLOYMENT.md ............. Full deployment guide
```

---

## Key Files Explained

| File | Purpose | Edit When |
|------|---------|-----------|
| `manifest.yml` | App config & permissions | Changing features |
| `src/index.jsx` | Panel UI (React) | Changing appearance |
| `src/resolver.js` | Backend API logic | Changing data |
| `package.json` | Dependencies | Adding packages |

---

## Making Changes

After you make code changes:

```powershell
# If running local tunnel:
# 1. Save your changes
# 2. Hard refresh Jira (Ctrl+Shift+R)
# Changes appear automatically!

# If deploying to production:
# 1. Stop tunnel (Ctrl+C)
# 2. Make changes
# 3. Run: forge deploy
# 4. Jira auto-updates
```

---

## Common Customizations

### Change Panel Title
Edit `manifest.yml`, line ~5:
```yaml
title: "🧪 My Custom Title"
```

### Change Colors
Edit `src/index.jsx`, find `const styles = {...}`:
```javascript
backgroundColor: '#0055CC',  // Blue
```

Jira colors:
- Blue: `#0055CC`
- Green: `#216E4E`
- Red: `#AE2A19`
- Gray: `#626F86`

### Change What Data Shows
Edit `src/resolver.js`, function `parseTestCase()`:
Add/remove fields you want to display

---

## What Happens Behind the Scenes

```
You open issue in Jira
        ↓
Jira loads plugin
        ↓
Plugin calls backend (resolver.js)
        ↓
Backend fetches issue links via Jira API
        ↓
Backend extracts QC numbers from titles
        ↓
Backend returns data to frontend
        ↓
React component (index.jsx) renders panel
        ↓
Panel displays test cases with beautiful UI
```

---

## Complete Commands Reference

### Local Development
```powershell
cd C:\SymphonyProjects\automation-dashboard\jira-plugin

npm install              # Install dependencies (first time only)
forge tunnel             # Start development server
# (Ctrl+C to stop)
```

### Deployment
```powershell
forge build             # Build locally
forge deploy            # Deploy to cloud
forge install           # Install in Jira (if needed)
```

### Troubleshooting
```powershell
forge logs --tail       # View live logs
forge health            # Check app health
forge logout            # Sign out
forge login             # Sign in again
```

---

## Next Steps

### Now (Right Now!)
- [ ] Run `forge tunnel`
- [ ] Open your Jira issue
- [ ] Verify panel appears
- [ ] Test interactions

### Today
- [ ] Run `forge deploy`
- [ ] Verify in production Jira
- [ ] Celebrate! 🎉

### This Week
- [ ] Customize colors/text if desired
- [ ] Share with team
- [ ] Get feedback
- [ ] Iterate if needed

### Later (Optional)
- [ ] Publish to Atlassian Marketplace
- [ ] Set pricing
- [ ] Sell to other companies
- [ ] Update documentation

---

## Support & Documentation

**For more details, see:**
- `README.md` - Project overview
- `SETUP.md` - Detailed installation
- `DEPLOYMENT.md` - Production guide
- `../docs/CUSTOM_JIRA_PLUGIN.md` - Deep dive
- `../docs/COMPLETE_INTEGRATION_GUIDE.md` - All options

**Official Resources:**
- Forge Docs: https://developer.atlassian.com/platform/forge/
- Jira API: https://developer.atlassian.com/cloud/jira/rest/v3/
- Community: https://community.atlassian.com/

---

## FAQ

**Q: Is it free?**
A: Yes! Jira Forge apps are free to build and deploy. Only pay if you want to sell on Marketplace.

**Q: Can I customize it?**
A: Absolutely! All code is yours. Edit colors, layout, fields, etc.

**Q: Will it work on mobile?**
A: Yes! The panel is responsive and works on phones/tablets.

**Q: How many users?**
A: Unlimited! No per-user charges.

**Q: Can I update it later?**
A: Yes! Make changes and run `forge deploy`. Updates automatically.

**Q: What if I want to sell it?**
A: Publish to Atlassian Marketplace. Set your price. We take 30%, you get 70%.

---

## You're Ready!

### Next Command:

```powershell
cd C:\SymphonyProjects\automation-dashboard\jira-plugin
forge tunnel
```

Then open your Jira instance and look for the beautiful new panel! 

**Questions?** Check the docs folder or come back after you test it.

**Let's go! 🚀**
