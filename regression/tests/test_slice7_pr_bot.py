"""Unit tests for Slice 7 CI PR bot."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from regression.impact import select_impact
from regression.pr_bot import build_narrative, render_pr_comment, run_pr_bot


class ImpactSelectTests(unittest.TestCase):
    def test_smoke_mode(self):
        sel = select_impact([], mode="smoke")
        self.assertEqual(sel.packs, ["smoke"])

    def test_impacted_regression_paths(self):
        sel = select_impact(
            ["regression/tools.py", "docs/regression/BUILD_SLICES.md"],
            mode="impacted",
        )
        self.assertIn("smoke", sel.packs)
        self.assertIn("FEATURE-PLATFORM", sel.features)

    def test_impacted_mapper_path(self):
        sel = select_impact(
            [
                "mobile-backend-integration-tests/core/action_list_domain_mapper.py",
            ],
            mode="impacted",
        )
        self.assertIn("FEATURE-021", sel.features)


class PrBotRunTests(unittest.TestCase):
    def test_smoke_pack_passes(self):
        report = run_pr_bot(env="epsilon", mode="smoke")
        self.assertTrue(report.ok, report.as_dict())
        self.assertEqual(report.exit_code, 0)
        tools = [s.tool for s in report.steps]
        self.assertIn("domain_parity", tools)
        self.assertIn("action_list", tools)
        self.assertIn("resolve_env", tools)

    def test_narrative_does_not_flip_verdict(self):
        report = run_pr_bot(env="epsilon", mode="smoke")
        text, source = build_narrative(report.as_dict())
        self.assertEqual(source, "template")
        self.assertTrue(report.ok)
        # Even if narrative were empty, ok stays from tools
        self.assertTrue(report.ok)

    def test_comment_contains_policy(self):
        report = run_pr_bot(env="epsilon", mode="smoke", pr_number="42", head_sha="abc")
        md = render_pr_comment(report)
        self.assertIn("<!-- regression-pr-bot -->", md)
        self.assertIn("**Verdict:** `PASS`", md)
        self.assertIn("PASS/FAIL is taken only from tool", md)
        self.assertIn("domain_parity", md)

    def test_failed_tool_fails_bot(self):
        from regression.tools import ToolResponse

        def fake_invoke(name, args=None):
            if name == "domain_parity":
                return ToolResponse(
                    ok=False, tool=name, exit_code=1, error="forced fail"
                )
            return ToolResponse(ok=True, tool=name, exit_code=0, result={"ok": True})

        with patch("regression.pr_bot.invoke_tool", side_effect=fake_invoke):
            report = run_pr_bot(env="epsilon", mode="smoke")
        self.assertFalse(report.ok)
        self.assertEqual(report.exit_code, 1)
        md = render_pr_comment(report)
        self.assertIn("**Verdict:** `FAIL`", md)
        text, _ = build_narrative(report.as_dict())
        self.assertIn("FAILED", text)


class CliPrBotTests(unittest.TestCase):
    def test_cli_pr_bot_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            json_out = Path(tmp) / "out.json"
            md_out = Path(tmp) / "out.md"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "regression" / "cli.py"),
                    "pr-bot",
                    "run",
                    "--env=epsilon",
                    "--mode=smoke",
                    f"--json-out={json_out}",
                    f"--comment-out={md_out}",
                ],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            data = json.loads(proc.stdout)
            self.assertTrue(data["ok"])
            self.assertTrue(json_out.is_file())
            self.assertIn("Verdict", md_out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
