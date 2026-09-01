"""Unit tests for Slice 2 auth smoke (mocked HTTP)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from regression.auth import (
    AuthCredentials,
    AuthCredentialsMissing,
    load_credentials,
    run_auth_smoke,
)


class LoadCredentialsTests(unittest.TestCase):
    def test_from_env(self):
        with patch.dict(
            os.environ,
            {
                "REGRESSION_USERNAME": "u1",
                "REGRESSION_PASSWORD": "p1",
                "REGRESSION_DEVICE_ID": "dev-1",
            },
            clear=False,
        ):
            creds = load_credentials()
        self.assertEqual(creds.username, "u1")
        self.assertEqual(creds.password, "p1")
        self.assertEqual(creds.device_id, "dev-1")
        self.assertEqual(creds.source, "cli_or_env")

    def test_from_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test-accounts.json"
            path.write_text(
                json.dumps(
                    {
                        "accounts": {
                            "standard_user": {
                                "username": "file_user",
                                "password": "file_pass",
                                "deviceId": "file-dev",
                                "tokenType": "simple",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True):
                # Clear regression creds if present
                for key in ("REGRESSION_USERNAME", "REGRESSION_PASSWORD"):
                    os.environ.pop(key, None)
                creds = load_credentials(accounts_path=path)
            self.assertEqual(creds.username, "file_user")
            self.assertTrue(creds.source.startswith("file:"))

    def test_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "nope.json"
            with patch.dict(os.environ, {}, clear=True):
                os.environ.pop("REGRESSION_USERNAME", None)
                os.environ.pop("REGRESSION_PASSWORD", None)
                with self.assertRaises(AuthCredentialsMissing):
                    load_credentials(accounts_path=missing)


class AuthSmokeMockTests(unittest.TestCase):
    def test_success_path(self):
        responses = [
            (200, {"token": "tok-123", "detail": "ok"}, "{}"),
            (200, {"id": 9, "username": "u1", "email": "u1@example.com"}, "{}"),
        ]

        def fake_http(method, url, *, headers, body=None, timeout=20.0):
            status, payload, raw = responses.pop(0)
            return status, payload, raw

        creds = AuthCredentials(username="u1", password="p1", source="test")
        with patch("regression.auth._http_json", side_effect=fake_http):
            result = run_auth_smoke("epsilon", credentials=creds)
        self.assertTrue(result.ok)
        self.assertEqual(result.base_url, "https://epsilon.rebotics.net")
        self.assertEqual(result.user_id, 9)
        self.assertTrue(result.token_present)
        self.assertIsNone(result.error)

    def test_auth_failure(self):
        def fake_http(method, url, *, headers, body=None, timeout=20.0):
            return 401, {"detail": "bad"}, "{}"

        creds = AuthCredentials(username="u1", password="bad", source="test")
        with patch("regression.auth._http_json", side_effect=fake_http):
            result = run_auth_smoke("epsilon", credentials=creds)
        self.assertFalse(result.ok)
        self.assertIn("401", result.error or "")


class CliAuthSmokeTests(unittest.TestCase):
    def _run(self, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
        full_env = os.environ.copy()
        if env is not None:
            full_env.update(env)
            for k in ("REGRESSION_USERNAME", "REGRESSION_PASSWORD"):
                if k not in env:
                    full_env.pop(k, None)
        return subprocess.run(
            [sys.executable, str(ROOT / "regression" / "cli.py"), *args],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env=full_env,
        )

    def test_skip_if_no_creds(self):
        proc = self._run(
            "auth-smoke",
            "--env",
            "epsilon",
            "--skip-if-no-creds",
            env={"REGRESSION_ACCOUNTS_PATH": "/tmp/regression-no-accounts-file.json"},
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertTrue(data["skipped"])
        self.assertEqual(data["base_url"], "https://epsilon.rebotics.net")


if __name__ == "__main__":
    unittest.main()
