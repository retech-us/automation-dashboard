# Complete Integration Guide: Inhouse TC Generator + Jira

End-to-end guide for all three integration levels with Jira.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│         Inhouse TC Generator (our tool)                     │
│  - Generates test cases from Jira issues                    │
│  - Creates QC-100, QC-101, etc.                             │
│  - Stores in database                                       │
└────────────┬────────────────────────────────────────────────┘
             │
             ├──► Level 1: Custom Field (No plugin needed)
             │    - Adds "Inhouse TC Generator" custom field
             │    - Updates parent issue with test case list
             │    - Simple, lightweight
             │
             ├──► Level 2: Marketplace App (Recommended)
             │    - Xray, Zephyr, TestRail
             │    - Professional test management
             │    - Full integration ecosystem
             │
             └──► Level 3: Custom Plugin (Enterprise)
                  - Custom Jira panel
                  - Branded UI
                  - Full control
```

---

## Implementation Levels

### Level 1: Custom Field (Currently Implemented ✓)

**What it does:**
- Automatically creates custom field on first sync
- Updates parent issue with list of generated test cases
- Shows: `• [QC-100] [REB3-20608] - synced`

**Setup:** Already done! Just test it.

**Pros:**
- ✅ No plugin needed
- ✅ Fast implementation
- ✅ Works immediately
- ✅ Simple display

**Cons:**
- ❌ Basic UI
- ❌ Limited customization
- ❌ No rich formatting

**Test it:**
```bash
1. Generate test cases
2. Approve one
3. Check parent REB3 issue
4. Should see new custom field with test case links
```

---

### Level 2: Marketplace App (Professional)

**Options:**

#### A. Xray for Jira (RECOMMENDED)

**Features:**
- Test case management UI
- Test execution tracking
- BDD/Gherkin support
- Beautiful dashboards
- Integration with CI/CD

**Setup Time:** 30 minutes
**Cost:** $15-30/month

**Installation:**
```
Jira Settings → Apps → Find new apps → Search "Xray"
→ Install → Configure in project
```

**Integration with our tool:**
```python
# In sync/jira_sync.py

def sync_to_xray(self, test_case_data):
    """Send test case to Xray"""
    url = f"{self.base_url}/rest/xray/2.0/testcases"
    payload = {
        'fields': {
            'summary': test_case_data['title'],
            'description': test_case_data['description'],
            'issuetype': {'name': 'Test'},  # Xray Test type
            'project': {'key': 'REB3'}
        },
        'testCaseDefinition': {
            'steps': [
                {'action': step, 'data': '', 'result': ''}
                for step in test_case_data.get('steps', [])
            ]
        }
    }
    
    # POST to Xray
    return self._make_request('POST', '/testcases', payload)
```

**Workflow:**
```
Generate in our tool
    ↓
Create in Jira as REB3-20608
    ↓
Link to Xray Test type
    ↓
Xray shows: Test steps, execution history, results
    ↓
Dashboard displays coverage & status
```

**Pros:**
- ✅ Professional look & feel
- ✅ Test execution built-in
- ✅ Reporting dashboards
- ✅ CI/CD integration
- ✅ Mobile app

**Cons:**
- ❌ Monthly cost
- ❌ Need Jira admin to install
- ❌ More complex setup

---

#### B. Zephyr Scale (Alternative)

**Features:**
- Test management
- Test cycles & execution
- Reports and analytics
- Lightweight

**Cost:** $10-15/month
**Setup:** Similar to Xray

```
Apps → Find new apps → "Zephyr Scale" → Install
```

---

### Level 3: Custom Jira Plugin (Enterprise)

**What it does:**
- Custom panel in issue view
- Shows: `🧪 Inhouse TC Generator`
- Lists all generated test cases
- Real-time updates
- Custom branding

**Setup Time:** 2-4 days
**Cost:** Development only

**Features:**
- Custom UI matching your brand
- Rich formatting
- Direct integration with our tool
- No dependency on third-party apps
- Full control

**Components:**
1. **Frontend Panel** (React)
   ```
   Shows: QC-100, QC-101, QC-102...
   Status: Synced / Pending / Failed
   Refresh button
   ```

2. **Backend** (Node.js/Python)
   ```
   Fetches linked issues
   Filters by type: Test Case
   Returns formatted data
   ```

3. **Manifest** (Atlassian Forge)
   ```
   Declares permissions
   Registers module locations
   Configures authentication
   ```

**Pros:**
- ✅ Complete control
- ✅ Perfect branding
- ✅ No third-party dependency
- ✅ Custom features
- ✅ Sellable to others

**Cons:**
- ❌ Requires development
- ❌ Maintenance burden
- ❌ Longer setup time

**Complete plugin code:** See `CUSTOM_JIRA_PLUGIN.md`

---

## Quick Start: Each Level

### Level 1: Custom Field (5 minutes)

```bash
cd C:\SymphonyProjects\automation-dashboard
python server.py
```

1. Generate test cases
2. Approve one
3. Check parent issue - should see custom field with `[QC-100]` link

**Done!**

---

### Level 2: Install Xray (30 minutes)

**As Jira Admin:**

1. **Go to Settings:**
   ```
   ⚙️ Settings → Apps → Find new apps
   ```

2. **Search and Install:**
   ```
   Search: "Xray"
   Click: Xray for Jira
   Click: "Get it now"
   Approve permissions
   Click: "Install"
   ```

3. **Configure:**
   ```
   Project Settings → Apps → Xray
   Enable for project: REB3
   Set issue type for tests: "Test"
   ```

4. **Get API Key:**
   ```
   Xray Settings → Integrations
   Copy: API Key & Client ID
   ```

5. **Create custom fields** (if needed)

6. **Test it:**
   - In our tool, generate & approve
   - Check Xray dashboard
   - Should see test case created

**Done!**

---

### Level 3: Build Custom Plugin (2 days)

**Prerequisites:**
- Node.js installed
- Jira Cloud account (admin)
- Basic JavaScript/React knowledge

**Steps:**

1. **Install Tools:**
   ```bash
   npm install -g @atlassian/forge-cli
   ```

2. **Create Project:**
   ```bash
   forge create
   (Choose: Issue panel template)
   ```

3. **Code the Panel:**
   See `CUSTOM_JIRA_PLUGIN.md` for complete code

4. **Test Locally:**
   ```bash
   forge tunnel
   # Opens http://localhost:2990/jira
   ```

5. **Deploy:**
   ```bash
   forge deploy
   # Choose: Cloud
   ```

6. **Configure in Project:**
   ```
   Project Settings → Apps → Inhouse TC Generator
   Enable panel
   ```

7. **Test in Production:**
   - Generate test case
   - Open parent issue
   - Panel should show: `🧪 Inhouse TC Generator`

---

## Which Level Should You Choose?

### Choose Level 1 (Custom Field) If:
- ✅ You want immediate results
- ✅ Budget is minimal
- ✅ Simple display is enough
- ✅ No Jira admin access needed
- ✅ Quick POC/demo

### Choose Level 2 (Xray/Marketplace) If:
- ✅ You need professional test management
- ✅ Team size > 5 people
- ✅ Need test execution tracking
- ✅ Want CI/CD integration
- ✅ Budget: $10-30/month
- ✅ Standard features are enough

### Choose Level 3 (Custom Plugin) If:
- ✅ You need complete control
- ✅ Want to sell/distribute plugin
- ✅ Team has developers
- ✅ Custom branding is critical
- ✅ Unique features needed
- ✅ Budget: Development cost only

---

## Implementation Timeline

### Week 1: Get Baseline Working
```
Day 1: Level 1 (Custom Field) - 30 min
  └─ Test cases appear in custom field

Day 2-3: Testing & refinement
  └─ Verify QC numbering
  └─ Test auto-sync
  └─ Verify linking

Day 4-5: Optional - Level 2 (Marketplace)
  └─ Install Xray
  └─ Configure integration
  └─ Demo to team
```

### Week 2-3: Enterprise Features
```
Day 6-10: Level 3 (Custom Plugin)
  └─ Setup dev environment
  └─ Build panel UI
  └─ Backend integration
  └─ Testing

Day 11-15: Polish & Deploy
  └─ Security review
  └─ Performance testing
  └─ Deploy to production
  └─ User training
```

---

## API Integration Examples

### Custom Field Update
```python
from sync.custom_fields import CustomFieldsManager

cf = CustomFieldsManager(jira_url, email, token)

# Get or create custom field
field_id = cf.get_or_create_custom_field()

# Add test case to field
cf.add_test_case_to_issue(
    'REB3-20607',
    'REB3-20608',  # child issue
    'QC-100'       # QC number
)
```

### Xray Integration
```python
import requests

# Create test in Xray
headers = {
    'Authorization': f'Bearer {xray_token}',
    'Content-Type': 'application/json'
}

payload = {
    'fields': {
        'summary': '[QC-100] Test Case Title',
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

### Custom Plugin GraphQL
```javascript
// Fetch test cases for issue panel
async function getTestCases(issueKey) {
  const response = await api.asUser().requestJira(
    `/rest/api/3/issues/${issueKey}?expand=changelog`,
    { headers: { 'Accept': 'application/json' } }
  );
  
  const issue = await response.json();
  
  // Extract linked test cases
  return issue.fields.issuelinks
    .filter(link => link.type.name === 'relates to')
    .map(link => ({
      key: link.outwardIssue.key,
      title: link.outwardIssue.fields.summary,
      status: 'synced'
    }));
}
```

---

## Troubleshooting

### Custom Field Not Appearing
```bash
# Ensure custom field was created
1. Check Jira: Settings → Customize fields
2. Look for: "Inhouse TC Generator"
3. If missing: API might have failed
4. Check server logs for errors
```

### Xray Installation Issues
```bash
# Xray not showing in apps
1. Verify admin account
2. Check Jira Cloud (not Data Center)
3. Try different browser
4. Contact Xray support
```

### Plugin Not Loading
```bash
# Panel doesn't appear in issue
1. forge logs  # Check deployment logs
2. forge deploy again
3. Clear browser cache
4. Verify manifest.yml syntax
```

---

## Next Actions

1. **Immediate (Today):**
   - [ ] Test Level 1 (custom field)
   - [ ] Verify QC numbering
   - [ ] Confirm test cases linked

2. **This Week:**
   - [ ] Evaluate Level 2 (Xray vs others)
   - [ ] Get Jira admin approval if needed
   - [ ] Install marketplace app (if chosen)

3. **Next Week:**
   - [ ] Plan Level 3 (if needed)
   - [ ] Allocate development resources
   - [ ] Start plugin development

---

## Support Resources

- **Jira API Docs**: https://developer.atlassian.com/cloud/jira/rest/v3/
- **Forge Docs**: https://developer.atlassian.com/platform/forge/
- **Xray Docs**: https://docs.getxray.app/
- **Atlassian Community**: https://community.atlassian.com/
- **Our Documentation**: See `/docs` folder

---

## Questions?

- Level 1: Check `sync/custom_fields.py`
- Level 2: See `JIRA_MARKETPLACE_APPS.md`
- Level 3: See `CUSTOM_JIRA_PLUGIN.md`
- General: Check GitHub issues or contact team

**Ready to integrate? Start with Level 1 today!** 🚀
