import unittest
from core.ir_task_flow_builder import (
    get_task_flow,
    build_harr_reference_task_8648127,
    build_krcs_reference_task_42288818,
    synthesize_task_flow_from_raw_actions,
)


class TestIrTaskFlowBuilder(unittest.TestCase):

    def test_harr_reference_task_lineage(self):
        flow = build_harr_reference_task_8648127()
        self.assertEqual(flow["status"], "success")
        self.assertEqual(flow["task_id"], 8648127)
        self.assertEqual(flow["metadata"]["store_code"], "208_Test")
        self.assertEqual(flow["metadata"]["status_reason"], "AI Exception - Low Compliance Post Reset")
        self.assertEqual(flow["metadata"]["quality_gate"], "NEEDS_ATTENTION")
        
        events = flow["events"]
        event_types = [e["event_type"] for e in events]
        self.assertIn("created", event_types)
        self.assertIn("started", event_types)
        self.assertIn("survey_start", event_types)
        self.assertIn("photo", event_types)
        self.assertIn("ai_result", event_types)
        self.assertIn("compliance", event_types)
        self.assertIn("actions", event_types)
        self.assertIn("survey_end", event_types)
        self.assertIn("timer_posted", event_types)
        self.assertIn("closed", event_types)

        # Check action batches
        batches = flow["action_batches"]
        self.assertIn("batch_harr_1", batches)
        batch1 = batches["batch_harr_1"]
        self.assertEqual(batch1["action_type"], "ACTION_IDENTIFY")
        self.assertEqual(batch1["state"], "STATE_REJECTED")
        self.assertEqual(batch1["item_count"], 5)
        self.assertEqual(len(batch1["items"]), 5)

        # Check bay summary
        self.assertIn("Bay 1", flow["bay_summaries"])
        bay1 = flow["bay_summaries"]["Bay 1"]
        self.assertEqual(bay1["pre_photo_scan_id"], 3768606)
        self.assertEqual(bay1["ai_latency_sec"], 23)
        self.assertEqual(bay1["post_compliance_pct"], 93.0)

    def test_krcs_reference_task_lineage(self):
        flow = build_krcs_reference_task_42288818()
        self.assertEqual(flow["status"], "success")
        self.assertEqual(flow["task_id"], 42288818)
        self.assertEqual(flow["metadata"]["store_code"], "705-00835_Test")
        self.assertEqual(flow["metadata"]["status"], "completed")
        self.assertEqual(flow["metadata"]["quality_gate"], "PASSED")
        self.assertEqual(len(flow["metadata"]["bays"]), 6)

    def test_get_task_flow_local_or_synth(self):
        # 8648127 returns HARR reference
        f_harr = get_task_flow(8648127)
        self.assertEqual(f_harr["task_id"], 8648127)

        # 42288818 returns KRCS reference
        f_krcs = get_task_flow(42288818)
        self.assertEqual(f_krcs["task_id"], 42288818)

        # Arbitrary task ID
        f_custom = get_task_flow(99999999)
        self.assertEqual(f_custom["status"], "success")
        self.assertEqual(f_custom["task_id"], 99999999)
        self.assertTrue(len(f_custom["events"]) > 0)


if __name__ == "__main__":
    unittest.main()
