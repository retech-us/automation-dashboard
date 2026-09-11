"""
Dry-Run Mode - Test sync logic without modifying Jira
Perfect for testing without touching production data
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class DryRunMode:
    """Manages dry-run testing mode"""

    def __init__(self):
        """Initialize dry-run mode"""
        self.enabled = False
        self.test_results = []
        self.mock_responses = {}
        self.created_issues = []
        self.updated_fields = []
        self.linked_issues = []

    def enable(self):
        """Enable dry-run mode"""
        self.enabled = True
        self.test_results = []
        self.created_issues = []
        self.updated_fields = []
        self.linked_issues = []
        logger.info("✓ DRY-RUN MODE ENABLED - No changes will be made to Jira")

    def disable(self):
        """Disable dry-run mode"""
        self.enabled = False
        logger.info("✓ Dry-run mode disabled - Back to live mode")

    def is_enabled(self) -> bool:
        """Check if dry-run mode is active"""
        return self.enabled

    def log_action(self, action_type: str, details: Dict) -> None:
        """Log what WOULD happen"""
        if not self.enabled:
            return

        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "action": action_type,
            "details": details,
            "would_execute": True
        }

        self.test_results.append(log_entry)

        # Log based on action type
        if action_type == "create_issue":
            self.created_issues.append(details)
            logger.info(
                f"[DRY-RUN] Would create issue: {details.get('key', 'N/A')} - {details.get('summary', 'N/A')}"
            )

        elif action_type == "update_custom_field":
            self.updated_fields.append(details)
            logger.info(
                f"[DRY-RUN] Would update field on {details.get('issue_key', 'N/A')}"
            )

        elif action_type == "link_issues":
            self.linked_issues.append(details)
            logger.info(
                f"[DRY-RUN] Would link {details.get('from_key', 'N/A')} → {details.get('to_key', 'N/A')}"
            )

        elif action_type == "increment_counter":
            logger.info(
                f"[DRY-RUN] Would increment QC counter: {details.get('current', '?')} → {details.get('next', '?')}"
            )

    def get_preview(self) -> Dict:
        """Get preview of all changes that would happen"""
        return {
            "mode": "DRY-RUN",
            "enabled": self.enabled,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_actions": len(self.test_results),
                "issues_to_create": len(self.created_issues),
                "fields_to_update": len(self.updated_fields),
                "links_to_create": len(self.linked_issues),
            },
            "details": {
                "created_issues": self.created_issues,
                "updated_fields": self.updated_fields,
                "linked_issues": self.linked_issues,
            },
            "actions_log": self.test_results,
            "warning": "⚠️ DRY-RUN MODE: No actual changes will be made to Jira"
        }

    def mock_jira_response(self, endpoint: str, method: str = "GET") -> Dict:
        """Return mock Jira API responses"""
        if not self.enabled:
            return {}

        # Mock responses for common endpoints
        mock_responses = {
            "/rest/api/3/issues": {
                "GET": {"status": 200, "issues": []},
                "POST": {
                    "status": 201,
                    "key": f"REB3-{20000 + len(self.created_issues)}",
                    "id": f"{1000000 + len(self.created_issues)}",
                    "self": f"https://example.atlassian.net/rest/api/3/issues/{1000000 + len(self.created_issues)}"
                }
            },
            "/rest/api/3/issuelinks": {
                "POST": {"status": 201, "id": "10000"}
            }
        }

        key = f"{method} {endpoint}"
        if endpoint in mock_responses:
            response = mock_responses[endpoint].get(method, {"status": 200})
            logger.debug(f"[DRY-RUN] Mock response for {key}: {response}")
            return response

        return {"status": 200, "mock": True}

    def reset(self):
        """Reset dry-run results"""
        self.test_results = []
        self.created_issues = []
        self.updated_fields = []
        self.linked_issues = []
        logger.info("✓ Dry-run results cleared")


# Global instance
_dry_run = None


def get_dry_run_mode() -> DryRunMode:
    """Get or create global dry-run instance"""
    global _dry_run
    if _dry_run is None:
        _dry_run = DryRunMode()
    return _dry_run


def enable_dry_run():
    """Enable dry-run mode globally"""
    dry_run = get_dry_run_mode()
    dry_run.enable()
    return dry_run


def disable_dry_run():
    """Disable dry-run mode globally"""
    dry_run = get_dry_run_mode()
    dry_run.disable()
    return dry_run


def is_dry_run_enabled() -> bool:
    """Check if dry-run is enabled"""
    dry_run = get_dry_run_mode()
    return dry_run.is_enabled()


def get_dry_run_preview() -> Dict:
    """Get preview of changes"""
    dry_run = get_dry_run_mode()
    return dry_run.get_preview()
