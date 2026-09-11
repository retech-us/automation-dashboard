#!/usr/bin/env python3
"""
Fetch All Jira Projects Available to User
Lists all projects the user has access to with their keys and details
"""

import requests
import base64
import json
import sys
from typing import List, Dict

class JiraProjectFetcher:
    """Fetches Jira projects for a user"""

    def __init__(self, jira_url: str, email: str, api_token: str):
        """Initialize with Jira credentials"""
        self.jira_url = jira_url.rstrip('/')
        self.email = email
        self.api_token = api_token
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create authenticated session"""
        session = requests.Session()
        credentials = f"{self.email}:{self.api_token}"
        encoded = base64.b64encode(credentials.encode()).decode()
        session.headers.update({
            'Authorization': f'Basic {encoded}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        return session

    def test_connection(self) -> bool:
        """Test Jira connection"""
        try:
            print("🔍 Testing Jira connection...")
            url = f"{self.jira_url}/rest/api/3/myself"
            response = self.session.get(url)

            if response.status_code == 200:
                user = response.json()
                print(f"✓ Connected to Jira")
                print(f"  User: {user.get('displayName')}")
                print(f"  Email: {user.get('emailAddress')}")
                return True
            else:
                print(f"❌ Connection failed: {response.status_code}")
                print(f"  Response: {response.text}")
                return False

        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False

    def fetch_projects(self) -> List[Dict]:
        """Fetch all projects accessible to the user"""
        try:
            print(f"\n🔄 Fetching projects...")

            # Try API v3 first
            url = f"{self.jira_url}/rest/api/3/projects"

            print(f"📤 Requesting: {url}")
            response = self.session.get(url)

            if response.status_code == 200:
                projects = response.json()
                print(f"✓ Fetched {len(projects)} projects")
                return projects
            else:
                print(f"❌ Failed to fetch projects")
                print(f"  Status: {response.status_code}")
                print(f"  Response: {response.text}")
                return []

        except Exception as e:
            print(f"❌ Error fetching projects: {e}")
            return []

    def display_projects(self, projects: List[Dict]) -> None:
        """Display projects in a nice format"""
        if not projects:
            print("\n❌ No projects found")
            return

        print("\n" + "="*80)
        print("📋 AVAILABLE JIRA PROJECTS")
        print("="*80)

        # Sort by key
        projects = sorted(projects, key=lambda x: x.get('key', ''))

        for i, project in enumerate(projects, 1):
            key = project.get('key', 'N/A')
            name = project.get('name', 'N/A')
            proj_type = project.get('projectTypeKey', 'N/A')
            lead = project.get('lead', {})
            lead_name = lead.get('displayName', 'N/A') if isinstance(lead, dict) else 'N/A'

            print(f"\n{i}. {key}")
            print(f"   Name: {name}")
            print(f"   Type: {proj_type}")
            print(f"   Lead: {lead_name}")
            print(f"   URL: {self.jira_url}/browse/{key}")

        print("\n" + "="*80)
        print(f"✓ Total projects: {len(projects)}")
        print("="*80)

    def save_projects_to_file(self, projects: List[Dict], filename: str = "jira_projects.json") -> None:
        """Save projects list to JSON file"""
        try:
            filepath = f"data/{filename}"
            with open(filepath, 'w') as f:
                json.dump({
                    "total": len(projects),
                    "projects": projects
                }, f, indent=2)
            print(f"\n✓ Projects saved to: {filepath}")
        except Exception as e:
            print(f"⚠️  Could not save to file: {e}")


def main():
    """Main entry point"""
    print("\n" + "="*80)
    print("🧪 Jira Project Fetcher")
    print("="*80)

    # Get credentials
    print("\n📝 Enter your Jira credentials:")

    jira_url = input("Jira Base URL (e.g., https://your-company.atlassian.net): ").strip()
    email = input("Jira Email: ").strip()
    api_token = input("Jira API Token: ").strip()

    if not (jira_url and email and api_token):
        print("\n❌ Missing credentials")
        return False

    # Create fetcher
    fetcher = JiraProjectFetcher(jira_url, email, api_token)

    # Test connection
    print()
    if not fetcher.test_connection():
        print("❌ Cannot connect to Jira. Check credentials and try again.")
        return False

    # Fetch projects
    projects = fetcher.fetch_projects()

    if not projects:
        print("\n❌ No projects found or API error")
        return False

    # Display projects
    fetcher.display_projects(projects)

    # Save to file
    fetcher.save_projects_to_file(projects)

    # Summary
    print("\n✅ PROJECT FETCH COMPLETE!")
    print("\n📋 Use these PROJECT KEYS for configuration:")
    project_keys = [p.get('key') for p in projects if p.get('key')]
    print(f"   {', '.join(project_keys)}")

    print("\n💡 Next steps:")
    print("   1. Note the project key(s) you want to use (e.g., REB3)")
    print("   2. Update your dashboard configuration")
    print("   3. Resume test case generation")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
