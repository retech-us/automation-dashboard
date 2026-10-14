"""Contracts for the IR Studio live-only Existing Task workflow."""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import runner_server
from core.action_generation_validator import validate_action_generation


class _Response:
    def __init__(self, payload):
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self._body


class IrStudioLiveContractTests(unittest.TestCase):
    @staticmethod
    def _move(action_id, source, target, title="Product"):
        return {
            "id": action_id,
            "upc": str(action_id),
            "product_title": title,
            "action": "fix_position_in_bay",
            "state": "STATE_IDLE",
            "current_position": {
                "action": "fix_position_in_bay",
                "section_info": {"id": 1, "name": "1"},
                "shelf": 1,
                "position": source,
            },
            "expected_position": {
                "action": "fix_position_in_bay",
                "section_info": {"id": 1, "name": "1"},
                "shelf": 1,
                "position": target,
            },
        }

    def test_fetch_live_actions_follows_pagination(self):
        pages = [
            _Response({"results": [{"id": 1}], "next": "/page/2"}),
            _Response({"results": [{"id": 2}], "next": None}),
        ]
        with patch("runner_server.urllib.request.urlopen", side_effect=pages) as mocked:
            rows, source = runner_server.fetch_live_task_actions(
                "https://example.rebotics.net", 42, "token"
            )

        self.assertEqual([row["id"] for row in rows], [1, 2])
        self.assertIn("/action-list/retailer/", source)
        self.assertIn("version=2", source)
        self.assertNotIn("setbay=", source)
        requested = [call.args[0].full_url for call in mocked.call_args_list]
        self.assertEqual(mocked.call_count, 2)
        self.assertTrue(all("version=2" in url and "type=set_bay" not in url for url in requested))

    def test_set_bay_request_uses_the_current_section_name(self):
        pages = [
            _Response({"results": [{"id": 9, "current_position": {"section_info": {"name": "2"}}}], "next": "/page/2"}),
            _Response({"results": [{"id": 10}], "next": None}),
        ]
        with patch("runner_server.urllib.request.urlopen", side_effect=pages) as mocked:
            rows, source = runner_server.fetch_live_task_actions(
                "https://example.rebotics.net", 42, "token", section="2"
            )

        self.assertEqual([row["id"] for row in rows], [9, 10])
        requested = [call.args[0].full_url for call in mocked.call_args_list]
        self.assertIn("type=set_bay", source)
        self.assertIn("section=2", source)
        self.assertTrue(all("version=2" in url and "type=set_bay" in url and "section=2" in url for url in requested))

    def test_shelf_reset_requests_every_current_section_by_name(self):
        calls = []

        def fake(_base, _task, _token, timeout=12, section=None):
            calls.append(section)
            if section is None:
                return [
                    {"id": 1, "current_position": {"action": "identify", "section_info": {"name": "2"}}},
                    {"id": 2, "current_position": {"section_info": {"name": "1"}}},
                ], "base"
            if section == "1":
                return [{"id": 2}, {"id": 3, "loaded_section": section}], f"section-{section}"
            return [{"id": 4, "loaded_section": section}], f"section-{section}"

        with patch.object(runner_server, "fetch_live_task_actions", side_effect=fake):
            rows, _url = runner_server.fetch_shelf_reset_actions("https://example.rebotics.net", 42, "token")

        self.assertEqual(calls, [None, "1", "2"])
        self.assertEqual([row["id"] for row in rows], [1, 2, 3, 4])

    def test_fetch_live_actions_requires_auth(self):
        with self.assertRaisesRegex(ValueError, "Authentication required"):
            runner_server.fetch_live_task_actions(
                "https://example.rebotics.net", 42, ""
            )

    def test_existing_task_handlers_do_not_read_task_only_cache(self):
        source = Path(runner_server.__file__).read_text(encoding="utf-8")
        load_body = source.split("def _handle_load_existing_task", 1)[1].split(
            "def _handle_step_patch", 1
        )[0]
        audit_body = source.split("def _handle_audit_task_endpoint", 1)[1].split(
            "def _handle_simulate_refresh_diff", 1
        )[0]
        self.assertNotIn("raw_backend_actions_task_", load_body)
        self.assertNotIn("raw_backend_actions_task_", audit_body)
        self.assertIn("fetch_live_task_actions", load_body)
        self.assertIn("fetch_live_task_actions", audit_body)

    def test_right_slide_walks_from_vacancy_end(self):
        raw = [
            self._move(1, 1, 2, "A"),
            self._move(2, 2, 3, "B"),
            self._move(3, 3, 4, "C"),
        ]
        actions = runner_server.parse_raw_action_items(raw, 42)
        self.assertEqual([row["id"] for row in actions], [3, 2, 1])
        self.assertEqual({row["slide_direction"] for row in actions}, {"right"})
        result = validate_action_generation(raw, actions)
        self.assertTrue(result["can_start"], result["findings"])

    def test_occupied_destination_blocks_start(self):
        raw = [
            self._move(1, 1, 2, "A"),
            {
                "id": 2,
                "upc": "2",
                "product_title": "Stationary B",
                "action": "identify",
                "state": "STATE_IDLE",
                "current_position": {
                    "action": "identify",
                    "section_info": {"id": 1, "name": "1"},
                    "shelf": 1,
                    "position": 2,
                },
            },
        ]
        actions = runner_server.parse_raw_action_items(raw, 42)
        result = validate_action_generation(raw, actions)
        self.assertFalse(result["can_start"])
        self.assertIn(
            "OCCUPIED_DESTINATION",
            {item["code"] for item in result["findings"]},
        )

    def test_two_product_swap_is_legal(self):
        raw = [
            self._move(9, 9, 10, "A"),
            self._move(10, 10, 9, "B"),
        ]
        actions = runner_server.parse_raw_action_items(raw, 42)
        result = validate_action_generation(raw, actions)
        self.assertTrue(result["can_start"], result["findings"])
        self.assertEqual(set(result["swap_action_ids"]), {9, 10})

    def test_duplicate_target_slot_blocks_start(self):
        raw = [
            self._move(1, 1, 3, "A"),
            self._move(2, 2, 3, "B"),
        ]
        result = validate_action_generation(
            raw, runner_server.parse_raw_action_items(raw, 42)
        )
        self.assertFalse(result["can_start"])
        self.assertIn(
            "DUPLICATE_TARGET_SLOT",
            {item["code"] for item in result["findings"]},
        )

    def test_ir_studio_loads_and_validates_without_a_separate_start_button(self):
        html = (ROOT / "test_runner.html").read_text(encoding="utf-8")
        self.assertIn('id="btn-fast-load"', html)
        self.assertIn("Run complete task validation", html)
        self.assertNotIn('id="btn-historical-audit"', html)
        self.assertNotIn('id="btn-start-existing-test"', html)
        self.assertNotIn("function startExistingTaskTest", html)
        self.assertIn('id="existing-task-status"', html)
        self.assertIn('id="existing-task-findings"', html)
        self.assertIn("function setExistingTaskPhase", html)
        self.assertIn("function applyExistingTaskValidation", html)
        self.assertNotIn("Cached actions were not used", html)
        self.assertNotIn("Load Actions &amp; Start Test", html)
        self.assertNotIn("Load Actions & Start Test", html)

    def test_full_check_sends_token_and_avoids_blocking_dialogs(self):
        html = (ROOT / "test_runner.html").read_text(encoding="utf-8")
        audit = html.split("async function runHistoricalTaskAudit(options = {})", 1)[1].split(
            "function executeNextStep", 1
        )[0]
        self.assertIn("token: token.trim() || undefined", audit)
        self.assertNotIn("confirm(", audit)
        self.assertNotIn("alert(", audit)


if __name__ == "__main__":
    unittest.main()
