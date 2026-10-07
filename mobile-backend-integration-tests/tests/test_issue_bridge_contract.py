"""Contract checks for the failure↔Jira bridge, lifecycle, and attention filters."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class IssueBridgeContractTests(unittest.TestCase):
    def test_bridge_script_is_loaded_before_app(self):
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        bridge = index.find("assets/js/issue-bridge.js")
        app = index.find("assets/js/app.v16.js")
        self.assertGreater(bridge, 0)
        self.assertGreater(app, bridge)

    def test_attention_panel_exposes_filters(self):
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="attention-filters"', index)
        self.assertIn('id="attention-filter-suite"', index)
        self.assertIn('id="attention-filter-bucket"', index)
        self.assertIn('id="attention-filter-area"', index)
        self.assertIn('id="attention-filter-lifecycle"', index)
        self.assertIn('id="attention-filter-orphan"', index)
        self.assertIn('id="attention-filter-q"', index)

    def test_ir_quality_findings_are_visible_on_summary(self):
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="ir-quality-findings"', index)
        self.assertIn("Quality findings", index)
        self.assertEqual(index.count('id="ir-quality-findings"'), 1)
        self.assertEqual(index.count('id="ir-quality-scans"'), 1)
        self.assertNotIn('id="ir-quality-findings" hidden', index)

    def test_bridge_exposes_lifecycle_and_verify_helpers(self):
        script = (ROOT / "assets/js/issue-bridge.js").read_text(encoding="utf-8")
        for name in (
            "failureId",
            "getLink",
            "setLink",
            "getState",
            "setState",
            "reconcile",
            "listVerified",
            "findOrphans",
            "findMatches",
            "createIssueUrl",
            "readAttentionFilters",
            "writeAttentionFilters",
            "STATES",
        ):
            self.assertIn(name, script)
        for state in ("detected", "investigating", "linked", "fixed", "verified", "reopened"):
            self.assertIn(state, script)

    def test_app_wires_lifecycle_actions_and_cleared_section(self):
        app = (ROOT / "assets/js/app.v16.js").read_text(encoding="utf-8")
        self.assertIn("function gotoAttention", app)
        self.assertIn("renderFailureLifecycleBlock", app)
        self.assertIn("renderVerifiedClearedSection", app)
        self.assertIn("renderOrphanSummaryBar", app)
        self.assertIn("renderOrphanJiraPanel", app)
        self.assertIn("data-lifecycle-state", app)
        self.assertIn("data-orphan-filter", app)
        self.assertIn("IssueBridge.reconcile", app)
        self.assertIn("data-jira-create", app)

    def test_trends_link_periods_to_attention(self):
        app = (ROOT / "assets/js/app.v16.js").read_text(encoding="utf-8")
        for name in (
            "detectTrendRegressions",
            "suiteForPeriodDrill",
            "renderTrendFailureStrip",
            "data-trend-drill",
            "chart-regress-band",
        ):
            self.assertIn(name, app)
        self.assertIn("gotoAttention({ suite: drill.getAttribute('data-suite')", app)

    def test_create_issue_url_targets_reb3_by_project_key(self):
        script = (ROOT / "assets/js/issue-bridge.js").read_text(encoding="utf-8")
        self.assertIn("selectedProjectKey", script)
        self.assertIn("CreateIssue!default.jspa", script)
        self.assertNotIn("pid: projectKey", script)
        fetcher = (ROOT / "scripts/fetch-jira.py").read_text(encoding="utf-8")
        self.assertIn('os.environ.get("JIRA_PROJECT_KEY", "REB3")', fetcher)
        self.assertNotIn('or "STORE"', fetcher)


class IssueBridgeReconcileLogicTests(unittest.TestCase):
    """Exercise reconcile rules with a tiny JS runtime if node is available."""

    def test_reconcile_rules_with_node(self):
        import shutil
        import subprocess
        import tempfile

        if not shutil.which("node"):
            self.skipTest("node not available")

        bridge = (ROOT / "assets/js/issue-bridge.js").read_text(encoding="utf-8")
        # Minimal in-memory localStorage for node.
        script = f"""
const store = {{}};
global.localStorage = {{
  getItem: (k) => (k in store ? store[k] : null),
  setItem: (k, v) => {{ store[k] = String(v); }},
  removeItem: (k) => {{ delete store[k]; }},
}};
global.window = global;
global.DASHBOARD_SNAPSHOTS = {{
  snapshots: {{
    jira: {{
      jiraUrl: 'https://example.atlassian.net',
      projectKey: 'REB3',
      issues: [
        {{ key: 'REB3-1', status: 'Done', statusCategory: 'done', summary: 'login broken' }},
        {{ key: 'REB3-2', status: 'In Progress', statusCategory: 'indeterminate', summary: 'scan fail' }},
      ],
    }},
  }},
}};
{bridge}
const failA = {{ repo: 'web', name: 'login fails', feature: 'Login', status: 'failed', category: 'assertion' }};
const failB = {{ repo: 'web', name: 'scan fails', feature: 'Scans', status: 'failed', category: 'api' }};
IssueBridge.setLink(failA, {{ key: 'REB3-1' }});
IssueBridge.setLink(failB, {{ key: 'REB3-2' }});
IssueBridge.reconcile([failA, failB]);
const a1 = IssueBridge.getState(failA);
const b1 = IssueBridge.getState(failB);
IssueBridge.reconcile([]);
const a2 = IssueBridge.getState(failA);
const b2 = IssueBridge.getState(failB);
const verifiedAfterClear = IssueBridge.listVerified().map(r => r.key);
IssueBridge.reconcile([failA]);
const a3 = IssueBridge.getState(failA);
console.log(JSON.stringify({{ a1, b1, a2, b2, a3, verifiedAfterClear }}));
"""
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as handle:
            handle.write(script)
            path = handle.name
        result = subprocess.run(["node", path], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        import json
        data = json.loads(result.stdout.strip())
        self.assertEqual(data["a1"], "fixed")
        self.assertEqual(data["b1"], "linked")
        self.assertEqual(data["a2"], "verified")
        self.assertEqual(data["b2"], "linked")
        self.assertEqual(data["a3"], "reopened")
        self.assertIn("REB3-1", data["verifiedAfterClear"] or [])

    def test_find_orphans_with_node(self):
        import json
        import shutil
        import subprocess
        import tempfile

        if not shutil.which("node"):
            self.skipTest("node not available")

        bridge = (ROOT / "assets/js/issue-bridge.js").read_text(encoding="utf-8")
        script = f"""
const store = {{}};
global.localStorage = {{
  getItem: (k) => (k in store ? store[k] : null),
  setItem: (k, v) => {{ store[k] = String(v); }},
  removeItem: (k) => {{ delete store[k]; }},
}};
global.window = global;
global.DASHBOARD_SNAPSHOTS = {{
  snapshots: {{
    jira: {{
      jiraUrl: 'https://example.atlassian.net',
      issues: [
        {{ key: 'REB3-10', type: 'Bug', status: 'Open', statusCategory: 'new', summary: 'Cart checkout timeout on staging' }},
        {{ key: 'REB3-11', type: 'Bug', status: 'Done', statusCategory: 'done', summary: 'Old resolved bug' }},
        {{ key: 'REB3-12', type: 'Bug', status: 'Open', statusCategory: 'new', summary: 'login password reset broken' }},
        {{ key: 'REB3-13', type: 'Story', status: 'Open', statusCategory: 'new', summary: 'Improve scan UX' }},
      ],
    }},
  }},
}};
{bridge}
const failLogin = {{ repo: 'web', name: 'login password reset broken', feature: 'Login', status: 'failed', category: 'assertion' }};
const failScan = {{ repo: 'api', name: 'scan upload 500', feature: 'Scans', status: 'failed', category: 'api' }};
IssueBridge.setLink(failLogin, {{ key: 'REB3-12' }});
const orphans = IssueBridge.findOrphans([failLogin, failScan]);
console.log(JSON.stringify({{
  unlinked: orphans.unlinkedFailures.map(f => f.name),
  orphanKeys: orphans.orphanJira.map(i => i.key),
  counts: orphans.counts,
}}));
"""
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as handle:
            handle.write(script)
            path = handle.name
        result = subprocess.run(["node", path], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout.strip())
        self.assertEqual(data["unlinked"], ["scan upload 500"])
        self.assertIn("REB3-10", data["orphanKeys"])
        self.assertNotIn("REB3-11", data["orphanKeys"])  # Done
        self.assertNotIn("REB3-12", data["orphanKeys"])  # linked / matched
        self.assertNotIn("REB3-13", data["orphanKeys"])  # Story, not Bug


if __name__ == "__main__":
    unittest.main()
