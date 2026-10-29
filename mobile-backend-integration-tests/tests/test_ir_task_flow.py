import unittest
from core.ir_task_flow_builder import (
    build_harr_reference_task_8648127,
    build_krcs_reference_task_42288818,
    build_stage_action_payload,
    enrich_flow_with_digital_shelf_evidence,
    format_duration_hm,
    get_task_flow,
    synthesize_task_flow_from_raw_actions,
)


class TestIrTaskFlowBuilder(unittest.TestCase):

    def test_pre_and_post_photo_actions_have_separate_payloads(self):
        pre_actions = [{
            "id": 1,
            "action": "ACTION_MOVE",
            "product_title": "Before product",
            "current_position": {"shelf": 1, "position": "1", "section_info": {"name": "1"}},
            "expected_position": {"shelf": 1, "position": "2", "section_info": {"name": "1"}},
        }]
        post_actions = [{
            "id": 2,
            "action": "ACTION_REMOVE",
            "product_title": "After product",
            "current_position": {"shelf": 2, "position": "3", "section_info": {"name": "1"}},
        }]

        payload = build_stage_action_payload(
            1234,
            pre_actions,
            post_actions,
            post_loaded=True,
            post_error=None,
            metadata_override={"status": "completed"},
        )

        self.assertTrue(payload["pre_photo"]["loaded"])
        self.assertEqual(payload["pre_photo"]["row_count"], 1)
        self.assertTrue(payload["post_photo"]["loaded"])
        self.assertEqual(payload["post_photo"]["row_count"], 1)
        pre_item = next(iter(payload["pre_photo"]["action_batches"].values()))["items"][0]
        post_item = next(iter(payload["post_photo"]["action_batches"].values()))["items"][0]
        self.assertEqual(pre_item["product_name"], "Before product")
        self.assertEqual(post_item["product_name"], "After product")

    def test_unavailable_post_photo_stage_stays_separate_and_empty(self):
        payload = build_stage_action_payload(
            1234,
            [{"id": 1, "action": "ACTION_REMOVE", "current_position": {"section_info": {"name": "1"}}}],
            [],
            post_loaded=False,
            post_error="Backend ignored ?stage=post_photo",
        )

        self.assertFalse(payload["post_photo"]["loaded"])
        self.assertEqual(payload["post_photo"]["action_batches"], {})
        self.assertIn("ignored", payload["post_photo"]["error"])

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

    def test_live_duration_evidence_is_preserved_without_fallback(self):
        actions = [{
            "id": 1,
            "action": "ACTION_MOVE",
            "displayed_upc": "123",
            "current_position": {"shelf": 1, "position": "2", "section_info": {"name": "1"}},
            "expected_position": {"shelf": 2, "position": "3", "section_info": {"name": "2"}},
        }]
        flow = synthesize_task_flow_from_raw_actions(
            1234,
            actions,
            metadata_override={
                "wall_duration_min": None,
                "duration_source": None,
                "duration_started_at": None,
                "duration_completed_at": None,
            },
        )

        self.assertIsNone(flow["metadata"]["wall_duration_min"])
        self.assertIsNone(flow["metadata"]["duration_source"])
        self.assertIn("not recorded", flow["events"][-1]["detail"])
        item = next(iter(flow["action_batches"].values()))["items"][0]
        self.assertEqual(item["from_bay"], "Bay 1")
        self.assertEqual(item["to_bay"], "Bay 2")

    def test_intra_shelf_slide_and_redundant_same_slot_discrepancy_tagging(self):
        raw_actions = [
            {
                "id": 101,
                "action": "ACTION_MOVE",
                "displayed_upc": "011110636584",
                "product_title": "ST CRAN CHERRIES TRAIL MX",
                "current_position": {"shelf": 5, "position": "4", "section_info": {"name": "1"}},
                "expected_position": {"shelf": 5, "position": "5", "section_info": {"name": "1"}},
            },
            {
                "id": 102,
                "action": "ACTION_MOVE",
                "displayed_upc": "011110999999",
                "product_title": "Redundant Product",
                "current_position": {"shelf": 3, "position": "2", "section_info": {"name": "1"}},
                "expected_position": {"shelf": 3, "position": "2", "section_info": {"name": "1"}},
            },
        ]
        flow = synthesize_task_flow_from_raw_actions(44061994, raw_actions)
        all_items = [it for b in flow["action_batches"].values() for it in b["items"]]
        cran_item = next(it for it in all_items if it["upc"] == "011110636584")
        redundant_item = next(it for it in all_items if it["upc"] == "011110999999")

        self.assertEqual(cran_item["discrepancy_type"], "intra_shelf_slide")
        self.assertIn("Pos 4 → 5", cran_item["discrepancy_label"])
        self.assertEqual(redundant_item["discrepancy_type"], "redundant_same_slot")
        self.assertEqual(redundant_item["discrepancy_label"], "Redundant Same-Slot Move")

    def test_enrich_flow_with_digital_shelf_relative_sequence_ok(self):
        raw_actions = [
            {
                "id": 101,
                "action": "ACTION_MOVE",
                "displayed_upc": "011110636584",
                "product_title": "ST CRAN CHERRIES TRAIL MX",
                "current_position": {"shelf": 5, "position": "4", "section_info": {"name": "1"}},
                "expected_position": {"shelf": 5, "position": "5", "section_info": {"name": "1"}},
            },
        ]
        flow = synthesize_task_flow_from_raw_actions(44061994, raw_actions)

        # Mock Digital Shelf item reporting this UPC as OK with action_taken = "-"
        mock_digital_items = [
            {
                "upc": "011110636584",
                "action_type": "ok",
                "action_taken": "-",
                "section": "1",
                "rog_position": "5:4",
                "pog_position": "5:5",
            }
        ]
        enriched = enrich_flow_with_digital_shelf_evidence(flow, mock_digital_items)
        all_items = [it for b in enriched["action_batches"].values() for it in b["items"]]
        cran_item = next(it for it in all_items if it["upc"] == "011110636584")

        self.assertEqual(cran_item["discrepancy_type"], "relative_sequence_ok")
        self.assertEqual(cran_item["digital_action_type"], "ok")
        self.assertEqual(cran_item["digital_action_taken"], "-")
        self.assertIn("Rel-Seq OK (Threshold=0)", cran_item["discrepancy_label"])
        self.assertIn("SequenceMatcher", cran_item["discrepancy_detail"])

    def test_format_duration_hm(self):
        self.assertEqual(format_duration_hm(None), "not recorded")
        self.assertEqual(format_duration_hm(0), "0 mins")
        self.assertEqual(format_duration_hm(1), "1 min")
        self.assertEqual(format_duration_hm(28.3), "28 mins")
        self.assertEqual(format_duration_hm(60), "1 hr")
        self.assertEqual(format_duration_hm(61), "1 hr 1 min")
        self.assertEqual(format_duration_hm(120), "2 hrs")
        self.assertEqual(format_duration_hm(351.7), "5 hrs 52 mins")
        self.assertEqual(format_duration_hm(1440.0), "24 hrs")

    def test_synthesize_task_flow_formats_duration_in_hours_and_minutes(self):
        actions = [{
            "id": 999,
            "action": "ACTION_MOVE",
            "product_title": "Product X",
            "displayed_upc": "999",
            "current_position": {"shelf": 1, "position": "1", "section_info": {"name": "1"}},
            "expected_position": {"shelf": 1, "position": "2", "section_info": {"name": "1"}},
        }]
        flow = synthesize_task_flow_from_raw_actions(
            5555,
            actions,
            metadata_override={"wall_duration_min": 351.7},
        )
    def test_flow_items_include_scan_id_and_digital_shelf_link(self):
        actions = [{
            "id": 101,
            "action": "ACTION_MOVE",
            "product_title": "Trail Mix",
            "displayed_upc": "011110636584",
            "current_position": {
                "shelf": 5,
                "position": "4",
                "section_info": {"name": "1"},
                "scan_id": 998877,
            },
            "expected_position": {"shelf": 5, "position": "5", "section_info": {"name": "1"}},
        }]
        flow = synthesize_task_flow_from_raw_actions(
            5555,
            actions,
            metadata_override={"instance": "harr"},
        )
        batch = next(iter(flow["action_batches"].values()))
        self.assertEqual(batch["scan_id"], 998877)
        self.assertEqual(batch["digital_shelf_url"], "https://harr.rebotics.net/reporting/scans/998877")
        item = batch["items"][0]
        self.assertEqual(item["scan_id"], 998877)
        self.assertEqual(item["digital_shelf_url"], "https://harr.rebotics.net/reporting/scans/998877")

    def test_reference_tasks_include_scan_evidence(self):
        # HARR
        harr = build_harr_reference_task_8648127()
        self.assertEqual(harr["metadata"]["pre_photo_scan_id"], 3768606)
        self.assertEqual(harr["metadata"]["post_photo_scan_id"], 3769854)
        self.assertEqual(harr["metadata"]["digital_shelf_scan_url"], "https://harr.rebotics.net/reporting/scans/3768606")
        batch1 = harr["action_batches"]["batch_harr_1"]
        self.assertEqual(batch1["scan_id"], 3768606)
        self.assertEqual(batch1["digital_shelf_url"], "https://harr.rebotics.net/reporting/scans/3768606")
        self.assertEqual(batch1["items"][0]["scan_id"], 3768606)
        self.assertEqual(batch1["items"][0]["digital_shelf_url"], "https://harr.rebotics.net/reporting/scans/3768606")

        # KRCS
        krcs = build_krcs_reference_task_42288818()
        self.assertEqual(krcs["metadata"]["pre_photo_scan_id"], 17146891)
        self.assertEqual(krcs["metadata"]["post_photo_scan_id"], 17147320)
        self.assertEqual(krcs["metadata"]["digital_shelf_scan_url"], "https://krcs.rebotics.net/reporting/scans/17146891")
        k_batch = next(iter(krcs["action_batches"].values()))
        self.assertIsNotNone(k_batch["scan_id"])
        self.assertTrue(k_batch["digital_shelf_url"].startswith("https://krcs.rebotics.net/reporting/scans/"))
        self.assertEqual(k_batch["items"][0]["scan_id"], k_batch["scan_id"])
        self.assertEqual(k_batch["items"][0]["digital_shelf_url"], k_batch["digital_shelf_url"])

    def test_identified_products_have_bounding_boxes_and_crop_urls(self):
        harr = build_harr_reference_task_8648127()
        batch1 = harr["action_batches"]["batch_harr_1"]
        self.assertEqual(batch1["action_type"], "ACTION_IDENTIFY")
        for item in batch1["items"]:
            self.assertIsNotNone(item.get("bounding_box"))
            self.assertIn("x", item["bounding_box"])
            self.assertIn("y", item["bounding_box"])
            self.assertTrue(item["crop_image_url"].startswith("https://"))
            self.assertTrue(item["image"].startswith("https://"))

        # Verify synthesized action with coordinates gets bounding box
        actions = [{
            "id": 881,
            "action": "ACTION_IDENTIFY",
            "product_title": "Identified Item",
            "displayed_upc": "123456789012",
            "coordinates": {"x": 512.0, "y": 640.0, "width": 80.0, "height": 140.0},
            "image": "https://bucket-test.s3.amazonaws.com/crop.png",
            "current_position": {"shelf": 2, "position": "1", "section_info": {"name": "1"}},
        }]
        flow = synthesize_task_flow_from_raw_actions(7777, actions)
        item = next(iter(flow["action_batches"].values()))["items"][0]
        self.assertEqual(item["bounding_box"]["x"], 512.0)
        self.assertEqual(item["bounding_box"]["y"], 640.0)
        self.assertEqual(item["crop_image_url"], "https://bucket-test.s3.amazonaws.com/crop.png")


if __name__ == "__main__":
    unittest.main()
