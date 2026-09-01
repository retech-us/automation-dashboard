"""Unit tests for Slice 3 provisioner."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from regression.image_catalog import ImageCatalog
from regression.provisioner import ProvisionerError, build_provision_plan, run_provision


class ProvisionPlanTests(unittest.TestCase):
    def test_pasta_dry_plan(self):
        plan = build_provision_plan(
            env="epsilon",
            category="pasta",
            bays=[1, 2],
            stage="pre_photo",
            mode="dry_run",
        )
        self.assertEqual(plan.base_url, "https://epsilon.rebotics.net")
        self.assertEqual(len(plan.scans), 2)
        self.assertEqual(plan.scans[0].image_id, "pasta_bay1_pre")
        self.assertTrue(plan.scans[0].exists)
        self.assertIn("dry_run=true", " ".join(plan.notes))

    def test_unknown_category_fails(self):
        with self.assertRaises(Exception) as ctx:
            build_provision_plan(
                env="epsilon",
                category="pharmacy",
                bays=[1],
                stage="pre_photo",
            )
        self.assertIn("No catalog image", str(ctx.exception))

    def test_run_provision_dry_run(self):
        result = run_provision(
            env="epsilon",
            category="deli",
            bays=[1],
            dry_run=True,
        )
        self.assertTrue(result.ok)
        self.assertTrue(result.dry_run)
        self.assertEqual(result.plan.scans[0].image_id, "deli_bay1_pre")


class ProvisionExecuteGuardTests(unittest.TestCase):
    def test_execute_requires_store(self):
        with self.assertRaises(ProvisionerError) as ctx:
            run_provision(
                env="epsilon",
                category="pasta",
                bays=[1],
                dry_run=False,
                task_id=123,
                pog_id=1,
            )
        self.assertIn("store-id", str(ctx.exception))


class CliProvisionTests(unittest.TestCase):
    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(ROOT / "regression" / "cli.py"), *args],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )

    def test_cli_dry_run(self):
        proc = self._run(
            "provision",
            "--env",
            "epsilon",
            "--category",
            "pasta",
            "--bays",
            "1,2",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertTrue(data["ok"])
        self.assertTrue(data["dry_run"])
        self.assertEqual(len(data["plan"]["scans"]), 2)

    def test_cli_unknown_category(self):
        proc = self._run(
            "provision",
            "--env",
            "epsilon",
            "--category",
            "pharmacy",
            "--bays",
            "1",
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("No catalog image", proc.stderr)


if __name__ == "__main__":
    unittest.main()
