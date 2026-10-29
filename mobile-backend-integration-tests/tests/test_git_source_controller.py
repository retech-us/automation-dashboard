"""
Unit tests for GitSourceController.
Verifies repo name resolution, revision resolution, branch inspection, and safe error handling.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.git_source_controller import GitSourceController


class GitSourceControllerTests(unittest.TestCase):
    def setUp(self):
        self.controller = GitSourceController()

    def test_repo_alias_resolution(self):
        backend_path = self.controller._get_repo_path("backend")
        self.assertIsNotNone(backend_path)
        self.assertIn("rebotics-management-django", str(backend_path))

        android_path = self.controller._get_repo_path("android")
        self.assertIsNotNone(android_path)
        self.assertIn("android-rebotics", str(android_path))

        ios_path = self.controller._get_repo_path("ios")
        self.assertIsNotNone(ios_path)
        self.assertIn("ios-rebotics", str(ios_path))

    def test_unknown_repo_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.controller._get_repo_path("non_existent_repo_123")

    def test_resolve_revision_unknown_repo(self):
        res = self.controller.resolve_revision("non_existent_repo_123")
        self.assertFalse(res["resolved_cleanly"])
        self.assertIn("Unknown repository target", res["error"])

    @patch("subprocess.run")
    def test_resolve_revision_success(self, mock_run):
        # 1. rev-parse
        mock_rev_parse = MagicMock(returncode=0, stdout="e4d909c290d0fb1ca068ffaddf22cbd0addf41ad\n")
        # 2. log pretty=%B
        mock_msg = MagicMock(returncode=0, stdout="fix: shelf action rules\n")
        # 3. log pretty=%an
        mock_author = MagicMock(returncode=0, stdout="Dev QA <qa@rebotics.net>\n")
        # 4. log pretty=%cd
        mock_date = MagicMock(returncode=0, stdout="2026-10-23 15:30:00\n")
        # 5. branch --show-current
        mock_branch = MagicMock(returncode=0, stdout="master\n")

        mock_run.side_effect = [mock_rev_parse, mock_msg, mock_author, mock_date, mock_branch]

        res = self.controller.resolve_revision("backend", branch="master", commit="auto")
        self.assertTrue(res["resolved_cleanly"])
        self.assertEqual(res["resolved_sha"], "e4d909c290d0fb1ca068ffaddf22cbd0addf41ad")
        self.assertEqual(res["short_sha"], "e4d909c2")
        self.assertEqual(res["commit_author"], "Dev QA <qa@rebotics.net>")
        self.assertEqual(res["commit_date"], "2026-10-23 15:30:00")
        self.assertEqual(res["commit_message"], "fix: shelf action rules")
        self.assertEqual(res["selected_branch"], "master")

    @patch("subprocess.run")
    def test_resolve_revision_specific_commit(self, mock_run):
        mock_rev_parse = MagicMock(returncode=0, stdout="1234567890abcdef1234567890abcdef12345678\n")
        mock_msg = MagicMock(returncode=0, stdout="release prep\n")
        mock_author = MagicMock(returncode=0, stdout="Alice <alice@test.com>\n")
        mock_date = MagicMock(returncode=0, stdout="2026-10-22\n")
        mock_branch = MagicMock(returncode=0, stdout="release/v2.1\n")

        mock_run.side_effect = [mock_rev_parse, mock_msg, mock_author, mock_date, mock_branch]

        res = self.controller.resolve_revision("android", branch="release/v2.1", commit="1234567890abcdef1234567890abcdef12345678")
        self.assertTrue(res["resolved_cleanly"])
        self.assertEqual(res["resolved_sha"], "1234567890abcdef1234567890abcdef12345678")
        self.assertEqual(res["target_ref"], "1234567890abcdef1234567890abcdef12345678")

    @patch("subprocess.run")
    def test_resolve_revision_git_error(self, mock_run):
        mock_rev_parse = MagicMock()
        mock_rev_parse.returncode = 128
        mock_rev_parse.stderr = "fatal: ambiguous argument 'bad_sha': unknown revision\n"
        mock_run.return_value = mock_rev_parse

        res = self.controller.resolve_revision("ios", branch="master", commit="bad_sha")
        self.assertFalse(res["resolved_cleanly"])
        self.assertIn("unknown revision", res["error"])


if __name__ == "__main__":
    unittest.main()
