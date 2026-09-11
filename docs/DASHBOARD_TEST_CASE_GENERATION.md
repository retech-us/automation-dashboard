# Dashboard Test Case Generation UI

**Status:** ✅ Implemented and Ready  
**Date:** 2026-09-08  
**Feature:** Generate BDD test scenarios directly from the dashboard

---

## Quick Start

### 1. Start the Dashboard

```bash
# Terminal 1: Start the server
python server.py

# Terminal 2: Generate mock Jira issues
python test-local.py
```

### 2. Open Dashboard

```
http://localhost:6060
```

### 3. Login

Use one of these passkeys:
- `RetechQA2026!` (Retech QA team)
- `SymphonyQA2026!` (Symphony AI QA team)

### 4. Click Generate Button

You'll see a new **⚡ Generate Test Cases** button in the header next to the Refresh button.

---

## How to Use

### Step 1: Select Issues

1. Click **⚡ Generate Test Cases** button
2. A modal will open showing all available Jira issues
3. **Select issues** you want to generate test cases for
   - Click individual checkboxes
   - Use **"Select All"** to select all issues
   - Use the search box to filter by issue key or summary

4. Click **Generate**

### Step 2: Generation in Progress

The modal shows:
- **Progress bar** - Visual indication of generation progress
- **Status updates:**
  - Issues Processed: X
  - Scenarios Generated: Y
  - API Provider: Claude/OpenAI
  - Estimated Time: ~2 minutes

### Step 3: View Results

Once complete, you'll see:
- **Total Scenarios Generated** - Number of BDD scenarios created
- **Successful** - Number of issues that succeeded
- **Failed** - Number of issues that failed (if any)
- **Scenarios Preview** - Sample of generated test cases showing:
  - Scenario title
  - Type (positive, negative, edge-case, etc.)
  - Priority (P1, P2, P3)
  - Category (functional, validation, security, etc.)

---

## Understanding the Results

### Scenario Types

- **Positive** 🟢 - Happy path, system works as expected
- **Negative** 🔴 - Error handling, invalid inputs
- **Edge-Case** 🟡 - Boundary conditions, unusual scenarios
- **Security** 🔐 - Security testing scenarios
- **Performance** ⚡ - Load testing scenarios

### Scenario Priority

- **P1** - Critical functionality, directly maps to acceptance criteria
- **P2** - Important but less critical
- **P3** - Nice to have, edge case coverage

### Scenario Categories

- **Functional** - Feature works as designed
- **Validation** - Input validation, format checking
- **Performance** - Speed, load, scalability
- **Security** - Authentication, authorization, injection attacks
- **UX** - User experience, UI responsiveness
- **Design** - Visual appearance, styling

---

## Generated Test Case Format

Each generated test case includes:

```json
{
  "id": "SC-001",
  "title": "User logs in with valid credentials",
  "type": "positive",
  "category": "functional",
  "priority": "P1",
  "preconditions": [
    "Given user account exists in database",
    "And user is on login page"
  ],
  "steps": [
    {
      "stepNumber": 1,
      "action": "When user enters valid email",
      "expectedResult": "Email field is populated"
    },
    {
      "stepNumber": 2,
      "action": "When user clicks 'Login' button",
      "expectedResult": "Request sent to backend"
    }
  ],
  "expectedResult": "User is logged in and redirected to dashboard",
  "automationHint": "Selenium: Use WebDriverWait, find elements by ID",
  "tags": ["@positive", "@smoke", "@critical"],
  "coverage": ["AC1", "AC2"]
}
```

---

## Backend Configuration

### API Endpoints

The dashboard uses these new endpoints:

**GET** `/api/jira-issues` - Get all available Jira issues
```bash
curl http://localhost:6060/api/jira-issues
```

**POST** `/api/generate-test-cases` - Trigger test case generation
```bash
curl -X POST http://localhost:6060/api/generate-test-cases \
  -H "Content-Type: application/json" \
  -d '{"issueKeys": ["TEST-101", "TEST-102"]}'
```

**GET** `/api/test-cases` - Get all generated test cases
```bash
curl http://localhost:6060/api/test-cases
```

**GET** `/api/test-cases/:issueKey` - Get test cases for specific issue
```bash
curl http://localhost:6060/api/test-cases/TEST-101
```

---

## Files Created

### UI Components
- `assets/js/test-case-generator.js` - Modal logic and interactions (330 lines)
- `assets/css/test-case-generator.css` - Modal styling (500 lines)

### Backend
- Updated `server.py` - Added API endpoints for test case generation

### Integration
- Updated `index.html` - Added CSS and JS imports

---

## Error Handling

### No Jira Issues

If you see "No Jira issues available":
```bash
# Generate mock Jira data first
python test-local.py
```

### Generation Fails

If generation fails:
1. Check your environment variables:
   ```bash
   $env:ANTHROPIC_API_KEY
   $env:JIRA_BASE_URL
   ```

2. Check console for error messages (F12 → Console tab)

3. Check server logs:
   ```
   python server.py  # Shows any errors
   ```

### API Key Not Set

If you see "No AI provider configured":
```bash
# Set your Claude API key
$env:ANTHROPIC_API_KEY = "sk-ant-your-key"

# Or OpenAI key
$env:OPENAI_API_KEY = "sk-your-key"
```

---

## Features

✅ **Issue Selection**
- Multi-select with checkboxes
- Search/filter by key or summary
- "Select All" checkbox

✅ **Generation Progress**
- Real-time progress bar
- Status updates
- Estimated time remaining

✅ **Results Display**
- Summary statistics (total, successful, failed)
- Sample scenarios preview
- Scenario type and priority badges

✅ **Dark Mode Support**
- Modal adapts to light/dark theme
- Consistent with dashboard styling

✅ **Responsive Design**
- Works on desktop and tablet
- Mobile-friendly modal

✅ **Error Handling**
- Graceful error messages
- Validation of user input
- Fallback UI states

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Escape` | Close modal |
| `Enter` | Confirm action (when focused on button) |
| `Ctrl+A` | Select all issues (when search is focused) |

---

## Tips & Tricks

### Batch Generation

Generate test cases for multiple issues at once:
1. Open modal
2. Click "Select All"
3. Click "Generate"
4. Wait for completion

### Specific Project

Filter issues by project:
1. Open modal
2. Type project key in search (e.g., "TEST-")
3. Select desired issues
4. Generate

### Monitor Generation

Watch the progress in real-time:
- Progress bar shows completion percentage
- Status indicators update live
- Check browser console (F12) for detailed logs

---

## Troubleshooting

### Modal Won't Open

**Problem:** Button click doesn't open modal

**Solution:**
1. Refresh page (Ctrl+R)
2. Check browser console (F12) for errors
3. Verify JavaScript is loaded:
   ```
   Open DevTools → Network → filter by "test-case-generator.js"
   Should show "200 OK"
   ```

### Issues Not Loading

**Problem:** Modal shows "Loading issues..."

**Solution:**
1. Verify mock data exists:
   ```bash
   ls -la data/jira.json
   ```

2. If missing, generate it:
   ```bash
   python test-local.py
   ```

3. Refresh page (Ctrl+Shift+R for hard refresh)

### Generation Timeout

**Problem:** Generation takes too long or times out

**Solution:**
1. Reduce number of issues selected
2. Check API key is valid
3. Try with fewer test types
4. Check network connectivity

### Results Not Showing

**Problem:** After generation, results are blank

**Solution:**
1. Check browser console for errors
2. Verify API endpoint works:
   ```bash
   curl http://localhost:6060/api/test-cases
   ```

3. Generate mock test cases:
   ```bash
   python scripts/generate-test-cases.py
   ```

---

## Performance

### Typical Generation Times

- **5 issues:** ~1-2 minutes
- **10 issues:** ~2-4 minutes
- **20 issues:** ~4-8 minutes

Times depend on:
- AI provider (Claude faster than GPT-4)
- Issue complexity
- Network speed
- System resources

### Optimization Tips

- Generate 5-10 issues at a time
- Use Claude (default) - it's faster
- Run during off-peak hours
- Close unnecessary browser tabs

---

## Next Steps

1. ✅ Start server: `python server.py`
2. ✅ Generate mock data: `python test-local.py`
3. ✅ Open dashboard: http://localhost:6060
4. ✅ Login with test passkey
5. ✅ Click "⚡ Generate Test Cases"
6. ✅ Select issues and generate!

---

## Support

For issues or questions:
- Check browser console (F12)
- Review server logs
- Verify environment variables
- Check documentation files

---

**Dashboard test case generation is ready to use!** 🚀
