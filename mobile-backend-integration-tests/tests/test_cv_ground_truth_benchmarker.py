"""
Unit and Integration tests for CvGroundTruthBenchmarker.
Verifies spatial IoU calculation, bipartite matching, classification accuracy,
action precision/recall/F1 metrics, and scorecard generation.
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.cv_ground_truth_benchmarker import (
    CvBenchmarkReport,
    CvGroundTruthBenchmarker,
    calculate_iou,
)

WORKSPACE_DIR = Path(__file__).resolve().parents[2]


class IoUCalculationTests(unittest.TestCase):

    def test_exact_overlap_returns_one(self):
        box1 = [[0, 0], [10, 10]]
        box2 = [[0, 0], [10, 10]]
        self.assertAlmostEqual(calculate_iou(box1, box2), 1.0)

    def test_no_overlap_returns_zero(self):
        box1 = [[0, 0], [10, 10]]
        box2 = [[20, 20], [30, 30]]
        self.assertEqual(calculate_iou(box1, box2), 0.0)

    def test_partial_overlap_calculation(self):
        # Box 1: [0, 0, 10, 10] -> Area = 100
        # Box 2: [5, 0, 15, 10] -> Area = 100
        # Intersection: [5, 0, 10, 10] -> Area = 50
        # Union: 100 + 100 - 50 = 150
        # IoU = 50 / 150 = 1/3 ~ 0.333333
        box1 = [[0, 0], [10, 10]]
        box2 = [[5, 0], [15, 10]]
        self.assertAlmostEqual(calculate_iou(box1, box2), 50.0 / 150.0, places=5)

    def test_supports_different_box_formats(self):
        format_list_4 = [0, 0, 10, 10]
        format_dict = {"x1": 0, "y1": 0, "x2": 10, "y2": 10}
        format_nested = [[0, 0], [10, 10]]
        self.assertAlmostEqual(calculate_iou(format_list_4, format_nested), 1.0)
        self.assertAlmostEqual(calculate_iou(format_dict, format_nested), 1.0)

    def test_invalid_and_empty_boxes_safe(self):
        self.assertEqual(calculate_iou(None, [[0, 0], [10, 10]]), 0.0)
        self.assertEqual(calculate_iou([], []), 0.0)
        self.assertEqual(calculate_iou("invalid", [[0, 0], [10, 10]]), 0.0)


class CvGroundTruthBenchmarkerTests(unittest.TestCase):

    def setUp(self):
        self.benchmarker = CvGroundTruthBenchmarker(iou_threshold=0.5)
        self.gt_file = Path(__file__).resolve().parents[1] / "test-data" / "ground-truth" / "shelf_intelligence_gt.json"
        self.has_gt_file = self.gt_file.exists()
        if self.has_gt_file:
            self.gt_data = json.loads(self.gt_file.read_text(encoding="utf-8"))

    def test_perfect_detection_and_classification(self):
        ground_truth = [
            {"id": "g1", "upc": "111", "coordinates": [[0, 0], [10, 10]], "shelf": 1, "position": 1},
            {"id": "g2", "upc": "222", "coordinates": [[12, 0], [22, 10]], "shelf": 1, "position": 2},
        ]
        ai_detections = [
            {"id": "d1", "upc": "111", "coordinates": [[0, 0], [10, 10]], "shelf": 1, "position": 1},
            {"id": "d2", "upc": "222", "coordinates": [[12, 0], [22, 10]], "shelf": 1, "position": 2},
        ]

        report = self.benchmarker.evaluate(ai_detections, ground_truth)
        m = report.metrics

        self.assertEqual(m.true_positive_detections, 2)
        self.assertEqual(m.false_positive_detections, 0)
        self.assertEqual(m.false_negative_detections, 0)
        self.assertEqual(m.detection_precision, 1.0)
        self.assertEqual(m.detection_recall, 1.0)
        self.assertEqual(m.detection_f1, 1.0)
        self.assertEqual(m.classification_accuracy_pct, 100.0)
        self.assertEqual(m.shelf_position_accuracy_pct, 100.0)
        self.assertAlmostEqual(m.mean_iou, 1.0)

    def test_ghost_detection_lowers_precision(self):
        ground_truth = [
            {"id": "g1", "upc": "111", "coordinates": [[0, 0], [10, 10]], "shelf": 1, "position": 1},
        ]
        # AI detects real facing + 1 ghost facing
        ai_detections = [
            {"id": "d1", "upc": "111", "coordinates": [[0, 0], [10, 10]], "shelf": 1, "position": 1},
            {"id": "d2_ghost", "upc": "999", "coordinates": [[50, 50], [60, 60]], "shelf": 3, "position": 4},
        ]

        report = self.benchmarker.evaluate(ai_detections, ground_truth)
        m = report.metrics

        self.assertEqual(m.true_positive_detections, 1)
        self.assertEqual(m.false_positive_detections, 1)
        self.assertEqual(m.detection_precision, 0.5)
        self.assertEqual(m.detection_recall, 1.0)
        self.assertEqual(len(report.unmatched_detections), 1)

    def test_missed_facing_lowers_recall(self):
        ground_truth = [
            {"id": "g1", "upc": "111", "coordinates": [[0, 0], [10, 10]], "shelf": 1, "position": 1},
            {"id": "g2_missed", "upc": "222", "coordinates": [[20, 0], [30, 10]], "shelf": 1, "position": 2},
        ]
        ai_detections = [
            {"id": "d1", "upc": "111", "coordinates": [[0, 0], [10, 10]], "shelf": 1, "position": 1},
        ]

        report = self.benchmarker.evaluate(ai_detections, ground_truth)
        m = report.metrics

        self.assertEqual(m.true_positive_detections, 1)
        self.assertEqual(m.false_negative_detections, 1)
        self.assertEqual(m.detection_recall, 0.5)
        self.assertEqual(len(report.unmatched_gt), 1)

    def test_action_accuracy_confusion_matrix(self):
        gt_facings = [{"id": f"g{i}", "coordinates": [[i*10, 0], [(i+1)*10, 10]]} for i in range(5)]
        ai_facings = list(gt_facings)

        # Ground truth requires 2 actions: remove 111, move 222
        gt_actions = [
            {"upc": "111", "action": "remove"},
            {"upc": "222", "action": "place_on_shelf_add_to_bay"},
        ]
        # AI generated: remove 111 (TP), move 222 (TP), move 333 (FP - unnecessary)
        ai_actions = [
            {"upc": "111", "action": "remove"},
            {"upc": "222", "action": "place_on_shelf_add_to_bay"},
            {"upc": "333", "action": "fix_position_in_bay"},  # Unnecessary action
        ]

        report = self.benchmarker.evaluate(
            ai_detections=ai_facings,
            ground_truth_facings=gt_facings,
            ai_actions=ai_actions,
            ground_truth_actions=gt_actions,
        )
        m = report.metrics

        self.assertEqual(m.action_tp, 2)
        self.assertEqual(m.action_fp, 1)
        self.assertEqual(m.action_fn, 0)
        self.assertAlmostEqual(m.action_precision, 2.0 / 3.0, places=4)
        self.assertEqual(m.action_recall, 1.0)
        self.assertEqual(len(report.action_discrepancies), 1)
        self.assertEqual(report.action_discrepancies[0]["kind"], "FALSE_POSITIVE_ACTION")

    def test_scorecard_markdown_generation(self):
        ground_truth = [{"id": "g1", "upc": "111", "coordinates": [[0, 0], [10, 10]], "shelf": 1, "position": 1}]
        ai_detections = [{"id": "d1", "upc": "111", "coordinates": [[0, 0], [10, 10]], "shelf": 1, "position": 1}]
        report = self.benchmarker.evaluate(ai_detections, ground_truth, dataset_name="Test Suite Dataset")
        scorecard = report.generate_markdown_scorecard()

        self.assertIn("Computer Vision & AI Ground Truth Benchmark Scorecard", scorecard)
        self.assertIn("Mean IoU", scorecard)
        self.assertIn("Detection Precision", scorecard)
        self.assertIn("Action Precision", scorecard)

    def test_evaluate_against_curated_ground_truth_dataset(self):
        if not self.has_gt_file:
            self.skipTest("Curated ground truth fixture not found")

        gt_facings = self.gt_data["facings"]
        gt_actions = self.gt_data["expected_actions"]

        # Simulate high-accuracy AI predictions matching the ground truth
        simulated_ai_detections = [
            {
                "id": f"ai_{f['id']}",
                "upc": f["upc"],
                "product_title": f["product_title"],
                "coordinates": f["coordinates"],
                "shelf": f["shelf"],
                "position": f["position"],
            }
            for f in gt_facings
        ]
        simulated_ai_actions = list(gt_actions)

        report = self.benchmarker.evaluate(
            ai_detections=simulated_ai_detections,
            ground_truth_facings=gt_facings,
            ai_actions=simulated_ai_actions,
            ground_truth_actions=gt_actions,
            dataset_name=self.gt_data["name"],
        )
        m = report.metrics

        self.assertEqual(m.detection_f1, 1.0)
        self.assertEqual(m.classification_accuracy_pct, 100.0)
        self.assertEqual(m.action_f1, 1.0)
        self.assertEqual(m.action_tp, 3)
        self.assertEqual(m.action_fp, 0)
        self.assertEqual(m.action_fn, 0)


if __name__ == "__main__":
    unittest.main()
