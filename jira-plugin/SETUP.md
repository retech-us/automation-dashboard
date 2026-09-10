# Jira Plugin Setup Guide

Custom Jira Cloud app for "Inhouse TC Generator" panel.

## Prerequisites

- **Node.js** v14+ (https://nodejs.org)
- **Jira Cloud** account with admin access
- **Windows PowerShell** or cmd

## Installation (15 minutes)

### Step 1: Install Node.js

```powershell
# Check if Node is installed
node --version
npm --version

# If not, download and install from:
# https://nodejs.org/en/download/
```

### Step 2: Install Atlassian Forge CLI

```powershell
npm install -g @atlassian/forge-cli

# Verify installation
forge --version
```

### Step 3: Authenticate with Atlassian

```powershell
forge login

# This will open browser
# 1. Click "Allow"
# 2. Grant permissions
# 3. Copy code from browser
# 4. Paste into terminal
```

### Step 4: Create Plugin Project

```powershell
cd C:\SymphonyProjects\automation-dashboard
forge create --no-git

# When prompted:
# - App name: inhouse-tc-generator
# - Template: issue-panel
```

This creates:
```
jira-plugin/
├── manifest.yml
├── package.json
├── src/
│   ├── index.jsx
│   └── resolver.js
└── README.md
```

### Step 5: Navigate to Project

```powershell
cd jira-plugin
```

### Step 6: Test Locally

```powershell
forge tunnel

# Output: Tunnel running at: ...
# Keep this terminal open
```

This creates a tunnel to your local machine. Open another terminal for next steps.

## Project Structure

```
jira-plugin/
├── manifest.yml ..................... App configuration
├── package.json .................... Dependencies
├── src/
│   ├── index.jsx ................... React panel component
│   └── resolver.js ................. Backend functions
├── README.md
└── test-jira-url.txt ............... For testing
```

## Next Steps

1. Replace files with code from this guide
2. Run locally with `forge tunnel`
3. Open Jira in browser
4. Test the panel
5. Deploy when ready

## Troubleshooting

### forge tunnel won't start
```
# Check for port conflicts
netstat -ano | findstr :9000

# Kill process if needed
taskkill /PID <PID> /F
```

### CLI installation failed
```
# Try with npm directly
npm install -g @atlassian/forge-cli@latest

# Or reinstall Node.js
```

### Login issues
```
# Clear credentials
forge logout

# Try again
forge login
```

See detailed guide in main docs for more help.
