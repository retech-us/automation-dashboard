"""Scan problem investigator: wrong-slot ok, same-slot moves, post-photo repeats."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.scan_issue_investigator import compare_realogram_positions, investigate_issue, parse_scan_url, planogram_slots


class ScanIssueInvestigatorTests(unittest.TestCase):
    def test_parse_reporting_url(self):
        parsed = parse_scan_url(
            "https://krcs.rebotics.net/reporting/scans/17806323?store=5346&category=830&planogram=1217193&date=2026-10-07"
        )
        self.assertEqual(parsed["scan_id"], "17806323")
        self.assertEqual(parsed["store"], "5346")
        self.assertEqual(parsed["planogram"], "1217193")
        self.assertEqual(parsed["base_url"], "https://krcs.rebotics.net")

    def test_horizontal_facings_share_one_product_slot(self):
        slots = planogram_slots(
            [{"section": "2", "shelf": 3, "position": 1, "horizontal_facing": 5, "product": {"id": 9, "name": "Oxi"}}],
            {"9": {"upc": "033200003984", "title": "Oxi"}},
        )
        self.assertEqual(slots[("2", "3:1")]["upc"], "033200003984")
        self.assertNotIn(("2", "3:2"), slots)

    def test_ok_on_wrong_slot_is_the_led_finding_when_the_problem_says_ok(self):
        report = investigate_issue(
            "why is this product ok when the location does not match the planogram",
            [{
                "id": 1,
                "section": "1",
                "stage": "pre_photo",
                "items": [{
                    "upc": "070200551640",
                    "label": "LEMON",
                    "pos": "7:1",
                    "action_type": "ACTION_CORRECT",
                    "type": "ok",
                }],
                "actions": [],
            }],
            {
                ("1", "7:1"): {"upc": "070200551619", "name": "HOMESTYLE"},
                ("1", "7:2"): {"upc": "070200551640", "name": "LEMON"},
            },
        )
        self.assertEqual(report["focus"], "wrong_slot_ok")
        self.assertEqual(report["counts"]["wrong_slot_ok"], 1)
        self.assertIn("shelf", report["root_cause"])
        self.assertIn("ACTION_CORRECT", report["how_to_solve"])

    def test_same_slot_move_explains_the_set_aside(self):
        report = investigate_issue(
            "why does it ask to set aside a product that is already in the correct slot",
            [{
                "id": 2,
                "section": "1",
                "stage": "pre_photo",
                "items": [{
                    "upc": "030772171066",
                    "label": "TIDE PODS",
                    "pos": "4:1",
                    "action_type": "ACTION_MOVE",
                    "type": "ok",
                }],
                "actions": [{
                    "upc": "030772171066",
                    "action": "ACTION_MOVE",
                    "reason": "Add Item",
                    "from": "4:1",
                    "to": "4:1",
                    "state": "STATE_ACCEPTED",
                }],
            }],
            {("1", "4:1"): {"upc": "030772171066", "name": "TIDE PODS"}},
        )
        self.assertEqual(report["counts"]["same_slot_actions"], 1)
        self.assertIn("same slot", report["problem"])
        self.assertIn("set-aside", report["root_cause"])

    def test_post_photo_repeats_a_pre_photo_same_slot_action(self):
        action = {
            "upc": "033200977193",
            "action": "ACTION_MOVE",
            "reason": "Add Item",
            "from": "6:2",
            "to": "6:2",
            "state": "STATE_ACCEPTED",
        }
        item = {
            "upc": "033200977193",
            "label": "AHMR",
            "pos": "6:2",
            "action_type": "ACTION_MOVE",
            "type": "ok",
        }
        report = investigate_issue(
            "why does post photo processing ask for the same action on a corrected product",
            [
                {"id": 10, "section": "2", "stage": "pre_photo", "items": [item], "actions": [action]},
                {"id": 11, "section": "2", "stage": "post_photo", "items": [item], "actions": [action]},
            ],
            {("2", "6:2"): {"upc": "033200977193", "name": "AHMR"}},
        )
        self.assertEqual(report["counts"]["post_photo_repeats"], 1)
        self.assertIn("Post-photo", report["root_cause"])
        self.assertEqual(report["findings"][0]["code"], "POST_PHOTO_REPEATS_SAME_SLOT")

    def test_evidence_explains_each_slot_and_merges_repeats(self):
        action = {"upc": "030772172391", "action": "ACTION_MOVE", "reason": "Add Item", "from": "6:2", "to": "6:2", "state": "STATE_ACCEPTED"}
        item = {"upc": "030772172391", "label": "TIDE", "pos": "6:2", "action_type": "ACTION_MOVE", "type": "ok"}
        report = investigate_issue(
            "show every problem in this visit",
            [
                {"id": 20, "section": "4", "stage": "pre_photo", "items": [item], "actions": [action]},
                {"id": 21, "section": "4", "stage": "post_photo", "items": [item], "actions": [action]},
                {"id": 22, "section": "1", "stage": "pre_photo", "items": [
                    {"upc": "070200551640", "label": "LEMON", "pos": "7:1", "action_type": "ACTION_CORRECT", "type": "ok"},
                ], "actions": []},
            ],
            {
                ("4", "6:2"): {"upc": "030772172391", "name": "TIDE"},
                ("1", "7:1"): {"upc": "070200551619", "name": "HOMESTYLE"},
                ("1", "7:2"): {"upc": "070200551640", "name": "LEMON"},
            },
        )
        findings = {row["upc"]: row for row in report["findings"]}
        self.assertEqual(len(report["findings"]), 2)

        tide = findings["030772172391"]
        self.assertEqual(tide["code"], "POST_PHOTO_REPEATS_SAME_SLOT")
        self.assertEqual(tide["product"], "TIDE")
        self.assertEqual(tide["stages"], ["pre-photo", "post-photo"])
        self.assertEqual(
            tide["issue_labels"],
            ["Move to the same slot", "Post-photo repeats the same-slot move"],
        )
        self.assertEqual([issue["scan_id"] for issue in tide["issues"]], [20, 21])
        self.assertIn("6:2 → 6:2", tide["detail"])
        self.assertIn("Add Item", tide["detail"])

        lemon = findings["070200551640"]
        self.assertEqual(lemon["issue_labels"], ["Marked OK in the wrong slot"])
        self.assertEqual(lemon["expected_upc"], "070200551619")
        self.assertEqual(lemon["expected_product"], "HOMESTYLE")
        self.assertEqual(lemon["belongs_at"], "7:2")
        self.assertIn("HOMESTYLE", lemon["detail"])

    def test_report_lists_scan_actions_and_flags_the_ones_tied_to_findings(self):
        report = investigate_issue(
            "why does it ask to set aside a product that is already in the correct slot",
            [{
                "id": 30,
                "section": "2",
                "stage": "pre_photo",
                "items": [{"upc": "111", "label": "SOAP", "pos": "3:1", "action_type": "ACTION_MOVE", "type": "ok"}],
                "actions": [
                    {"upc": "111", "action": "ACTION_MOVE", "reason": "Add Item", "from": "3:1", "to": "3:1", "state": "STATE_ACCEPTED"},
                    {"upc": "222", "action": "ACTION_REMOVE", "reason": "Remove", "from": "5:4", "to": "", "state": "STATE_NEW"},
                ],
            }],
            {("2", "3:1"): {"upc": "111", "name": "SOAP"}, ("2", "1:1"): {"upc": "222", "name": "SHAMPOO"}},
        )
        actions = report["actions"]
        self.assertEqual(len(actions), 2)
        self.assertEqual(actions[0]["product"], "SOAP")
        self.assertEqual(actions[0]["stage"], "pre-photo")
        self.assertEqual((actions[0]["from"], actions[0]["to"]), ("3:1", "3:1"))
        self.assertEqual(actions[0]["issues"], ["Move to the same slot"])
        self.assertEqual(actions[1]["product"], "SHAMPOO")
        self.assertEqual(actions[1]["issues"], [])

    def test_report_with_no_scan_actions_returns_an_empty_list(self):
        report = investigate_issue(
            "why is this ok",
            [{"id": 40, "section": "1", "stage": "pre_photo", "items": [], "actions": []}],
            {},
        )
        self.assertEqual(report["actions"], [])
        self.assertEqual(report["findings"], [])

    def test_counts_products_seen_away_from_their_planogram_slot(self):
        report = compare_realogram_positions(
            [{
                "id": 1,
                "section": "1",
                "stage": "pre_photo",
                "items": [
                    {"upc": "070200551640", "label": "LEMON", "pos": "7:1", "type": "ok"},
                    {"upc": "070200551640", "label": "LEMON", "pos": "7:1", "type": "ok"},
                    {"upc": "811892026807", "label": "CABO", "pos": "2:1", "type": "ok"},
                    {"upc": "999", "label": "INVADER", "pos": "1:1", "type": "invader"},
                ],
            }],
            {
                ("1", "7:1"): {"upc": "070200551619", "name": "HOMESTYLE"},
                ("1", "7:2"): {"upc": "070200551640", "name": "LEMON"},
                ("1", "2:1"): {"upc": "811892026807", "name": "CABO"},
            },
        )
        self.assertEqual(report["different_position"], 1)
        self.assertEqual(report["same_position"], 1)
        self.assertEqual(report["not_on_planogram"], 1)
        self.assertEqual(report["examples"][0]["belongs_at"], "1 7:2")


if __name__ == "__main__":
    unittest.main()
