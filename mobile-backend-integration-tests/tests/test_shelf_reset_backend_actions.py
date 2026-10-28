"""Shelf Reset Mobile shows the retailer action list without rewriting it."""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import runner_server
from core.backend_shelf_actions import present_backend_actions, validate_backend_shelf_actions


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
    def test_keeps_duplicates_and_unknown_actions_in_store_order(self):
        raw = [
            _row(9, "remove", current=_position("remove", "2", 3, 4)),
            _row(9, "remove", current=_position("remove", "2", 3, 4)),
            _row(4, "custom_future_action", expected=_position("custom_future_action", "1", 1, 2)),
            _row(2, "place_on_shelf_restock", expected=_position("place_on_shelf_restock", "1", 2, 1)),
        ]
        presented = present_backend_actions(raw)
        self.assertEqual([item["id"] for item in presented], [9, 9, 2, 4])
        self.assertEqual(
            [item["step_role"] for item in presented],
            ["remove", "remove", "restock", "other"],
        )
        self.assertEqual(presented[0]["backend_action"], "remove")
        self.assertEqual(presented[3]["backend_action"], "custom_future_action")
        self.assertNotIn("pull", [item["type"] for item in presented])

    def test_walks_identify_then_remove_then_each_bay(self):
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
            [(item["id"], item["step_role"], item["sequence_label"]) for item in presented],
            [
                (5, "identify", "All bays · Identify"),
                (4, "remove", "All bays · Remove"),
                (3, "set_aside", "Bay 01 · Set aside"),
                (6, "move_to_bay", "Bay 02 · Move to another bay"),
                (2, "fix_in_bay", "Bay 02 · Fix in bay"),
                (3, "add_to_shelf", "Bay 02 · Add to shelf"),
                (1, "restock", "Bay 02 · Restock"),
            ],
        )
        self.assertEqual(presented[2]["backend_action"], "set_aside")
        self.assertEqual(presented[3]["backend_action"], "fix_position_move_to_bay")
        self.assertEqual(presented[5]["backend_action"], "place_on_shelf_add_to_bay")
        self.assertTrue(all(not item["rule_flags"] for item in presented))

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

    def test_target_occupancy_follows_walk_order(self):
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
        self.assertEqual([item["id"] for item in presented], [2, 1, 3, 5, 4])
        self.assertIsNone(presented[0]["target_occupancy"])
        self.assertEqual(presented[1]["target_occupancy"]["status"], "vacant")
        self.assertEqual(presented[1]["target_occupancy"]["cleared_at_step"], 1)
        self.assertEqual(presented[2]["target_occupancy"]["status"], "occupied")
        self.assertEqual(presented[3]["target_occupancy"]["status"], "vacant")
        self.assertEqual(presented[3]["target_occupancy"]["cleared_at_step"], 2)
        self.assertEqual(presented[4]["target_occupancy"]["status"], "vacant")

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
            res_converted = runner_server.run_shelf_reset_backend_actions({"instance": "krcs", "task_id": 44093318})
            self.assertEqual(res_converted["converted_same_bay_set_asides"], 1)
            self.assertEqual(res_converted["validation"]["rule_check"]["same_bay_set_aside"], 0)
            self.assertEqual(len(res_converted["steps"]), 3)  # 1 step for same-bay + 2 steps for cross-bay

            res_unconverted = runner_server.run_shelf_reset_backend_actions({
                "instance": "krcs", "task_id": 44093318, "auto_convert_same_bay": False
            })
            self.assertEqual(res_unconverted["converted_same_bay_set_asides"], 0)
            self.assertEqual(res_unconverted["validation"]["rule_check"]["same_bay_set_aside"], 1)
            self.assertEqual(len(res_unconverted["steps"]), 4)  # 2 steps each



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
        self.assertIn("hidden", page[page.index('id="view-tab-rules"') - 80:page.index('id="view-tab-rules"') + 120])
