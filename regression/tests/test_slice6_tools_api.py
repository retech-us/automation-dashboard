"""Unit tests for Slice 6 agent tools JSON API."""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from regression.tools import invoke_tool, list_tools_payload
from regression.tools_http import make_server

CAT1 = ROOT / "regression" / "tests" / "fixtures" / "domain_cat1_t5_mixed.json"
AL_FIXTURE = ROOT / "regression" / "tests" / "fixtures" / "action_list_retailer_sample.json"


class ToolRegistryTests(unittest.TestCase):
    def test_list_includes_core_tools(self):
        payload = list_tools_payload()
        names = {t["name"] for t in payload["tools"]}
        self.assertIn("resolve_env", names)
        self.assertIn("domain_parity", names)
        self.assertIn("action_list", names)
        self.assertIn("verdict_policy", payload)

    def test_unknown_tool(self):
        resp = invoke_tool("nope", {})
        self.assertFalse(resp.ok)
        self.assertEqual(resp.exit_code, 2)

    def test_resolve_env(self):
        resp = invoke_tool("resolve_env", {"env": "epsilon"})
        self.assertTrue(resp.ok)
        self.assertEqual(resp.result["base_url"], "https://epsilon.rebotics.net")

    def test_resolve_images_pasta(self):
        resp = invoke_tool(
            "resolve_images",
            {"category": "pasta", "bays": [1, 2], "allow_missing_files": True},
        )
        self.assertTrue(resp.ok, resp.as_dict())
        self.assertEqual(len(resp.result["images"]), 2)

    def test_domain_parity_case(self):
        resp = invoke_tool("domain_parity", {"env": "epsilon", "case": "cat1_t5_mixed"})
        self.assertTrue(resp.ok, resp.as_dict())
        self.assertEqual(resp.result["domain_card_count"], 6)

    def test_action_list_fixture(self):
        resp = invoke_tool(
            "action_list",
            {
                "env": "epsilon",
                "task_id": 999,
                "fixture": str(AL_FIXTURE),
            },
        )
        self.assertTrue(resp.ok, resp.as_dict())
        self.assertEqual(resp.result["item_count"], 3)

    def test_provision_dry_run(self):
        resp = invoke_tool(
            "provision",
            {"env": "epsilon", "category": "pasta", "bays": "1,2"},
        )
        self.assertTrue(resp.ok, resp.as_dict())
        self.assertTrue(resp.result["dry_run"])

    def test_health(self):
        resp = invoke_tool("health", {})
        self.assertTrue(resp.ok)
        self.assertGreaterEqual(resp.result["tool_count"], 6)


class CliToolsTests(unittest.TestCase):
    def test_cli_tools_list(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "regression" / "cli.py"), "tools", "list"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertIn("tools", data)

    def test_cli_tools_call(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "regression" / "cli.py"),
                "tools",
                "call",
                "resolve_env",
                "--args-json",
                '{"env":"epsilon"}',
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        data = json.loads(proc.stdout)
        self.assertTrue(data["ok"])
        self.assertEqual(data["result"]["env"], "epsilon")


class HttpToolsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = make_server("127.0.0.1", 0)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def _get(self, path: str):
        with urllib.request.urlopen(f"{self.base}{path}", timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))

    def _post(self, path: str, body: dict):
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    def test_get_tools(self):
        status, data = self._get("/v1/tools")
        self.assertEqual(status, 200)
        self.assertTrue(any(t["name"] == "resolve_env" for t in data["tools"]))

    def test_post_resolve_env(self):
        status, data = self._post("/v1/tools/resolve_env", {"env": "epsilon"})
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"])
        self.assertEqual(data["result"]["base_url"], "https://epsilon.rebotics.net")

    def test_post_domain_parity(self):
        status, data = self._post(
            "/v1/tools/domain_parity",
            {"env": "epsilon", "fixture": str(CAT1)},
        )
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"])
        self.assertEqual(data["result"]["domain_card_count"], 6)

    def test_post_call_envelope(self):
        status, data = self._post(
            "/v1/tools/call",
            {"tool": "health", "args": {}},
        )
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"])

    def test_unknown_tool_http(self):
        status, data = self._post("/v1/tools/not_a_tool", {})
        self.assertEqual(status, 400)
        self.assertFalse(data["ok"])


if __name__ == "__main__":
    unittest.main()
