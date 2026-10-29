"""
Shelf Intelligence Quality Automation — Computer Vision & AI Ground Truth Benchmarker.
Validates AI computer vision detection quality, bounding box IoU accuracy, product classification,
and shelf action precision/recall against authoritative ground truth datasets.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


def _normalize_box(box: Any) -> Optional[Tuple[float, float, float, float]]:
    """
    Normalizes bounding box representations into (x1, y1, x2, y2).
    Supported formats:
    - [[x1, y1], [x2, y2]]
    - [x1, y1, x2, y2]
    - {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
    """
    if not box:
        return None
    try:
        if isinstance(box, (list, tuple)):
            if len(box) == 2 and isinstance(box[0], (list, tuple)) and isinstance(box[1], (list, tuple)):
                x1, y1 = float(box[0][0]), float(box[0][1])
                x2, y2 = float(box[1][0]), float(box[1][1])
                return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)
            elif len(box) == 4:
                x1, y1, x2, y2 = float(box[0]), float(box[1]), float(box[2]), float(box[3])
                return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)
        elif isinstance(box, dict):
            if "x1" in box and "y1" in box and "x2" in box and "y2" in box:
                x1, y1, x2, y2 = float(box["x1"]), float(box["y1"]), float(box["x2"]), float(box["y2"])
                return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)
    except (ValueError, TypeError, IndexError):
        return None
    return None


def calculate_iou(box_a: Any, box_b: Any) -> float:
    """
    Calculates Intersection over Union (IoU) between two bounding boxes.
    Returns float in range [0.0, 1.0].
    """
    norm_a = _normalize_box(box_a)
    norm_b = _normalize_box(box_b)
    if not norm_a or not norm_b:
        return 0.0

    ax1, ay1, ax2, ay2 = norm_a
    bx1, by1, bx2, by2 = norm_b

    # Intersection coordinates
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)

    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    intersection_area = inter_w * inter_h

    if intersection_area <= 0.0:
        return 0.0

    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    union_area = area_a + area_b - intersection_area

    if union_area <= 0.0:
        return 0.0

    return float(intersection_area / union_area)


@dataclass
class DetectionMatch:
    detection_id: Any
    gt_id: Any
    iou: float
    detected_upc: str
    gt_upc: str
    classification_correct: bool
    shelf_matched: bool
    position_matched: bool


@dataclass
class CvBenchmarkMetrics:
    total_ground_truth_facings: int
    total_ai_detections: int
    true_positive_detections: int
    false_positive_detections: int  # Ghost detections
    false_negative_detections: int  # Missed facings
    detection_precision: float
    detection_recall: float
    detection_f1: float
    mean_iou: float
    classification_accuracy_pct: float
    shelf_position_accuracy_pct: float
    action_precision: float
    action_recall: float
    action_f1: float
    action_tp: int
    action_fp: int
    action_fn: int
    action_tn: int


@dataclass
class CvBenchmarkReport:
    task_id: Any
    dataset_name: str
    metrics: CvBenchmarkMetrics
    matches: List[DetectionMatch] = field(default_factory=list)
    unmatched_detections: List[Dict[str, Any]] = field(default_factory=list)
    unmatched_gt: List[Dict[str, Any]] = field(default_factory=list)
    action_discrepancies: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def generate_markdown_scorecard(self) -> str:
        m = self.metrics
        det_grade = "PASSED" if m.detection_f1 >= 0.85 else "NEEDS_IMPROVEMENT"
        act_grade = "PASSED" if m.action_f1 >= 0.85 else "NEEDS_IMPROVEMENT"

        lines = [
            f"# Computer Vision & AI Ground Truth Benchmark Scorecard",
            f"**Dataset / Task:** {self.dataset_name} (Task #{self.task_id})",
            "",
            "## 1. Facing Detection & Spatial Accuracy (IoU)",
            f"| Metric | Result | Benchmark Target | Status |",
            f"| :--- | :--- | :--- | :--- |",
            f"| **Mean IoU** | {m.mean_iou:.3f} | $\\ge 0.700$ | {'✅ OK' if m.mean_iou >= 0.70 else '⚠️ Low'} |",
            f"| **Detection Precision** | {m.detection_precision * 100:.1f}% | $\\ge 90.0\\%$ | {'✅ OK' if m.detection_precision >= 0.9 else '⚠️ Low'} |",
            f"| **Detection Recall** | {m.detection_recall * 100:.1f}% | $\\ge 90.0\\%$ | {'✅ OK' if m.detection_recall >= 0.9 else '⚠️ Low'} |",
            f"| **Detection F1 Score** | {m.detection_f1:.3f} | $\\ge 0.850$ | {det_grade} |",
            "",
            "## 2. Product Classification & Positioning Accuracy",
            f"| Metric | Result | Benchmark Target | Status |",
            f"| :--- | :--- | :--- | :--- |",
            f"| **Classification Accuracy (UPC)** | {m.classification_accuracy_pct:.1f}% | $\\ge 95.0\\%$ | {'✅ OK' if m.classification_accuracy_pct >= 95.0 else '⚠️ Low'} |",
            f"| **Shelf Position Match** | {m.shelf_position_accuracy_pct:.1f}% | $\\ge 95.0\\%$ | {'✅ OK' if m.shelf_position_accuracy_pct >= 95.0 else '⚠️ Low'} |",
            "",
            "## 3. Action Generation Accuracy (True/False Action Generation)",
            f"| Metric | Count / Score | Interpretation |",
            f"| :--- | :--- | :--- |",
            f"| **True Positives (TP)** | {m.action_tp} | Correct actions generated for true shelf discrepancies |",
            f"| **False Positives (FP)** | {m.action_fp} | Unnecessary / incorrect action cards generated |",
            f"| **False Negatives (FN)** | {m.action_fn} | Required shelf actions missed by AI |",
            f"| **True Negatives (TN)** | {m.action_tn} | Correctly un-moved compliant facings |",
            f"| **Action Precision** | {m.action_precision * 100:.1f}% | Ratio of valid generated actions |",
            f"| **Action Recall** | {m.action_recall * 100:.1f}% | Coverage of necessary shelf fixes |",
            f"| **Action F1 Score** | {m.action_f1:.3f} | Harmonized action quality rating |",
        ]
        return "\n".join(lines)


class CvGroundTruthBenchmarker:
    """
    Evaluates AI shelf detections and generated actions against Ground Truth annotations.
    """

    def __init__(self, iou_threshold: float = 0.5):
        self.iou_threshold = iou_threshold

    def evaluate(
        self,
        ai_detections: List[Dict[str, Any]],
        ground_truth_facings: List[Dict[str, Any]],
        ai_actions: Optional[List[Dict[str, Any]]] = None,
        ground_truth_actions: Optional[List[Dict[str, Any]]] = None,
        task_id: Any = "Benchmark-001",
        dataset_name: str = "Shelf Ground Truth Dataset",
    ) -> CvBenchmarkReport:
        """
        Executes complete spatial IoU bipartite matching, classification accuracy check,
        and action confusion matrix calculation.
        """
        matches: List[DetectionMatch] = []
        unmatched_det: List[Dict[str, Any]] = []
        unmatched_gt: List[Dict[str, Any]] = []

        # 1. Spatial IoU Matrix Calculation
        matched_gt_indices: Set[int] = set()
        matched_det_indices: Set[int] = set()
        ious: List[float] = []

        # Calculate all pair IoUs
        pair_candidates = []
        for d_idx, det in enumerate(ai_detections):
            d_box = det.get("coordinates") or det.get("bbox")
            for g_idx, gt in enumerate(ground_truth_facings):
                g_box = gt.get("coordinates") or gt.get("bbox")
                score = calculate_iou(d_box, g_box)
                if score >= self.iou_threshold:
                    pair_candidates.append((score, d_idx, g_idx))

        # Greedy bipartite matching by highest IoU
        pair_candidates.sort(key=lambda x: x[0], reverse=True)
        for score, d_idx, g_idx in pair_candidates:
            if d_idx in matched_det_indices or g_idx in matched_gt_indices:
                continue

            matched_det_indices.add(d_idx)
            matched_gt_indices.add(g_idx)
            ious.append(score)

            det = ai_detections[d_idx]
            gt = ground_truth_facings[g_idx]

            det_upc = str(det.get("displayed_upc") or det.get("upc") or "").strip()
            gt_upc = str(gt.get("displayed_upc") or gt.get("upc") or "").strip()
            class_ok = bool(det_upc and gt_upc and det_upc == gt_upc)

            det_shelf = det.get("shelf")
            gt_shelf = gt.get("shelf")
            shelf_ok = (det_shelf is not None and gt_shelf is not None and str(det_shelf) == str(gt_shelf))

            det_pos = det.get("position")
            gt_pos = gt.get("position")
            pos_ok = (det_pos is not None and gt_pos is not None and str(det_pos) == str(gt_pos))

            matches.append(
                DetectionMatch(
                    detection_id=det.get("id", d_idx),
                    gt_id=gt.get("id", g_idx),
                    iou=score,
                    detected_upc=det_upc,
                    gt_upc=gt_upc,
                    classification_correct=class_ok,
                    shelf_matched=shelf_ok,
                    position_matched=pos_ok,
                )
            )

        for d_idx, det in enumerate(ai_detections):
            if d_idx not in matched_det_indices:
                unmatched_det.append(det)

        for g_idx, gt in enumerate(ground_truth_facings):
            if g_idx not in matched_gt_indices:
                unmatched_gt.append(gt)

        # Metrics computation
        tp_det = len(matches)
        fp_det = len(unmatched_det)
        fn_det = len(unmatched_gt)

        det_prec = tp_det / (tp_det + fp_det) if (tp_det + fp_det) > 0 else 0.0
        det_rec = tp_det / (tp_det + fn_det) if (tp_det + fn_det) > 0 else 0.0
        det_f1 = (2 * det_prec * det_rec) / (det_prec + det_rec) if (det_prec + det_rec) > 0 else 0.0
        mean_iou = sum(ious) / len(ious) if ious else 0.0

        class_correct = sum(1 for m in matches if m.classification_correct)
        class_acc = (class_correct / tp_det * 100.0) if tp_det > 0 else 0.0

        pos_correct = sum(1 for m in matches if (m.shelf_matched and m.position_matched))
        pos_acc = (pos_correct / tp_det * 100.0) if tp_det > 0 else 0.0

        # 2. Action Generation Confusion Matrix Evaluation
        action_discrepancies: List[Dict[str, Any]] = []
        act_tp = 0
        act_fp = 0
        act_fn = 0
        act_tn = 0

        gen_actions = ai_actions or []
        gt_actions = ground_truth_actions or []

        # Map actions by UPC or slot key
        def _action_key(act: Dict[str, Any]) -> Tuple[str, str]:
            u = str(act.get("upc") or act.get("displayed_upc") or "").strip()
            typ = str(act.get("action") or act.get("type") or "").strip().lower()
            return u, typ

        gt_act_map = {_action_key(a): a for a in gt_actions if _action_key(a)[0]}
        matched_gt_acts = set()

        for a in gen_actions:
            key = _action_key(a)
            if not key[0]:
                continue
            if key in gt_act_map:
                act_tp += 1
                matched_gt_acts.add(key)
            else:
                act_fp += 1
                action_discrepancies.append({
                    "kind": "FALSE_POSITIVE_ACTION",
                    "action": a,
                    "reason": f"AI generated {key[1]} for UPC {key[0]} but Ground Truth does not require it.",
                })

        for key, a in gt_act_map.items():
            if key not in matched_gt_acts:
                act_fn += 1
                action_discrepancies.append({
                    "kind": "FALSE_NEGATIVE_ACTION",
                    "action": a,
                    "reason": f"Ground Truth requires {key[1]} for UPC {key[0]} but AI failed to generate it.",
                })

        # Calculate True Negatives: matched items that correctly required no action
        total_facings = max(len(ground_truth_facings), len(ai_detections))
        total_discrepancies = len(gt_act_map)
        act_tn = max(0, total_facings - total_discrepancies - act_fp)

        act_prec = act_tp / (act_tp + act_fp) if (act_tp + act_fp) > 0 else (1.0 if act_fn == 0 else 0.0)
        act_rec = act_tp / (act_tp + act_fn) if (act_tp + act_fn) > 0 else 1.0
        act_f1 = (2 * act_prec * act_rec) / (act_prec + act_rec) if (act_prec + act_rec) > 0 else 0.0

        metrics = CvBenchmarkMetrics(
            total_ground_truth_facings=len(ground_truth_facings),
            total_ai_detections=len(ai_detections),
            true_positive_detections=tp_det,
            false_positive_detections=fp_det,
            false_negative_detections=fn_det,
            detection_precision=det_prec,
            detection_recall=det_rec,
            detection_f1=det_f1,
            mean_iou=mean_iou,
            classification_accuracy_pct=class_acc,
            shelf_position_accuracy_pct=pos_acc,
            action_precision=act_prec,
            action_recall=act_rec,
            action_f1=act_f1,
            action_tp=act_tp,
            action_fp=act_fp,
            action_fn=act_fn,
            action_tn=act_tn,
        )

        return CvBenchmarkReport(
            task_id=task_id,
            dataset_name=dataset_name,
            metrics=metrics,
            matches=matches,
            unmatched_detections=unmatched_det,
            unmatched_gt=unmatched_gt,
            action_discrepancies=action_discrepancies,
        )
