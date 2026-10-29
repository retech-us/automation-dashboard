"""
Unit and Integration tests for ShelfIntelligenceRulesEngine.
Verifies business-rule soundness, product recognition precision, multi-bay invariant enforcement,
rescan lifecycle, and cross-platform mobile parsing parity.
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.shelf_intelligence_rules import ShelfIntelligenceRulesEngine

WORKSPACE_DIR = Path(__file__).resolve().parents[2]


class ShelfIntelligenceRulesTests(unittest.TestCase):

    def setUp(self):
        self.raw_file = WORKSPACE_DIR / "raw_backend_actions_task_8601238.json"
        self.has_raw_file = self.raw_file.exists()
        if self.has_raw_file:
            self.task_8601238_data = json.loads(self.raw_file.read_text(encoding="utf-8"))

    def test_detects_redundant_same_slot_moves(self):
        flawed_actions = [
            {
                "id": 1,
                "upc": "012345678901",
                "action": "fix_position_in_bay",
                "current_position": {"shelf": 2, "position": 3, "section_info": {"name": "1"}},
                "expected_position": {"shelf": 2, "position": 3, "section_info": {"name": "1"}},
            }
        ]
        violations, metrics = ShelfIntelligenceRulesEngine.verify_action_soundness_and_completeness(flawed_actions)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].rule_code, "REDUNDANT_SAME_SLOT_MOVE")
        self.assertFalse(metrics["soundness_passed"])

    def test_detects_duplicate_action_cards(self):
        flawed_actions = [
            {
                "id": 10,
                "upc": "012345678901",
                "action": "fix_position_in_bay",
                "current_position": {"shelf": 1, "position": 1, "section_info": {"name": "1"}},
                "expected_position": {"shelf": 1, "position": 2, "section_info": {"name": "1"}},
            },
            {
                "id": 11,
                "upc": "012345678901",
                "action": "fix_position_in_bay",
                "current_position": {"shelf": 1, "position": 1, "section_info": {"name": "1"}},
                "expected_position": {"shelf": 1, "position": 2, "section_info": {"name": "1"}},
            },
        ]
        violations, metrics = ShelfIntelligenceRulesEngine.verify_action_soundness_and_completeness(flawed_actions)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].rule_code, "DUPLICATE_ACTION_CARD")
        self.assertFalse(metrics["soundness_passed"])

    def test_detects_target_slot_collisions(self):
        two_claimants = [
            {
                "id": 100,
                "upc": "111111111111",
                "action": "place_on_shelf_add_to_bay",
                "expected_position": {"shelf": 3, "position": 5, "section_info": {"name": "2"}},
            },
            {
                "id": 101,
                "upc": "222222222222",
                "action": "place_on_shelf_add_to_bay",
                "expected_position": {"shelf": 3, "position": 5, "section_info": {"name": "2"}},
            },
        ]
        violations, metrics = ShelfIntelligenceRulesEngine.verify_product_and_position_precision(two_claimants)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].rule_code, "DUPLICATE_TARGET_SLOT_COLLISION")
        self.assertFalse(metrics["position_precision_passed"])

    def test_detects_missing_target_coordinates(self):
        missing_coords = [
            {
                "id": 200,
                "upc": "333333333333",
                "action": "place_on_shelf_add_to_bay",
                "expected_position": {"shelf": None, "position": None, "section_info": None},
            }
        ]
        violations, metrics = ShelfIntelligenceRulesEngine.verify_product_and_position_precision(missing_coords)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].rule_code, "MISSING_TARGET_COORDINATES")

    def test_cross_platform_parsing_parity(self):
        actions = [
            {
                "id": 1,
                "upc": "040000002376",
                "action": "remove",
                "state": "STATE_IDLE",
                "current_position": {"shelf": 1, "position": 2, "section_info": {"name": "1"}},
                "expected_position": None,
            },
            {
                "id": 2,
                "upc": "011110087456",
                "action": "place_on_shelf_add_to_bay",
                "state": "STATE_IDLE",
                "current_position": {"shelf": 1, "position": 4, "section_info": {"name": "1"}},
                "expected_position": {"shelf": 3, "position": 1, "section_info": {"name": "2"}},
            },
            {
                "id": 3,
                "upc": "041220789012",
                "action": "fix_position_in_bay",
                "state": "STATE_IDLE",
                "current_position": {"shelf": 2, "position": 1, "section_info": {"name": "1"}},
                "expected_position": {"shelf": 2, "position": 5, "section_info": {"name": "1"}},
            },
        ]
        violations, metrics = ShelfIntelligenceRulesEngine.verify_cross_platform_parsing_parity(actions)
        self.assertEqual(len(violations), 0)
        self.assertTrue(metrics["platform_parity_passed"])
        self.assertEqual(metrics["platform_parity_mismatches"], 0)

    def test_repeat_scans_delta_resolution(self):
        pre_actions = [{"id": 1, "state": "STATE_IDLE"}, {"id": 2, "state": "STATE_IDLE"}]
        # Post actions where action #1 was resolved/completed
        post_actions = [{"id": 2, "state": "STATE_IDLE"}]

        violations, metrics = ShelfIntelligenceRulesEngine.verify_repeat_scans_and_rescan_lifecycle(
            pre_actions, post_actions
        )
        self.assertEqual(len(violations), 0)
        self.assertEqual(metrics["resolved_actions_count"], 1)
        self.assertTrue(metrics["rescan_lifecycle_passed"])

    def test_repeat_scans_ignored_post_photo_warning(self):
        pre_actions = [{"id": 1, "state": "STATE_IDLE"}]
        post_actions = [{"id": 1, "state": "STATE_IDLE"}]

        violations, metrics = ShelfIntelligenceRulesEngine.verify_repeat_scans_and_rescan_lifecycle(
            pre_actions, post_actions
        )
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].rule_code, "POST_PHOTO_IGNORED")
        self.assertEqual(violations[0].severity, "warning")

    def test_evaluate_all_on_real_task_dataset(self):
        if not self.has_raw_file:
            self.skipTest("Task dataset raw_backend_actions_task_8601238.json not present")

        report = ShelfIntelligenceRulesEngine.evaluate_all(self.task_8601238_data)
        self.assertIsInstance(report.total_actions, int)
        self.assertGreater(report.total_actions, 0)
        # Check rule results
        self.assertIn("1_action_soundness_and_completeness", report.rule_results)
        self.assertIn("2_product_and_position_precision", report.rule_results)
        self.assertIn("3_workflow_sequencing_and_invariants", report.rule_results)
        self.assertIn("5_cross_platform_parsing_parity", report.rule_results)
        self.assertTrue(report.rule_results["5_cross_platform_parsing_parity"])


if __name__ == "__main__":
    unittest.main()
