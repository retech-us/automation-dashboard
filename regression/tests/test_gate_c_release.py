"""Tests for Gate C release pack."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from regression.gate_c import render_gate_c_markdown, run_gate_c, to_run_summary
from regression.pr_bot import PrBotReport, StepResult
from regression.tools import ToolResponse


def _pr_ok():
    return PrBotReport(
        ok=True,
        exit_code=0,
        env="epsilon",
        mode="smoke",
        packs=["smoke"],
        features=["FEATURE-PLATFORM"],
        steps=[StepResult(tool="health", pack="smoke", ok=True, exit_code=0)],
        narrative="ok",
        narrative_source="template",
        verdict_policy="x",
        generated_at="2026-01-01T00:00:00Z",
    )


class GateCRunTests(unittest.TestCase):
    def test_release_pack_offline(self):
        with patch("regression.gate_c.run_pr_bot", return_value=_pr_ok()), patch(
            "regression.gate_c.invoke_tool",
            return_value=ToolResponse(
                ok=True,
                tool="domain_parity",
                exit_code=0,
                result={"domain_card_count": 6},
            ),
        ), patch.dict("os.environ", {}, clear=False):
            # Force no env creds for this process path; accounts file may still exist
            report = run_gate_c(env="epsilon", require_live=False)

        names = [x.name for x in report.layers]
        self.assertIn("gate_a_pr_bot_smoke", names)
        self.assertIn("domain_parity_cat1", names)
        self.assertIn("api_ir_subset", names)
        self.assertIn("appium_ir_thin", names)
        self.assertTrue(report.ok, report.as_dict())
        # external layers skipped
        self.assertEqual(
            next(x for x in report.layers if x.name == "api_ir_subset").status,
            "skipped",
        )

    def test_failed_layer_fails_gate(self):
        bad = _pr_ok()
        bad.ok = False
        bad.exit_code = 1
        with patch("regression.gate_c.run_pr_bot", return_value=bad), patch(
            "regression.gate_c.invoke_tool",
            return_value=ToolResponse(ok=True, tool="domain_parity", exit_code=0),
        ):
            report = run_gate_c(env="epsilon", require_live=False)
        self.assertFalse(report.ok)
        self.assertEqual(report.exit_code, 1)

    def test_run_summary_shape(self):
        with patch("regression.gate_c.run_pr_bot", return_value=_pr_ok()), patch(
            "regression.gate_c.invoke_tool",
            return_value=ToolResponse(ok=True, tool="domain_parity", exit_code=0),
        ):
            report = run_gate_c(env="epsilon")
        summary = to_run_summary(report)
        self.assertEqual(summary["schemaVersion"], "1.0")
        self.assertEqual(summary["repo"], "regression")
        self.assertEqual(summary["status"], "passed")
        self.assertIn("regression_platform", summary)
        self.assertIn("summary", summary)
        md = render_gate_c_markdown(report)
        self.assertIn("Gate C", md)
        self.assertIn("PASS", md)


class CliGateCTests(unittest.TestCase):
    def test_cli_help(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "regression" / "cli.py"),
                "gate-c",
                "run",
                "--help",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("--summary-out", proc.stdout)


if __name__ == "__main__":
    unittest.main()
