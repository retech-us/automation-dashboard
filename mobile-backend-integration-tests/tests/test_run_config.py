"""
Unit tests for Shelf Intelligence Run Configuration Engine (RunConfig).
Verifies parsing, schema validation, environment variable interpolation, and credential safety.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.run_config import (
    AuthConfig,
    ExecutionConfig,
    RunConfig,
    SourceConfig,
    TargetConfig,
    TestsConfig,
    expand_env_vars,
)


class ExpandEnvVarsTests(unittest.TestCase):
    def setUp(self):
        self._orig_env = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._orig_env)

    def test_expand_simple_env_var(self):
        os.environ["FOO_TEST_VAR"] = "bar_value"
        result = expand_env_vars("prefix_${FOO_TEST_VAR}_suffix")
        self.assertEqual(result, "prefix_bar_value_suffix")

    def test_expand_with_fallback_default(self):
        if "UNSET_VAR_XYZ" in os.environ:
            del os.environ["UNSET_VAR_XYZ"]
        result = expand_env_vars("host: ${UNSET_VAR_XYZ:-http://localhost:8000}")
        self.assertEqual(result, "host: http://localhost:8000")

    def test_expand_with_fallback_empty_when_unset_and_no_default(self):
        if "UNSET_VAR_ABC" in os.environ:
            del os.environ["UNSET_VAR_ABC"]
        result = expand_env_vars("val: '${UNSET_VAR_ABC}'")
        self.assertEqual(result, "val: ''")

    def test_expand_multiple_vars(self):
        os.environ["VAR_A"] = "alpha"
        os.environ["VAR_B"] = "beta"
        result = expand_env_vars("${VAR_A}:${VAR_B}:${VAR_C:-gamma}")
        self.assertEqual(result, "alpha:beta:gamma")


class AuthConfigTests(unittest.TestCase):
    def setUp(self):
        self._orig_env = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._orig_env)

    def test_auth_empty_credentials(self):
        os.environ.pop("TEST_USER", None)
        os.environ.pop("TEST_PASS", None)
        os.environ.pop("TEST_TOK", None)

        auth = AuthConfig(
            username_env="TEST_USER",
            password_env="TEST_PASS",
            token_env="TEST_TOK",
        )
        self.assertFalse(auth.has_credentials())
        creds = auth.resolve_credentials()
        self.assertIsNone(creds["username"])
        self.assertIsNone(creds["password"])
        self.assertIsNone(creds["token"])

    def test_auth_token_credentials(self):
        os.environ["TEST_TOK"] = "mock-secret-token"
        auth = AuthConfig(token_env="TEST_TOK")
        self.assertTrue(auth.has_credentials())
        creds = auth.resolve_credentials()
        self.assertEqual(creds["token"], "mock-secret-token")

    def test_auth_username_password_credentials(self):
        os.environ["TEST_USER"] = "qa_user"
        os.environ["TEST_PASS"] = "secure_pass"
        auth = AuthConfig(username_env="TEST_USER", password_env="TEST_PASS")
        self.assertTrue(auth.has_credentials())
        creds = auth.resolve_credentials()
        self.assertEqual(creds["username"], "qa_user")
        self.assertEqual(creds["password"], "secure_pass")


class SourceConfigTests(unittest.TestCase):
    def test_valid_repositories(self):
        for repo in ("backend", "android", "ios", "all", "rebotics-management-django"):
            cfg = SourceConfig(repository=repo)
            cfg.validate()

    def test_invalid_repository_raises_value_error(self):
        cfg = SourceConfig(repository="unknown_repo")
        with self.assertRaises(ValueError) as ctx:
            cfg.validate()
        self.assertIn("Invalid source repository", str(ctx.exception))


class TargetConfigTests(unittest.TestCase):
    def test_valid_target_url(self):
        cfg = TargetConfig(base_url="https://krcs.rebotics.net")
        cfg.validate()
        cfg_http = TargetConfig(base_url="http://localhost:8000")
        cfg_http.validate()

    def test_invalid_target_scheme(self):
        cfg = TargetConfig(base_url="ftp://ftp.rebotics.net")
        with self.assertRaises(ValueError) as ctx:
            cfg.validate()
        self.assertIn("valid http or https scheme", str(ctx.exception))

    def test_missing_hostname(self):
        cfg = TargetConfig(base_url="https://")
        with self.assertRaises(ValueError) as ctx:
            cfg.validate()
        self.assertIn("missing hostname", str(ctx.exception))


class TestsConfigTests(unittest.TestCase):
    def test_valid_scopes(self):
        for scope in ("smoke", "rules", "api", "ai_benchmark", "regression", "all"):
            cfg = TestsConfig(scope=scope)
            cfg.validate()

    def test_invalid_scope(self):
        cfg = TestsConfig(scope="non_existent_scope")
        with self.assertRaises(ValueError) as ctx:
            cfg.validate()
        self.assertIn("Invalid test scope", str(ctx.exception))


class ExecutionConfigTests(unittest.TestCase):
    def test_valid_modes_and_platforms(self):
        cfg = ExecutionConfig(mode="dry_run", platform="all")
        cfg.validate()
        cfg_live = ExecutionConfig(mode="live", platform="ios")
        cfg_live.validate()

    def test_invalid_mode(self):
        cfg = ExecutionConfig(mode="destructive")
        with self.assertRaises(ValueError) as ctx:
            cfg.validate()
        self.assertIn("Invalid execution mode", str(ctx.exception))

    def test_invalid_platform(self):
        cfg = ExecutionConfig(platform="windows_phone")
        with self.assertRaises(ValueError) as ctx:
            cfg.validate()
        self.assertIn("Invalid platform", str(ctx.exception))


class RunConfigSerializationTests(unittest.TestCase):
    def test_from_dict_defaults(self):
        cfg = RunConfig.from_dict({})
        self.assertEqual(cfg.version, "1.0")
        self.assertEqual(cfg.source.repository, "backend")
        self.assertEqual(cfg.target.name, "epsilon")
        self.assertEqual(cfg.tests.scope, "regression")
        self.assertEqual(cfg.execution.mode, "dry_run")
        self.assertFalse(cfg.execution.allow_state_changes)

    def test_from_dict_custom_values(self):
        payload = {
            "version": "2.0",
            "source": {"repository": "ios", "branch": "feature/ai", "commit": "abc1234"},
            "target": {"name": "krcs", "base_url": "https://krcs.rebotics.net"},
            "tests": {"scope": "rules", "scenarios": ["scenario_01"]},
            "execution": {"mode": "live", "allow_state_changes": False, "platform": "ios"},
        }
        cfg = RunConfig.from_dict(payload)
        self.assertEqual(cfg.version, "2.0")
        self.assertEqual(cfg.source.repository, "ios")
        self.assertEqual(cfg.source.branch, "feature/ai")
        self.assertEqual(cfg.source.commit, "abc1234")
        self.assertEqual(cfg.target.name, "krcs")
        self.assertEqual(cfg.target.base_url, "https://krcs.rebotics.net")
        self.assertEqual(cfg.tests.scope, "rules")
        self.assertEqual(cfg.execution.mode, "live")
        self.assertEqual(cfg.execution.platform, "ios")

    def test_to_safe_dict_sanitizes_credentials(self):
        cfg = RunConfig()
        safe = cfg.to_safe_dict()
        self.assertIn("target", safe)
        self.assertIn("auth", safe["target"])
        self.assertIn("credentials_configured", safe["target"]["auth"])
        self.assertNotIn("password", safe["target"]["auth"])
        self.assertNotIn("token", safe["target"]["auth"])

    def test_from_file_json(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({
                "source": {"repository": "backend", "branch": "master"},
                "target": {"name": "epsilon", "base_url": "https://epsilon.rebotics.net"}
            }, f)
            temp_path = f.name

        try:
            cfg = RunConfig.from_file(temp_path)
            self.assertEqual(cfg.source.repository, "backend")
            self.assertEqual(cfg.source.branch, "master")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_from_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            RunConfig.from_file("/path/that/does/not/exist.json")


if __name__ == "__main__":
    unittest.main()
