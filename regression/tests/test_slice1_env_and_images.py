"""Unit tests for Slice 1: env resolver + image catalog."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from regression.env import EnvironmentResolutionError, resolve_base_url
from regression.image_catalog import ImageCatalog, ImageCatalogError


class EnvResolverTests(unittest.TestCase):
    def test_epsilon_pattern(self):
        r = resolve_base_url("epsilon")
        self.assertEqual(r.base_url, "https://epsilon.rebotics.net")
        self.assertEqual(r.env, "epsilon")
        self.assertEqual(r.source, "pattern")
        self.assertTrue(r.mutate_allowed)

    def test_normalizes_case(self):
        r = resolve_base_url("  Delta ")
        self.assertEqual(r.base_url, "https://delta.rebotics.net")

    def test_override(self):
        r = resolve_base_url("epsilon", base_url_override="https://custom.example.com/api/")
        self.assertEqual(r.base_url, "https://custom.example.com/api")
        self.assertEqual(r.source, "override")

    def test_rejects_bad_slug(self):
        with self.assertRaises(EnvironmentResolutionError):
            resolve_base_url("bad env!")

    def test_production_mutate_blocked(self):
        r = resolve_base_url("production")
        self.assertEqual(r.base_url, "https://production.rebotics.net")
        self.assertFalse(r.mutate_allowed)

    def test_allow_mutate_override(self):
        r = resolve_base_url("production", allow_mutate=True)
        self.assertTrue(r.mutate_allowed)


class ImageCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = ImageCatalog.load(repo_root=ROOT)

    def test_pasta_bay1(self):
        res = self.catalog.resolve(category="pasta", bay=1, stage="pre_photo")
        self.assertEqual(res.entry.id, "pasta_bay1_pre")
        self.assertTrue(res.entry.absolute_path.is_file())

    def test_deli_multi_bay(self):
        rows = self.catalog.resolve_bays(
            category="deli_meat", bays=[1, 2], stage="pre_photo"
        )
        self.assertEqual([r.entry.bay for r in rows], [1, 2])

    def test_unknown_category_fails_fast(self):
        with self.assertRaises(ImageCatalogError) as ctx:
            self.catalog.resolve(category="pharmacy", bay=1, stage="pre_photo")
        self.assertIn("No catalog image", str(ctx.exception))
        self.assertIn("Do not fall back", str(ctx.exception))

    def test_wrong_bay_for_pasta_fails(self):
        with self.assertRaises(ImageCatalogError):
            self.catalog.resolve(category="pasta", bay=99, stage="pre_photo")


class CliSmokeTests(unittest.TestCase):
    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(ROOT / "regression" / "cli.py"), *args],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )

    def test_cli_resolve_env(self):
        proc = self._run("resolve-env", "--env", "epsilon")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["base_url"], "https://epsilon.rebotics.net")

    def test_cli_resolve_images_pasta(self):
        proc = self._run(
            "resolve-images",
            "--category",
            "pasta",
            "--bays",
            "1,2",
            "--stage",
            "pre_photo",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(len(data["images"]), 2)

    def test_cli_resolve_images_unknown_fails(self):
        proc = self._run(
            "resolve-images",
            "--category",
            "unknown_category_xyz",
            "--bays",
            "1",
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("No catalog image", proc.stderr)


if __name__ == "__main__":
    unittest.main()
