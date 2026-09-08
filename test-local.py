#!/usr/bin/env python3
"""
Local Testing Tool - Test Dashboard with Mock Data
Uses test passkey 'test' for local development

Usage:
    python3 test-local.py
    python3 test-local.py --generate-test-cases
    python3 test-local.py --passkey demo
    python3 test-local.py --help
"""

import os
import json
import sys
import logging
import argparse
from datetime import datetime

# Add scripts to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from local_auth import (
    LocalAuthManager,
    get_auth_manager,
    TEST_PASSKEYS,
    use_local_testing
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LocalTestingTool:
    """Tool for local testing with mock data"""

    def __init__(self, passkey: str = 'test'):
        self.auth = get_auth_manager()
        self.passkey = passkey
        self.is_valid = self.auth.validate_passkey(passkey)

    def run(self):
        """Run local testing mode"""
        if not self.is_valid:
            logger.error(f"Invalid passkey: {self.passkey}")
            self.list_passkeys()
            return False

        logger.info("=" * 70)
        logger.info("LOCAL TESTING MODE - Automation Dashboard")
        logger.info("=" * 70)
        logger.info(f"\n✓ Passkey: {self.passkey}")
        logger.info(f"✓ Level: {TEST_PASSKEYS[self.passkey]['level']}")
        logger.info(f"✓ Purpose: {TEST_PASSKEYS[self.passkey]['description']}")
        logger.info("")

        return True

    def generate_mock_jira_data(self, count: int = 5) -> bool:
        """Generate mock Jira data for testing"""
        logger.info(f"Generating {count} mock Jira issues...")

        mock_data = self.auth.get_mock_jira_response(count)

        # Add metadata
        mock_data['status'] = 'mock'
        mock_data['lastUpdated'] = datetime.now().isoformat()
        mock_data['source'] = 'local_testing'
        mock_data['passkey'] = self.passkey

        # Save to data/jira.json
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(data_dir, exist_ok=True)

        output_file = os.path.join(data_dir, 'jira.json')
        try:
            with open(output_file, 'w') as f:
                json.dump(mock_data, f, indent=2)
            logger.info(f"✓ Mock data saved to: {output_file}")
            logger.info(f"✓ {count} test issues created")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to save mock data: {e}")
            return False

    def generate_mock_test_cases(self) -> bool:
        """Generate mock test cases for testing"""
        logger.info("Generating mock test cases...")

        mock_response = self.auth.get_mock_claude_response()

        # Parse the JSON from response
        try:
            import json as json_module
            scenarios_text = mock_response['content'][0]['text']
            scenarios = json_module.loads(scenarios_text)

            # Wrap in test cases structure
            test_cases_data = {
                'timestamp': datetime.now().isoformat(),
                'model': 'claude-3-5-sonnet-20241022',
                'source': 'local_testing',
                'passkey': self.passkey,
                'testCases': [
                    {
                        'issueKey': 'TEST-101',
                        'summary': 'Test Issue 1: Sample Requirement',
                        'scenarios': scenarios,
                        'generatedAt': datetime.now().isoformat()
                    }
                ],
                'summary': {
                    'totalIssuesProcessed': 1,
                    'successfulGenerations': 1,
                    'failedGenerations': 0,
                    'totalScenarios': len(scenarios),
                    'mode': 'mock'
                }
            }

            # Save to data/test-cases.json
            data_dir = os.path.join(os.path.dirname(__file__), 'data')
            os.makedirs(data_dir, exist_ok=True)

            output_file = os.path.join(data_dir, 'test-cases.json')
            with open(output_file, 'w') as f:
                json.dump(test_cases_data, f, indent=2)

            logger.info(f"✓ Mock test cases saved to: {output_file}")
            logger.info(f"✓ {len(scenarios)} BDD scenarios created")
            return True

        except Exception as e:
            logger.error(f"✗ Failed to generate mock test cases: {e}")
            return False

    def show_credentials(self):
        """Display test credentials"""
        logger.info("\nTest Credentials (Development Only):")
        logger.info("-" * 70)

        creds = self.auth.get_test_credentials()
        for key, value in creds.items():
            logger.info(f"  {key}: {value}")

        logger.info("-" * 70)

    def show_startup_info(self):
        """Show how to start local server"""
        logger.info("\nNext Steps:")
        logger.info("-" * 70)
        logger.info("1. Start local server:")
        logger.info("   $ python3 server.py")
        logger.info("")
        logger.info("2. Open dashboard:")
        logger.info("   $ open http://localhost:6060")
        logger.info("")
        logger.info("3. You'll see mock data for local testing!")
        logger.info("-" * 70)

    @staticmethod
    def list_passkeys():
        """List available passkeys"""
        logger.info("\nAvailable Test Passkeys:")
        logger.info("-" * 70)

        for key, info in TEST_PASSKEYS.items():
            logger.info(f"\n  {key}")
            logger.info(f"    {info['name']}")
            logger.info(f"    {info['description']}")

        logger.info("\n" + "-" * 70)
        logger.info("\nUsage:")
        logger.info("  python3 test-local.py --passkey test")
        logger.info("  python3 test-local.py --passkey demo")
        logger.info("  python3 test-local.py --generate-test-cases")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Local Testing Tool for Automation Dashboard',
        epilog='Examples:\n  python3 test-local.py\n  python3 test-local.py --generate-test-cases\n  python3 test-local.py --passkey demo',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--passkey',
        default='test',
        help='Test passkey to use (default: test)'
    )
    parser.add_argument(
        '--generate-test-cases',
        action='store_true',
        help='Generate mock test cases'
    )
    parser.add_argument(
        '--issue-count',
        type=int,
        default=5,
        help='Number of mock issues to generate (default: 5)'
    )
    parser.add_argument(
        '--list-passkeys',
        action='store_true',
        help='List available test passkeys'
    )

    args = parser.parse_args()

    if args.list_passkeys:
        LocalTestingTool.list_passkeys()
        return 0

    # Create testing tool
    tool = LocalTestingTool(args.passkey)

    if not tool.run():
        return 1

    # Generate mock Jira data
    if not tool.generate_mock_jira_data(args.issue_count):
        return 1

    # Generate mock test cases if requested
    if args.generate_test_cases:
        if not tool.generate_mock_test_cases():
            return 1

    # Show credentials and next steps
    tool.show_credentials()
    tool.show_startup_info()

    logger.info("\n✓ Local testing setup complete!")
    logger.info("✓ Ready to develop on localhost:6060")
    return 0


if __name__ == '__main__':
    sys.exit(main())
