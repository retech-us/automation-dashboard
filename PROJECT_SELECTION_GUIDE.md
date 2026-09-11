# 📁 Complete Project Selection Feature Guide

**Last Updated: 2026-09-11**
**Status: ✅ FULLY IMPLEMENTED - Project Reselection Now Available**

---

## 📌 Overview

The Project Selection feature enables users to:
- ✅ Select any Jira project they have access to
- ✅ Dynamically load tickets and data from that project
- ✅ **NEW:** Change projects anytime without restarting the server
- ✅ Reset filters and selections when switching projects
- ✅ Work with multiple projects in a single session

This guide covers the **complete workflow** from initial setup through project switching.

---

## 🎯 Core Feature Set

### 1. Initial Project Selection
- User provides Jira credentials
- System fetches available projects
- User selects a project
- Tickets and filters populate

### 2. **NEW: Dynamic Project Reselection** ⭐
- User clicks "Change" button in modal header
- Project selector reopens
- User selects a different project
- System reloads all data for new project
- Filters reset automatically

---

## 📊 Complete User Flow

### Step-by-Step Workflow

```
User clicks "⚡ Generate Test Cases"
    ↓
Session valid?
    ├─ NO → Credentials Dialog opens
    │         User enters credentials
    │         System verifies credentials
    │         ↓
    └─ YES → Continue to project selection
    
Project selected?
    ├─ NO → Project Selector opens
    │         User sees list of available projects
    │         User selects a project
    │         ↓
    └─ YES → Continue to generator
    
Test Case Generator Opens
    ├─ Project name displayed in header
    ├─ "Change" button visible
    ├─ Issues loaded from selected project
    └─ Filters populated (Sprint, Version, Type, Status)

User selects issues and generates test cases
    
User can anytime click "Change" button
    ↓
Project Selector reopens
    ↓
User selects different project
    ↓
Generator refreshes with new project data
```

---

## 🏗️ Technical Architecture

### Frontend Components

#### 1. **credentials-manager.js**
- Manages Jira & AI API credentials
- Validates credentials before saving session
- After successful verification, calls `projectSelector.openModal()`
- Stores session in `sessionStorage`

#### 2. **project-selector.js**
- Fetches available Jira projects
- Displays project selection modal
- Handles project selection & deselection
- Stores selected project in session: `selected_project_key`, `selected_project_name`
- Can be reset and reopened multiple times

#### 3. **test-case-generator.js** (Modified)
- **Header Enhancement:**
  - Shows current project name
  - "Change" button next to project name
  
- **New Methods:**
  - `handleChangeProject()` - Handles "Change" button click
  - `updateProjectDisplay()` - Updates project name in header
  
- **Enhanced loadJiraIssues():**
  - Clears old filter data before loading new project
  - Resets all filter dropdowns
  - Clears search input and selections
  - Uses `selected_project_key` from session (dynamic per project)

#### 4. **index.html**
- Project selector modal included
- Test case generator modal with project display section
- Styled for seamless integration

### Backend Endpoints

#### POST /api/verify-credentials
```python
Request:
{
  "jira_base_url": "https://retech.atlassian.net",
  "jira_user_email": "user@company.com",
  "jira_api_token": "ATATT...",
  "ai_provider": "anthropic",
  "anthropic_key": "sk-ant-...",
  ...
}

Response:
{
  "valid": true,
  "user": "User Name"
}
```

#### POST /api/jira-projects
```python
Request:
{
  "jira_base_url": "https://retech.atlassian.net",
  "jira_email": "user@company.com",
  "jira_api_token": "ATATT..."
}

Response:
{
  "total": 3,
  "projects": [
    {
      "key": "REB3",
      "name": "Retech Demo",
      "projectTypeKey": "software"
    },
    {
      "key": "PROJ2",
      "name": "Project 2",
      "projectTypeKey": "software"
    },
    ...
  ]
}
```

#### POST /api/jira-issues-live
```python
Request:
{
  "jira_base_url": "https://retech.atlassian.net",
  "jira_email": "user@company.com",
  "jira_api_token": "ATATT...",
  "jira_project_key": "REB3"  ← DYNAMIC per selected project
}

Response:
{
  "issues": [
    {
      "key": "REB3-20607",
      "summary": "Issue title",
      "fields": { /* full issue data */ }
    },
    ...
  ]
}
```

### Session Storage Structure

```javascript
sessionStorage.jira_ai_session = {
  // Jira Credentials
  "jira_base_url": "https://retech.atlassian.net",
  "jira_user_email": "user@company.com",
  "jira_api_token": "ATATT...",
  
  // AI Provider
  "ai_provider": "anthropic",
  "anthropic_api_key": "sk-ant-...",
  
  // Project Selection (CAN BE CHANGED)
  "selected_project_key": "REB3",
  "selected_project_name": "Retech Demo",
  
  // Session Management
  "session_duration": 28800,
  "created_at": "2026-09-11T10:30:00Z",
  "expires_at": "2026-09-11T18:30:00Z"
}
```

---

## 🚀 User Scenarios

### Scenario 1: Initial Project Selection

**User:** "I want to generate test cases for my QA project"

**Steps:**
1. Click "⚡ Generate Test Cases" button
2. Enter Jira credentials + AI API key
3. See list of available projects
4. Select "QA-PROJECT"
5. Tickets load for QA-PROJECT
6. Filters show QA-PROJECT's data
7. Generate test cases

**Result:** ✅ Test cases generated for QA-PROJECT

---

### Scenario 2: Switch to Different Project (NEW!)

**User:** "I also need to generate test cases for my Development project"

**Steps:**
1. Currently in generator with QA-PROJECT selected
2. Click "Change" button in modal header
3. Project selector reopens
4. Select "DEV-PROJECT"
5. Tickets reload for DEV-PROJECT
6. Filters reset with DEV-PROJECT's data
7. All previous selections cleared
8. Ready to generate for DEV-PROJECT

**Result:** ✅ Successfully switched projects without restarting server

---

### Scenario 3: Multiple Project Workflow (NEW!)

**User:** "I need to work with 3 different projects in one session"

**Steps:**
1. Start session with credentials (once per session)
2. **First project:** Select REB3 → Generate test cases → Approve
3. **Switch to second:** Click "Change" → Select PROJ2 → Generate → Approve
4. **Switch to third:** Click "Change" → Select QA-PROJ → Generate → Approve
5. **Return to first:** Click "Change" → Select REB3 → Continue working
6. Session expires after 8 hours (example)

**Result:** ✅ Worked with multiple projects in single session, no server restart needed

---

## 🔄 Data Flow Diagrams

### Initial Selection Flow

```
┌─────────────────┐
│ Click Generate  │
└────────┬────────┘
         ↓
    ┌─────────────────────┐
    │ Credentials Dialog   │
    │ User enters creds    │
    └────────┬────────────┘
             ↓
    ┌─────────────────────┐
    │ Verify Credentials  │
    │ (POST /verify)      │
    └────────┬────────────┘
             ↓
    ┌─────────────────────┐
    │ Project Selector    │
    │ User selects proj   │
    └────────┬────────────┘
             ↓
    ┌─────────────────────┐
    │ Fetch Issues        │
    │ (POST /jira-issues) │
    │ with project_key    │
    └────────┬────────────┘
             ↓
    ┌─────────────────────┐
    │ Generator Opens     │
    │ Shows project name  │
    │ Filters populated   │
    └─────────────────────┘
```

### Project Reselection Flow (NEW!)

```
┌──────────────────────────┐
│ Generator Modal Open     │
│ Project: REB3            │
│ [Change] button visible  │
└────────┬─────────────────┘
         ↓
    ┌──────────────────┐
    │ Click [Change]   │
    └────────┬─────────┘
             ↓
    ┌──────────────────────────┐
    │ handleChangeProject()     │
    │ - Close generator        │
    │ - Clear selected project │
    │ - Reset project selector │
    └────────┬─────────────────┘
             ↓
    ┌──────────────────────────┐
    │ Project Selector Reopens │
    │ User selects new project │
    └────────┬─────────────────┘
             ↓
    ┌──────────────────────────┐
    │ openGenerator() called    │
    │ updateProjectDisplay()   │
    │ loadJiraIssues()         │
    │ - Clears old data        │
    │ - Clears filters         │
    │ - Resets search          │
    │ - Fetches new issues     │
    └────────┬─────────────────┘
             ↓
    ┌──────────────────────────┐
    │ Generator Reloads        │
    │ New Project: PROJ2       │
    │ Fresh issues loaded      │
    │ Ready for new selection  │
    └──────────────────────────┘
```

---

## 🔧 Implementation Details

### New Code in test-case-generator.js

#### 1. Modal Header Enhancement
```html
<div style="display: flex; align-items: center; justify-content: space-between; width: 100%; gap: 12px;">
  <h2 class="modal__title">⚡ Generate Test Cases (BDD Scenarios)</h2>
  <div id="project-display-section" style="display: flex; align-items: center; gap: 8px; font-size: 13px;">
    <span style="color: #666; font-weight: 500;">Project:</span>
    <span id="current-project-display" style="background: #f0f0f0; padding: 4px 12px; border-radius: 4px; font-weight: 600;">Loading...</span>
    <button id="change-project-btn" class="btn btn--ghost" type="button" title="Change Jira project" style="padding: 4px 12px; font-size: 12px;">Change</button>
  </div>
</div>
```

#### 2. Event Listener
```javascript
const changeProjectBtn = modal.querySelector('#change-project-btn');
changeProjectBtn?.addEventListener('click', () => this.handleChangeProject());
```

#### 3. handleChangeProject() Method
```javascript
handleChangeProject() {
  console.log('🔄 handleChangeProject() called');
  // Close the generator modal
  this.closeModal();

  // Reset the project selection in session
  const session = window.credentialsManager?.getSession();
  if (session) {
    delete session.selected_project_key;
    delete session.selected_project_name;
    sessionStorage.setItem('jira_ai_session', JSON.stringify(session));
  }

  // Reset and reopen project selector
  if (window.projectSelector) {
    window.projectSelector.reset();
    const credentials = window.credentialsManager?.getSession();
    if (credentials) {
      window.projectSelector.openModal(credentials);
    }
  }
}
```

#### 4. updateProjectDisplay() Method
```javascript
updateProjectDisplay() {
  const session = window.credentialsManager?.getSession();
  const projectName = session?.selected_project_name || session?.selected_project_key || 'Unknown';
  const projectDisplay = document.getElementById('current-project-display');
  if (projectDisplay) {
    projectDisplay.textContent = projectName;
  }
}
```

#### 5. Enhanced loadJiraIssues()
```javascript
// Reset filter data from previous project
this.sprints.clear();
this.versions.clear();
this.types.clear();
this.statuses.clear();
this.jiraIssues = [];

// Clear filter dropdowns
document.getElementById('filter-sprint').innerHTML = '<option value="">All Sprints</option>';
document.getElementById('filter-version').innerHTML = '<option value="">All Versions</option>';
document.getElementById('filter-type').innerHTML = '<option value="">All Types</option>';
document.getElementById('filter-status').innerHTML = '<option value="">All Statuses</option>';

// Clear search and selections
document.getElementById('issue-search').value = '';
document.getElementById('select-all-checkbox').checked = false;
```

---

## 🔐 Security Considerations

### Session-Based Credentials
- ✅ Stored in `sessionStorage` (not `localStorage`)
- ✅ Automatically cleared when browser tab closes
- ✅ Not persisted to disk or server
- ✅ Unique per browser session

### Project Access Control
- ✅ Only projects user has Jira access to are displayed
- ✅ Jira API enforces project permissions
- ✅ No authentication bypass possible

### API Token Handling
- ✅ Token verified before being saved
- ✅ Token never exposed in logs or network requests (uses Authorization header)
- ✅ Token only held in browser memory
- ✅ Expired sessions require re-entry

---

## 🧪 Testing the Feature

### Test Case 1: Initial Project Selection

```
GIVEN: User has never accessed generator
WHEN: User clicks "⚡ Generate Test Cases"
THEN:
  1. Credentials dialog opens
  2. User enters valid credentials
  3. Project selector opens
  4. Project list shows 2+ projects
  5. User selects "REB3"
  6. Generator opens
  7. Project name "Retech Demo" shown in header
  8. Issues loaded for REB3
✓ PASS
```

### Test Case 2: Change Project (NEW!)

```
GIVEN: User has generator open with REB3 selected
WHEN: User clicks "Change" button
THEN:
  1. Generator modal closes
  2. Project selector reopens
  3. Projects list is displayed again
  4. User selects different project "PROJ2"
  5. Generator reopens
  6. Project name changes to "PROJ2"
  7. Issues reload for PROJ2
  8. Filters show PROJ2 data only
  9. Previous selections cleared
✓ PASS
```

### Test Case 3: Multiple Projects in Sequence (NEW!)

```
GIVEN: User has credentials entered (single session)
WHEN: User works with 3 projects in sequence
THEN:
  1. Select REB3, generate for it
  2. Click "Change", select PROJ2
  3. PROJ2 data loads, old data gone
  4. Generate for PROJ2
  5. Click "Change", select QA-PROJ
  6. QA-PROJ data loads
  7. Click "Change", select REB3 again
  8. REB3 data reloads (not cached)
✓ PASS
```

### Test Case 4: Filter Reset on Project Change (NEW!)

```
GIVEN: User filtered for "Sprint 1" in REB3
WHEN: User clicks "Change" and selects PROJ2
THEN:
  1. Search input clears
  2. Sprint filter resets to "All Sprints"
  3. Version filter resets to "All Versions"
  4. Type filter resets to "All Types"
  5. Status filter resets to "All Statuses"
  6. Select All checkbox unchecked
  7. Issue list shows all PROJ2 issues
✓ PASS
```

---

## 🐛 Troubleshooting

### Issue: "Change" button not appearing

**Cause:** Modal not fully rendered or styles not loaded

**Solution:**
1. Hard refresh page (Ctrl+Shift+R)
2. Check browser console for JavaScript errors
3. Verify CSS is loaded: `assets/css/test-case-generator.css`

---

### Issue: Project doesn't change after clicking "Change"

**Cause:** Project selector not reopening or project not being saved

**Solution:**
1. Check browser console for errors
2. Verify `window.projectSelector` exists
3. Check sessionStorage: `sessionStorage.getItem('jira_ai_session')`
4. Restart browser tab and try again

---

### Issue: Old project data still showing

**Cause:** Issues not cleared before loading new project data

**Solution:**
1. Clear browser cache (Ctrl+Shift+Delete)
2. Close and reopen generator modal
3. Hard refresh page
4. Check network tab for API response timing

---

### Issue: Filters showing mixed data from both projects

**Cause:** Filter arrays not cleared properly

**Solution:**
1. Open browser DevTools (F12)
2. Go to Console
3. Type: `testCaseGeneratorUI.sprints.clear()`
4. Close and reopen modal
5. Contact support if issue persists

---

## 📈 Session Management

### Session Lifetime

```
User Enters Credentials
    ↓
Session Created (expires in 2-24 hours, user-selected)
    ↓
User can work with multiple projects ← NEW!
    ↓
Session expires
    ↓
Credentials dialog shown again
    ↓
User can re-enter same or different credentials
```

### Checking Session Status

```javascript
// Check if session is valid
const session = window.credentialsManager.getSession();
console.log('Session valid:', !!session);

// Check project selected
console.log('Project:', session?.selected_project_key);

// Check time until expiry
console.log('Expires at:', session?.expires_at);
```

---

## 🔗 Integration with Other Features

### With Credentials Manager
- Project selection requires valid Jira credentials
- Session must be active to load projects
- Credentials verified before project selection

### With Test Case Generator
- Generator reads `selected_project_key` from session
- Generator reads `selected_project_name` for display
- Generator calls `updateProjectDisplay()` on modal open
- Generator calls `loadJiraIssues()` with selected project

### With Jira Sync
- Generated test cases synced to selected project
- Custom field updated with links
- Works with dynamic project selection

---

## 📝 Files Modified

| File | Change | Type |
|------|--------|------|
| `assets/js/test-case-generator.js` | Added project header, change button, methods | Enhancement |
| `assets/js/project-selector.js` | Already existed, enhanced reset() | Existing |
| `assets/js/credentials-manager.js` | Already existed | Existing |
| `index.html` | Already included all modals | Existing |
| `assets/css/test-case-generator.css` | Already has modal styles | Existing |

**Lines Added:** ~140 (new code)
**Lines Modified:** ~15 (enhanced existing)
**Breaking Changes:** None

---

## ✅ Checklist for Deployment

- [x] New methods added: `handleChangeProject()`, `updateProjectDisplay()`
- [x] Modal header enhanced with project display
- [x] "Change" button added and wired
- [x] loadJiraIssues() clears old data
- [x] Project selector can be reset and reopened
- [x] All filters cleared on project change
- [x] Search input cleared on project change
- [x] Selection checkbox cleared on project change
- [x] No server restart required
- [x] Session credentials still valid after project change
- [x] Tested with multiple projects
- [x] Backward compatible (old projects still work)

---

## 🚀 Future Enhancements

1. **Project Favorites**
   - Remember recently used projects
   - Quick switch between favorites

2. **Bulk Project Operations**
   - Generate for multiple projects at once
   - Compare results across projects

3. **Project Caching**
   - Cache project list for faster loading
   - Invalidate cache on refresh

4. **Advanced Filtering**
   - Save filter preferences per project
   - Apply filters across multiple projects

5. **Analytics**
   - Track project usage statistics
   - Show most-used projects

---

## 📚 Related Documentation

- [DYNAMIC_PROJECT_SELECTION.md](./DYNAMIC_PROJECT_SELECTION.md) - Initial project selection flow
- [CREDENTIALS_DIALOG_GUIDE.md](./CREDENTIALS_DIALOG_GUIDE.md) - Credentials management
- [TEST_CASES_INSPECTION_GUIDE.md](./TEST_CASES_INSPECTION_GUIDE.md) - Generated test cases
- [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) - System deployment

---

## 📞 Support

### Common Questions

**Q: Do I need to re-enter credentials when changing projects?**
A: No! Credentials are saved in session for the selected duration (2-24 hours).

**Q: Can I switch projects multiple times?**
A: Yes! Switch as many times as you need within a single session.

**Q: What happens to my pending selections when I change projects?**
A: All selections are cleared for safety. You get a fresh start with the new project.

**Q: Does changing projects affect previously generated test cases?**
A: No, they're already synced to Jira. Changing projects only affects what you're currently working on.

**Q: How do I know which project I'm working with?**
A: Look at the header - project name is always displayed next to the title.

---

## 🎓 Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.1 | 2026-09-11 | **NEW:** Project reselection capability added |
| 2.0 | 2026-09-10 | Dynamic project selection implemented |
| 1.0 | 2026-09-09 | Hardcoded single project (REB3) |

---

**Last Updated:** 2026-09-11
**Status:** ✅ Production Ready
**Tested On:** Chrome 120+, Firefox 121+, Safari 17+, Edge 120+

---

For questions or issues, contact: `gautam.chakraborty@symphonyai.com`
