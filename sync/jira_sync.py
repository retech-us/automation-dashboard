"""
Jira Synchronization Engine for Automation Dashboard
Handles two-way sync between test scenarios and Jira issues
"""

import logging
import base64
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import urllib.request
import urllib.error

from database.models import db_manager
from database.repositories import RepositoryFactory

logger = logging.getLogger(__name__)


class JiraClient:
    """Jira API client for test case synchronization"""

    def __init__(self, jira_base_url: str, email: str, api_token: str):
        """Initialize Jira client with credentials"""
        self.base_url = jira_base_url.rstrip('/')
        self.email = email
        self.api_token = api_token
        self.session_counter = 0

    def _make_request(self, method: str, endpoint: str, payload: Optional[Dict] = None) -> Tuple[int, Dict]:
        """Make HTTP request to Jira API"""
        url = f"{self.base_url}/rest/api/3{endpoint}"
        credentials = f"{self.email}:{self.api_token}"
        encoded = base64.b64encode(credentials.encode()).decode()

        headers = {
            'Authorization': f'Basic {encoded}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        try:
            if method in ['POST', 'PUT']:
                data = json.dumps(payload).encode('utf-8') if payload else None
                req = urllib.request.Request(url, data=data, headers=headers, method=method)
            else:
                req = urllib.request.Request(url, headers=headers, method=method)

            with urllib.request.urlopen(req, timeout=10) as response:
                body = response.read().decode('utf-8')
                result = json.loads(body) if body else {}
                logger.debug(f"{method} {endpoint} → {response.status}")
                return response.status, result
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            try:
                error_data = json.loads(error_body)
            except:
                error_data = {"error": error_body}
            logger.error(f"{method} {endpoint} → {e.code}: {error_data}")
            return e.code, error_data
        except Exception as e:
            logger.error(f"Request failed ({method} {endpoint}): {e}")
            return 500, {"error": str(e)}

    def get_issue(self, issue_key: str) -> Optional[Dict]:
        """Get Jira issue details"""
        status, response = self._make_request('GET', f'/issues/{issue_key}')
        if status == 200:
            return response
        return None

    def create_child_issue(self, parent_key: str, scenario_data: Dict) -> Optional[Dict]:
        """Create a child issue for a test scenario"""
        try:
            parent = self.get_issue(parent_key)
            if not parent:
                logger.error(f"Parent issue {parent_key} not found")
                return None

            issue_key = parent_key.split('-')[0]  # Get project key

            # Format scenario details for Jira
            description = self._format_scenario_description(scenario_data)

            payload = {
                "fields": {
                    "project": {"key": issue_key},
                    "summary": scenario_data.get('title', 'Test Scenario')[:255],
                    "description": {
                        "version": 3,
                        "type": "doc",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": description
                                    }
                                ]
                            }
                        ]
                    },
                    "issuetype": {"name": "Story"},
                    "parent": {"key": parent_key},
                    "labels": scenario_data.get('tags', []) + ["test-scenario"]
                }
            }

            # Add custom fields if available
            custom_fields = self._get_custom_fields_mapping(issue_key)
            if custom_fields:
                payload["fields"].update(custom_fields)

            status, response = self._make_request('POST', '/issues', payload)

            if status == 201:
                child_key = response.get('key')
                logger.info(f"✓ Created child issue {child_key} for {parent_key}")
                return {
                    "key": child_key,
                    "url": f"{self.base_url}/browse/{child_key}"
                }
            else:
                logger.error(f"Failed to create child issue: {response}")
                return None

        except Exception as e:
            logger.error(f"Error creating child issue: {e}")
            return None

    def update_child_issue(self, child_key: str, scenario_data: Dict) -> bool:
        """Update child issue with scenario changes"""
        try:
            description = self._format_scenario_description(scenario_data)

            payload = {
                "fields": {
                    "summary": scenario_data.get('title', 'Test Scenario')[:255],
                    "description": {
                        "version": 3,
                        "type": "doc",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": description
                                    }
                                ]
                            }
                        ]
                    }
                }
            }

            status, response = self._make_request('PUT', f'/issues/{child_key}', payload)

            if status == 204:
                logger.info(f"✓ Updated child issue {child_key}")
                return True
            else:
                logger.error(f"Failed to update {child_key}: {response}")
                return False

        except Exception as e:
            logger.error(f"Error updating child issue: {e}")
            return False

    def add_comment(self, issue_key: str, comment_text: str) -> bool:
        """Add comment to Jira issue"""
        try:
            payload = {
                "body": {
                    "version": 3,
                    "type": "doc",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": comment_text
                                }
                            ]
                        }
                    ]
                }
            }

            status, response = self._make_request('POST', f'/issues/{issue_key}/comments', payload)

            if status == 201:
                logger.info(f"✓ Added comment to {issue_key}")
                return True
            else:
                logger.error(f"Failed to add comment: {response}")
                return False

        except Exception as e:
            logger.error(f"Error adding comment: {e}")
            return False

    def transition_issue(self, issue_key: str, transition_name: str) -> bool:
        """Transition issue to new status"""
        try:
            # Get available transitions
            status, transitions_data = self._make_request('GET', f'/issues/{issue_key}/transitions')

            if status != 200:
                logger.error(f"Failed to get transitions for {issue_key}")
                return False

            # Find matching transition
            transitions = transitions_data.get('transitions', [])
            transition = next((t for t in transitions if t['name'].lower() == transition_name.lower()), None)

            if not transition:
                logger.warning(f"Transition '{transition_name}' not found for {issue_key}")
                return False

            payload = {
                "transition": {"id": transition['id']}
            }

            status, response = self._make_request('POST', f'/issues/{issue_key}/transitions', payload)

            if status == 204:
                logger.info(f"✓ Transitioned {issue_key} to {transition_name}")
                return True
            else:
                logger.error(f"Failed to transition {issue_key}: {response}")
                return False

        except Exception as e:
            logger.error(f"Error transitioning issue: {e}")
            return False

    def _format_scenario_description(self, scenario_data: Dict) -> str:
        """Format scenario data as Jira description"""
        lines = []

        # Title
        lines.append(f"*Scenario:* {scenario_data.get('title', 'N/A')}")
        lines.append("")

        # Type and Priority
        lines.append(f"*Type:* {scenario_data.get('scenario_type', 'N/A')}")
        if scenario_data.get('priority'):
            lines.append(f"*Priority:* {scenario_data.get('priority')}")
        lines.append("")

        # Preconditions
        preconditions = scenario_data.get('preconditions', [])
        if preconditions:
            lines.append("*Preconditions:*")
            for i, condition in enumerate(preconditions, 1):
                lines.append(f"  {i}. {condition}")
            lines.append("")

        # Steps
        steps = scenario_data.get('steps', [])
        if steps:
            lines.append("*Steps:*")
            for step in steps:
                if isinstance(step, dict):
                    step_num = step.get('step', '?')
                    action = step.get('action', 'N/A')
                    lines.append(f"  {step_num}. {action}")
                else:
                    lines.append(f"  • {step}")
            lines.append("")

        # Expected Result
        if scenario_data.get('expected_result'):
            lines.append(f"*Expected Result:* {scenario_data.get('expected_result')}")
            lines.append("")

        # Automation Hint
        if scenario_data.get('automation_hint'):
            lines.append(f"*Automation:* {scenario_data.get('automation_hint')}")
            lines.append("")

        # Tags
        tags = scenario_data.get('tags', [])
        if tags:
            lines.append(f"*Tags:* {', '.join(tags)}")

        return "\n".join(lines)

    def _get_custom_fields_mapping(self, project_key: str) -> Dict:
        """Get custom fields mapping for project (placeholder)"""
        # TODO: Implement custom field resolution from ProjectSettings
        return {}


class SyncEngine:
    """Main synchronization engine for scenarios and Jira"""

    def __init__(self):
        """Initialize sync engine"""
        self.db_manager = db_manager

    def _get_repositories(self):
        """Get repository factory"""
        db_session = self.db_manager.get_session()
        return RepositoryFactory(db_session), db_session

    def sync_scenario_to_jira(self, scenario_id, jira_base_url: str,
                             jira_email: str, jira_token: str) -> Tuple[bool, Optional[str]]:
        """Sync a scenario to Jira as child issue"""
        try:
            repos, db_session = self._get_repositories()
            scenario_repo = repos.get_scenario_repo()
            sync_repo = repos.get_sync_repo()

            # Get scenario
            scenario = scenario_repo.get_scenario(scenario_id)
            if not scenario:
                return False, "Scenario not found"

            # Check if already synced
            if scenario.jira_child_issue_key:
                logger.warning(f"Scenario {scenario_id} already synced to {scenario.jira_child_issue_key}")
                return True, scenario.jira_child_issue_key

            # Initialize Jira client
            client = JiraClient(jira_base_url, jira_email, jira_token)

            # Prepare scenario data
            scenario_dict = {
                'title': scenario.title,
                'scenario_type': scenario.scenario_type,
                'priority': scenario.priority,
                'preconditions': scenario.preconditions,
                'steps': scenario.steps,
                'expected_result': scenario.expected_result,
                'automation_hint': scenario.automation_hint,
                'tags': scenario.tags or []
            }

            # Create child issue
            result = client.create_child_issue(scenario.jira_issue_key, scenario_dict)

            if result:
                child_key = result['key']
                child_url = result['url']

                # Update scenario with Jira details
                scenario_repo.update_scenario_sync_status(
                    scenario_id,
                    'synced',
                    child_key,
                    child_url
                )

                # Record sync
                sync_repo.record_sync(
                    scenario_id=scenario_id,
                    sync_direction='to_jira',
                    sync_type='create',
                    new_state={'jira_child_issue_key': child_key},
                    sync_status='success',
                    synced_by='sync-engine'
                )

                db_session.close()
                logger.info(f"✓ Synced scenario {scenario_id} to {child_key}")
                return True, child_key
            else:
                # Record failure
                sync_repo.record_sync(
                    scenario_id=scenario_id,
                    sync_direction='to_jira',
                    sync_type='create',
                    sync_status='failed',
                    error_message='Failed to create child issue',
                    synced_by='sync-engine'
                )
                db_session.close()
                return False, "Failed to create child issue"

        except Exception as e:
            logger.error(f"Error syncing scenario: {e}")
            return False, str(e)

    def sync_batch_scenarios(self, scenario_ids: List, jira_base_url: str,
                            jira_email: str, jira_token: str) -> Dict:
        """Sync multiple scenarios to Jira"""
        results = {
            'total': len(scenario_ids),
            'successful': 0,
            'failed': 0,
            'synced_issues': []
        }

        for scenario_id in scenario_ids:
            success, child_key = self.sync_scenario_to_jira(
                scenario_id, jira_base_url, jira_email, jira_token
            )

            if success:
                results['successful'] += 1
                results['synced_issues'].append(child_key)
            else:
                results['failed'] += 1
                logger.error(f"Failed to sync {scenario_id}: {child_key}")

        logger.info(f"Batch sync complete: {results['successful']}/{results['total']} successful")
        return results

    def sync_pending_scenarios(self, jira_base_url: str, jira_email: str,
                              jira_token: str, limit: int = 50) -> Dict:
        """Sync all pending scenarios to Jira"""
        try:
            repos, db_session = self._get_repositories()
            scenario_repo = repos.get_scenario_repo()

            # Get pending scenarios
            pending = scenario_repo.list_pending_scenarios(limit)
            scenario_ids = [s.scenario_id for s in pending]

            db_session.close()

            if not scenario_ids:
                logger.info("No pending scenarios to sync")
                return {'total': 0, 'successful': 0, 'failed': 0}

            logger.info(f"Syncing {len(scenario_ids)} pending scenarios...")
            return self.sync_batch_scenarios(scenario_ids, jira_base_url, jira_email, jira_token)

        except Exception as e:
            logger.error(f"Error in sync pending: {e}")
            return {'total': 0, 'successful': 0, 'failed': 0, 'error': str(e)}

    def handle_jira_webhook(self, webhook_data: Dict) -> bool:
        """Handle incoming Jira webhook (for future two-way sync)"""
        try:
            event_type = webhook_data.get('webhookEvent')
            issue = webhook_data.get('issue', {})
            issue_key = issue.get('key')

            logger.info(f"Webhook event: {event_type} for {issue_key}")

            # TODO: Implement webhook handling
            # - Update scenario if child issue changed
            # - Sync status changes back to dashboard
            # - Handle deletions

            return True
        except Exception as e:
            logger.error(f"Error handling webhook: {e}")
            return False

    def update_scenario_from_jira(self, scenario_id, jira_base_url: str,
                                 jira_email: str, jira_token: str) -> bool:
        """Update scenario based on child issue changes (from_jira sync)"""
        try:
            repos, db_session = self._get_repositories()
            scenario_repo = repos.get_scenario_repo()
            sync_repo = repos.get_sync_repo()

            scenario = scenario_repo.get_scenario(scenario_id)
            if not scenario or not scenario.jira_child_issue_key:
                return False

            client = JiraClient(jira_base_url, jira_email, jira_token)
            child_issue = client.get_issue(scenario.jira_child_issue_key)

            if not child_issue:
                return False

            # Extract updated fields from Jira
            fields = child_issue.get('fields', {})

            updates = {
                'title': fields.get('summary', scenario.title),
                'expected_result': fields.get('description', {}).get('content', [{}])[0].get('content', [{}])[0].get('text', ''),
            }

            # Update scenario
            scenario_repo.update_scenario(scenario_id, updates)

            # Record sync
            sync_repo.record_sync(
                scenario_id=scenario_id,
                sync_direction='from_jira',
                sync_type='update',
                previous_state={'title': scenario.title},
                new_state=updates,
                sync_status='success',
                synced_by='sync-engine'
            )

            db_session.close()
            logger.info(f"✓ Updated scenario {scenario_id} from Jira")
            return True

        except Exception as e:
            logger.error(f"Error updating scenario from Jira: {e}")
            return False

    def get_sync_conflicts(self) -> List[Dict]:
        """Get scenarios with conflicting changes (dashboard vs Jira)"""
        # TODO: Implement conflict detection
        return []

    def resolve_conflicts(self, conflict_resolution_strategy: str = 'dashboard_wins') -> int:
        """Resolve sync conflicts"""
        # TODO: Implement conflict resolution (dashboard_wins, jira_wins, manual)
        return 0


# Global sync engine
sync_engine = SyncEngine()
