"""Tests for Gate B live smoke (mocked network)."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from regression.auth import AuthCredentials, AuthSmokeResult
from regression.gate_b import discover_ir_task_id, run_gate_b
from regression.provisioner import ProvisionPlan, ProvisionResult


def _auth_ok():
    return AuthSmokeResult(
        ok=True,
        env="epsilon",
        base_url="https://epsilon.rebotics.net",
        skipped=False,
        username="u",
        user_id=1,
        email="u@example.com",
        token_present=True,
        me_status=200,
        error=None,
        credential_source="test",
    )


class DiscoverTaskTests(unittest.TestCase):
    def test_preferred_id(self):
        tid, src = discover_ir_task_id(
            "https://epsilon.rebotics.net",
            "tok",
            preferred_task_id=42,
        )
        self.assertEqual(tid, 42)
        self.assertEqual(src, "env_or_arg")


class GateBRunTests(unittest.TestCase):
    def test_gate_b_happy_path_mocked(self):
        sample = [
            {
                "id": 1,
                "action": "remove",
                "product_title": "X",
                "store_planogram_id": 9,
                "displayed_upc": "111",
                "upc": "111",
                "product_id": 1,
                "state": "STATE_IDLE",
                "current_position": {
                    "action": "remove",
                    "shelf": 1,
                    "position": "1",
                    "section_info": {"id": 1, "name": "1"},
                },
                "expected_position": None,
            }
        ]

        with patch(
            "regression.gate_b.load_credentials",
            return_value=AuthCredentials("u", "p"),
        ), patch(
            "regression.gate_b.run_auth_smoke", return_value=_auth_ok()
        ), patch(
            "regression.gate_b._login_token",
            return_value=("https://epsilon.rebotics.net", "tok"),
        ), patch(
            "regression.gate_b.discover_ir_task_id",
            return_value=(99, "test"),
        ), patch(
            "regression.gate_b.fetch_action_list_retailer",
            return_value=(200, sample, "http://x"),
        ), patch(
            "regression.gate_b.run_provision",
            return_value=ProvisionResult(
                ok=True,
                dry_run=True,
                plan=ProvisionPlan(
                    env="epsilon",
                    base_url="https://epsilon.rebotics.net",
                    category="pasta",
                    stage="pre_photo",
                    bays=[1],
                    store_id=None,
                    task_id=None,
                    pog_id=None,
                    mode="dry_run",
                    scans=[],
                ),
            ),
        ):
            report = run_gate_b(env="epsilon", task_id=99)

        self.assertTrue(report.ok, report.as_dict())
        names = [s.name for s in report.steps]
        self.assertIn("auth_smoke", names)
        self.assertIn("action_list_live", names)
        self.assertIn("domain_transform_live", names)
        self.assertIn("provision_dry_run", names)


class CliGateBTests(unittest.TestCase):
    def test_cli_help(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "regression" / "cli.py"), "gate-b", "run", "--help"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("--task-id", proc.stdout)


if __name__ == "__main__":
    unittest.main()
