import unittest

from core.dashboard_agents import answer_question, list_agents, run_agent


class DashboardAgentContractTests(unittest.TestCase):
    def test_all_dashboard_agents_are_read_only(self):
        agents = list_agents()
        self.assertEqual(len(agents), 6)
        self.assertTrue(all(agent["access"] == "read-only" for agent in agents))
        self.assertIn("ir-investigator", {agent["id"] for agent in agents})

    def test_ir_agent_treats_ok_dash_as_no_action_required(self):
        result = run_agent("ir-investigator", {
            "metadata": {"task_id": 123, "status": "completed", "final_compliance": 99},
            "performed_evidence": {
                "digital_rows_ok_no_action": 12,
                "digital_rows_unconfirmed": 0,
                "digital_rows_with_action": 4,
            },
        })

        self.assertEqual(result["verdict"], "clear")
        self.assertIn("12 products already OK", result["summary"])
        self.assertTrue(any("No associate action was required" in finding["detail"] for finding in result["findings"]))

    def test_ir_agent_warns_only_for_non_ok_dash_rows(self):
        result = run_agent("ir-investigator", {
            "metadata": {"task_id": 123, "status": "completed", "final_compliance": 99},
            "performed_evidence": {
                "digital_rows_ok_no_action": 12,
                "digital_rows_unconfirmed": 2,
                "digital_rows_with_action": 4,
                "unconfirmed_action_types": {"oos": 2},
            },
        })

        self.assertEqual(result["verdict"], "needs-attention")
        self.assertTrue(any("non-OK" in finding["detail"] for finding in result["findings"]))

    def test_release_agent_combines_suite_and_jira_evidence(self):
        result = run_agent("release-risk", {
            "suites": [{"repo": "web", "summary": {"total": 10, "passed": 8, "failed": 1, "broken": 1}}],
            "jira": {"summary": {"blockers": 2}},
        })

        self.assertEqual(result["verdict"], "hold")
        self.assertIn("2 Jira blockers", result["summary"])

    def test_triage_coverage_flaky_and_execution_agents_return_shared_contract(self):
        context = {
            "suites": [{"repo": "web", "summary": {"total": 10, "passed": 5, "broken": 4, "skipped": 1}}],
            "failures": [
                {"name": "Missing button", "category": "locator", "reason": "Element not interactable"},
                {"name": "Bad value", "category": "assertion", "reason": "Expected 1 but got 2"},
            ],
        }
        for agent_id in ("failure-triage", "coverage", "flaky-test", "test-execution"):
            result = run_agent(agent_id, context)
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["access"], "read-only")
            self.assertTrue(result["run_id"])
            self.assertIsInstance(result["recommendations"], list)

    def test_unknown_agent_uses_structured_error(self):
        result = run_agent("unknown", {})
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"]["code"], "UNKNOWN_AGENT")

    def test_duration_question_answers_only_the_duration(self):
        result = answer_question("How long did this reset take?", {
            "task_flow": {
                "metadata": {"task_id": 8900772, "wall_duration_min": 42, "status": "completed", "final_compliance": 99},
                "performed_evidence": {"digital_rows_ok_no_action": 10, "digital_rows_unconfirmed": 0},
            },
        })

        self.assertEqual(result["status"], "success")
        self.assertIn("42 minutes", result["answer"])
        self.assertNotIn("generated actions", result["answer"])
        self.assertEqual(result["question"], "How long did this reset take?")

    def test_action_taken_dash_question_explains_ok_products(self):
        result = answer_question("Why is Action Taken a dash?", {
            "task_flow": {
                "metadata": {"task_id": 8900772, "status": "completed", "final_compliance": 99},
                "performed_evidence": {
                    "digital_rows_ok_no_action": 10,
                    "digital_rows_unconfirmed": 0,
                    "digital_rows_with_action": 248,
                },
            },
        })

        self.assertIn("10", result["answer"])
        self.assertIn("already correct", result["answer"])
        self.assertNotIn("generated actions", result["answer"])

    def test_unrelated_question_does_not_invent_an_analysis(self):
        result = answer_question("What is the weather in Dallas?", {
            "task_flow": {"metadata": {"task_id": 1, "status": "completed"}},
        })

        self.assertEqual(result["verdict"], "not-covered")
        self.assertNotIn("generated actions", result["answer"])

    def test_release_question_uses_suite_and_jira_evidence(self):
        result = answer_question("Are we ready to release?", {
            "suites": [{"repo": "web", "summary": {"total": 10, "passed": 8, "failed": 1, "broken": 1}}],
            "jira": {"summary": {"blockers": 2}},
            "failures": [],
            "active_tab": "overview",
        })

        self.assertEqual(result["verdict"], "hold")
        self.assertIn("2 Jira blockers", result["answer"])
        self.assertEqual(result["context_label"], "Overview")

    def test_jira_tab_answers_from_jira_only(self):
        result = answer_question("How many defects are open?", {
            "active_tab": "jira",
            "jira": {
                "summary": {"totalDefects": 1000, "openDefects": 193, "blockers": 130},
                "byPriority": {"Highest": 130, "High": 236},
            },
        })

        self.assertEqual(result["context_label"], "Jira Quality & Delivery")
        self.assertIn("193 open", result["answer"])
        self.assertEqual(result["sources"], ["Jira summary"])

    def test_sentry_tab_answers_from_sentry_only(self):
        result = answer_question("What is our Sentry extra spend?", {
            "active_tab": "sentry",
            "sentry_config": {
                "plan": {
                    "features": [
                        {"feature": "Spans", "extra_spend_usd": 997.39},
                        {"feature": "Replays", "extra_spend_usd": 799.0},
                    ],
                },
            },
        })

        self.assertEqual(result["context_label"], "Sentry")
        self.assertIn("$1,796.39", result["answer"])
        self.assertNotIn("Jira", result["answer"])

    def test_ir_question_on_jira_tab_is_not_answered_from_ir(self):
        result = answer_question("How long did this reset take?", {
            "active_tab": "jira",
            "jira": {"summary": {"openDefects": 193}},
            "task_flow": {"metadata": {"wall_duration_min": 42}},
        })

        self.assertEqual(result["verdict"], "not-covered")
        self.assertIn("Jira Quality & Delivery", result["answer"])


if __name__ == "__main__":
    unittest.main()
