# Jira Marketplace Apps for Test Case Management

Guide to installing professional test management apps in Jira at the admin level.

## Option 1: Zephyr Scale (Recommended for Enterprise)

**Features:**
- Full test case management
- Test execution tracking
- Test result reporting
- Integration with CI/CD

**Installation:**

1. **As Jira Admin**, go to:
   ```
   Jira Settings (⚙️) → Apps → Manage apps
   ```

2. **Find New Apps**:
   - Click "Find new apps"
   - Search: "Zephyr Scale"
   - Click the Zephyr Scale result

3. **Install**:
   - Click "Free trial" or "Get it now"
   - Accept permissions
   - Click "Install"
   - Zephyr will appear in app menu

4. **Configure**:
   - Go to project settings
   - Find "Zephyr Scale" tab
   - Configure project for test case management

5. **Integration with Dashboard**:
   - API endpoint: `{jira_url}/api/v1/testcases`
   - Create test cases via API
   - They appear in Zephyr UI

**Cost:** ~$10-20/month per project

---

## Option 2: Xray for Jira (Enterprise Testing)

**Features:**
- Test management
- Test automation integration
- BDD/Gherkin support
- Test result dashboard

**Installation:**

1. **Navigate to Apps**:
   ```
   Jira Settings → Apps → Manage apps → Find new apps
   ```

2. **Search and Install**:
   - Search: "Xray for Jira"
   - Click "Get it now"
   - Accept permissions
   - Install

3. **License**:
   - Free tier available (limited)
   - Pro tier: ~$15/month
   - Enterprise: Custom pricing

4. **Configuration**:
   - Project → Project Settings
   - Find "Xray" section
   - Enable test management

5. **API Integration**:
   ```
   POST {jira_url}/rest/xray/2.0/testcases
   Headers:
     - Authorization: Bearer {token}
     - Content-Type: application/json
   ```

---

## Option 3: TestRail Integration

**Features:**
- Separate test management tool
- Deep Jira integration
- Test execution tracking
- Advanced reporting

**Installation:**

1. **Go to TestRail**:
   - Create account at testrail.com
   - Create project
   - Get API key from Settings

2. **Jira Integration**:
   - Jira Settings → Apps → Find new apps
   - Search: "TestRail for Jira"
   - Install app

3. **Connect TestRail**:
   - Get API key from TestRail
   - In Jira: Configure TestRail connection
   - Map Jira projects to TestRail projects

4. **Pricing**: ~$12-18/month

---

## Option 4: Smart Checklist (Lightweight)

**Features:**
- Simple checklist in issues
- Lightweight
- No additional project setup
- Good for basic test tracking

**Installation:**

1. **Marketplace**:
   - Apps → Find new apps
   - Search: "Smart Checklist"
   - Install

2. **Use Cases**:
   - Add checklist to test case issues
   - Track individual test steps
   - Simple progress tracking

**Cost:** Free

---

## Option 5: Test Coverage (Basic Tracking)

**Features:**
- Coverage reporting
- Test status tracking
- Lightweight
- Good for simple needs

**Installation:**

1. **Marketplace**:
   - Apps → Find new apps
   - Search: "Test Coverage"
   - Install

2. **Configure**:
   - Add coverage field to issues
   - Track test coverage by project

**Cost:** Free-$5/month

---

## How to Install at Admin Level

### Step-by-Step:

1. **Login as Jira Admin**:
   - Your account needs admin rights
   - Verify in Settings → Users

2. **Navigate to Apps**:
   ```
   Jira Logo → Settings (⚙️) → Manage apps → Find new apps
   ```

3. **Search and Review**:
   - Search for app name
   - Read description and reviews
   - Check ratings

4. **Install**:
   - Click "Free trial" or "Get it now"
   - Review permissions (click "Accept")
   - App installs automatically

5. **Post-Install Configuration**:
   - Check your project
   - New app appears in project menu
   - Configure settings as needed

### Granting Access to Users:

```
Project Settings → Apps → [App Name]
Enable for: All users / Specific users
```

---

## Recommended Setup for Inhouse TC Generator

### Recommended: Xray (Best for BDD)

```
Inhouse TC Generator (our tool)
        ↓
Creates test cases in Jira
        ↓
Xray manages & executes
        ↓
Test results visible in Xray dashboard
```

### Alternative: Smart Checklist (Lightweight)

```
Inhouse TC Generator
        ↓
Creates test case issues
        ↓
Smart Checklist adds steps
        ↓
Lightweight tracking
```

---

## Troubleshooting App Installation

### "App not found"
- Check Jira version compatibility
- Try official app name
- Check your region (some apps region-locked)

### "Permission denied"
- Need Jira Admin role
- Contact your Jira admin
- They can grant you temporary admin rights

### "App won't enable"
- Check project license level (some apps need premium)
- Try enabling for "Free" tier first
- Contact app support

---

## API Integration Examples

### Using Zephyr Scale API:
```python
import requests

headers = {
    'Authorization': f'Bearer {api_token}',
    'Content-Type': 'application/json'
}

# Create test case
payload = {
    'name': '[TC-100] Test Case Title',
    'projectId': project_id,
    'description': 'Test description'
}

response = requests.post(
    f'{jira_url}/api/v1/testcases',
    json=payload,
    headers=headers
)
```

### Using Xray API:
```python
import requests

# Create test case in Xray format
payload = {
    'fields': {
        'summary': '[TC-100] Test Case',
        'description': 'Test description',
        'issuetype': {'name': 'Test'},
        'project': {'key': 'REB3'}
    }
}

response = requests.post(
    f'{jira_url}/rest/xray/2.0/testcases',
    json=payload,
    headers=headers
)
```

---

## Next Steps

1. **Decide which app fits your needs**
2. **Have Jira admin install it**
3. **Configure in project settings**
4. **Get API credentials**
5. **Integrate with Inhouse TC Generator**

For questions, contact your Jira admin or app vendor support.
