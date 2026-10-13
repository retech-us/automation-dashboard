"""Scan investigation must sign in with the entered account, not a stale token."""

import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import runner_server


SCAN_URL = "https://krcs.rebotics.net/reporting/scans/17637228?store=53454&planogram=1218993&date=2026-10-08"
HOST = "https://krcs.rebotics.net"


class InvestigationAuthTests(unittest.TestCase):
    def tearDown(self):
        runner_server.INSTANCE_TOKENS.pop(HOST, None)
        runner_server.TOKEN = ""

    def test_entered_password_replaces_a_saved_token(self):
        runner_server.INSTANCE_TOKENS[HOST] = "stale-token"
        runner_server.TOKEN = "stale-token"
        calls = []

        def fake_auth(base_url=None, username=None, password=None, override_token=None):
            calls.append({
                "base_url": base_url,
                "username": username,
                "password": password,
                "override_token": override_token,
            })
            return "fresh-token"

        def fake_investigate(base_url, token, problem, scan_url, opener=None):
            self.assertEqual(base_url, HOST)
            self.assertEqual(token, "fresh-token")
            self.assertEqual(problem, "Explain this scan")
            return {"what_happened": "Checked the scan"}

        with patch.object(runner_server, "get_auth_token", fake_auth), \
             patch.object(runner_server, "investigate_scan_problem", fake_investigate), \
             patch.object(runner_server, "remember_instance_tokens"):
            result = runner_server.run_scan_investigation({
                "scan_url": SCAN_URL,
                "problem": "Explain this scan",
                "username": "associate",
                "password": "correct-password",
                "token": "stale-token",
            })

        self.assertEqual(result["status"], "success")
        self.assertEqual(calls, [{
            "base_url": HOST,
            "username": "associate",
            "password": "correct-password",
            "override_token": None,
        }])

    def test_rejected_saved_token_is_forgotten(self):
        runner_server.INSTANCE_TOKENS[HOST] = "stale-token"
        runner_server.TOKEN = "stale-token"

        def fake_investigate(*_args, **_kwargs):
            raise urllib.error.HTTPError(SCAN_URL, 401, "Unauthorized", None, None)

        with patch.object(runner_server, "investigate_scan_problem", fake_investigate), \
             patch.object(runner_server, "remember_instance_tokens"):
            result = runner_server.run_scan_investigation({
                "scan_url": SCAN_URL,
                "problem": "Explain this scan",
                "token": "stale-token",
            })

        self.assertEqual(result["status"], "error")
        self.assertIn("username and password", result["error"])
        self.assertNotIn(HOST, runner_server.INSTANCE_TOKENS)
        self.assertEqual(runner_server.TOKEN, "")

    def test_runner_sends_credentials_and_does_not_store_the_password(self):
        page = (ROOT / "test_runner.html").read_text(encoding="utf-8")
        start = page.index("async function investigateScanProblem()")
        body = page[start:page.index("function escapeInvestigationText", start)]
        self.assertIn("username: username || undefined", body)
        self.assertIn("password: password || undefined", body)
        self.assertIn("token: username && password ? undefined", body)
        stored = page[page.index("function saveAuthToLocalStorage()"):page.index("function loadAuthFromLocalStorage()")]
        self.assertNotIn("pass,", stored)
        self.assertNotIn("pass:", stored)

    def test_one_sign_in_panel_serves_both_workflows(self):
        page = (ROOT / "test_runner.html").read_text(encoding="utf-8")
        panel_start = page.index('<section class="ir-shared-signin"')
        workflows_start = page.index('<div class="ir-workflow-pair">')
        self.assertLess(panel_start, workflows_start)
        panel = page[panel_start:workflows_start]
        for field in ('id="cfg-username"', 'id="cfg-password"', 'id="cfg-token"'):
            self.assertIn(field, panel)
            self.assertEqual(page.count(field), 1)
        self.assertNotIn('id="cfg-base-url"', panel)
        task_card = page[workflows_start:page.index('aria-labelledby="scan-investigation-heading"')]
        self.assertIn('id="cfg-task-id-direct"', task_card)
        self.assertIn('id="cfg-base-url"', task_card)
        body = page[page.index("async function investigateScanProblem()"):page.index("function escapeInvestigationText")]
        self.assertIn("base_url: `https://${scanHost}`", body)
        self.assertNotIn("cfg-base-url", body)
        self.assertIn("showInvestigationActions(payload)", body)

    def test_task_load_prefers_entered_password_and_drops_cached_wording(self):
        page = (ROOT / "test_runner.html").read_text(encoding="utf-8")
        self.assertNotIn("Cached actions were not used", page)
        load = page[page.index("fetch('/api/runner/load_task'"):page.index("async function investigateScanProblem()")]
        self.assertIn("token: username && password ? undefined", load)
        self.assertIn("data.error_code === 'AUTH_REQUIRED'", load)
        sync = page[page.index("IR_STUDIO_SYNC_TASK"):page.index("IR_CREDENTIALS_SYNC")]
        self.assertNotIn("loadTaskById", sync)
        keys = page[page.index("event.key === 'Enter'"):page.index("event.key === 'Escape'")]
        self.assertIn("cfg-investigate-url", keys)
        self.assertIn("investigateScanProblem()", keys)
        self.assertIn("cfg-task-id-direct", keys)
        self.assertLess(keys.index("cfg-investigate-url"), keys.index("loadTaskById()"))


class _FakeResponse:
    def __init__(self, body, content_type):
        self._body = body.encode("utf-8")
        self.headers = {"Content-Type": content_type}

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class LiveActionListTests(unittest.TestCase):
    def _run(self, responses):
        def fake_urlopen(req, context=None, timeout=None):
            url = req.full_url
            for marker, outcome in responses:
                if marker in url:
                    if isinstance(outcome, Exception):
                        raise outcome
                    return outcome
            return _FakeResponse("<!DOCTYPE html><html></html>", "text/html; charset=utf-8")

        with patch.object(runner_server.urllib.request, "urlopen", fake_urlopen):
            return runner_server.fetch_live_task_actions("https://harr.rebotics.net", 8929252, "tok")

    def test_rejected_sign_in_is_reported_instead_of_web_page_errors(self):
        unauthorized = urllib.error.HTTPError("u", 401, "Unauthorized", None, None)
        with self.assertRaises(runner_server.LiveActionsAuthError) as ctx:
            self._run([("/api/v1/tasks/8929252/action-list/retailer/", unauthorized)])
        message = str(ctx.exception)
        self.assertIn("rejected the sign-in", message)
        self.assertNotIn("Expecting value", message)

    def test_web_page_endpoints_are_skipped(self):
        rows = '[{"id": 1}]'
        items, url = self._run([("/api/v1/tasks/8929252/action-list/", _FakeResponse(rows, "application/json"))])
        self.assertEqual(items, [{"id": 1}])

    def test_no_capture_explains_the_empty_action_list(self):
        message = runner_server.empty_action_list_message(8929252, "https://harr.rebotics.net", "NO_CAPTURE")
        self.assertIn("no shelf capture", message)
        self.assertIn("no scan", message)

    def test_empty_action_list_says_the_task_has_no_actions(self):
        with self.assertRaises(ValueError) as ctx:
            self._run([("/api/v1/tasks/8929252/action-list/retailer/", _FakeResponse('{"results": []}', "application/json"))])
        self.assertIn("has no actions yet", str(ctx.exception))

    def test_evidence_is_grouped_and_actions_fill_the_table(self):
        page = (ROOT / "test_runner.html").read_text(encoding="utf-8")
        evidence = page[page.index("function renderInvestigationEvidence"):page.index("function showInvestigationActions")]
        for text in ("issue_labels", "expected_product", "belongs_at", "issue.stage", "issue.scan_id", "row.detail", "groups.get(label).length"):
            self.assertIn(text, evidence)
        actions = page[page.index("function showInvestigationActions"):page.index("function renderInvestigation(report)")]
        for text in ("report.actions", "investigation_issues", "phase: 'investigation'", "This scan has no report actions.", "renderActionTable()"):
            self.assertIn(text, actions)


if __name__ == "__main__":
    unittest.main()
