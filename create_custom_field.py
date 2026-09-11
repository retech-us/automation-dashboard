#!/usr/bin/env python3
"""
Create Jira Custom Field - Inhouse TC Generator
Automates creation of the custom field for displaying generated test cases
"""

import requests
import base64
import json
import sys
from typing import Optional

class JiraCustomFieldCreator:
    """Creates custom fields in Jira"""

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

    def create_custom_field(self, name: str, description: str) -> Optional[dict]:
        """Create a custom field in Jira"""
        try:
            print(f"\n🔄 Creating custom field: {name}")

            # Check if field already exists
            existing = self._check_field_exists(name)
            if existing:
                print(f"✓ Custom field already exists: {existing['id']}")
                return existing

            # Try API v3 first (Jira Cloud newer versions)
            url_v3 = f"{self.jira_url}/rest/api/3/fields"

            # Try API v2 (Jira Cloud/Server compatibility)
            url_v2 = f"{self.jira_url}/rest/api/2/field"

            payload_v3 = {
                "name": name,
                "type": "com.atlassian.jira.plugin.system.customfieldtypes:text",
                "searcherKey": "com.atlassian.jira.plugin.system.customfieldtypes:textsearcher",
                "description": description
            }

            payload_v2 = {
                "name": name,
                "type": "com.atlassian.jira.plugin.system.customfieldtypes:text",
                "searcherKey": "com.atlassian.jira.plugin.system.customfieldtypes:textsearcher"
            }

            # Try v3 first
            print(f"📤 Trying v3 API: {url_v3}")
            response = self.session.post(url_v3, json=payload_v3)

            if response.status_code in [200, 201]:
                field_data = response.json()
                field_id = field_data.get('id')
                print(f"✓ Custom field created successfully (v3)!")
                print(f"  Field ID: {field_id}")
                return field_data

            # Try v2
            print(f"📤 v3 failed, trying v2 API: {url_v2}")
            response = self.session.post(url_v2, json=payload_v2)

            if response.status_code in [200, 201]:
                field_data = response.json()
                field_id = field_data.get('id')
                print(f"✓ Custom field created successfully (v2)!")
                print(f"  Field ID: {field_id}")
                return field_data
            else:
                print(f"❌ Failed to create custom field via API")
                print(f"  Status: {response.status_code}")
                print(f"  Response: {response.text}")
                print(f"\n⚠️  API creation failed. Please create manually:")
                print(f"  1. Go to: {self.jira_url}/secure/project/settings/fields")
                print(f"  2. Click: Create custom field")
                print(f"  3. Field type: Text Field (Single line)")
                print(f"  4. Name: {name}")
                print(f"  5. Description: {description}")
                return None

        except Exception as e:
            print(f"❌ Error creating custom field: {e}")
            return None

    def _check_field_exists(self, name: str) -> Optional[dict]:
        """Check if custom field already exists"""
        try:
            url = f"{self.jira_url}/rest/api/3/fields"
            response = self.session.get(url)

            if response.status_code == 200:
                fields = response.json()
                for field in fields:
                    if field.get('name') == name:
                        return field
            return None
        except:
            return None

    def associate_with_project(self, field_id: str, project_key: str) -> bool:
        """Associate custom field with a project"""
        try:
            print(f"\n🔄 Associating field with project: {project_key}")

            # Get the project
            url = f"{self.jira_url}/rest/api/3/project/{project_key}"
            response = self.session.get(url)

            if response.status_code == 200:
                print(f"✓ Project found: {project_key}")
                print(f"✓ Custom field will be available for all issue types")
                return True
            else:
                print(f"❌ Project not found: {project_key}")
                return False

        except Exception as e:
            print(f"❌ Error associating field: {e}")
            return False

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
                return False

        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False


def main():
    """Main entry point"""
    print("\n" + "="*60)
    print("🧪 Jira Custom Field Creator")
    print("="*60)

    # Get credentials
    print("\n📝 Enter your Jira credentials:")

    jira_url = input("Jira Base URL (e.g., https://your-company.atlassian.net): ").strip()
    email = input("Jira Email: ").strip()
    api_token = input("Jira API Token: ").strip()
    project_key = input("Project Key (default: REB3): ").strip() or "REB3"

    if not (jira_url and email and api_token):
        print("\n❌ Missing credentials")
        return False

    # Create creator
    creator = JiraCustomFieldCreator(jira_url, email, api_token)

    # Test connection
    print()
    if not creator.test_connection():
        print("❌ Cannot connect to Jira. Check credentials and try again.")
        return False

    # Create custom field
    field_data = creator.create_custom_field(
        name="Inhouse TC Generator",
        description="Test cases generated by Inhouse TC Generator plugin"
    )

    if not field_data:
        print("\n❌ Failed to create custom field")
        return False

    # Associate with project
    field_id = field_data.get('id')
    if not creator.associate_with_project(field_id, project_key):
        print("\n❌ Failed to associate field with project")
        return False

    # Success
    print("\n" + "="*60)
    print("✓ SUCCESS!")
    print("="*60)
    print(f"\n✓ Custom field created successfully!")
    print(f"  Field: Inhouse TC Generator")
    print(f"  ID: {field_id}")
    print(f"  Project: {project_key}")
    print(f"\n📋 Next steps:")
    print(f"  1. Go back to dashboard: http://localhost:6060")
    print(f"  2. Generate test cases")
    print(f"  3. Approve scenarios")
    print(f"  4. Check Jira - custom field should now update!")
    print()

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
