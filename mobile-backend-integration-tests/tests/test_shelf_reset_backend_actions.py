"""Shelf Reset Mobile shows the retailer action list without rewriting it."""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import runner_server
from core.backend_shelf_actions import (
    blocked_summary,
    mobile_display_actions,
    present_backend_actions,
    shelf_products_from_scans,
    shelf_slots_from_backend_actions,
    validate_backend_shelf_actions,
)


HOST = "https://harr.rebotics.net"


def _row(action_id, action, current=None, expected=None, **extra):
    row = {
        "id": action_id,
        "state": extra.pop("state", "STATE_IDLE"),
        "reason": extra.pop("reason", "planogram"),
        "product_title": extra.pop("product_title", "Sample product"),
        "upc": extra.pop("upc", "012345678905"),
        "current_position": current,
        "expected_position": expected,
    }
    row.update(extra)
    return row


def _position(action, bay="1", shelf=1, position=1):
    return {
        "action": action,
        "shelf": shelf,
        "position": position,
        "section_info": {"name": bay},
    }


class BackendActionPresentationTests(unittest.TestCase):
    def test_keeps_duplicates_and_unknown_actions_in_backend_order(self):
        raw = [
            _row(9, "remove", current=_position("remove", "2", 3, 4)),
            _row(9, "remove", current=_position("remove", "2", 3, 4)),
            _row(4, "custom_future_action", expected=_position("custom_future_action", "1", 1, 2)),
            _row(2, "place_on_shelf_restock", expected=_position("place_on_shelf_restock", "1", 2, 1)),
        ]
        presented = present_backend_actions(raw)
        self.assertEqual([item["id"] for item in presented], [9, 9, 4, 2])
        self.assertEqual(
            [item["step_role"] for item in presented],
            ["remove", "remove", "other", "restock"],
        )
        self.assertEqual(presented[0]["backend_action"], "remove")
        self.assertEqual(presented[2]["backend_action"], "custom_future_action")
        self.assertNotIn("pull", [item["type"] for item in presented])

    def test_steps_follow_the_order_the_backend_returned(self):
        raw = [
            _row(1, "place_on_shelf_restock", expected=_position("place_on_shelf_restock", "02", 1, 1), product_title="Restock"),
            _row(2, "fix_position_fix_in_bay",
                 current=_position("fix_position_fix_in_bay", "02", 1, 2),
                 expected=_position("fix_position_fix_in_bay", "02", 1, 3), product_title="Fix"),
            _row(3, "ACTION_MOVE",
                 current=_position("set_aside", "01", 4, 1),
                 expected=_position("place_on_shelf_add_to_bay", "02", 2, 1), product_title="Staged"),
            _row(4, "remove", current=_position("remove", "09", 1, 1), product_title="Gone"),
            _row(5, "identify", current=_position("identify", "08", 1, 1), product_title="Scan"),
            _row(6, "ACTION_MOVE",
                 current=_position(None, "02", 3, 1),
                 expected=_position("fix_position_move_to_bay", "01", 1, 4), product_title="Moved"),
        ]
        presented = present_backend_actions(raw)
        self.assertEqual(
            [(item["index"], item["id"], item["step_role"]) for item in presented],
            [
                (1, 1, "restock"),
                (2, 2, "fix_in_bay"),
                (3, 3, "set_aside"),
                (4, 3, "add_to_shelf"),
                (5, 4, "remove"),
                (6, 5, "identify"),
                (7, 6, "move_to_bay"),
            ],
        )
        self.assertEqual({item["sequence_label"] for item in presented}, {"Backend order"})
        self.assertEqual(presented[2]["backend_action"], "set_aside")
        self.assertEqual(presented[3]["backend_action"], "place_on_shelf_add_to_bay")
        self.assertEqual(presented[6]["backend_action"], "fix_position_move_to_bay")
        self.assertTrue(all(not item["rule_flags"] for item in presented))

    def test_mobile_shows_identify_then_remove_then_each_bay(self):
        raw = [
            _row(1, "place_on_shelf_restock", expected=_position("place_on_shelf_restock", "02", 1, 1), product_title="Restock"),
            _row(2, "fix_position_fix_in_bay",
                 current=_position("fix_position_fix_in_bay", "02", 1, 2),
                 expected=_position("fix_position_fix_in_bay", "02", 1, 3), product_title="Fix"),
            _row(3, "ACTION_MOVE",
                 current=_position("set_aside", "01", 4, 1),
                 expected=_position("place_on_shelf_add_to_bay", "02", 2, 1), product_title="Staged"),
            _row(4, "remove", current=_position("remove", "09", 1, 1), product_title="Gone"),
            _row(5, "identify", current=_position("identify", "08", 1, 1), product_title="Scan"),
            _row(6, "ACTION_MOVE",
                 current=_position(None, "02", 3, 1),
                 expected=_position("fix_position_move_to_bay", "01", 1, 4), product_title="Moved"),
        ]
        mobile = mobile_display_actions(raw)
        self.assertEqual(
            [(step["id"], step["step_role"], step["sequence_label"]) for step in mobile["steps"]],
            [
                (5, "identify", "All bays · Identify"),
                (4, "remove", "All bays · Remove"),
                (3, "set_aside", "Bay 01 · Set aside"),
                (2, "fix_in_bay", "Bay 02 · Fix in bay"),
                (6, "move_to_bay", "Bay 02 · Pick from"),
                (3, "add_to_shelf", "Bay 02 · Add to shelf"),
                (1, "restock", "Bay 02 · Restock"),
            ],
        )
        self.assertEqual(mobile["hidden"], [])
        self.assertEqual([step["id"] for step in present_backend_actions(raw)], [1, 2, 3, 3, 4, 5, 6])

    def test_mobile_order_clears_a_destination_that_the_backend_order_blocks(self):
        raw = [
            _row(1, "place_on_shelf_restock", expected=_position("place_on_shelf_restock", "1", 1, 1),
                 product_title="Incoming", upc="111"),
            _row(2, "remove", current=_position("remove", "1", 1, 1), product_title="Old", upc="222"),
        ]
        backend = present_backend_actions(raw)
        self.assertEqual(backend[0]["target_occupancy"]["status"], "occupied_cleared_later")
        mobile = mobile_display_actions(raw)["steps"]
        self.assertEqual([step["id"] for step in mobile], [2, 1])
        self.assertEqual(mobile[1]["target_occupancy"]["status"], "vacant")
        self.assertEqual(mobile[1]["target_occupancy"]["cleared_at_step"], 1)

    def test_mobile_hides_finished_repeated_and_unknown_actions_without_dropping_them(self):
        raw = [
            _row(1, "identify", current=_position("identify", "1", 1, 1), state="STATE_ACCEPTED"),
            _row(1, "identify", current=_position("identify", "1", 1, 2)),
            _row(2, "custom_future_action", expected=_position("custom_future_action", "1", 2, 1)),
            _row(3, "remove", current=_position("remove", "1", 3, 1)),
        ]
        mobile = mobile_display_actions(raw)
        self.assertEqual([(step["id"], step["step_role"]) for step in mobile["steps"]], [(1, "identify"), (3, "remove")])
        hidden = {step["id"]: step["mobile_note"] for step in mobile["hidden"]}
        self.assertEqual(len(mobile["hidden"]), 2)
        self.assertIn("Already handled", hidden[1])
        self.assertIn("no step", hidden[2])
        self.assertTrue(all(step["on_mobile"] is False for step in mobile["hidden"]))

    def test_only_backend_actions_become_cards(self):
        raw = [
            _row(1, "fix_position_fix_in_bay",
                 current=_position("fix_position_fix_in_bay", "1", 7, 6),
                 expected=_position("fix_position_fix_in_bay", "1", 7, 5), product_title="A", upc="1"),
            _row(2, "fix_position_fix_in_bay",
                 current=_position("fix_position_fix_in_bay", "1", 7, 5),
                 expected=_position("fix_position_fix_in_bay", "1", 7, 6), product_title="B", upc="2"),
            _row(3, "ACTION_MOVE",
                 current=_position(None, "1", 2, 1),
                 expected=_position("fix_position_move_to_bay", "3", 4, 2), product_title="C", upc="3"),
            _row(4, "new_backend_action", current=_position("new_backend_action", "2", 1, 1)),
        ]
        presented = present_backend_actions(raw)
        self.assertEqual(len(presented), 4)
        kinds = {item["movement"]["kind"] for item in presented}
        self.assertFalse(kinds & {"swap", "slide_left", "slide_right", "shelf_up", "shelf_down"})
        fixes = [item for item in presented if item["step_role"] == "fix_in_bay"]
        self.assertEqual([item["movement"]["kind"] for item in fixes], ["same_bay", "same_bay"])
        move = next(item for item in presented if item["id"] == 3)
        self.assertEqual(move["step_role"], "move_to_bay")
        self.assertEqual(move["movement"]["kind"], "change_bay")
        self.assertEqual(move["upc"], "3")
        unknown = next(item for item in presented if item["id"] == 4)
        self.assertEqual(unknown["action_label"], "new_backend_action")

    def test_swap_or_slide_shown_only_when_backend_sends_it(self):
        raw = [
            _row(1, "ACTION_SWAP",
                 current=_position(None, "1", 2, 1),
                 expected=_position("swap", "1", 2, 2), upc="11"),
        ]
        step = present_backend_actions(raw)[0]
        self.assertEqual(step["movement"]["kind"], "backend_swap")
        report = validate_backend_shelf_actions(raw)
        self.assertEqual(report["rule_check"]["backend_swap_actions"], 1)
        self.assertEqual(report["rule_check"]["backend_slide_actions"], 0)

    def test_red_flags_same_bay_set_aside_and_same_bay_moves_outside_fix_in_bay(self):
        raw = [
            _row(1, "ACTION_MOVE",
                 current=_position("set_aside", "1", 2, 7),
                 expected=_position("place_on_shelf_add_to_bay", "1", 2, 3),
                 product_title="Same bay staged", upc="038000175930"),
            _row(2, "ACTION_MOVE",
                 current=_position(None, "1", 3, 1),
                 expected=_position("fix_position_move_to_bay", "1", 3, 4),
                 product_title="Wrong action", upc="070501064320"),
            _row(3, "ACTION_MOVE",
                 current=_position(None, "1", 4, 1),
                 expected=_position("fix_position_fix_in_bay", "2", 4, 1),
                 product_title="Fix across bays", upc="038000304965"),
            _row(4, "ACTION_MOVE",
                 current=_position(None, "1", 5, 1),
                 expected=_position("fix_position_fix_in_bay", "1", 5, 2),
                 product_title="Correct fix", upc="070501069707"),
            _row(5, "ACTION_MOVE",
                 current=_position("set_aside", "1", 6, 1),
                 expected=_position("place_on_shelf_add_to_bay", "2", 6, 1),
                 product_title="Correct set aside", upc="012345678905"),
        ]
        presented = present_backend_actions(raw)
        codes = {item["id"]: [flag["code"] for flag in item["rule_flags"]] for item in presented}
        self.assertEqual(codes[1], ["SAME_BAY_SET_ASIDE"])
        self.assertEqual(codes[2], ["SAME_BAY_MOVE_NOT_FIX_IN_BAY"])
        self.assertEqual(codes[3], ["FIX_IN_BAY_ACROSS_BAYS"])
        self.assertEqual(codes[4], [])
        self.assertEqual(codes[5], [])
        flagged = next(item for item in presented if item["id"] == 1)
        self.assertIn("038000175930", flagged["rule_flags"][0]["message"])
        self.assertEqual(sum(1 for item in presented if item["id"] == 1), 2)
        report = validate_backend_shelf_actions(raw)
        self.assertEqual(report["rule_check"]["same_bay_set_aside"], 1)
        self.assertEqual(report["rule_check"]["same_bay_move_not_fix_in_bay"], 1)
        self.assertEqual(report["rule_check"]["fix_in_bay_across_bays"], 1)
        self.assertEqual(report["rule_check"]["rows_breaking_rules"], 3)
        self.assertEqual(report["state"], "blocked")

    def test_restock_onto_the_same_place_is_not_a_rule_break(self):
        raw = [
            _row(1, "place_on_shelf_restock",
                 current=_position("place_on_shelf_restock", "1", 2, 3),
                 expected=_position("place_on_shelf_restock", "1", 2, 3),
                 product_title="Backroom item", upc="111"),
            _row(2, "place_on_shelf_restock",
                 current=_position(None, "1", 2, 1),
                 expected=_position("place_on_shelf_restock", "1", 4, 1),
                 product_title="Same bay restock", upc="222"),
        ]
        presented = present_backend_actions(raw)
        self.assertEqual(presented[0]["rule_flags"], [])
        self.assertEqual(presented[1]["rule_flags"], [])
        findings = validate_backend_shelf_actions(raw)["findings"]
        codes = {item["code"] for item in findings}
        self.assertNotIn("REDUNDANT_SAME_SLOT_MOVE", codes)
        self.assertNotIn("SAME_BAY_MOVE_NOT_FIX_IN_BAY", codes)
        same_place = [item for item in findings if 1 in (item.get("action_ids") or [])]
        self.assertEqual(same_place, [])

    def test_a_move_is_flagged_when_another_product_is_sent_there_first(self):
        raw = [
            _row(1, "fix_position_fix_in_bay",
                 current=_position("fix_position_fix_in_bay", "1", 1, 2),
                 expected=_position("fix_position_fix_in_bay", "1", 1, 1),
                 product_title="Incoming", upc="111"),
            _row(2, "fix_position_move_to_bay",
                 current=_position("fix_position_move_to_bay", "1", 1, 1),
                 expected=_position("fix_position_move_to_bay", "2", 1, 1),
                 product_title="Leaves later", upc="222"),
        ]
        presented = present_backend_actions(raw)
        blocked = presented[0]["target_occupancy"]
        self.assertEqual(blocked["status"], "occupied_cleared_later")
        self.assertEqual(blocked["occupant_kind"], "moves_later")
        self.assertIn("needs to move", blocked["occupant_note"])
        self.assertIn("step 2", blocked["occupant_note"])
        self.assertIn("step 1", presented[1]["sequence_flag"])
        self.assertIn("Incoming", presented[1]["sequence_flag"])
        self.assertIn("before", presented[0]["target_occupancy"]["occupant_note"])

    def test_destination_is_blocked_when_its_product_leaves_only_later(self):
        raw = [
            _row(1, "place_on_shelf_add_to_bay",
                 current=_position("place_on_shelf_add_to_bay", "1", 1, 9),
                 expected=_position("place_on_shelf_add_to_bay", "1", 1, 1), product_title="New", upc="10"),
            _row(2, "remove", current=_position("remove", "1", 1, 1), product_title="Old", upc="20"),
            _row(3, "place_on_shelf_restock", expected=_position("place_on_shelf_restock", "1", 1, 1),
                 product_title="Restocked", upc="30"),
            _row(4, "place_on_shelf_restock", expected=_position("place_on_shelf_restock", "1", 2, 2),
                 product_title="Fresh", upc="40"),
            _row(5, "place_on_shelf_restock", expected=_position("place_on_shelf_restock", "1", 1, 9),
                 product_title="Into vacated", upc="50"),
        ]
        presented = present_backend_actions(raw)
        self.assertEqual([item["id"] for item in presented], [1, 2, 3, 4, 5])
        first = presented[0]["target_occupancy"]
        self.assertEqual(first["status"], "occupied_cleared_later")
        self.assertTrue(first["blocking"])
        self.assertEqual(first["cleared_at_step"], 2)
        self.assertEqual(first["occupant_product"], "Old")
        self.assertEqual(first["occupant_upc"], "20")
        self.assertIsNone(presented[1]["target_occupancy"])
        self.assertEqual(presented[2]["target_occupancy"]["status"], "vacant")
        self.assertEqual(presented[2]["target_occupancy"]["cleared_at_step"], 2)
        self.assertEqual(presented[3]["target_occupancy"]["status"], "vacant")
        self.assertEqual(presented[4]["target_occupancy"]["status"], "vacant")
        self.assertEqual(presented[4]["target_occupancy"]["cleared_at_step"], 1)

    def test_destination_is_vacant_when_the_backend_removes_its_product_first(self):
        raw = [
            _row(2, "remove", current=_position("remove", "1", 1, 1), product_title="Old", upc="20"),
            _row(1, "place_on_shelf_restock", expected=_position("place_on_shelf_restock", "1", 1, 1),
                 product_title="New", upc="10"),
        ]
        presented = present_backend_actions(raw)
        self.assertEqual([item["id"] for item in presented], [2, 1])
        occupancy = presented[1]["target_occupancy"]
        self.assertEqual(occupancy["status"], "vacant")
        self.assertEqual(occupancy["cleared_at_step"], 1)
        self.assertNotIn("blocking", occupancy)

    def test_shelf_scan_product_with_no_action_blocks_its_slot(self):
        raw = [
            _row(1, "place_on_shelf_restock", expected=_position("place_on_shelf_restock", "01", 3, 2),
                 product_title="Incoming", upc="111"),
            _row(2, "place_on_shelf_restock", expected=_position("place_on_shelf_restock", "01", 3, 4),
                 product_title="Matches shelf", upc="333"),
        ]
        shelf = {
            ("1", "3", "2"): {"product": "Marked OK here", "upc": "222"},
            ("1", "3", "4"): {"product": "Matches shelf", "upc": "333"},
        }
        presented = present_backend_actions(raw, shelf_products=shelf)
        blocked = presented[0]["target_occupancy"]
        self.assertEqual(blocked["status"], "occupied")
        self.assertTrue(blocked["blocking"])
        self.assertEqual(blocked["occupant_product"], "Marked OK here")
        self.assertEqual(blocked["occupant_upc"], "222")
        self.assertEqual(blocked["occupant_source"], "shelf_scan")
        self.assertFalse(blocked["occupant_has_action"])
        self.assertEqual(presented[1]["target_occupancy"]["status"], "vacant")
        self.assertEqual(present_backend_actions(raw)[0]["target_occupancy"]["status"], "vacant")

    def test_blocked_destination_says_whether_the_product_there_is_marked_ok(self):
        def blocked_by(scan_item, extra_rows=()):
            raw = [
                _row(1, "place_on_shelf_restock", expected=_position("place_on_shelf_restock", "1", 3, 2),
                     product_title="Incoming", upc="111"),
                *extra_rows,
            ]
            shelf = shelf_products_from_scans([{"stage": "pre_photo", "section": "1", "items": [scan_item]}])
            return present_backend_actions(raw, shelf_products=shelf)[0]["target_occupancy"]

        ok = blocked_by({"upc": "222", "label": "Shelf product", "on_shelf_position": "3:2", "type": "ok"})
        self.assertEqual(ok["occupant_kind"], "marked_ok")
        self.assertIn("marked OK", ok["occupant_note"])
        self.assertIn("no action", ok["occupant_note"])

        other = blocked_by({"upc": "222", "label": "Shelf product", "on_shelf_position": "3:2", "type": "unknown"})
        self.assertEqual(other["occupant_kind"], "detected_no_action")
        self.assertIn("not marked OK", other["occupant_note"])
        self.assertIn("unknown", other["occupant_note"])

        later = blocked_by(
            {"upc": "222", "label": "Shelf product", "on_shelf_position": "3:2", "type": "ok"},
            extra_rows=[_row(2, "remove", current=_position("remove", "1", 3, 2), product_title="Shelf product", upc="222")],
        )
        self.assertEqual(later["occupant_kind"], "moves_later")
        self.assertEqual(later["status"], "occupied_cleared_later")
        self.assertIn("needs to move", later["occupant_note"])
        self.assertIn("before that move", later["occupant_note"])

        identify_only = blocked_by(
            {"upc": "", "label": "", "on_shelf_position": "3:2", "type": "unknown"},
            extra_rows=[_row(3, "identify", current=_position("identify", "1", 3, 2), product_title="Unidentified", upc="")],
        )
        self.assertEqual(identify_only["status"], "occupied")
        self.assertEqual(identify_only["occupant_kind"], "has_action")
        self.assertIn("identify", identify_only["occupant_note"])
        self.assertIn("does not take it off", identify_only["occupant_note"])

    def test_blocker_placed_by_an_earlier_step_is_named_as_such(self):
        raw = [
            _row(1, "place_on_shelf_restock", expected=_position("place_on_shelf_restock", "1", 1, 1),
                 product_title="First", upc="111"),
            _row(2, "place_on_shelf_restock", expected=_position("place_on_shelf_restock", "1", 1, 1),
                 product_title="Second", upc="222"),
        ]
        second = present_backend_actions(raw)[1]["target_occupancy"]
        self.assertEqual(second["occupant_kind"], "placed_earlier")
        self.assertIn("placed here at step 1", second["occupant_note"])

    def test_blocked_summary_counts_blockers_by_what_holds_the_position(self):
        raw = [
            _row(1, "place_on_shelf_restock", expected=_position("place_on_shelf_restock", "1", 1, 1),
                 product_title="A", upc="1"),
            _row(2, "place_on_shelf_restock", expected=_position("place_on_shelf_restock", "1", 2, 1),
                 product_title="B", upc="2"),
            _row(3, "place_on_shelf_restock", expected=_position("place_on_shelf_restock", "1", 3, 1),
                 product_title="C", upc="3"),
            _row(4, "remove", current=_position("remove", "1", 3, 1), product_title="Leaves", upc="4"),
            _row(5, "place_on_shelf_restock", expected=_position("place_on_shelf_restock", "1", 4, 1),
                 product_title="D", upc="5"),
        ]
        shelf = shelf_products_from_scans([{"stage": "pre_photo", "section": "1", "items": [
            {"upc": "90", "label": "OK product", "on_shelf_position": "1:1", "type": "ok"},
            {"upc": "91", "label": "Seen only", "on_shelf_position": "2:1", "type": "unknown"},
            {"upc": "4", "label": "Leaves", "on_shelf_position": "3:1", "type": "ok"},
        ]}])
        counts = blocked_summary(present_backend_actions(raw, shelf_products=shelf))
        self.assertEqual(counts, {"total": 3, "marked_ok": 1, "no_action": 1, "moves_later": 1, "other": 0})
        self.assertEqual(blocked_summary([]), {"total": 0, "marked_ok": 0, "no_action": 0, "moves_later": 0, "other": 0})

    def test_blocked_finding_repeats_the_occupant_note(self):
        raw = [
            _row(1, "place_on_shelf_restock", expected=_position("place_on_shelf_restock", "1", 3, 2),
                 product_title="Incoming", upc="111"),
        ]
        shelf = shelf_products_from_scans([{"stage": "pre_photo", "section": "1", "items": [
            {"upc": "222", "label": "Shelf product", "on_shelf_position": "3:2", "type": "ok"},
        ]}])
        found = [item for item in validate_backend_shelf_actions(raw, shelf_products=shelf)["findings"]
                 if item["code"] == "OCCUPIED_DESTINATION"]
        self.assertEqual(found[0]["occupant_kind"], "marked_ok")
        self.assertIn("marked OK", found[0]["message"])

    def test_shelf_scan_product_with_a_later_removal_is_cleared_later(self):
        raw = [
            _row(1, "place_on_shelf_restock", expected=_position("place_on_shelf_restock", "1", 1, 1),
                 product_title="Incoming", upc="111"),
            _row(2, "remove", current=_position("remove", "1", 1, 1), product_title="Old", upc="222"),
        ]
        shelf = {("1", "1", "1"): {"product": "Old", "upc": "222"}}
        occupancy = present_backend_actions(raw, shelf_products=shelf)[0]["target_occupancy"]
        self.assertEqual(occupancy["status"], "occupied_cleared_later")
        self.assertEqual(occupancy["cleared_at_step"], 2)
        self.assertTrue(occupancy["occupant_has_action"])

    def test_occupied_target_names_blocking_product_and_upc(self):
        raw = [
            _row(1, "place_on_shelf_restock",
                 expected=_position("place_on_shelf_restock", "1", 1, 1),
                 product_title="Incoming", upc="111"),
            _row(2, "identify", current=_position("identify", "1", 1, 1),
                 product_title="Blocking product", upc="222"),
        ]
        restock = next(item for item in present_backend_actions(raw) if item["id"] == 1)
        occupancy = restock["target_occupancy"]
        self.assertEqual(occupancy["status"], "occupied")
        self.assertEqual(occupancy["occupant_product"], "Blocking product")
        self.assertEqual(occupancy["occupant_upc"], "222")
        self.assertTrue(occupancy["blocking"])
        self.assertIn("no earlier step moves or removes it", occupancy["text"])

    def test_validation_reports_findings_without_changing_rows(self):
        raw = [
            _row(
                1,
                "fix_position_fix_in_bay",
                current=_position("fix_position_fix_in_bay", "1", 1, 1),
                expected=_position("fix_position_fix_in_bay", "1", 1, 1),
            ),
            _row(1, "identify", current=_position("identify", "1", 1, 2)),
        ]
        original = json.dumps(raw)
        report = validate_backend_shelf_actions(raw)
        self.assertEqual(json.dumps(raw), original)
        self.assertEqual(len(present_backend_actions(raw)), 2)
        codes = {item["code"] for item in report["findings"]}
        self.assertIn("REDUNDANT_SAME_SLOT_MOVE", codes)
        self.assertIn("DUPLICATE_ACTION", codes)
        self.assertEqual(report["state"], "blocked")

    def _findings(self, raw, code, **kwargs):
        return [item for item in validate_backend_shelf_actions(raw, **kwargs)["findings"] if item["code"] == code]

    def test_sequence_check_reports_destinations_cleared_after_they_are_needed(self):
        raw = [
            _row(1, "place_on_shelf_restock", expected=_position("place_on_shelf_restock", "1", 1, 1),
                 product_title="Incoming", upc="111"),
            _row(2, "remove", current=_position("remove", "1", 1, 1), product_title="Old", upc="222"),
        ]
        report = validate_backend_shelf_actions(raw)
        later = [item for item in report["findings"] if item["code"] == "DESTINATION_CLEARED_LATER"]
        self.assertEqual(len(later), 1)
        self.assertEqual(later[0]["severity"], "critical")
        self.assertEqual(later[0]["action_ids"], [1])
        self.assertEqual(later[0]["index"], 1)
        self.assertEqual(later[0]["cleared_at_step"], 2)
        self.assertIn("Old", later[0]["message"])
        self.assertEqual(report["sequence_check"]["order"], "backend")
        self.assertEqual(report["sequence_check"]["destination_cleared_later"], 1)
        self.assertEqual(report["sequence_check"]["destination_never_cleared"], 0)
        self.assertEqual(report["state"], "blocked")
        flipped = validate_backend_shelf_actions(list(reversed(raw)))
        self.assertEqual(flipped["sequence_check"]["blocked_destinations"], 0)
        self.assertFalse([item for item in flipped["findings"] if item["code"] == "DESTINATION_CLEARED_LATER"])

    def test_sequence_check_reports_destinations_never_cleared(self):
        raw = [
            _row(1, "place_on_shelf_restock", expected=_position("place_on_shelf_restock", "1", 2, 2),
                 product_title="Incoming", upc="111"),
        ]
        shelf = {("1", "2", "2"): {"product": "Marked OK here", "upc": "222"}}
        found = self._findings(raw, "OCCUPIED_DESTINATION", shelf_products=shelf)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["action_ids"], [1])
        self.assertEqual(found[0]["occupant_product"], "Marked OK here")
        self.assertIn("Marked OK here", found[0]["message"])
        self.assertFalse(self._findings(raw, "OCCUPIED_DESTINATION"))

    def test_two_direct_moves_into_each_others_slots_wait_on_each_other(self):
        raw = [
            _row(1, "fix_position_fix_in_bay",
                 current=_position("fix_position_fix_in_bay", "1", 1, 1),
                 expected=_position("fix_position_fix_in_bay", "1", 1, 2), product_title="A", upc="1"),
            _row(2, "fix_position_fix_in_bay",
                 current=_position("fix_position_fix_in_bay", "1", 1, 2),
                 expected=_position("fix_position_fix_in_bay", "1", 1, 1), product_title="B", upc="2"),
            _row(3, "fix_position_fix_in_bay",
                 current=_position("fix_position_fix_in_bay", "1", 2, 1),
                 expected=_position("fix_position_fix_in_bay", "1", 2, 2), product_title="C", upc="3"),
            _row(4, "remove", current=_position("remove", "1", 2, 2), product_title="D", upc="4"),
        ]
        mutual = self._findings(raw, "MUTUAL_BLOCK")
        self.assertEqual(len(mutual), 1)
        self.assertEqual(sorted(mutual[0]["action_ids"]), [1, 2])
        self.assertEqual(mutual[0]["severity"], "critical")
        self.assertIn("each other", mutual[0]["message"].lower())
        # Step numbers differ between the two orders, so the message names actions, not steps.
        self.assertIn("Actions 1, 2", mutual[0]["message"])
        self.assertNotIn("Steps", mutual[0]["message"])

    def test_backend_named_swap_is_not_reported_as_a_deadlock(self):
        raw = [
            _row(1, "ACTION_SWAP", current=_position(None, "1", 1, 1),
                 expected=_position("swap", "1", 1, 2), product_title="A", upc="1"),
            _row(2, "ACTION_SWAP", current=_position(None, "1", 1, 2),
                 expected=_position("swap", "1", 1, 1), product_title="B", upc="2"),
        ]
        self.assertFalse(self._findings(raw, "MUTUAL_BLOCK"))

    def test_set_aside_with_no_destination_is_reported(self):
        raw = [_row(7, "ACTION_MOVE", current=_position("set_aside", "1", 1, 1), product_title="Held", upc="9")]
        found = self._findings(raw, "SET_ASIDE_WITHOUT_PLACEMENT")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["action_ids"], [7])
        self.assertEqual(found[0]["severity"], "warning")

    def test_every_blocked_step_has_a_matching_finding(self):
        raw = [
            _row(1, "place_on_shelf_restock", expected=_position("place_on_shelf_restock", "1", 1, 1),
                 product_title="One", upc="111"),
            _row(2, "remove", current=_position("remove", "1", 1, 1), product_title="Two", upc="222"),
            _row(3, "place_on_shelf_restock", expected=_position("place_on_shelf_restock", "1", 5, 5),
                 product_title="Three", upc="333"),
        ]
        shelf = {("1", "5", "5"): {"product": "Stuck", "upc": "444"}}
        steps = present_backend_actions(raw, shelf_products=shelf)
        report = validate_backend_shelf_actions(raw, shelf_products=shelf)
        blocked_ids = {step["id"] for step in steps if (step["target_occupancy"] or {}).get("blocking")}
        finding_ids = {
            action_id
            for item in report["findings"]
            if item["code"] in ("OCCUPIED_DESTINATION", "DESTINATION_CLEARED_LATER")
            for action_id in item["action_ids"]
        }
        self.assertEqual(blocked_ids, {1, 3})
        self.assertEqual(finding_ids, blocked_ids)
        self.assertEqual(report["sequence_check"]["blocked_destinations"], 2)


class ShelfScanOccupantTests(unittest.TestCase):
    def test_shelf_map_shows_the_before_photo_product_standing_in_a_destination(self):
        raw = [
            _row(1, "place_on_shelf_restock", expected=_position("place_on_shelf_restock", "01", 3, 2),
                 product_title="Incoming", upc="111"),
        ]
        shelf = {("1", "3", "2"): {"product": "Marked OK here", "upc": "222"}, ("1", "9", "9"): {"product": "Elsewhere", "upc": "5"}}
        slots = {slot["id"]: slot for slot in shelf_slots_from_backend_actions(raw, shelf_products=shelf)}
        self.assertEqual(slots["Bay01_S3_P2"]["current"], "Marked OK here")
        self.assertEqual(slots["Bay01_S3_P2"]["target"], "Incoming")
        self.assertEqual(len(slots), 1)
        self.assertIsNone(shelf_slots_from_backend_actions(raw)[0]["current"])

    def test_reads_every_detected_product_slot_from_the_before_photo(self):
        scans = [
            {
                "stage": "pre_photo",
                "section": "01",
                "items": [
                    {"upc": "222", "label": "Marked OK here", "on_shelf_position": "3:2", "type": "ok"},
                    {"upc": "222", "label": "Marked OK here", "on_shelf_position": "3:2", "type": "ok"},
                    {"upc": "", "label": "", "on_shelf_position": "3:5", "type": "unknown"},
                    {"upc": "999", "label": "Gone", "on_shelf_position": "3:6", "type": "missing"},
                    {"upc": "888", "label": "No slot", "on_shelf_position": "", "type": "ok"},
                ],
            },
            {
                "stage": "post_photo",
                "section": "01",
                "items": [{"upc": "777", "label": "After", "on_shelf_position": "1:1", "type": "ok"}],
            },
        ]
        found = shelf_products_from_scans(scans)
        self.assertEqual(found[("01", "3", "2")], {"product": "Marked OK here", "upc": "222", "scan_type": "ok"})
        self.assertEqual(found[("01", "3", "5")], {"product": "Unidentified product", "upc": "", "scan_type": "unknown"})
        self.assertNotIn(("01", "3", "6"), found)
        self.assertNotIn(("01", "1", "1"), found)
        self.assertEqual(len(found), 2)


class ShelfResetBackendEndpointTests(unittest.TestCase):
    def setUp(self):
        self._saved_tokens = dict(runner_server.INSTANCE_TOKENS)
        self._saved_token = runner_server.TOKEN
        runner_server.INSTANCE_TOKENS.clear()
        runner_server.TOKEN = None
        persist = patch.object(runner_server, "remember_instance_tokens", lambda: None)
        persist.start()
        self.addCleanup(persist.stop)

    def tearDown(self):
        runner_server.INSTANCE_TOKENS.clear()
        runner_server.INSTANCE_TOKENS.update(self._saved_tokens)
        runner_server.TOKEN = self._saved_token

    def test_credentials_load_live_rows_in_order(self):
        raw = [
            _row(3, "remove", current=_position("remove")),
            _row(8, "place_on_shelf_add_to_bay", expected=_position("place_on_shelf_add_to_bay", "4", 2, 2)),
        ]

        def fake_access(host, base_url, username, password, supplied_token):
            self.assertEqual(username, "associate")
            self.assertEqual(password, "secret")
            self.assertEqual(supplied_token, "")
            return "fresh-token", "credentials"

        with patch.object(runner_server, "investigation_access", fake_access), \
             patch.object(runner_server, "fetch_live_task_actions", return_value=(raw, "https://harr.rebotics.net/actions")):
            result = runner_server.run_shelf_reset_backend_actions({
                "instance": "harr",
                "task_id": "8648127",
                "username": "associate",
                "password": "secret",
                "token": "stale-token",
            })

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["source"], "live")
        self.assertEqual([step["id"] for step in result["steps"]], [3, 8])
        self.assertEqual(result["action_count"], 2)
        self.assertNotIn("secret", json.dumps(result))
        self.assertNotIn("fresh-token", json.dumps(result))
        self.assertNotIn("stale-token", json.dumps(result))

    def test_missing_sign_in_asks_for_credentials(self):
        result = runner_server.run_shelf_reset_backend_actions({"instance": "harr", "task_id": 1})
        self.assertEqual(result["error_code"], "AUTH_REQUIRED")
        self.assertIn("username", result["message"].lower())

    def test_rejected_token_is_forgotten(self):
        runner_server.INSTANCE_TOKENS[HOST] = "expired-token"
        runner_server.TOKEN = "expired-token"

        def fake_access(*_args):
            return "expired-token", "saved"

        with patch.object(runner_server, "investigation_access", fake_access), \
             patch.object(runner_server, "fetch_live_task_actions", side_effect=runner_server.LiveActionsAuthError("rejected")):
            result = runner_server.run_shelf_reset_backend_actions({"instance": "harr", "task_id": 1})

        self.assertEqual(result["error_code"], "AUTH_REQUIRED")
        self.assertNotIn(HOST, runner_server.INSTANCE_TOKENS)

    def test_empty_action_list_stays_empty(self):
        def fake_access(*_args):
            return "token", "saved"

        with patch.object(runner_server, "investigation_access", fake_access), \
             patch.object(runner_server, "fetch_live_task_actions", side_effect=ValueError("Task #1 on https://harr.rebotics.net has no actions yet.")), \
             patch.object(runner_server, "_shelf_task_scan_status", return_value="NO_CAPTURE"):
            result = runner_server.run_shelf_reset_backend_actions({"instance": "harr", "task_id": 1})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["steps"], [])
        self.assertIn("no shelf capture", result["message"])
        self.assertEqual(result["source"], "live")

    def test_auto_convert_same_bay_set_aside_to_fix_in_bay(self):
        raw = [
            _row(1, "ACTION_MOVE",
                 current=_position("set_aside", "2", 2, 7),
                 expected=_position("place_on_shelf_add_to_bay", "2", 2, 1),
                 product_title="Cool Whip Lite", upc="038000175930"),
            _row(2, "ACTION_MOVE",
                 current=_position("set_aside", "2", 6, 2),
                 expected=_position("place_on_shelf_add_to_bay", "3", 6, 2),
                 product_title="Lemon Cream Pie", upc="012345678905"),
        ]
        from core.backend_shelf_actions import convert_same_bay_set_asides_to_fix_in_bay
        converted, count = convert_same_bay_set_asides_to_fix_in_bay(raw)
        self.assertEqual(count, 1)
        self.assertEqual(converted[0]["current_position"]["action"], "fix_position_fix_in_bay")
        self.assertEqual(converted[0]["expected_position"]["action"], "fix_position_fix_in_bay")
        self.assertEqual(converted[1]["current_position"]["action"], "set_aside")

        def fake_access(*_args):
            return "token", "saved"

        with patch.object(runner_server, "investigation_access", fake_access), \
             patch.object(runner_server, "fetch_shelf_reset_actions", return_value=(raw, "https://krcs.rebotics.net/actions")):
            res_default = runner_server.run_shelf_reset_backend_actions({"instance": "krcs", "task_id": 44093318})
            self.assertEqual(res_default["converted_same_bay_set_asides"], 0)
            self.assertEqual(res_default["validation"]["rule_check"]["same_bay_set_aside"], 1)
            self.assertEqual(len(res_default["steps"]), 4)  # 2 steps each, rows untouched
            self.assertEqual(raw[0]["current_position"]["action"], "set_aside")

            res_converted = runner_server.run_shelf_reset_backend_actions({
                "instance": "krcs", "task_id": 44093318, "auto_convert_same_bay": True
            })
            self.assertEqual(res_converted["converted_same_bay_set_asides"], 1)
            self.assertEqual(res_converted["validation"]["rule_check"]["same_bay_set_aside"], 0)
            self.assertEqual(len(res_converted["steps"]), 3)  # 1 step for same-bay + 2 steps for cross-bay

    def test_endpoint_keeps_backend_order_and_reports_the_sequence_check(self):
        raw = [
            _row(8, "place_on_shelf_restock", expected=_position("place_on_shelf_restock", "1", 1, 1),
                 product_title="Incoming", upc="111"),
            _row(3, "remove", current=_position("remove", "1", 1, 1), product_title="Old", upc="222"),
        ]

        def fake_access(*_args):
            return "token", "saved"

        with patch.object(runner_server, "investigation_access", fake_access), \
             patch.object(runner_server, "fetch_shelf_reset_actions", return_value=(raw, "https://harr.rebotics.net/actions")):
            result = runner_server.run_shelf_reset_backend_actions({"instance": "harr", "task_id": 5})

        self.assertEqual([step["id"] for step in result["steps"]], [8, 3])
        self.assertEqual([step["id"] for step in result["mobile_steps"]], [3, 8])
        self.assertEqual(result["mobile_steps"][0]["sequence_label"], "All bays · Remove")
        self.assertEqual(result["mobile_steps"][1]["sequence_label"], "Bay 1 · Restock")
        self.assertEqual(result["steps"][0]["target_occupancy"]["status"], "occupied_cleared_later")
        self.assertEqual(result["sequence"]["order"], "backend")
        self.assertEqual(result["sequence"]["blocked_destinations"], 1)
        self.assertEqual(result["validation"]["sequence_check"]["destination_cleared_later"], 1)
        self.assertEqual(result["shelf_scan"]["status"], "not_used")
        self.assertIn("order the backend returned", result["message"])
        # The phone order removes the old product first, so only the backend order is blocked here.
        self.assertEqual(result["blocked_summary"]["backend"]["total"], 1)
        self.assertEqual(result["blocked_summary"]["mobile"]["total"], 0)

    def test_endpoint_checks_destinations_against_the_before_photo(self):
        raw = [
            _row(1, "place_on_shelf_restock",
                 expected={**_position("place_on_shelf_restock", "01", 3, 2), "scan_id": 555},
                 product_title="Incoming", upc="111"),
        ]
        scan_payload = {
            "id": 555, "stage": "pre_photo", "section": "01",
            "items": [{"upc": "222", "label": "Marked OK here", "on_shelf_position": "3:2", "type": "ok"}],
        }

        def fake_access(*_args):
            return "token", "saved"

        with patch.object(runner_server, "investigation_access", fake_access), \
             patch.object(runner_server, "fetch_shelf_reset_actions", return_value=(raw, "https://harr.rebotics.net/actions")), \
             patch.object(runner_server, "fetch_scan_payloads", return_value=[scan_payload]) as fetched:
            result = runner_server.run_shelf_reset_backend_actions({"instance": "harr", "task_id": 5})

        self.assertEqual(fetched.call_args.args[2], [555])
        occupancy = result["steps"][0]["target_occupancy"]
        self.assertEqual(occupancy["status"], "occupied")
        self.assertEqual(occupancy["occupant_product"], "Marked OK here")
        self.assertEqual(result["shelf_scan"], {"status": "used", "scans": 1, "positions": 1})
        self.assertEqual(result["validation"]["sequence_check"]["destination_never_cleared"], 1)
        self.assertEqual(occupancy["occupant_kind"], "marked_ok")
        self.assertEqual(result["blocked_summary"]["mobile"]["marked_ok"], 1)
        self.assertEqual(result["blocked_summary"]["backend"]["marked_ok"], 1)

    def test_endpoint_says_so_when_the_before_photo_cannot_be_read(self):
        raw = [
            _row(1, "place_on_shelf_restock",
                 expected={**_position("place_on_shelf_restock", "01", 3, 2), "scan_id": 555},
                 product_title="Incoming", upc="111"),
        ]

        def fake_access(*_args):
            return "token", "saved"

        with patch.object(runner_server, "investigation_access", fake_access), \
             patch.object(runner_server, "fetch_shelf_reset_actions", return_value=(raw, "https://harr.rebotics.net/actions")), \
             patch.object(runner_server, "fetch_scan_payloads", side_effect=RuntimeError("scan service down")):
            result = runner_server.run_shelf_reset_backend_actions({"instance": "harr", "task_id": 5})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["shelf_scan"]["status"], "unavailable")
        self.assertIn("scan service down", result["shelf_scan"]["message"])
        self.assertEqual(result["validation"]["sequence_check"]["occupancy_source"], "action_rows")



class ShelfResetMobileContractTests(unittest.TestCase):
    def test_page_loads_live_actions_and_keeps_password_out_of_storage(self):
        page = (ROOT / "shelf_reset_mobile.html").read_text(encoding="utf-8")
        load_start = page.index("async function loadDataset")
        load_end = page.index("function loadLocalFallback")
        load_body = page[load_start:load_end]
        save_start = page.index("function saveSession")
        save_end = page.index("function restoreSession")
        save_body = page[save_start:save_end]

        self.assertIn("/api/runner/shelf_reset/backend_actions", load_body)
        catalog_start = page.index("async function ensureInstanceSignIn")
        catalog_end = page.index("function normalizeBay")
        catalog_body = page[catalog_start:catalog_end]
        history_at = catalog_body.index("/api/runner/ir_history")
        self.assertLess(catalog_body.index("ensureInstanceSignIn"), history_at)
        self.assertLess(history_at, catalog_body.index("data.signed_in"))
        self.assertLess(catalog_body.index("data.signed_in"), catalog_body.index("populateTaskOptions"))
        self.assertIn("auth_status", catalog_body)
        self.assertIn("submitCredentials", page)
        self.assertIn('id="shelf-username"', page)
        self.assertIn('id="shelf-password"', page)
        self.assertNotIn("shelf_reset/sequence", load_body)
        self.assertNotIn("ir_tasks", load_body)
        self.assertNotIn("clientSideSequenceSlots", load_body)
        self.assertNotIn("loadLocalFallback", load_body)
        self.assertNotIn("password", save_body)

    def test_page_keeps_the_task_loaded_in_the_intelligent_reset_tab(self):
        page = (ROOT / "shelf_reset_mobile.html").read_text(encoding="utf-8")
        catalog = page[page.index("async function loadTasksForInstance"):page.index("function normalizeBay")]
        self.assertIn("const chosen = requested || tasks[0].task_id", catalog)
        self.assertNotIn("selectedTask && tasks.some", catalog)
        listener = page[page.index("window.addEventListener('message'"):page.index("const urlParams")]
        self.assertIn('loadTasksForInstance(state.instance, syncedTask || state.dataset, { submitCredentials: true })', listener)
        self.assertIn("syncedTask = String(taskId)", listener)
        self.assertIn("loadTasksForInstance(state.instance, syncedTask);", page)

        flow = (ROOT / "assets/js/ir-flow.js").read_text(encoding="utf-8")
        app = (ROOT / "assets/js/app.v16.js").read_text(encoding="utf-8")
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("function openShelfMobile(frame, baseSrc, forceReload)", flow)
        self.assertIn("task_id=${encodeURIComponent(loadedTask.taskId)}", flow)
        self.assertIn("IrTaskFlow.openShelfMobile(frame, mobileSrc)", app)
        # The frame has no source until the tab opens, so its first load carries the task.
        frame_tag = index[index.index('<iframe id="iframe-shelf-mobile"'):]
        frame_tag = frame_tag[:frame_tag.index(">")]
        self.assertNotIn(" src=", frame_tag)
        self.assertIn("openShelfMobile(f, 'shelf_reset_mobile.html?v=20261106e', true)", index)
        self.assertIn("IrTaskFlow.shelfMobileUrl('shelf_reset_mobile.html')", index)

    def test_page_marks_every_blocked_destination_and_reports_the_sequence(self):
        page = (ROOT / "shelf_reset_mobile.html").read_text(encoding="utf-8")
        self.assertIn('id="sequence-check"', page)
        self.assertIn('id="order-mode-mobile"', page)
        self.assertIn("function setOrderMode", page)
        self.assertIn("state.mobileSteps", page)
        self.assertIn('data-type="BLOCKED"', page)
        self.assertIn("function renderSequenceCheck", page)
        self.assertIn("blockedDestinations", page)
        self.assertIn('filterType === "BLOCKED"', page)
        self.assertNotIn("identify, remove, then each bay", page)
        self.assertNotIn("Identify and remove cover every bay first", page)
        self.assertIn("const look = { ...occupancyStyle(s.target_occupancy) }", page)

    def test_page_explains_each_block_inside_the_action_sequence(self):
        page = (ROOT / "shelf_reset_mobile.html").read_text(encoding="utf-8")
        self.assertIn("Where the associate gets blocked", page)
        self.assertIn("Marked OK · no action", page)
        self.assertIn("function blockerSentence", page)
        # A row under each blocked step puts the reason inside the sequence the associate follows.
        self.assertIn("blockerRowHtml(s)", page)
        # The three phases of the associate app are named in the panel.
        self.assertIn("① Identify all bays", page)
        self.assertIn("② Remove all bays", page)
        self.assertIn("③ Bay by bay", page)
        self.assertIn("pick from", page)
        self.assertIn("Needs to move first", page)
        self.assertIn("state.blockedSummary", page)
        self.assertIn("hidden", page[page.index('id="view-tab-rules"') - 80:page.index('id="view-tab-rules"') + 120])
