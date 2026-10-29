"""
Unit tests for PlanogramSnapshotExporter and Mode C Planogram Compatibility Comparator.
"""

import unittest

from core.planogram_snapshot_exporter import (
    PlanogramSnapshotExporter,
    compute_planogram_hash,
)


class PlanogramSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.exporter = PlanogramSnapshotExporter()

    def test_canonical_snapshot_building_and_sorting(self):
        # Unsorted items
        items = [
            {"section": "Bay 02", "shelf": 2, "position": 2, "upc": "222", "product_name": "Prod B"},
            {"section": "Bay 01", "shelf": 1, "position": 1, "upc": "111", "product_name": "Prod A"},
            {"section": "Bay 01", "shelf": 1, "position": 2, "upc": "112", "product_name": "Prod A2"},
        ]
        snapshot = self.exporter.build_canonical_snapshot(
            planogram_id=5001,
            category_name="test_cat",
            items=items,
        )

        self.assertEqual(snapshot["planogram_id"], 5001)
        self.assertEqual(len(snapshot["sections"]), 2)
        # Sections must be sorted
        self.assertEqual(snapshot["sections"][0]["section_name"], "Bay 01")
        self.assertEqual(snapshot["sections"][1]["section_name"], "Bay 02")
        # Check SHA-256 hash existence
        self.assertIn("sha256", snapshot)
        self.assertEqual(len(snapshot["sha256"]), 64)

    def test_mode_c_planogram_diff_identical(self):
        items = [{"section": "Bay 01", "shelf": 1, "position": 1, "upc": "111", "product_name": "P1"}]
        snap1 = self.exporter.build_canonical_snapshot(100, "cat", items=items)
        snap2 = self.exporter.build_canonical_snapshot(100, "cat", items=items)

        diff = self.exporter.compare_planogram_snapshots(snap1, snap2)
        self.assertTrue(diff.is_identical)
        self.assertEqual(len(diff.added_upcs), 0)
        self.assertEqual(len(diff.removed_upcs), 0)

    def test_mode_c_planogram_diff_detects_changes(self):
        # v1 layout
        items_v1 = [
            {"section": "Bay 01", "shelf": 1, "position": 1, "upc": "111", "product_name": "Kept Prod", "horizontal_facing": 1},
            {"section": "Bay 01", "shelf": 1, "position": 2, "upc": "222", "product_name": "Removed Prod", "horizontal_facing": 1},
            {"section": "Bay 01", "shelf": 2, "position": 1, "upc": "333", "product_name": "Moved Prod", "horizontal_facing": 1},
        ]
        snap_v1 = self.exporter.build_canonical_snapshot(101, "cat", items=items_v1)

        # v2 layout (222 removed, 444 added, 333 moved to shelf 1, 111 facings increased from 1 to 2)
        items_v2 = [
            {"section": "Bay 01", "shelf": 1, "position": 1, "upc": "111", "product_name": "Kept Prod", "horizontal_facing": 2},
            {"section": "Bay 01", "shelf": 1, "position": 3, "upc": "333", "product_name": "Moved Prod", "horizontal_facing": 1},
            {"section": "Bay 01", "shelf": 2, "position": 1, "upc": "444", "product_name": "Added Prod", "horizontal_facing": 1},
        ]
        snap_v2 = self.exporter.build_canonical_snapshot(102, "cat", items=items_v2)

        diff = self.exporter.compare_planogram_snapshots(snap_v1, snap_v2)
        self.assertFalse(diff.is_identical)
        self.assertIn("444", diff.added_upcs)
        self.assertIn("222", diff.removed_upcs)
        self.assertEqual(len(diff.moved_upcs), 1)
        self.assertEqual(diff.moved_upcs[0]["upc"], "333")
        self.assertEqual(len(diff.facing_changes), 1)
        self.assertEqual(diff.facing_changes[0]["upc"], "111")
        self.assertEqual(diff.facing_changes[0]["from_facing"], 1)
        self.assertEqual(diff.facing_changes[0]["to_facing"], 2)


if __name__ == "__main__":
    unittest.main()
