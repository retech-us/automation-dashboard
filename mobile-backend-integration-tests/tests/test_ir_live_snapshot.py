import unittest
from pathlib import Path
import tempfile

from core.ir_live_snapshot import (
    build_ir_live_snapshot,
    load_ir_snapshot,
    save_ir_snapshot,
)


class IrLiveSnapshotTests(unittest.TestCase):
    def test_missing_metrics_are_unknown_not_zero(self):
        snapshot = build_ir_live_snapshot(
            {
                "active_task_id": 99,
                "task_status": "in_progress",
                "pipeline": {"is_running": True, "step_name": "Waiting for CV"},
                "actions": [],
            }
        )

        self.assertEqual(snapshot["task_id"], 99)
        self.assertEqual(snapshot["live_state"], "running")
        self.assertIsNone(snapshot["metrics"]["digital_alignment_pct"])
        self.assertIsNone(snapshot["metrics"]["post_alignment_pct"])
        self.assertEqual(snapshot["post_photo"]["state"], "not_checked")
        self.assertFalse(snapshot["capabilities"]["fresh_e2e_includes_post_photo"])
        self.assertIn("not been checked", snapshot["plain_language_summary"])

    def test_live_steps_update_completion_before_historical_audit(self):
        snapshot = build_ir_live_snapshot({
            "active_task_id": 88,
            "task_status": "in_progress",
            "actions": [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}],
            "step_telemetry": [
                {"action_id": 1, "step_index": 1},
                {"action_id": 2, "step_index": 2},
            ],
            "pipeline": {"is_running": False, "step_name": "Actions ready"},
        })

        self.assertEqual(snapshot["metrics"]["displayed_steps"], 4)
        self.assertEqual(snapshot["metrics"]["performed_steps"], 2)
        self.assertEqual(snapshot["metrics"]["pending_steps"], 2)
        self.assertEqual(snapshot["metrics"]["work_finished_pct"], 50.0)
        self.assertIsNone(snapshot["metrics"]["digital_alignment_pct"])
        self.assertIn("2 of 4", snapshot["plain_language_summary"])

    def test_uses_audit_values_without_double_counting_two_phase_moves(self):
        snapshot = build_ir_live_snapshot(
            {
                "active_task_id": 99,
                "task_status": "completed",
                "instance_slug": "harr",
                "latest_audit": {
                    "task_id": 99,
                    "total_raw_db_detections": 12,
                    "unique_backend_actions": 8,
                    "total_generated_mobile_cards": 10,
                    "total_performed_actions": 9,
                    "total_pending_actions": 1,
                    "total_rejected_actions": 0,
                    "compliance_score_pct": 90.0,
                    "digital_alignment_pct": 87.5,
                    "combined_compliance_pct": 87.5,
                    "digital_compare_counts": {
                        "matched": 7,
                        "mismatched": 1,
                        "generated_only": 0,
                        "digital_only": 2,
                    },
                    "action_counts_by_type": {
                        "SET_ASIDE": 2,
                        "ADD_TO_SHELF": 2,
                        "REMOVE": 4,
                    },
                    "post_stage_supported": True,
                    "post_generated_action_count": 3,
                    "post_digital_loaded": True,
                    "post_digital_alignment_pct": 100.0,
                    "post_digital_compare_counts": {"matched": 3},
                    "task_timeline": {
                        "pre_scan": {"scan_id": 7001},
                        "post_scan": {"scan_id": 7002},
                    },
                },
            }
        )

        self.assertEqual(snapshot["metrics"]["logical_actions"], 8)
        self.assertEqual(snapshot["metrics"]["displayed_steps"], 10)
        self.assertEqual(snapshot["action_mix"]["moved_items"], 2)
        self.assertEqual(snapshot["post_photo"]["state"], "verified")
        self.assertEqual(snapshot["post_photo"]["scan_id"], 7002)
        self.assertEqual(snapshot["quality_gate"]["state"], "fail")

    def test_post_error_is_explained_and_never_becomes_zero_alignment(self):
        snapshot = build_ir_live_snapshot(
            {
                "active_task_id": 99,
                "latest_audit": {
                    "task_id": 99,
                    "digital_alignment_pct": 100.0,
                    "post_digital_loaded": False,
                    "post_stage_supported": False,
                    "post_digital_alignment_pct": None,
                    "post_digital_error": "Backend ignored ?stage=post_photo",
                    "task_timeline": {},
                },
            }
        )

        self.assertEqual(snapshot["post_photo"]["state"], "unavailable")
        self.assertIsNone(snapshot["metrics"]["post_alignment_pct"])
        self.assertIn("ignored", snapshot["post_photo"]["explanation"])

    def test_scan_diagnostics_and_findings_use_only_explicit_source_data(self):
        snapshot = build_ir_live_snapshot({
            "active_task_id": 99,
            "scan_results": [
                {
                    "id": 7001,
                    "scan_type": "pre_photo",
                    "status": "completed",
                    "image_quality": 81,
                    "blurry_pct": 12.5,
                    "shelf_mismatch": False,
                },
                {
                    "id": 7002,
                    "is_post_photo": True,
                    "status": "failed",
                    "shelf_mismatch": True,
                },
            ],
            "latest_audit": {
                "task_id": 99,
                "combined_compliance_pct": 80.0,
                "digital_alignment_pct": 80.0,
                "digital_compare_counts": {"matched": 8, "mismatched": 2},
                "total_pending_actions": 1,
                "total_rejected_actions": 0,
                "total_dropped_actions": 0,
                "post_digital_loaded": False,
                "post_digital_error": "R07 post fetch failed",
                "task_timeline": {},
            },
        })

        self.assertEqual(len(snapshot["scan_diagnostics"]), 2)
        self.assertEqual(snapshot["scan_diagnostics"][0]["image_quality"], 81)
        self.assertIsNone(snapshot["scan_diagnostics"][1]["image_quality"])
        finding_codes = {finding["code"] for finding in snapshot["findings"]}
        self.assertIn("IR-QUALITY-GATE", finding_codes)
        self.assertIn("IR-DIGITAL-MISMATCH", finding_codes)
        self.assertIn("IR-POST-UNAVAILABLE", finding_codes)
        self.assertIn("IR-ACTION-INCOMPLETE", finding_codes)
        for finding in snapshot["findings"]:
            self.assertIn("IR-TASK-99-", finding["jira"]["reference"])
            self.assertNotIn("password", str(finding).lower())

    def test_snapshot_persistence_contains_no_credentials(self):
        snapshot = build_ir_live_snapshot({
            "active_task_id": 77,
            "instance_slug": "harr",
            "token": "must-not-be-written",
            "password": "must-not-be-written",
        })
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ir-live-snapshot.json"
            save_ir_snapshot(snapshot, path)
            saved_text = path.read_text(encoding="utf-8")
            loaded = load_ir_snapshot(path)

        self.assertNotIn("must-not-be-written", saved_text)
        self.assertEqual(loaded["task_id"], 77)


class IrLiveSnapshotUiContractTests(unittest.TestCase):
    def test_runner_has_plain_language_live_scorecard(self):
        runner_html = (
            Path(__file__).resolve().parents[2] / "test_runner.html"
        ).read_text(encoding="utf-8")

        self.assertIn('id="ir-live-scorecard"', runner_html)
        self.assertIn('aria-live="polite"', runner_html)
        self.assertIn("/api/runner/ir_live_snapshot", runner_html)
        self.assertIn("What this means", runner_html)
        self.assertIn("Not checked", runner_html)
        self.assertIn("Pre-photo pipeline", runner_html)
        self.assertIn("does not upload or verify the post photo", runner_html)

    def test_main_dashboard_has_native_ir_quality_view(self):
        root = Path(__file__).resolve().parents[2]
        index_html = (root / "index.html").read_text(encoding="utf-8")
        app_js = (root / "assets/js/app.v16.js").read_text(encoding="utf-8")

        self.assertIn('data-tab="ir"', index_html)
        self.assertIn('id="panel-ir"', index_html)
        self.assertIn("ir-live-dashboard.js", index_html)
        self.assertIn('id="ir-quality-findings"', index_html)
        self.assertIn('id="ir-quality-scans"', index_html)
        self.assertIn("'ir'", app_js)


if __name__ == "__main__":
    unittest.main()
