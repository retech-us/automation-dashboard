"""Tests for keeping instance sign-ins across runner restarts."""

import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.session_store import load_tokens, save_tokens


class SaveTokensTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "session-tokens.json"

    def tearDown(self):
        self.dir.cleanup()

    def test_tokens_survive_a_round_trip(self):
        save_tokens(self.path, {"https://harr.rebotics.net": "abc123"}, now=1000.0)

        self.assertEqual(
            load_tokens(self.path, now=1000.0, max_age_seconds=3600),
            {"https://harr.rebotics.net": "abc123"},
        )

    def test_file_is_not_readable_by_other_users(self):
        save_tokens(self.path, {"https://harr.rebotics.net": "abc123"}, now=1000.0)

        mode = stat.S_IMODE(os.stat(self.path).st_mode)
        self.assertEqual(mode, 0o600)

    def test_stale_tokens_are_ignored_rather_than_used(self):
        save_tokens(self.path, {"https://harr.rebotics.net": "abc123"}, now=1000.0)

        fresh = load_tokens(self.path, now=1000.0 + 3599, max_age_seconds=3600)
        stale = load_tokens(self.path, now=1000.0 + 3601, max_age_seconds=3600)

        self.assertEqual(fresh, {"https://harr.rebotics.net": "abc123"})
        self.assertEqual(stale, {})

    def test_blank_and_malformed_tokens_are_dropped(self):
        save_tokens(
            self.path,
            {"https://a.net": "ok", "https://b.net": "", "https://c.net": None, "": "x"},
            now=1000.0,
        )

        self.assertEqual(
            load_tokens(self.path, now=1000.0, max_age_seconds=3600),
            {"https://a.net": "ok"},
        )

    def test_saving_nothing_removes_the_file(self):
        save_tokens(self.path, {"https://a.net": "ok"}, now=1000.0)
        save_tokens(self.path, {}, now=1000.0)

        self.assertFalse(self.path.exists())
        self.assertEqual(load_tokens(self.path, now=1000.0, max_age_seconds=3600), {})


class LoadTokensTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "session-tokens.json"

    def tearDown(self):
        self.dir.cleanup()

    def test_missing_file_is_not_an_error(self):
        self.assertEqual(load_tokens(self.path, now=1.0, max_age_seconds=3600), {})

    def test_corrupt_file_is_not_an_error(self):
        self.path.write_text("{ this is not json", encoding="utf-8")

        self.assertEqual(load_tokens(self.path, now=1.0, max_age_seconds=3600), {})

    def test_unexpected_shape_is_not_an_error(self):
        self.path.write_text(json.dumps(["nope"]), encoding="utf-8")

        self.assertEqual(load_tokens(self.path, now=1.0, max_age_seconds=3600), {})


class SecretHygieneTests(unittest.TestCase):
    root = Path(__file__).resolve().parents[2]

    def test_the_token_file_is_ignored_by_git(self):
        ignored = (self.root / ".gitignore").read_text(encoding="utf-8")

        self.assertIn("data/session-tokens.json", ignored)

    def test_passwords_are_never_written_to_the_token_file(self):
        source = (self.root / "mobile-backend-integration-tests/core/session_store.py").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("password", source.casefold())


if __name__ == "__main__":
    unittest.main()
