# Windows Quick Start - Local Testing with Test Passkey

## ⚠️ Dashboard Authentication

The dashboard itself (at http://localhost:6060) requires one of these passkeys:
- **`RetechQA2026!`**
- **`SymphonyQA2026!`**

These are different from the local testing passkey "test" (which is for the Python testing system).

Here's how to use the dashboard on Windows:

---

## 🚀 **QUICK START (3 Steps)**

### **Step 1: Generate Mock Data**

**PowerShell (Recommended):**
```powershell
python test-local.py
```

**Command Prompt:**
```cmd
python test-local.py
```

**If python not found, use full path:**
```powershell
C:\Python314\python.exe test-local.py
```

**Output:**
```
✓ Passkey: test (for Python testing system)
✓ Level: full
✓ Purpose: For local development and testing
✓ Mock data saved to: data/jira.json
✓ 5 test issues created
```

**Note:** The "test" passkey is for the Python testing system. The dashboard login requires **`RetechQA2026!`** or **`SymphonyQA2026!`**

### **Step 2: Start Local Server**

```powershell
python server.py
```

Or with full path:
```powershell
C:\Python314\python.exe server.py
```

**Output:**
```
✓ Server running on: http://localhost:6060
✓ Dashboard available at: http://localhost:6060/index.html
✓ Press CTRL+C to stop server
```

### **Step 3: Open Dashboard**

Open browser and go to:
```
http://localhost:6060
```

**Done!** You'll see 5 mock Jira issues for testing! ✅

---

## 🔧 **Fix Python PATH (Optional)**

If you get "python: command not found", add Python to PATH:

### **Option A: Use Full Path (Simplest)**
```powershell
C:\Python314\python.exe test-local.py
C:\Python314\python.exe server.py
```

### **Option B: Add Python to PATH (Permanent)**

1. Find your Python installation:
   ```powershell
   where python
   # Shows: C:\Python314\python.exe
   ```

2. Open Environment Variables:
   - Press: `Windows Key + X` → System
   - Click: Environment Variables
   - Click: Edit the system environment variables
   - Click: Environment Variables button

3. Add Python to PATH:
   - User variables → PATH → Edit
   - New → `C:\Python314`
   - OK, OK, OK

4. Restart PowerShell and test:
   ```powershell
   python --version
   ```

---

## 💡 **Windows-Friendly Commands**

### Generate Mock Data
```powershell
python test-local.py --issue-count 10    # Generate 10 issues
python test-local.py --generate-test-cases  # With test cases
python test-local.py --passkey demo      # Use demo passkey
```

### Start Server
```powershell
python server.py
# Server runs on http://localhost:6060
```

### Stop Server
```
Press CTRL+C in PowerShell
```

### View Mock Data
```powershell
# View Jira issues
Get-Content data/jira.json | ConvertFrom-Json | ConvertTo-Json -Depth 5

# Or use VS Code
code data/jira.json
```

---

## ✅ Test Passkeys Available

| Passkey | Level | Purpose |
|---------|-------|---------|
| **test** | Full | Local development (DEFAULT) |
| **demo** | Read-only | Demo/presentation |
| **ci-test** | Full | CI/CD testing |

### Use Different Passkey
```powershell
python test-local.py --passkey demo
python test-local.py --passkey ci-test
```

---

## 📊 What You Get

After running `python test-local.py`:

✅ **5 Mock Jira Issues**
- TEST-101: Sample Story
- TEST-102: Sample Task
- TEST-103-105: More samples

✅ **Test Credentials** (for testing)
```
jira_base_url: https://test-domain.atlassian.net
jira_user_email: test@example.com
jira_api_token: test-jira-token-12345
anthropic_api_key: sk-ant-test-key-12345
```

✅ **Dashboard Ready**
- All features working locally
- No real API calls
- Perfect for development

---

## 🎯 Development Workflow

### Terminal 1: Generate Data
```powershell
python test-local.py --generate-test-cases
# Creates: data/jira.json + mock test cases
```

### Terminal 2: Start Server
```powershell
python server.py
# Starts: http://localhost:6060
```

### Terminal 3: Develop
```powershell
# Edit files in VS Code or your IDE
# Refresh browser (Ctrl+R) to see changes
# Run tests
pytest tests/ -v
```

### Browser
```
Open: http://localhost:6060
Edit code → Refresh → See changes instantly
```

---

## 🚨 Troubleshooting

### Python not found
```powershell
# Use full path
C:\Python314\python.exe test-local.py
C:\Python314\python.exe server.py
```

### Port 6060 already in use
```powershell
# Kill process on port 6060
Get-Process | Where-Object { $_.Handles -match "6060" } | Stop-Process

# Or change port in server.py:
# PORT = 6060 → PORT = 6061
```

### Mock data not showing
```powershell
# Regenerate
python test-local.py

# Hard refresh browser
# Press: Ctrl+Shift+R (Windows)

# Check data exists
Get-ChildItem data/jira.json
```

### Dependencies missing
```powershell
# Install requirements
pip install -r requirements.txt
```

---

## ✨ Ready to Go!

### One-line setup:
```powershell
python test-local.py; python server.py
```

Then open: `http://localhost:6060`

---

**Test passkey "test" is ready for local development! 🚀**
