#!/usr/bin/env python3
"""Test which Jira API endpoints are accessible"""

import os
import base64
import urllib.request
import urllib.error
import json

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Get credentials
base_url = os.getenv('JIRA_BASE_URL', '').rstrip('/')
email = os.getenv('JIRA_USER_EMAIL', '')
token = os.getenv('JIRA_API_TOKEN', '')

if not all([base_url, email, token]):
    print("❌ Missing Jira credentials in .env")
    print(f"  JIRA_BASE_URL: {base_url or 'NOT SET'}")
    print(f"  JIRA_USER_EMAIL: {email or 'NOT SET'}")
    print(f"  JIRA_API_TOKEN: {token or 'NOT SET'}")
    exit(1)

print(f"Testing Jira endpoints for: {base_url}\n")

# Create auth header
credentials = f"{email}:{token}"
encoded = base64.b64encode(credentials.encode()).decode()
headers = {
    "Authorization": f"Basic {encoded}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# Test endpoints
endpoints = [
    ("GET", "/rest/api/3/myself", None, "User info (v3)"),
    ("GET", "/rest/api/2/myself", None, "User info (v2)"),
    ("GET", "/rest/api/3/search?jql=type%20in%20(Story,Task)&maxResults=1", None, "Search (v3)"),
    ("GET", "/rest/api/2/search?jql=type%20in%20(Story,Task)&maxResults=1", None, "Search (v2)"),
    ("GET", "/rest/api/3/projects", None, "List projects (v3)"),
    ("GET", "/rest/api/2/projects", None, "List projects (v2)"),
    ("GET", "/rest/api/3/issues", None, "List issues (v3)"),
    ("GET", "/rest/api/2/issues", None, "List issues (v2)"),
]

for method, endpoint, data, description in endpoints:
    url = f"{base_url}{endpoint}"
    try:
        req = urllib.request.Request(url, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=5) as response:
            print(f"✅ {description:30} {response.status} OK")
            try:
                body = json.loads(response.read().decode('utf-8'))
                if isinstance(body, dict):
                    keys = list(body.keys())[:3]
                    print(f"   Response keys: {keys}\n")
            except:
                pass
    except urllib.error.HTTPError as e:
        print(f"❌ {description:30} {e.code} {e.reason}")
        try:
            error_msg = e.read().decode('utf-8')
            print(f"   Error: {error_msg[:100]}\n")
        except:
            print()
    except Exception as e:
        print(f"⚠️  {description:30} Error: {str(e)[:50]}\n")

print("\nDiagnostics complete!")
