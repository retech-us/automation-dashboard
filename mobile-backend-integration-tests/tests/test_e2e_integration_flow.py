"""
Unit and Integration Tests for Intelligent Reset End-to-End Mobile-to-Backend Flow,
Duplicate UPC Multi-Location Mapping, and Mid-Task Lifecycle Resilience (Zero Dropped Actions & Pending Item Details).
"""

import json
import unittest
from pathlib import Path
import tempfile

from core.e2e_audit_engine import (
    audit_task_execution,
    audit_app_lifecycle_resilience,
    derive_why_user_performs_action,
    StepTelemetryRecord,
    TaskAuditSummary,
    UpcLocationCluster,
    LifecycleEventAudit
)
from core.e2e_audit_report_generator import generate_e2e_audit_html_report

WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent


class TestE2EIntegrationFlow(unittest.TestCase):

    def setUp(self):
        raw_file = WORKSPACE_DIR / "raw_backend_actions_task_8601238.json"
        self.raw_items_8601238 = json.loads(raw_file.read_text(encoding="utf-8"))
        self.audit_8601238 = audit_task_execution(
            task_id=8601238,
            store_id=810,
            pog_id=86738,
            raw_items=self.raw_items_8601238,
            instance_slug="harr",
            pog_name="3 ft - ICE CREAM TOPPINGS"
        )

    def test_why_user_performs_action_explanations(self):
        """Verify clear operational context is generated for every action type."""
        why_remove = derive_why_user_performs_action("REMOVE", "040000002376", "Delisted Item", "1", 3, "2", "1", 3, "2")
        self.assertIn("Foreign/Delisted SKU", why_remove)
        self.assertIn("backroom cart", why_remove)

        why_setaside = derive_why_user_performs_action("SET_ASIDE", "011110087456", "Ice Cream Cone", "1", 1, "4", "2", 3, "1")
        self.assertIn("Cross-Bay Movement", why_setaside)
        self.assertIn("rolling cart", why_setaside)

        why_add = derive_why_user_performs_action("ADD_TO_SHELF", "011110087456", "Ice Cream Cone", "1", 1, "4", "2", 3, "1")
        self.assertIn("Target Placement", why_add)
        self.assertIn("destination", why_add)

        why_fix = derive_why_user_performs_action("FIX_IN_BAY", "041220789012", "Sprinkles", "1", 4, "1", "1", 4, "5")
        self.assertIn("Intra-Bay Alignment", why_fix)
        self.assertIn("horizontally", why_fix)

    def test_historical_audit_task_8601238_counts_and_metrics(self):
        """Verify Task #8601238 audit breakdown across all 50 raw detections and 42 actionable cards."""
        audit = self.audit_8601238
        self.assertEqual(audit.task_id, 8601238)
        self.assertEqual(audit.total_raw_db_detections, 50)
        self.assertEqual(audit.total_generated_mobile_cards, 42)
        self.assertEqual(audit.total_dropped_actions, 0)
        self.assertEqual(audit.action_counts_by_type["SET_ASIDE"], 13)
        self.assertEqual(audit.action_counts_by_type["ADD_TO_SHELF"], 13)
        self.assertEqual(audit.action_counts_by_type["FIX_IN_BAY"], 9)
        self.assertEqual(audit.action_counts_by_type["RESTOCK"], 5)
        self.assertEqual(audit.action_counts_by_type["REMOVE"], 2)

    def test_duplicate_upc_clustering_and_location_mapping(self):
        """Verify same UPCs are grouped aside into multi-location clusters with exact shelf/bay locations."""
        audit = self.audit_8601238
        self.assertGreater(len(audit.duplicate_upc_clusters), 0, "Task #8601238 must have duplicate/multi-facing UPC clusters")
        
        # Verify cluster properties
        for cluster in audit.duplicate_upc_clusters:
            self.assertGreater(cluster.total_facings, 1)
            self.assertEqual(len(cluster.locations), cluster.total_facings)
            self.assertTrue(len(cluster.unique_bays) >= 1)
            self.assertTrue(len(cluster.unique_shelves) >= 1)
            
            # Verify each occurrence has valid location info
            for loc in cluster.locations:
                self.assertIn("step_index", loc)
                self.assertIn("location_desc", loc)
                self.assertIn("action_type", loc)
                self.assertIn("source_bay", loc)

    def test_mid_task_app_refresh_resilience_and_pending_records(self):
        """Verify refresh after 5 actions: user finds 37 pending, performs 5 more, 32 still left."""
        audits = audit_app_lifecycle_resilience(
            task_id=8601238,
            step_records=self.audit_8601238.step_records,
            performed_count=5
        )
        refresh_audit = next((a for a in audits if a.event_name == "APP_PULL_TO_REFRESH"), None)
        self.assertIsNotNone(refresh_audit)

        self.assertEqual(refresh_audit.initial_mobile_actions, 42)
        self.assertEqual(refresh_audit.actions_performed_before_event, 5)
        self.assertEqual(refresh_audit.reloaded_completed_count, 5)
        self.assertEqual(refresh_audit.reloaded_pending_count, 37, "User must find exactly 37 pending actions on mobile after refresh")
        self.assertEqual(refresh_audit.reloaded_total_available, 42)
        self.assertEqual(refresh_audit.dropped_actions, 0)
        self.assertEqual(refresh_audit.phantom_duplicate_actions, 0)
        self.assertEqual(refresh_audit.mismatch_count, 0)
        self.assertTrue(refresh_audit.is_resilience_passed)

        # Continuation: user performs 5 more from the 37 pending, 32 still left
        self.assertEqual(refresh_audit.actions_performed_after_returning, 5, "User performs 5 actions from pending after returning")
        self.assertEqual(refresh_audit.final_remaining_after_performing, 32, "32 actions still left after performing 5 from 37 pending")

        # Verify itemized records — user sees exactly 37 pending cards
        self.assertEqual(len(refresh_audit.completed_records), 5)
        self.assertEqual(len(refresh_audit.pending_records), 37)
        self.assertEqual(refresh_audit.next_active_card["step_index"], 6)
        self.assertEqual(refresh_audit.pending_records[0]["step_index"], 6)
        self.assertEqual(refresh_audit.pending_records[-1]["step_index"], 42)
        self.assertTrue(bool(refresh_audit.next_active_card["product_title"]))

    def test_mid_task_user_logout_and_relogin_resilience(self):
        """Verify logout after 10 actions: user finds 32 pending, performs 5 more, 27 still left."""
        audits = audit_app_lifecycle_resilience(
            task_id=8601238,
            step_records=self.audit_8601238.step_records,
            performed_count=5
        )
        logout_audit = next((a for a in audits if a.event_name == "USER_LOGOUT_AND_RELOGIN"), None)
        self.assertIsNotNone(logout_audit)

        self.assertEqual(logout_audit.initial_mobile_actions, 42)
        self.assertEqual(logout_audit.actions_performed_before_event, 10)
        self.assertEqual(logout_audit.reloaded_completed_count, 10)
        self.assertEqual(logout_audit.reloaded_pending_count, 32, "User must find exactly 32 pending actions on mobile after logout & relogin")
        self.assertEqual(logout_audit.reloaded_total_available, 42)
        self.assertEqual(logout_audit.dropped_actions, 0)
        self.assertEqual(logout_audit.mismatch_count, 0)
        self.assertTrue(logout_audit.is_resilience_passed)

        # Continuation: user performs 5 more from the 32 pending, 27 still left
        self.assertEqual(logout_audit.actions_performed_after_returning, 5, "User performs 5 actions from pending after relogin")
        self.assertEqual(logout_audit.final_remaining_after_performing, 27, "27 actions still left after performing 5 from 32 pending")

        self.assertEqual(len(logout_audit.pending_records), 32)
        self.assertEqual(logout_audit.next_active_card["step_index"], 11)

    def test_mid_task_screen_navigation_switch_resilience(self):
        """Verify screen switch after 15 actions: user finds 27 pending, performs 5 more, 22 still left."""
        audits = audit_app_lifecycle_resilience(
            task_id=8601238,
            step_records=self.audit_8601238.step_records,
            performed_count=5
        )
        nav_audit = next((a for a in audits if a.event_name == "SCREEN_NAVIGATION_SWITCH"), None)
        self.assertIsNotNone(nav_audit)

        self.assertEqual(nav_audit.actions_performed_before_event, 15)
        self.assertEqual(nav_audit.reloaded_completed_count, 15)
        self.assertEqual(nav_audit.reloaded_pending_count, 27, "User must find exactly 27 pending actions on mobile after screen switch")
        self.assertEqual(nav_audit.reloaded_total_available, 42)
        self.assertEqual(nav_audit.dropped_actions, 0)
        self.assertTrue(nav_audit.is_resilience_passed)

        # Continuation: user performs 5 more from the 27 pending, 22 still left
        self.assertEqual(nav_audit.actions_performed_after_returning, 5, "User performs 5 actions from pending after screen switch")
        self.assertEqual(nav_audit.final_remaining_after_performing, 22, "22 actions still left after performing 5 from 27 pending")

        self.assertEqual(len(nav_audit.pending_records), 27)
        self.assertEqual(nav_audit.next_active_card["step_index"], 16)

    def test_mid_task_app_kill_and_background_resume_resilience_and_visible_cards(self):
        """Verify app kill after 20 actions: user finds 22 pending, performs all 22, 0 still left."""
        audits = audit_app_lifecycle_resilience(
            task_id=8601238,
            step_records=self.audit_8601238.step_records,
            performed_count=5
        )
        kill_audit = next((a for a in audits if a.event_name == "APP_KILL_AND_BACKGROUND_RESUME"), None)
        self.assertIsNotNone(kill_audit)

        self.assertEqual(kill_audit.actions_performed_before_event, 20)
        self.assertEqual(kill_audit.reloaded_completed_count, 20)
        self.assertEqual(kill_audit.reloaded_pending_count, 22, "User must find exactly 22 pending actions on mobile after app kill & resume")
        self.assertEqual(kill_audit.reloaded_total_available, 42)
        self.assertEqual(kill_audit.dropped_actions, 0)
        self.assertEqual(kill_audit.phantom_duplicate_actions, 0)
        self.assertTrue(kill_audit.is_resilience_passed)

        # Continuation: last lifecycle event, user performs ALL 22 remaining to complete the task
        self.assertEqual(kill_audit.actions_performed_after_returning, 22, "User performs all 22 remaining actions to finish the task")
        self.assertEqual(kill_audit.final_remaining_after_performing, 0, "0 actions left — task completion imminent")

        # Confirm next visible card after kill/resume
        self.assertEqual(kill_audit.next_active_card["step_index"], 21)
        self.assertEqual(len(kill_audit.pending_records), 22)
        for r in kill_audit.pending_records:
            self.assertIn("banner_text", r)
            self.assertIn("product_title", r)
            self.assertIn("upc", r)
            self.assertIn("movement_line", r)
            self.assertIn("why_performed", r)

    def test_task_completed_final_stage_all_actions_done(self):
        """Verify TASK_COMPLETED final row: 42/42 completed, 0 pending, 0 dropped."""
        audits = audit_app_lifecycle_resilience(
            task_id=8601238,
            step_records=self.audit_8601238.step_records,
            performed_count=5
        )
        completed_audit = next((a for a in audits if a.event_name == "TASK_COMPLETED"), None)
        self.assertIsNotNone(completed_audit, "TASK_COMPLETED stage must exist as final lifecycle row")

        self.assertEqual(completed_audit.initial_mobile_actions, 42)
        self.assertEqual(completed_audit.actions_performed_before_event, 42, "All 42 actions completed")
        self.assertEqual(completed_audit.reloaded_completed_count, 42, "42/42 actions in COMPLETED state")
        self.assertEqual(completed_audit.reloaded_pending_count, 0, "0 pending — all done")
        self.assertEqual(completed_audit.reloaded_total_available, 42)
        self.assertEqual(completed_audit.dropped_actions, 0)
        self.assertEqual(completed_audit.phantom_duplicate_actions, 0)
        self.assertEqual(completed_audit.mismatch_count, 0)
        self.assertTrue(completed_audit.is_resilience_passed)

        # Final stage: no more actions to perform
        self.assertEqual(completed_audit.actions_performed_after_returning, 0)
        self.assertEqual(completed_audit.final_remaining_after_performing, 0)
        self.assertIsNone(completed_audit.next_active_card, "No next card — all done")
        self.assertEqual(len(completed_audit.completed_records), 42)
        self.assertEqual(len(completed_audit.pending_records), 0)

    def test_historical_audit_task_27277459(self):
        """Verify Task #27277459 audit breakdown on Epsilon (397 raw DB vs 383 mobile cards)."""
        raw_file = WORKSPACE_DIR / "raw_backend_actions_task_27277459.json"
        self.assertTrue(raw_file.exists(), "raw_backend_actions_task_27277459.json must exist")

        raw_items = json.loads(raw_file.read_text(encoding="utf-8"))
        audit = audit_task_execution(
            task_id=27277459,
            store_id=30248,
            pog_id=4139874,
            raw_items=raw_items,
            instance_slug="epsilon",
            pog_name="6.00 ft - ICE CREAM TOPPINGS"
        )

        self.assertEqual(audit.task_id, 27277459)
        self.assertEqual(audit.total_raw_db_detections, 397)
        self.assertEqual(audit.total_generated_mobile_cards, 383)
        self.assertEqual(audit.total_dropped_actions, 0)
        self.assertGreater(len(audit.duplicate_upc_clusters), 0)

    def test_simplified_e2e_audit_report_generation(self):
        """Verify HTML audit report renders cleanly with simplified KPI cards, duplicate UPC clusters, and lifecycle resilience."""
        raw_file = WORKSPACE_DIR / "raw_backend_actions_task_8601238.json"
        raw_items = json.loads(raw_file.read_text(encoding="utf-8"))
        audit = audit_task_execution(
            task_id=8601238,
            store_id=810,
            pog_id=86738,
            raw_items=raw_items,
            instance_slug="harr",
            pog_name="3 ft - ICE CREAM TOPPINGS",
            executed_step_indexes=[1, 2, 3, 4, 5]
        )

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        out_path = generate_e2e_audit_html_report(audit, tmp_path)
        self.assertTrue(out_path.exists())
        content = out_path.read_text(encoding="utf-8")
        
        # Check Simplified Header & KPIs
        self.assertIn("Intelligent Reset Action Count &amp; Resumption Audit", content)
        self.assertIn("Task #8601238", content)
        self.assertIn("Backend Actions Generated", content)
        self.assertIn("Mobile Actions Displayed", content)
        self.assertIn("Actions Completed (Accepted)", content)
        self.assertIn("Pending Left to Perform", content)
        self.assertIn("Dropped on Reload / Resume", content)
        
        # Check Section 1: Duplicate UPC Multi-Location Mapping
        self.assertIn("Duplicate / Same UPC Multi-Location Distribution", content)
        self.assertIn("Present in Which All Locations", content)
        
        # Check Section 2: Lifecycle Resilience & Itemized Pending Actions
        self.assertIn("App Refresh, Logout, Screen Switch &amp; App Kill Resilience", content)
        self.assertIn("APP PULL TO REFRESH", content)
        self.assertIn("USER LOGOUT AND RELOGIN", content)
        self.assertIn("SCREEN NAVIGATION SWITCH", content)
        self.assertIn("APP KILL AND BACKGROUND RESUME", content)
        self.assertIn("PASSED (Zero Loss)", content)
        self.assertIn("View", content)
        self.assertIn("Immediate Next Active Card on Mobile Screen", content)
        self.assertIn("Full Itemized List of Pending Mobile Actions", content)
        
        # Check Section 3: Trace Table
        self.assertIn("Streamlined Step-by-Step Bi-Directional Trace", content)
        self.assertIn("Why User Performs This Action", content)
        self.assertIn("Inspect Payload", content)

        # Check Section 4: Continuous Full-Duplex Network Traffic Log
        self.assertIn("Full-Duplex Bi-Directional HTTP Traffic Log", content)
        self.assertIn("Tracks all requests going from Mobile", content)
        self.assertIn("Inspect Call &amp; Response", content)
        self.assertIn("trafficModal", content)
        
        tmp_path.unlink(missing_ok=True)

    def test_continuous_active_and_idle_network_traffic_logging(self):
        """Verify that all calls from mobile to backend and backend to mobile during active and idle periods are tracked."""
        from runner_server import record_network_traffic, EXECUTION_STATE
        
        # Test 1: Active User Step Call
        active_entry = record_network_traffic(
            method="PATCH",
            url="https://harr.rebotics.net/api/v1/tasks/8601238/action-list/retailer/101/",
            status_code=200,
            latency_ms=38,
            request_headers={"Authorization": "Token 508e73...fe85", "Content-Type": "application/json"},
            request_payload={"state": "STATE_ACCEPTED"},
            response_headers={"Content-Type": "application/json"},
            response_body={"id": 101, "state": "STATE_ACCEPTED"},
            activity_state="ACTIVE_USER_INTERACTION",
            caller_event="STEP_1_SET_ASIDE",
            task_id=8601238
        )
        self.assertEqual(active_entry["activity_state"], "ACTIVE_USER_INTERACTION")
        self.assertEqual(active_entry["method"], "PATCH")
        self.assertEqual(active_entry["status_code"], 200)
        self.assertIn("curl -X PATCH", active_entry["curl_command"])
        self.assertIn("Authorization", active_entry["curl_command"])

        # Test 2: Idle Background Sync Call (when user is not doing anything on app)
        idle_entry = record_network_traffic(
            method="POST",
            url="/api/runner/heartbeat",
            status_code=200,
            latency_ms=11,
            request_headers={"Content-Type": "application/json", "X-Client-State": "IDLE"},
            request_payload={"client_state": "IDLE", "task_id": 8601238},
            response_headers={"Content-Type": "application/json"},
            response_body={"status": "connected", "server_time": "2026-08-27 14:30:00"},
            activity_state="IDLE_BACKGROUND_POLL",
            caller_event="BACKGROUND_HEARTBEAT",
            task_id=8601238
        )
        self.assertEqual(idle_entry["activity_state"], "IDLE_BACKGROUND_POLL")
        self.assertEqual(idle_entry["caller_event"], "BACKGROUND_HEARTBEAT")
        self.assertEqual(idle_entry["latency_ms"], 11)

        # Verify entry appended to EXECUTION_STATE
        self.assertIn(active_entry, EXECUTION_STATE["network_traffic_log"])
        self.assertIn(idle_entry, EXECUTION_STATE["network_traffic_log"])


if __name__ == "__main__":
    unittest.main()

