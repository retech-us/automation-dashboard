# Building a Custom Jira Plugin for Inhouse TC Generator

Complete guide to creating a custom Jira Cloud app that displays the "Inhouse TC Generator" panel.

## What We're Building

A Jira Cloud app that:
- Adds a custom panel to issue view
- Shows all generated test cases
- Displays QC-100, QC-101, etc. numbers
- Updates automatically when new test cases created
- Shows approval status

## Prerequisites

- Jira Cloud account (admin access)
- Node.js & npm installed
- Atlassian CLI tools
- Basic JavaScript knowledge

## Step 1: Setup Development Environment

### Install Atlassian SDK

```bash
# Install Node
node --version  # Should be v14+

# Install Atlassian CLI
npm install -g @atlassian/developer-console

# Or use Docker
docker run --rm -v ~/.ssh:/home/user/.ssh \
  atlassian/default-image:latest \
  atlas-run-standalone --product jira --version latest
```

## Step 2: Create Plugin Project

### Create Project Structure

```bash
mkdir inhouse-tc-generator-plugin
cd inhouse-tc-generator-plugin
npm init -y
npm install @atlassian/forge-cli
```

### Authenticate

```bash
forge login
```

## Step 3: Initialize Forge App

```bash
forge create
```

**Choose:**
- App name: `inhouse-tc-generator`
- Product: `Jira`
- Template: `Issue panel`

This creates:
```
.
├── manifest.yml
├── src/
│   └── index.jsx
├── package.json
└── README.md
```

## Step 4: Create the Panel Component

### Edit `src/index.jsx`:

```javascript
import React, { useState, useEffect } from 'react';
import { invoke } from '@forge/bridge';
import { invoke as invokeAsync } from '@forge/async';

export default function IssuePanelComponent({ issue }) {
  const [testCases, setTestCases] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTestCases();
  }, [issue.key]);

  async function loadTestCases() {
    try {
      setLoading(true);
      // Call backend to get linked test cases
      const cases = await invoke('getTestCases', { 
        issueKey: issue.key 
      });
      setTestCases(cases || []);
    } catch (error) {
      console.error('Error loading test cases:', error);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return <div>Loading test cases...</div>;
  }

  if (testCases.length === 0) {
    return (
      <div style={{ padding: '16px', textAlign: 'center', color: '#626F86' }}>
        <p>No test cases generated yet</p>
      </div>
    );
  }

  return (
    <div style={{ padding: '16px' }}>
      <h3>🧪 Inhouse TC Generator</h3>
      <p style={{ color: '#626F86', marginBottom: '12px' }}>
        {testCases.length} test case(s) generated from this issue
      </p>

      <div style={{ borderTop: '1px solid #EBECF0' }}>
        {testCases.map((tc, idx) => (
          <div 
            key={idx}
            style={{
              padding: '12px',
              borderBottom: '1px solid #EBECF0',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}
          >
            <div>
              <strong style={{ color: '#0055CC' }}>
                {tc.qcNumber}
              </strong>
              <p style={{ margin: '4px 0 0 0', color: '#626F86' }}>
                {tc.title}
              </p>
            </div>
            <div>
              <span 
                style={{
                  padding: '4px 8px',
                  backgroundColor: tc.status === 'synced' ? '#DFFCF0' : '#FFF7D6',
                  color: tc.status === 'synced' ? '#216E4E' : '#974F0C',
                  borderRadius: '4px',
                  fontSize: '12px'
                }}
              >
                {tc.status === 'synced' ? '✓ Synced' : 'Pending'}
              </span>
            </div>
          </div>
        ))}
      </div>

      <div style={{ marginTop: '12px' }}>
        <button 
          onClick={loadTestCases}
          style={{
            padding: '8px 12px',
            backgroundColor: '#0055CC',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          Refresh
        </button>
      </div>
    </div>
  );
}
```

## Step 5: Configure Manifest

### Edit `manifest.yml`:

```yaml
modules:
  issue-panel:
    - key: inhouse-tc-generator-panel
      resource: inhouse-tc-generator-panel
      title: Inhouse TC Generator
      description: Shows test cases generated from this issue
      provider:
        key: inhouse-tc-generator-backend

permissions:
  - key: issue:read
    reason: Read issue to display linked test cases

backends:
  - key: inhouse-tc-generator-backend
    function: getTestCases
```

## Step 6: Create Backend Function

### Create `src/backend.js`:

```javascript
import { storage } from '@forge/api';
import { asUser } from '@forge/api';
import * as api from '@forge/api';

export async function getTestCases(request) {
  const { issueKey } = request.payload;

  try {
    // Fetch issue from Jira
    const response = await api.asUser().requestJira(
      `/rest/api/3/issues/${issueKey}`,
      {
        headers: {
          'Accept': 'application/json'
        }
      }
    );

    if (!response.ok) {
      return [];
    }

    const issue = await response.json();

    // Get linked issues with 'relates to' link
    const links = issue.fields?.issuelinks || [];
    const testCases = [];

    links.forEach(link => {
      if (link.type?.name === 'relates to' && link.outwardIssue) {
        const linkedIssue = link.outwardIssue;
        const title = linkedIssue.fields?.summary || '';
        
        // Extract QC number from title
        const qcMatch = title.match(/\[TC: (QC-\d+)\]/);
        const qcNumber = qcMatch ? qcMatch[1] : 'N/A';

        testCases.push({
          key: linkedIssue.key,
          title: title.replace(/\[TC: QC-\d+\]\s*/, ''),
          qcNumber: qcNumber,
          status: 'synced',
          url: `${linkedIssue.self}`
        });
      }
    });

    return testCases;
  } catch (error) {
    console.error('Error fetching test cases:', error);
    return [];
  }
}
```

## Step 7: Update package.json

```json
{
  "name": "inhouse-tc-generator",
  "version": "1.0.0",
  "description": "Inhouse TC Generator - Display generated test cases in Jira",
  "main": "src/index.jsx",
  "dependencies": {
    "@atlassian/forge-cli": "^latest",
    "react": "^17.0.0",
    "@atlassian/react-confluence-macros": "latest"
  },
  "devDependencies": {
    "@babel/preset-react": "^7.0.0"
  }
}
```

## Step 8: Deploy Plugin

### Local Testing

```bash
forge deploy --no-verify
```

### Production Deployment

```bash
# Build
forge build

# Deploy
forge deploy

# Publish to Marketplace
forge publish
```

## Step 9: Install in Jira

### For Cloud Instance:

1. Go to Jira Settings
2. Apps → Manage apps → Settings → Upload app
3. Browse to your built plugin `.jar` file
4. Install

### For Cloud via Marketplace:

1. Go to Atlassian Marketplace
2. Submit your plugin
3. Atlassian reviews
4. Published to marketplace

## Step 10: Configure in Project

1. Go to Project Settings
2. Find "Inhouse TC Generator" panel
3. Enable for issue type: "Test Case"
4. Panel appears on all issues

## Complete Manifest Example

```yaml
descriptor:
  key: com.inhouse.tc-generator
  name: Inhouse TC Generator
  description: Display test cases generated from Jira issues
  vendor:
    name: Internal Tools
    url: https://internal.company.com
  version: 1.0.0
  
modules:
  panels:
    - key: tc-generator-panel
      location: atl.jira.view.issue.right.context
      weight: 200
      title: Inhouse TC Generator
      description: Shows all generated test cases from this issue
      resource: tc-generator-panel-resource
      context:
        - issue

permissions:
  - key: read:jira-work
    reason: Read issue details to display test cases
  - key: write:jira-work
    reason: Update custom fields with test case info

apiVersion: 1
```

## Testing Locally

```bash
# Run local Jira for testing
docker run -v ${PWD}:/plugin atlassian/jira:latest

# In separate terminal
forge tunnel

# Open: http://localhost:2990/jira
# Use plugin in development mode
```

## Deployment Checklist

- [ ] Component renders correctly
- [ ] Test cases display properly
- [ ] Refresh button works
- [ ] Handles empty state
- [ ] Responsive design
- [ ] Error handling
- [ ] Performance (< 2s load)
- [ ] Manifests correct
- [ ] Permissions minimal

## Support & Documentation

- **Forge Documentation**: https://developer.atlassian.com/platform/forge/
- **Jira API Docs**: https://developer.atlassian.com/cloud/jira/rest/v3/
- **React Components**: https://atlaskit.atlassian.com/

## Pricing for Marketplace

- **Free tier**: No cost to publish
- **Paid tier**: Set your price
- **Revenue share**: Atlassian takes 30%
- **Payout**: Monthly to registered vendor

## Next Steps

1. Clone the generated project
2. Customize styling to match your brand
3. Test with real Jira instance
4. Deploy to Marketplace
5. Users install from: Settings → Find new apps

For questions, contact Atlassian Developer support.
