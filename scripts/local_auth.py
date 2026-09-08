"""
Local Authentication & Test Passkeys
For development and testing purposes only
"""

import os
import logging

logger = logging.getLogger(__name__)

# Test passkeys for local development
TEST_PASSKEYS = {
    'test': {
        'name': 'Test Passkey',
        'description': 'For local development and testing',
        'level': 'full',
        'environment': 'development'
    },
    'demo': {
        'name': 'Demo Passkey',
        'description': 'For demo/presentation purposes',
        'level': 'read-only',
        'environment': 'development'
    },
    'ci-test': {
        'name': 'CI Test Passkey',
        'description': 'For CI/CD testing',
        'level': 'full',
        'environment': 'ci'
    }
}


class LocalAuthManager:
    """Manages local authentication for development"""

    def __init__(self):
        self.is_development = os.getenv('ENVIRONMENT', 'development') == 'development'
        self.passkey = os.getenv('LOCAL_PASSKEY', 'test')

    def validate_passkey(self, passkey: str) -> bool:
        """
        Validate a test passkey (development only).

        Args:
            passkey: The passkey to validate

        Returns:
            True if valid, False otherwise
        """
        if not self.is_development:
            logger.warning("Passkey validation only available in development mode")
            return False

        if passkey in TEST_PASSKEYS:
            logger.info(f"✓ Passkey validated: {TEST_PASSKEYS[passkey]['name']}")
            return True

        logger.warning(f"✗ Invalid passkey: {passkey}")
        return False

    def get_test_credentials(self) -> dict:
        """
        Get mock credentials for testing without real API keys.

        Returns:
            Dictionary with test credentials
        """
        if not self.is_development:
            raise ValueError("Test credentials only available in development")

        return {
            'jira_base_url': 'https://test-domain.atlassian.net',
            'jira_user_email': 'test@example.com',
            'jira_api_token': 'test-jira-token-12345',
            'anthropic_api_key': 'sk-ant-test-key-12345',
            'environment': 'test',
            'mode': 'local',
            'passkey': 'test'
        }

    def get_mock_jira_response(self, issue_count: int = 5) -> dict:
        """
        Get mock Jira API response for testing.

        Args:
            issue_count: Number of mock issues to generate

        Returns:
            Mock Jira API response
        """
        issues = []
        for i in range(1, issue_count + 1):
            issues.append({
                'key': f'TEST-{100 + i}',
                'summary': f'Test Issue {i}: Sample Requirement',
                'description': f'This is a test issue for local development.\n\nAC1: First acceptance criterion\nAC2: Second acceptance criterion',
                'fields': {
                    'issuetype': {'name': 'Story' if i % 2 == 0 else 'Task'},
                    'status': {'name': 'In Progress' if i % 3 == 0 else 'To Do'},
                    'attachment': [],
                    'customfield_10014': None
                }
            })

        return {
            'expand': 'names,schema',
            'startAt': 0,
            'maxResults': issue_count,
            'total': issue_count,
            'issues': issues
        }

    def get_mock_claude_response(self, issue_key: str = 'TEST-101') -> dict:
        """
        Get mock Claude API response for testing.

        Args:
            issue_key: Jira issue key

        Returns:
            Mock Claude API response with BDD scenarios
        """
        return {
            'id': 'msg-test-12345',
            'type': 'message',
            'role': 'assistant',
            'content': [
                {
                    'type': 'text',
                    'text': '''[
  {
    "id": "SC-001",
    "title": "Valid test scenario for positive case",
    "type": "positive",
    "category": "functional",
    "priority": "P1",
    "preconditions": [
      "Given system is in test mode",
      "And test data is available"
    ],
    "steps": [
      {
        "stepNumber": 1,
        "action": "When test action is performed",
        "expectedResult": "System responds correctly"
      },
      {
        "stepNumber": 2,
        "action": "Then expected result appears",
        "expectedResult": "Test passes"
      }
    ],
    "expectedResult": "All test assertions pass",
    "automationHint": "Use test framework assertions",
    "tags": ["@test", "@local", "@positive"],
    "coverage": ["AC1"]
  },
  {
    "id": "SC-002",
    "title": "Invalid input is rejected",
    "type": "negative",
    "category": "validation",
    "priority": "P2",
    "preconditions": [
      "Given test environment is active"
    ],
    "steps": [
      {
        "stepNumber": 1,
        "action": "When invalid data is submitted",
        "expectedResult": "Validation error occurs"
      }
    ],
    "expectedResult": "Error message displayed",
    "automationHint": "Verify error state",
    "tags": ["@test", "@negative"],
    "coverage": ["AC1"]
  }
]'''
                }
            ],
            'model': 'claude-3-5-sonnet-20241022',
            'stop_reason': 'end_turn',
            'usage': {
                'input_tokens': 500,
                'output_tokens': 300
            }
        }

    def print_passkey_info(self):
        """Print available test passkeys and credentials"""
        if not self.is_development:
            logger.warning("Passkey information only available in development mode")
            return

        logger.info("=" * 70)
        logger.info("LOCAL TESTING - TEST PASSKEYS & CREDENTIALS")
        logger.info("=" * 70)
        logger.info("")
        logger.info("Available Test Passkeys:")
        logger.info("-" * 70)

        for key, info in TEST_PASSKEYS.items():
            logger.info(f"\n  Passkey: {key}")
            logger.info(f"  Name: {info['name']}")
            logger.info(f"  Description: {info['description']}")
            logger.info(f"  Level: {info['level']}")
            logger.info(f"  Environment: {info['environment']}")

        logger.info("\n" + "-" * 70)
        logger.info("\nUsage:")
        logger.info("  export LOCAL_PASSKEY='test'")
        logger.info("  python3 scripts/generate-test-cases.py")
        logger.info("\nTest Credentials (Development Only):")
        logger.info("-" * 70)

        creds = self.get_test_credentials()
        for key, value in creds.items():
            logger.info(f"  {key}: {value}")

        logger.info("\n" + "=" * 70)


# Global instance
_auth_manager = None


def get_auth_manager() -> LocalAuthManager:
    """Get or create the local auth manager"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = LocalAuthManager()
    return _auth_manager


def use_local_testing() -> bool:
    """Check if local testing mode is enabled"""
    return os.getenv('ENVIRONMENT', 'development') == 'development'


def validate_local_passkey(passkey: str) -> bool:
    """Validate a local test passkey"""
    manager = get_auth_manager()
    return manager.validate_passkey(passkey)


def get_mock_credentials() -> dict:
    """Get mock credentials for testing"""
    manager = get_auth_manager()
    return manager.get_test_credentials()


def print_local_auth_info():
    """Print local authentication information"""
    manager = get_auth_manager()
    manager.print_passkey_info()
