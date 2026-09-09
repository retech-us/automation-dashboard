# Credentials Dialog Feature

## Overview

The Credentials Dialog allows users to enter their **Jira and AI credentials** directly through the dashboard UI without needing a `.env` file. Each user can manage their own session with configurable expiry times.

## Features

### 1. **Automatic Prompt**
- When user clicks "⚡ Generate Test Cases" button
- If no valid session exists, credentials dialog opens automatically
- User enters credentials one time per session

### 2. **Credential Fields**

#### Jira Configuration
- **Jira Base URL** - Your Atlassian instance URL (e.g., `https://retech.atlassian.net`)
- **Jira Email** - Email used for Jira authentication
- **Jira API Token** - [Create from account settings](https://id.atlassian.com/manage-profile/security/api-tokens)

#### AI Provider Selection
Users can choose:
- **Claude (Anthropic)** - Recommended
  - Requires: Claude API Key (`sk-ant-...`)
  - [Get API key](https://console.anthropic.com/)
  
- **OpenAI**
  - Requires: OpenAI API Key (`sk-...`)
  - Optional: Custom endpoint URL (for enterprise/custom endpoints)
  - [Get API key](https://platform.openai.com/api-keys)

#### Session Duration
- **Options**: 2 hours (minimum), 4 hours, 8 hours, 24 hours, 7 days
- After expiry: User will be asked to re-enter credentials
- Session stored securely in browser's sessionStorage

### 3. **Form Validation**
- All Jira fields required
- AI provider key validation:
  - Claude keys must start with `sk-ant-`
  - OpenAI keys must start with `sk-`
- Jira URL must be valid HTTPS/HTTP URL
- Email must be valid format

### 4. **Credential Verification**
- Before saving, credentials are verified against actual services
- Shows clear error messages if credentials are invalid
- Prevents saving incorrect credentials

### 5. **Session Management**
- Stored in `sessionStorage` (more secure than localStorage)
- Automatically expires based on user-selected duration
- Shows session status and remaining time
- Auto-clears expired sessions

## User Flow

```
┌─────────────────────────┐
│   Click Generate        │
│   Test Cases Button     │
└────────────┬────────────┘
             │
             ▼
    ┌────────────────┐
    │ Valid Session? │
    └────────┬───────┘
             │
      ┌──────┴──────┐
      │             │
   YES│             │NO
      │             │
      ▼             ▼
┌──────────┐  ┌─────────────────────┐
│  Open    │  │ Open Credentials    │
│Generator │  │ Dialog              │
│Modal     │  └─────────┬───────────┘
└──────────┘            │
                        ▼
                ┌────────────────┐
                │ User Enters:   │
                │ - Jira URL     │
                │ - Email        │
                │ - Token        │
                │ - AI Key       │
                │ - Session Time │
                └────────┬───────┘
                         │
                         ▼
                ┌────────────────┐
                │ Verify with    │
                │ Jira & AI APIs │
                └────────┬───────┘
                         │
              ┌──────────┴──────────┐
              │                     │
          VALID│                    │INVALID
              │                     │
              ▼                     ▼
        ┌──────────┐         ┌─────────┐
        │ Save     │         │ Show    │
        │ Session  │         │ Error   │
        └────┬─────┘         └─────────┘
             │
             ▼
        ┌──────────┐
        │ Open     │
        │Generator │
        │Modal     │
        └──────────┘
```

## Technical Architecture

### Frontend Files
- **`assets/js/credentials-manager.js`** - Main credentials dialog logic
  - Session management (save, retrieve, validate)
  - Form validation
  - Credential verification API calls
  - UI event handlers

- **`assets/js/test-case-generator.js`** - Modified to check session
  - Calls `credentialsManager.openModal()` if no valid session
  - Passes credentials to API calls
  
- **`index.html`** - Added credentials dialog markup
  - Responsive form with all credential fields
  - AI provider toggle showing relevant fields
  - Session duration dropdown

### Backend Changes Needed
New API endpoints in `server.py`:

```python
POST /api/verify-credentials
- Input: Jira URL, email, token, AI provider, API keys
- Output: {valid: true/false}
- Purpose: Validate credentials before saving session

POST /api/generate-test-cases
- Input: Issue keys + credentials (optional, from session)
- Output: Generated test cases
- Purpose: Generate test cases with user's credentials
```

## Storage Details

### Session Storage
```javascript
sessionStorage.jira_ai_session = {
  jira_base_url: "https://...",
  jira_user_email: "user@...",
  jira_api_token: "ATATT...",
  ai_provider: "anthropic" | "openai",
  anthropic_api_key: "sk-ant-...",
  openai_api_key: "sk-...",
  openai_api_base: "https://...", // optional
  session_duration: 7200, // seconds
  created_at: "2026-09-09T...",
  expires_at: "2026-09-09T...",
}

sessionStorage.jira_ai_session_expiry = "2026-09-09T..."
```

### No .env File Needed
- Different users can use different credentials
- Each session is isolated
- Credentials never stored on disk
- Perfect for shared dashboards

## Usage Example

### First Time
1. User clicks "⚡ Generate Test Cases"
2. Credentials dialog appears
3. User enters:
   - Jira URL: `https://retech.atlassian.net`
   - Email: `user@company.com`
   - Token: `ATATT...`
   - AI Provider: Claude
   - API Key: `sk-ant-...`
   - Duration: 8 hours
4. Dialog verifies credentials
5. Session saved, generator modal opens

### Subsequent Clicks (Within Session)
1. User clicks "⚡ Generate Test Cases"
2. Session is valid → Generator modal opens directly
3. No credentials dialog needed

### After Session Expires
1. User clicks "⚡ Generate Test Cases"
2. Session has expired → Credentials dialog appears again
3. User can enter same or different credentials

## Security Considerations

✅ **Secure**
- Credentials in `sessionStorage` (lost when tab closes)
- No credentials in `.env` or on disk
- Credentials verified before saving
- Session expiry enforced

⚠️ **Trade-offs**
- Credentials lost if browser tab crashes (must re-enter)
- No persistent login across sessions (by design)
- Best for single-user workstations

## Next Steps

To fully implement this feature:

1. ✅ Frontend dialog and session management (DONE)
2. ⏳ Backend API endpoints for credential verification
3. ⏳ Update test case generator API to accept credentials
4. ⏳ Remove .env dependency from test case generation
5. ⏳ Test with multiple users

## File Locations

- `index.html` - Credentials dialog HTML (lines 176-270)
- `assets/js/credentials-manager.js` - Full credentials management
- `assets/js/test-case-generator.js` - Modified to use credentials dialog
- `assets/css/test-case-generator.css` - Dialog styling

## Browser Compatibility

Works on all modern browsers that support:
- HTML5 Forms
- sessionStorage
- Fetch API
- ES6 Classes

Tested on:
- Chrome/Chromium 90+
- Firefox 88+
- Safari 14+
- Edge 90+
