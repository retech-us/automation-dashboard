"""
Dry-Run API Endpoints
Provides endpoints for testing sync without modifying Jira
"""

import json
import logging
from typing import Dict, Tuple
from sync.dry_run_mode import (
    get_dry_run_mode,
    enable_dry_run,
    disable_dry_run,
    is_dry_run_enabled,
    get_dry_run_preview
)
from sync.qc_counter import get_qc_counter

logger = logging.getLogger(__name__)


class DryRunAPI:
    """API endpoints for dry-run testing"""

    @staticmethod
    def enable_dry_run() -> Tuple[str, int, str]:
        """POST /api/dry-run/enable - Enable dry-run mode"""
        try:
            dry_run = enable_dry_run()
            qc_counter = get_qc_counter()
            current_qc = qc_counter.get_current_qc_number()

            return json.dumps({
                "status": "enabled",
                "mode": "DRY-RUN",
                "message": "Dry-run mode enabled - No changes will be made to Jira",
                "current_qc_number": current_qc,
                "warning": "⚠️ All sync operations will be simulated only"
            }), 200, 'application/json'

        except Exception as e:
            logger.error(f"Error enabling dry-run: {e}")
            return json.dumps({"error": str(e)}), 500, 'application/json'

    @staticmethod
    def disable_dry_run() -> Tuple[str, int, str]:
        """POST /api/dry-run/disable - Disable dry-run mode"""
        try:
            disable_dry_run()

            return json.dumps({
                "status": "disabled",
                "mode": "LIVE",
                "message": "Dry-run mode disabled - Back to live Jira sync"
            }), 200, 'application/json'

        except Exception as e:
            logger.error(f"Error disabling dry-run: {e}")
            return json.dumps({"error": str(e)}), 500, 'application/json'

    @staticmethod
    def get_status() -> Tuple[str, int, str]:
        """GET /api/dry-run/status - Get dry-run mode status"""
        try:
            enabled = is_dry_run_enabled()
            qc_counter = get_qc_counter()
            current_qc = qc_counter.get_current_qc_number()

            return json.dumps({
                "dry_run_enabled": enabled,
                "mode": "DRY-RUN" if enabled else "LIVE",
                "current_qc_number": current_qc,
                "message": "Dry-run mode is " + ("ENABLED" if enabled else "DISABLED")
            }), 200, 'application/json'

        except Exception as e:
            logger.error(f"Error getting dry-run status: {e}")
            return json.dumps({"error": str(e)}), 500, 'application/json'

    @staticmethod
    def get_preview() -> Tuple[str, int, str]:
        """GET /api/dry-run/preview - Get preview of changes that would happen"""
        try:
            if not is_dry_run_enabled():
                return json.dumps({
                    "error": "Dry-run mode is not enabled",
                    "message": "Enable dry-run mode first: POST /api/dry-run/enable"
                }), 400, 'application/json'

            preview = get_dry_run_preview()

            return json.dumps(preview), 200, 'application/json'

        except Exception as e:
            logger.error(f"Error getting preview: {e}")
            return json.dumps({"error": str(e)}), 500, 'application/json'

    @staticmethod
    def test_sync(body: str) -> Tuple[str, int, str]:
        """POST /api/dry-run/test-sync - Test sync without actually doing it"""
        try:
            if not is_dry_run_enabled():
                return json.dumps({
                    "error": "Dry-run mode is not enabled",
                    "message": "Enable first: POST /api/dry-run/enable"
                }), 400, 'application/json'

            request_data = json.loads(body) if body else {}

            # Simulate what WOULD happen
            dry_run = get_dry_run_mode()
            qc_counter = get_qc_counter()

            # Log the scenario
            scenario_data = request_data.get('scenario_data', {})
            parent_key = request_data.get('parent_issue_key', 'REB3-?')

            # Simulate creating issue
            next_qc = qc_counter.get_current_qc_number() + 1
            new_issue_key = f"REB3-{20000 + next_qc}"

            dry_run.log_action("increment_counter", {
                "current": qc_counter.get_current_qc_number(),
                "next": next_qc,
                "new_qc_number": f"QC-{next_qc}"
            })

            dry_run.log_action("create_issue", {
                "key": new_issue_key,
                "summary": f"[TC: QC-{next_qc}] {scenario_data.get('title', 'Test Case')}",
                "issue_type": "Test Case",
                "project": "REB3"
            })

            dry_run.log_action("link_issues", {
                "from_key": parent_key,
                "to_key": new_issue_key,
                "link_type": "relates to"
            })

            dry_run.log_action("update_custom_field", {
                "issue_key": parent_key,
                "field_name": "Inhouse TC Generator",
                "action": "append",
                "content": f"• [QC-{next_qc}] [{new_issue_key}] - synced"
            })

            preview = get_dry_run_preview()

            return json.dumps({
                "status": "simulated",
                "message": "Sync operation simulated successfully (no changes made)",
                "preview": preview,
                "summary": {
                    "scenario_title": scenario_data.get('title', 'N/A'),
                    "would_create_issue": new_issue_key,
                    "would_use_qc_number": f"QC-{next_qc}",
                    "would_link_to": parent_key,
                    "would_update_custom_field": True
                }
            }), 200, 'application/json'

        except Exception as e:
            logger.error(f"Error in test sync: {e}")
            return json.dumps({"error": str(e)}), 500, 'application/json'

    @staticmethod
    def reset() -> Tuple[str, int, str]:
        """POST /api/dry-run/reset - Reset dry-run results"""
        try:
            dry_run = get_dry_run_mode()
            dry_run.reset()

            return json.dumps({
                "status": "reset",
                "message": "Dry-run results cleared",
                "mode": "DRY-RUN" if is_dry_run_enabled() else "LIVE"
            }), 200, 'application/json'

        except Exception as e:
            logger.error(f"Error resetting dry-run: {e}")
            return json.dumps({"error": str(e)}), 500, 'application/json'
