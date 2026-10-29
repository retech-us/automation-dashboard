"""
Unit tests for Shelf Intelligence Preflight Validation Engine (PreflightValidator).
Verifies Git source resolution, URL validation, credential readiness, and state mutation guards.
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.preflight_validator import PreflightValidator
from core.run_config import RunConfig


class PreflightValidatorTests(unittest.TestCase):
    def setUp(self):
        self._orig_env = dict(os.environ)
        # Mock Git Controller to isolate test runs
        self.mock_git = MagicMock()
        self.mock_git.resolve_revision.return_value = {
            "resolved_cleanly": True,
            "repo_name": "rebotics-management-django",
            "repo_path": "/Users/vipin.nair1/sympohonyworkspace/rebotics-management-django",
            "target_ref": "master",
            "resolved_sha": "a" * 40,
            "short_sha": "a" * 7,
            "commit_author": "Dev Lead <lead@retech.com>",
            "commit_date": "2026-10-23 12:00:00",
            "commit_message": "feat: shelf reset updates",
            "selected_branch": "master",
        }
        self.validator = PreflightValidator(git_controller=self.mock_git)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._orig_env)

    def test_preflight_dry_run_success(self):
        cfg = RunConfig.from_dict({
            "source": {"repository": "backend", "branch": "master", "commit": "auto"},
            "target": {"name": "epsilon", "base_url": "https://epsilon.rebotics.net"},
            "tests": {"scope": "regression"},
            "execution": {"mode": "dry_run", "allow_state_changes": False},
        })
        result = self.validator.validate(cfg)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
        self.assertIn("backend", result.resolved_sources)
        self.assertEqual(result.resolved_sources["backend"]["resolved_sha"], "a" * 40)
        self.assertEqual(result.target_summary["hostname"], "epsilon.rebotics.net")
        self.assertTrue(result.target_summary["is_secure"])

    def test_preflight_resolves_all_repositories(self):
        cfg = RunConfig.from_dict({
            "source": {"repository": "all", "branch": "master", "commit": "auto"},
            "target": {"name": "epsilon", "base_url": "https://epsilon.rebotics.net"},
        })
        result = self.validator.validate(cfg)
        self.assertTrue(result.is_valid)
        self.assertEqual(self.mock_git.resolve_revision.call_count, 3)
        self.assertIn("backend", result.resolved_sources)
        self.assertIn("android", result.resolved_sources)
        self.assertIn("ios", result.resolved_sources)

    def test_preflight_git_resolution_failure_produces_error(self):
        self.mock_git.resolve_revision.return_value = {
            "resolved_cleanly": False,
            "error": "Commit SHA deadbeef not found in tree",
        }
        cfg = RunConfig.from_dict({
            "source": {"repository": "backend", "branch": "master", "commit": "deadbeef"},
        })
        result = self.validator.validate(cfg)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("Failed to resolve Git revision" in err for err in result.errors))

    def test_preflight_live_mode_without_credentials_fails(self):
        os.environ.pop("TEST_USERNAME", None)
        os.environ.pop("TEST_PASSWORD", None)
        os.environ.pop("TEST_TOKEN", None)

        cfg = RunConfig.from_dict({
            "target": {"name": "krcs", "base_url": "https://krcs.rebotics.net"},
            "execution": {"mode": "live", "allow_state_changes": True},
        })
        result = self.validator.validate(cfg)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("no authentication credentials found" in err for err in result.errors))

    def test_preflight_live_mode_with_credentials_passes(self):
        os.environ["TEST_TOKEN"] = "valid-test-token"
        cfg = RunConfig.from_dict({
            "target": {"name": "krcs", "base_url": "https://krcs.rebotics.net"},
            "execution": {"mode": "live", "allow_state_changes": True},
        })
        result = self.validator.validate(cfg)
        self.assertTrue(result.is_valid)
        self.assertTrue(result.target_summary["auth_configured"])

    def test_preflight_mutation_guard_blocks_state_changes_when_disallowed(self):
        os.environ["TEST_TOKEN"] = "token123"
        cfg = RunConfig.from_dict({
            "tests": {"scope": "workflow"},  # modifying scope
            "execution": {"mode": "live", "allow_state_changes": False},
        })
        result = self.validator.validate(cfg)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("modifies application state" in err for err in result.errors))

    def test_preflight_invalid_target_url_scheme_fails(self):
        cfg = RunConfig()
        cfg.target.base_url = "ftp://files.rebotics.net"
        result = self.validator.validate(cfg)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("valid http or https scheme" in err for err in result.errors))

    def test_preflight_result_to_dict(self):
        cfg = RunConfig.from_dict({})
        result = self.validator.validate(cfg)
        d = result.to_dict()
        self.assertIn("is_valid", d)
        self.assertIn("resolved_sources", d)
        self.assertIn("target_summary", d)
        self.assertIn("execution_manifest", d)


if __name__ == "__main__":
    unittest.main()
