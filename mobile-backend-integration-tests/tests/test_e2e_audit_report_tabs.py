import tempfile
import unittest
from pathlib import Path

from core.e2e_audit_engine import audit_task_execution
from core.e2e_audit_report_generator import generate_e2e_audit_html_report


class TestE2EAuditReportTabs(unittest.TestCase):
    def setUp(self):
        self.raw_items = [{
            "id": 101,
            "source_id": 101,
            "upc": "840093104403",
            "displayed_upc": "840093104403",
            "product_title": "NATURES TRUTH ESS OIL DIFFUSER 1 CT",
            "product_id": 501,
            "action": "remove",
            "state": "STATE_ACCEPTED",
            "store_planogram_id": 87125,
            "current_position": {
                "action": "remove",
                "section_info": {"id": 1, "name": "1"},
                "shelf": 7,
                "position": 1,
                "scan_id": 16920444,
                "state": "STATE_ACCEPTED",
            },
        }]
        self.digital_items = [{
            "scan_id": 16920444,
            "upc": "840093104403",
            "product_name": "NATURES TRUTH ESS OIL DIFFUSER 1 CT",
            "section": "1",
            "pog_position": "7:1",
            "rog_position": "7:1",
            "action_type": "remove",
            "action_taken": "remove",
        }]

    def _audit(self):
        post_items = [dict(self.digital_items[0], scan_id=16920445)]
        post_raw_items = [{
            **self.raw_items[0],
            "current_position": {
                **self.raw_items[0]["current_position"],
                "scan_id": 16920445,
            },
        }]
        return audit_task_execution(
            task_id=99,
            store_id=810,
            pog_id=87125,
            raw_items=self.raw_items,
            instance_slug="harr",
            executed_step_indexes=[1],
            digital_actions=self.digital_items,
            digital_loaded=True,
            task_timeline={
                "task_created_at": "2026-09-01T09:00:00Z",
                "task_started_at": "2026-09-01T09:05:00Z",
                "task_completed_at": "2026-09-01T10:00:00Z",
                "task_duration_seconds": 3300,
                "photo_duration_seconds": 2400,
                "pre_scan": {
                    "scan_id": 16920444,
                    "uploaded_at": "2026-09-01T09:10:00Z",
                },
                "post_scan": {
                    "scan_id": 16920445,
                    "uploaded_at": "2026-09-01T09:50:00Z",
                },
            },
            post_digital_actions=post_items,
            post_digital_loaded=True,
            post_scan_id=16920445,
            post_raw_items=post_raw_items,
            post_stage_loaded=True,
            action_list_growth_after_post=0,
        )

    def test_engine_preserves_scan_id_and_calculates_digital_compliance(self):
        audit = self._audit()

        self.assertEqual(audit.step_records[0].scan_id, 16920444)
        self.assertEqual(audit.step_records[0].digital_action_type, "remove")
        self.assertEqual(audit.step_records[0].digital_action_taken, "remove")
        self.assertEqual(audit.step_records[0].digital_match_status, "MATCH")
        self.assertEqual(audit.digital_alignment_pct, 100.0)
        self.assertEqual(audit.combined_compliance_pct, 100.0)

    def test_post_compare_never_reuses_pre_photo_actions(self):
        audit = audit_task_execution(
            task_id=99,
            store_id=810,
            pog_id=87125,
            raw_items=self.raw_items,
            digital_actions=self.digital_items,
            digital_loaded=True,
            post_digital_actions=[
                dict(self.digital_items[0], scan_id=16920445)
            ],
            post_digital_loaded=True,
            post_scan_id=16920445,
            post_raw_items=[],
            post_stage_loaded=False,
            post_digital_error="Post-photo action list unavailable",
        )

        self.assertFalse(audit.post_digital_loaded)
        self.assertEqual(audit.post_generated_action_count, 0)
        self.assertEqual(audit.post_digital_compare, [])
        self.assertIn("Post-photo action list unavailable", audit.post_digital_error)

    def test_html_contains_tabs_timeline_and_pre_post_compare_data(self):
        audit = self._audit()
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
            output_path = Path(tmp.name)
        try:
            generate_e2e_audit_html_report(
                audit,
                output_path,
                category_id=1805,
                report_date="2026-09-01",
            )
            html = output_path.read_text(encoding="utf-8")
        finally:
            output_path.unlink(missing_ok=True)

        for tab_id in (
            "tab-overview",
            "tab-slot",
            "tab-step-trace",
            "tab-action-compare",
            "tab-post-photo-compare",
        ):
            self.assertIn(f'id="{tab_id}"', html)
        for removed_content in (
            'id="tab-lifecycle"',
            'id="tab-http"',
            'id="panel-lifecycle"',
            'id="panel-http"',
            "Inspect Payload",
            'id="inspectorModal"',
            'id="trafficModal"',
            'id="lifecycleModal"',
        ):
            self.assertNotIn(removed_content, html)
        self.assertIn("Streamlined Step-by-Step Bi-Directional Trace", html)
        self.assertIn("Digital Action Type", html)
        self.assertIn("User Action Taken", html)
        self.assertIn("Work Finished", html)
        self.assertIn("Work Done Correctly", html)
        self.assertIn("Overall Score", html)
        self.assertIn("All 1 generated actions were performed correctly", html)
        self.assertIn("MATCH", html)
        self.assertIn('data-digital-action="remove"', html)
        self.assertIn("category=1805", html)
        self.assertIn("date=2026-09-01", html)
        self.assertIn("reporting/scans/16920444", html)
        self.assertIn("selectedProductKey=840093104403-7:1", html)
        self.assertIn("Task &amp; Photo Timeline", html)
        self.assertIn("55m", html)
        self.assertIn("40m", html)
        self.assertIn(">Pre Photo Compare<", html)
        self.assertIn(">Post Photo Compare<", html)
        self.assertIn("Pre Photo — Generated vs User-Performed Action Compare", html)
        self.assertIn("Post Photo — Generated-Action Compare", html)
        self.assertIn("Scan #16920444", html)
        self.assertIn("Scan #16920445", html)
        self.assertIn("reporting/scans/16920445", html)
        self.assertIn("did not increase the generated action count", html)

    def test_step_trace_explains_unavailable_and_unmatched_digital_data(self):
        unavailable = audit_task_execution(
            99,
            810,
            87125,
            self.raw_items,
            digital_loaded=False,
            digital_error="HTTP 401 Unauthorized",
        )
        unmatched = audit_task_execution(
            99,
            810,
            87125,
            self.raw_items,
            digital_actions=[],
            digital_loaded=True,
        )

        for audit, expected in (
            (unavailable, "Digital data unavailable: HTTP 401 Unauthorized"),
            (unmatched, "NOT IN DIGITAL"),
        ):
            with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
                output_path = Path(tmp.name)
            try:
                generate_e2e_audit_html_report(audit, output_path)
                html = output_path.read_text(encoding="utf-8")
            finally:
                output_path.unlink(missing_ok=True)
            self.assertIn(expected, html)

    def test_overview_gates_use_real_counts_and_explain_failures(self):
        audit = audit_task_execution(
            99,
            810,
            87125,
            self.raw_items,
            executed_step_indexes=[],
            digital_loaded=False,
            digital_error="HTTP 401 Unauthorized",
            post_stage_loaded=False,
            post_digital_error="No verified post-photo action list",
        )
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
            output_path = Path(tmp.name)
        try:
            generate_e2e_audit_html_report(audit, output_path)
            html = output_path.read_text(encoding="utf-8")
        finally:
            output_path.unlink(missing_ok=True)

        self.assertIn("Run Quality Checks", html)
        self.assertIn("Post photo available", html)
        self.assertIn("No verified post-photo action list", html)
        self.assertIn("Actions Completed (Accepted)</div>", html)
        self.assertIn('class="kpi-value" style="color: #10B981;">0</div>', html)
        self.assertIn("Pending Left to Perform</div>", html)
        self.assertIn(">1</div>", html)
        self.assertIn("NEEDS ATTENTION", html)


class TestRunnerReportViewer(unittest.TestCase):
    def test_generated_reports_open_in_embedded_runner_viewer(self):
        runner_html = (
            Path(__file__).resolve().parents[2] / "test_runner.html"
        ).read_text(encoding="utf-8")

        self.assertIn('id="report-viewer"', runner_html)
        self.assertIn('id="report-viewer-frame"', runner_html)
        self.assertIn("openReportInRunner(reportUrl", runner_html)
        self.assertNotIn("window.open(reportUrl, '_blank')", runner_html)
        self.assertNotIn("window.open(data.report_url", runner_html)


if __name__ == "__main__":
    unittest.main()
