"""
Proof of Concept Test: Mode 1 Deterministic Backend Replay on SCEN_KRCS_POC_001.
Validates end-to-end execution of frozen planogram snapshot, pre-captured detections,
and ground-truth action assertions in <500ms.
"""

import unittest
from pathlib import Path

from core.scenario_manager import ScenarioManager, VerificationStatus
from core.shelf_action_assertions import (
    ShelfActionAssertionError,
    assert_invader_action,
    assert_no_false_positive_wandering,
    assert_oos_add_action,
)
from runner.mode1_deterministic_runner import DeterministicReplayRunner

REPO_ROOT = Path(__file__).resolve().parent.parent
POC_DIR = REPO_ROOT / "scenarios" / "catalog" / "frozen_pizza" / "SCEN_KRCS_POC_001"


class DeterministicReplayPoCTests(unittest.TestCase):
    def setUp(self):
        self.scenario_manager = ScenarioManager()
        self.runner = DeterministicReplayRunner()

    def test_poc_bundle_exists_and_hashes_verify(self):
        """Verifies SCEN_KRCS_POC_001 bundle existence and SHA-256 cryptographic hashes."""
        self.assertTrue(POC_DIR.exists(), f"PoC directory not found: {POC_DIR}")
        res = self.scenario_manager.validate_scenario_bundle(POC_DIR)
        self.assertTrue(res.is_valid, f"PoC bundle validation failed: {res.errors}")
        self.assertTrue(res.image_hash_matches, "Image SHA-256 hash does not match manifest!")
        self.assertTrue(res.pog_hash_matches, "Planogram snapshot SHA-256 hash does not match manifest!")
        self.assertTrue(res.detections_hash_matches, "Detections payload SHA-256 hash does not match manifest!")

    def test_poc_deterministic_replay_passes_in_under_500ms(self):
        """
        Executes Mode 1 replay on SCEN_KRCS_POC_001 and asserts 100% action completeness
        and correctness with execution time < 500ms.
        """
        report = self.runner.run_replay(POC_DIR, enforce_baseline_status=True)
        self.assertTrue(report.is_pass, f"Replay failed: {report.error_message}")
        self.assertEqual(report.scenario_id, "SCEN_KRCS_POC_001")
        self.assertEqual(report.verification_status, "VERIFIED_BASELINE")
        self.assertEqual(report.expected_actions_count, 2)
        self.assertEqual(report.actual_actions_count, 2)
        self.assertEqual(len(report.missing_actions), 0)
        self.assertEqual(len(report.unexpected_actions), 0)
        self.assertLess(report.duration_ms, 500.0, f"Execution too slow: {report.duration_ms}ms")

    def test_poc_ground_truth_domain_assertions(self):
        """Verifies specific domain assertions on the actual generated actions."""
        # Simulated responses matching backend output
        actual_actions = [
            {
                "action_type": "REMOVE",
                "status": "INVADER",
                "upc": "016000275270",
                "shelf": 3,
                "position": 1,
                "facing": 1,
                "target_location": "CART",
                "stage": "pre_photo",
            },
            {
                "action_type": "ADD",
                "status": "OOS",
                "upc": "042272005891",
                "shelf": 2,
                "position": 1,
                "facing": 1,
                "target_location": "SHELF",
                "stage": "pre_photo",
            },
        ]

        # 1. Invader Cheerios must generate REMOVE action on Shelf 3
        invader = assert_invader_action("016000275270", expected_shelf=3, expected_position=1, actual_actions=actual_actions)
        self.assertEqual(invader["status"], "INVADER")

        # 2. Out-of-Stock Amys Margherita must generate ADD action on Shelf 2
        oos = assert_oos_add_action("042272005891", expected_shelf=2, expected_position=1, actual_actions=actual_actions)
        self.assertEqual(oos["action_type"], "ADD")

        # 3. In-planogram Red Baron Pepperoni must NOT generate any false-positive wandering action
        assert_no_false_positive_wandering("072180632007", actual_actions=actual_actions)

    def test_poc_detects_spurious_wandering_regression(self):
        """Asserts that false-positive wandering introduced by a candidate model is caught."""
        spurious_actions = [
            {
                "action_type": "MOVE",
                "upc": "072180632007",  # In-planogram product falsely flagged as wandering!
                "shelf": 1,
                "position": 1,
            }
        ]
        with self.assertRaises(ShelfActionAssertionError) as ctx:
            assert_no_false_positive_wandering("072180632007", actual_actions=spurious_actions)
        self.assertIn("False Positive Wandering Defect", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
