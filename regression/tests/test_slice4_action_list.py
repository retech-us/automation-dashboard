"""Unit tests for Slice 4 action-list contract."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from regression.action_list import (
    ActionListError,
    fetch_action_list_retailer,
    run_action_list_check,
)
from regression.contracts import (
    assert_action_list_contract,
    extract_action_items,
    load_contract,
)

FIXTURE = ROOT / "regression" / "tests" / "fixtures" / "action_list_retailer_sample.json"


def _sample_items():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class ContractLoadTests(unittest.TestCase):
    def test_baseline_loads(self):
        cfg = load_contract()
        self.assertEqual(cfg.get("version"), 1)
        self.assertIn("id", cfg.get("item_required_fields") or [])


class ExtractEnvelopeTests(unittest.TestCase):
    def test_bare_list(self):
        items = extract_action_items(_sample_items())
        self.assertEqual(len(items), 3)

    def test_results_envelope(self):
        items = extract_action_items({"results": _sample_items()})
        self.assertEqual(len(items), 3)

    def test_bad_envelope(self):
        with self.assertRaises(Exception):
            extract_action_items({"data": []})


class ContractAssertTests(unittest.TestCase):
    def test_valid_fixture_passes(self):
        report = assert_action_list_contract(_sample_items())
        self.assertTrue(report.ok, report.as_dict())
        self.assertEqual(report.item_count, 3)
        self.assertEqual(report.errors, [])

    def test_results_envelope_passes(self):
        report = assert_action_list_contract({"results": _sample_items()})
        self.assertTrue(report.ok)

    def test_empty_list_ok(self):
        report = assert_action_list_contract([])
        self.assertTrue(report.ok)
        self.assertEqual(report.item_count, 0)

    def test_missing_required_fails(self):
        bad = [{"id": 1, "action": "ACTION_MOVE"}]  # missing title + store_planogram_id
        report = assert_action_list_contract(bad)
        self.assertFalse(report.ok)
        rules = {e.rule for e in report.errors}
        self.assertIn("required", rules)

    def test_product_id_without_upc_fails(self):
        item = {
            "id": 1,
            "action": "ACTION_MOVE",
            "product_title": "X",
            "store_planogram_id": 9,
            "product_id": 42,
            "displayed_upc": "",
            "upc": None,
        }
        report = assert_action_list_contract([item])
        self.assertFalse(report.ok)
        self.assertTrue(any(e.rule == "upc" for e in report.errors))

    def test_unknown_action_warns_by_default(self):
        item = {
            "id": 1,
            "action": "ACTION_NEVER_SEEN",
            "product_title": "X",
            "store_planogram_id": 9,
            "displayed_upc": "123",
        }
        report = assert_action_list_contract([item])
        self.assertTrue(report.ok)
        self.assertEqual(len(report.warnings), 1)
        self.assertEqual(report.warnings[0].rule, "known_action")

    def test_unknown_action_strict_fails(self):
        item = {
            "id": 1,
            "action": "ACTION_NEVER_SEEN",
            "product_title": "X",
            "store_planogram_id": 9,
            "displayed_upc": "123",
        }
        report = assert_action_list_contract([item], strict_unknown_actions=True)
        self.assertFalse(report.ok)

    def test_bad_type_fails(self):
        item = {
            "id": "not-int",
            "action": "ACTION_MOVE",
            "product_title": "X",
            "store_planogram_id": 9,
        }
        report = assert_action_list_contract([item])
        self.assertFalse(report.ok)
        self.assertTrue(any(e.rule == "type" for e in report.errors))


class FetchFallbackTests(unittest.TestCase):
    def test_rejects_html_v4_fallback(self):
        def fake_http(method, url, **_k):
            if "/api/v1/" in url:
                return 404, {"detail": "No Task matches the given query."}, "{}"
            return 200, {"_raw": "<!DOCTYPE html>"}, "<!DOCTYPE html>"

        with patch("regression.action_list._http_json", side_effect=fake_http):
            with self.assertRaises(ActionListError) as ctx:
                fetch_action_list_retailer("https://epsilon.rebotics.net", "tok", 1)
        self.assertIn("No Task matches", str(ctx.exception))

    def test_accepts_v4_json_when_v1_missing(self):
        items = _sample_items()

        def fake_http(method, url, **_k):
            if "/api/v1/" in url:
                return 404, {"detail": "missing"}, "{}"
            return 200, items, "[]"

        with patch("regression.action_list._http_json", side_effect=fake_http):
            status, payload, url = fetch_action_list_retailer(
                "https://epsilon.rebotics.net", "tok", 1
            )
        self.assertEqual(status, 200)
        self.assertIn("/api/v4/", url)
        self.assertEqual(len(payload), 3)


class ActionListCheckTests(unittest.TestCase):
    def test_offline_payload_override(self):
        result = run_action_list_check(
            env="epsilon",
            task_id=999,
            payload_override=_sample_items(),
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.item_count, 3)
        self.assertEqual(result.env, "epsilon")
        self.assertIn("ACTION_MOVE", result.sample_actions)

    def test_offline_contract_fail(self):
        result = run_action_list_check(
            env="epsilon",
            task_id=999,
            payload_override=[{"id": 1}],
        )
        self.assertFalse(result.ok)
        self.assertGreater(len(result.contract.get("errors") or []), 0)

    def test_fetch_path_uses_login(self):
        payload = _sample_items()

        def fake_login(*_a, **_k):
            return "https://epsilon.rebotics.net", "tok"

        def fake_fetch(base_url, token, task_id, **_k):
            self.assertEqual(token, "tok")
            self.assertEqual(task_id, 42)
            return 200, payload, f"{base_url}/api/v1/tasks/42/action-list/retailer/?limit=1000"

        with patch("regression.action_list._login_token", side_effect=fake_login), patch(
            "regression.action_list.fetch_action_list_retailer", side_effect=fake_fetch
        ), patch(
            "regression.action_list.load_credentials",
            return_value=object(),
        ):
            result = run_action_list_check(env="epsilon", task_id=42)
        self.assertTrue(result.ok)
        self.assertEqual(result.http_status, 200)


class CliActionListTests(unittest.TestCase):
    def test_cli_offline_via_fixture_file(self):
        # CLI uses live fetch; unit path covered above. Smoke-test help/parse.
        proc = subprocess.run(
            [sys.executable, str(ROOT / "regression" / "cli.py"), "action-list", "--help"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("--task-id", proc.stdout)

    def test_cli_with_fixture_flag(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "regression" / "cli.py"),
                "action-list",
                "--env=epsilon",
                "--task-id=999",
                f"--fixture={FIXTURE}",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        data = json.loads(proc.stdout)
        self.assertTrue(data["ok"])
        self.assertEqual(data["item_count"], 3)


if __name__ == "__main__":
    unittest.main()
