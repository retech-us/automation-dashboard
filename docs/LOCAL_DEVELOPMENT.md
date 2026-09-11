# Local Development Guide - Port 6060

## Overview

Run the automation-dashboard locally on `localhost:6060` for testing and development.

**Two options available:**
1. **Python Server** (Simplest, built-in) ⭐ **Recommended**
2. **Node.js/Express** (More features, API endpoints)

---

## Option 1: Python Server (Recommended)

### Quick Start

```bash
# Navigate to project directory
cd /path/to/automation-dashboard

# Run the Python development server
python3 server.py

# Output should show:
# ✓ Server running on: http://localhost:6060
# ✓ Dashboard available at: http://localhost:6060/index.html
```

### Access Dashboard

Open browser and go to:
```
http://localhost:6060
```

or

```
http://localhost:6060/index.html
```

### Features

- ✅ Serves all static files (HTML, CSS, JS, JSON)
- ✅ CORS enabled for local development
- ✅ No-cache headers (always load latest)
- ✅ Logs all requests to console
- ✅ Zero external dependencies
- ✅ Simple and reliable

### Stop Server

Press **CTRL+C** in terminal

### Troubleshooting

**Port already in use:**
```bash
# Kill process on port 6060
lsof -i :6060                    # List process
kill -9 <PID>                    # Kill it

# Or use different port (edit server.py PORT variable)
```

**Permission denied:**
```bash
# Make script executable (macOS/Linux)
chmod +x server.py
python3 server.py
```

**Firewall issues:**
- Windows may ask to allow Python
- Click "Allow" when prompted

---

## Option 2: Node.js/Express Server

### Setup

```bash
# 1. Install Node.js (if not already installed)
# Download from: https://nodejs.org/

# 2. Install dependencies
npm install express cors body-parser

# 3. Run the server
node server.js

# Output should show:
# ✓ Server running on: http://localhost:6060
# ✓ API endpoints available
```

### Access Dashboard

Open browser:
```
http://localhost:6060
```

### API Endpoints (Express Only)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Serve index.html |
| `/api/jira` | GET | Fetch Jira data |
| `/api/test-cases` | GET | Fetch generated test cases |
| `/api/generate-test-cases` | POST | Queue generation (mock) |
| `/health` | GET | Health check |

### Test API Endpoints

```bash
# Health check
curl http://localhost:6060/health

# Fetch Jira data
curl http://localhost:6060/api/jira

# Fetch test cases
curl http://localhost:6060/api/test-cases

# Trigger generation
curl -X POST http://localhost:6060/api/generate-test-cases \
  -H "Content-Type: application/json" \
  -d '{"issueKey":"REB3-105","issueType":"Story","testTypes":["positive","negative"]}'
```

### Stop Server

Press **CTRL+C** in terminal

---

## Testing with Real Data

### 1. Generate Real Jira Data (First Time)

```bash
# Set environment variables
export JIRA_BASE_URL="https://your-domain.atlassian.net"
export JIRA_USER_EMAIL="your-email@company.com"
export JIRA_API_TOKEN="your-token"

# Fetch latest Jira data
python3 scripts/fetch-jira.py

# This creates/updates data/jira.json
```

### 2. Run Local Server

```bash
# In a new terminal
python3 server.py

# Visit: http://localhost:6060
```

### 3. View Real Jira Data

Dashboard now shows real Jira issues from your instance!

### 4. Generate Test Cases (Phase 1)

```bash
# Set all required env vars
export JIRA_BASE_URL="..."
export JIRA_USER_EMAIL="..."
export JIRA_API_TOKEN="..."
export ANTHROPIC_API_KEY="sk-ant-..."

# Generate test cases (Phase 1 implementation)
python3 scripts/generate-test-cases.py

# This creates data/test-cases.json
```

### 5. View Generated Test Cases

Refresh dashboard (`http://localhost:6060`) to see generated test cases!

---

## Development Workflow

### Standard Workflow

```bash
# Terminal 1: Start local server
python3 server.py
# Server runs on http://localhost:6060

# Terminal 2: Fetch Jira data (when needed)
export JIRA_BASE_URL="..."
export JIRA_USER_EMAIL="..."
export JIRA_API_TOKEN="..."
python3 scripts/fetch-jira.py

# Terminal 3: Generate test cases (Phase 1)
export JIRA_BASE_URL="..."
export JIRA_USER_EMAIL="..."
export JIRA_API_TOKEN="..."
export ANTHROPIC_API_KEY="sk-ant-..."
python3 scripts/generate-test-cases.py

# Browser: Open http://localhost:6060
# Edit files and refresh browser to see changes
```

### Hot Reload

The Python server **does NOT** have automatic hot-reload.

To test code changes:
1. **Edit** your HTML/CSS/JS files
2. **Refresh** browser (Ctrl+R or Cmd+R)
3. **Hard refresh** if needed (Ctrl+Shift+R or Cmd+Shift+R)

---

## Testing During Phase 1 Development

### Daily Workflow

**Day 1-5 (Phase 1 Implementation):**

```bash
# Terminal 1: Local server
python3 server.py

# Terminal 2: Test changes
cd /path/to/automation-dashboard

# After implementing JiraClient.fetch_issues()
python3 -m pytest tests/test_jira_integration.py -v

# After implementing BDDGenerator
python3 -m pytest tests/test_claude_integration.py -v

# Browser: http://localhost:6060 (refresh to see UI changes)
```

### Testing New Features

1. **Implement feature** in Python/JavaScript
2. **Run tests:** `pytest tests/`
3. **Refresh browser:** See changes live
4. **Check console** (F12) for errors/logs
5. **Verify API responses** in Network tab

---

## Browser DevTools

### Enable Developer Tools

| Browser | Shortcut |
|---------|----------|
| Chrome | F12 or Ctrl+Shift+I |
| Firefox | F12 or Ctrl+Shift+I |
| Safari | Cmd+Option+I |
| Edge | F12 or Ctrl+Shift+I |

### Useful Tabs

| Tab | Purpose |
|-----|---------|
| **Console** | View logs, errors, JS debugging |
| **Network** | See API calls and responses |
| **Elements** | Inspect HTML structure |
| **Sources** | Debug JavaScript |
| **Storage** | View localStorage, sessionStorage |

### Testing API Responses

```javascript
// In console (F12):

// Check if Jira data loaded
console.log(window.jiraData);

// Check if test cases loaded
console.log(window.testCases);

// Manually trigger Jira tab
if (window.JiraTracker) {
  window.JiraTracker.init();
}

// Check for errors
window.addEventListener('error', (e) => {
  console.error('Error:', e.message);
});
```

---

## Troubleshooting

### Dashboard Won't Load

**Problem:** Blank page or 404 error

**Solutions:**
1. Check server is running: `http://localhost:6060/health`
2. Clear cache: Hard refresh (Ctrl+Shift+R)
3. Check browser console (F12) for errors
4. Check terminal for server errors

### Jira Data Not Loading

**Problem:** Empty Jira tab

**Solutions:**
1. Generate Jira data first:
   ```bash
   export JIRA_BASE_URL="..."
   python3 scripts/fetch-jira.py
   ```
2. Verify `data/jira.json` exists
3. Hard refresh browser
4. Check console for errors

### Test Cases Not Showing

**Problem:** No test cases visible

**Solutions:**
1. Generate test cases first:
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   python3 scripts/generate-test-cases.py
   ```
2. Verify `data/test-cases.json` exists
3. Hard refresh browser
4. Check JavaScript console for errors

### CORS Errors

**Problem:** "Cross-Origin Request Blocked" error

**Solutions:**
1. Ensure Python server is running (CORS enabled)
2. Check server logs for requests
3. Verify correct localhost:6060 URL
4. Clear browser cache

### Port 6060 Already in Use

**Problem:** "Address already in use" error

**Solutions:**
```bash
# Find process using port 6060
lsof -i :6060            # macOS/Linux
netstat -ano | findstr :6060  # Windows PowerShell

# Kill process
kill -9 <PID>            # macOS/Linux
Stop-Process -Id <PID> -Force  # Windows PowerShell

# Or change port in server.py
# Edit: PORT = 6060 → PORT = 6061
```

---

## Deployment vs Local Development

| Aspect | Local (6060) | Production (GitHub Pages) |
|--------|-------------|--------------------------|
| **URL** | localhost:6060 | GitHub Pages (auto) |
| **Data Source** | Local `data/` files | GitHub repo files |
| **Updates** | Manual (git pull) | GitHub Actions (auto) |
| **Cache** | Disabled (always fresh) | Browser cached |
| **CORS** | Enabled | N/A (same origin) |
| **SSL/TLS** | No (HTTP) | Yes (HTTPS) |
| **Speed** | Instant (local) | CDN-backed |

---

## Quick Reference

### Python Server

```bash
# Start server
python3 server.py

# Stop server
CTRL+C

# Access
http://localhost:6060

# No setup needed (Python built-in)
```

### Node.js Server

```bash
# Install dependencies (once)
npm install express cors body-parser

# Start server
node server.js

# Stop server
CTRL+C

# Access
http://localhost:6060

# API endpoints available
```

### Data Management

```bash
# Fetch latest Jira data
python3 scripts/fetch-jira.py

# Generate test cases (Phase 1)
python3 scripts/generate-test-cases.py

# View data files
ls -la data/

# Clear data (start fresh)
rm data/jira.json
rm data/test-cases.json
```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_bdd_generator.py -v

# Run with coverage
pytest tests/ --cov=scripts --cov-report=html

# View coverage
open htmlcov/index.html
```

---

## Examples

### Example 1: Testing Dashboard UI Changes

```bash
# Terminal 1: Start server
python3 server.py

# Terminal 2: Make UI changes
# Edit: assets/js/jira-tracker.js
# Save file

# Browser:
# Go to http://localhost:6060
# Press F12 (open DevTools)
# Hard refresh (Ctrl+Shift+R)
# See changes reflected
```

### Example 2: Testing with Real Jira Data

```bash
# Terminal 1: Fetch real Jira data
export JIRA_BASE_URL="https://retech.atlassian.net"
export JIRA_USER_EMAIL="user@company.com"
export JIRA_API_TOKEN="your-token"
python3 scripts/fetch-jira.py

# Terminal 2: Start server
python3 server.py

# Browser: http://localhost:6060
# See real Jira issues from REB3 project
```

### Example 3: Testing Phase 1 Implementation

```bash
# Terminal 1: Run unit tests
pytest tests/test_jira_integration.py -v --tb=short

# Terminal 2: Generate test data
export ANTHROPIC_API_KEY="sk-ant-..."
python3 scripts/generate-test-cases.py

# Terminal 3: Start server
python3 server.py

# Browser: http://localhost:6060
# See generated test cases in dashboard
```

---

## Next Steps

1. ✅ Choose server: Python (simple) or Node.js (advanced)
2. ✅ Start server: `python3 server.py`
3. ✅ Open browser: `http://localhost:6060`
4. ✅ Explore dashboard (static data)
5. ✅ Fetch Jira data: `python3 scripts/fetch-jira.py`
6. ✅ Refresh browser (see real data)
7. ✅ During Phase 1: Generate test cases and test UI

---

## Support

**Questions?**
- Check: Troubleshooting section above
- Server logs: Watch terminal for errors
- Browser console: F12 → Console tab
- Network tab: F12 → Network to see API calls

**Still stuck?**
- Check docs: `docs/` directory
- Review: `PHASE1_IMPLEMENTATION.md`
- Remember: Local testing is just for development!

---

**Local Development Ready! 🚀**

Start with:
```bash
python3 server.py
```

Then open:
```
http://localhost:6060
```

Happy developing! 🎯
