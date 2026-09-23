"""Tests for fetching the post-photo action list via ?stage=post_photo."""

import unittest
from unittest.mock import patch

import runner_server
from core.e2e_audit_engine import build_generated_comparison_actions


class PostPhotoStageFetchTests(unittest.TestCase):
    def setUp(self):
        self.pre_items = [{"id": 1}, {"id": 2}]

    def _fake_fetch(self, items, error=None, status=200):
        def fetch(base_url, token, task_id, stage=None):
            self.captured_stage = stage
            self.captured_url = (
                f"{base_url}/api/v1/tasks/{task_id}/action-list/retailer/"
                f"?limit=1000&stage={stage}"
            )
            return list(items), error, status, self.captured_url

        return fetch

    def test_stage_query_param_is_sent_and_post_actions_returned(self):
        post_items = [{"id": 91}, {"id": 92}, {"id": 93}]
        with patch.object(runner_server, "fetch_task_action_list", self._fake_fetch(post_items)):
            items, loaded, error = runner_server.load_post_photo_actions(
                "https://harr.rebotics.net", "tok", 8648127, self.pre_items
            )
        self.assertEqual(self.captured_stage, "post_photo")
        self.assertIn("stage=post_photo", self.captured_url)
        self.assertEqual(len(items), 3)
        self.assertTrue(loaded)
        self.assertIsNone(error)

    def test_identical_response_is_treated_as_unsupported_stage(self):
        with patch.object(
            runner_server, "fetch_task_action_list", self._fake_fetch(self.pre_items)
        ):
            items, loaded, error = runner_server.load_post_photo_actions(
                "https://harr.rebotics.net", "tok", 8648127, self.pre_items
            )
        self.assertEqual(items, [])
        self.assertFalse(loaded)
        self.assertIn("ignored ?stage=post_photo", error)

    def test_same_action_ids_with_different_scan_ids_are_valid_post_data(self):
        pre_items = [
            {"id": 1, "current_position": {"scan_id": 7001}},
            {"id": 2, "current_position": {"scan_id": 7001}},
        ]
        post_items = [
            {"id": 1, "current_position": {"scan_id": 7002}},
            {"id": 2, "current_position": {"scan_id": 7002}},
        ]
        with patch.object(
            runner_server, "fetch_task_action_list", self._fake_fetch(post_items)
        ):
            items, loaded, error = runner_server.load_post_photo_actions(
                "https://harr.rebotics.net", "tok", 8648127, pre_items
            )
        self.assertTrue(loaded)
        self.assertIsNone(error)
        self.assertEqual(items, post_items)

    def test_empty_post_response_is_not_reported_as_verified(self):
        with patch.object(
            runner_server, "fetch_task_action_list", self._fake_fetch([])
        ):
            items, loaded, error = runner_server.load_post_photo_actions(
                "https://harr.rebotics.net", "tok", 8648127, self.pre_items
            )
        self.assertEqual(items, [])
        self.assertFalse(loaded)
        self.assertIn("returned no post-photo actions", error)

    def test_http_error_is_reported_without_raising(self):
        with patch.object(
            runner_server,
            "fetch_task_action_list",
            self._fake_fetch([], error="HTTP 400 from action-list", status=400),
        ):
            items, loaded, error = runner_server.load_post_photo_actions(
                "https://harr.rebotics.net", "tok", 8648127, self.pre_items
            )
        self.assertEqual(items, [])
        self.assertFalse(loaded)
        self.assertEqual(error, "HTTP 400 from action-list")


class ScanIdResolutionTests(unittest.TestCase):
    def test_scan_id_read_from_position_payload(self):
        items = [{"id": 1, "current_position": {"scan_id": 3769854}}]
        self.assertEqual(runner_server.scan_id_from_action_items(items), 3769854)

    def test_returns_none_when_no_scan_id_present(self):
        self.assertIsNone(runner_server.scan_id_from_action_items([{"id": 1}]))


class PostGeneratedActionShapeTests(unittest.TestCase):
    def test_post_raw_items_are_shaped_for_comparison(self):
        raw = [{
            "id": 55,
            "action_type": "Remove",
            "upc": "9347774003372",
            "product_title": "Test Product",
            "current_position": {
                "scan_id": 3769854,
                "shelf": 6,
                "position": 12,
                "planogram_info": {"bay": "1"},
            },
        }]
        actions = build_generated_comparison_actions(
            raw, fallback_scan_id=3769854
        )
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["scan_id"], 3769854)
        self.assertEqual(actions[0]["source_action_id"], 55)

    def test_fallback_scan_does_not_overwrite_each_actions_real_scan(self):
        raw = [
            {
                "id": 1,
                "action": "remove",
                "upc": "111",
                "current_position": {"scan_id": 7001, "shelf": 1, "position": 1},
            },
            {
                "id": 2,
                "action": "remove",
                "upc": "222",
                "current_position": {"scan_id": 7002, "shelf": 1, "position": 2},
            },
        ]

        actions = build_generated_comparison_actions(raw, fallback_scan_id=9999)

        self.assertEqual({item["scan_id"] for item in actions}, {7001, 7002})


if __name__ == "__main__":
    unittest.main()
