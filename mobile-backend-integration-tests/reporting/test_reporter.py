"""
Test Reporter for Headless Mobile-Backend Integration Tests.
Generates JUnit XML, JSON, and Human-Readable Markdown Parity Reports.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List
from adapters.core.models import ScenarioResult


class TestReporter:
    """Generates execution reports across scenarios and platforms."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_json_report(self, results: List[ScenarioResult]) -> Path:
        report_data = {
            "total": len(results),
            "passed": sum(1 for r in results if r.status == "PASS"),
            "failed": sum(1 for r in results if r.status == "FAIL"),
            "results": [
                {
                    "scenarioId": r.scenario_id,
                    "scenarioName": r.scenario_name,
                    "platform": r.platform.value if hasattr(r.platform, "value") else str(r.platform),
                    "status": r.status,
                    "durationMs": r.duration_ms,
                    "failureReason": r.failure_reason,
                    "steps": [
                        {
                            "name": s.step_name,
                            "status": s.status,
                            "durationMs": s.duration_ms,
                            "error": s.error_message,
                            "actions": [a.to_dict() for a in s.captured_actions],
                            "state": s.resulting_state.to_dict(),
                        }
                        for s in r.step_results
                    ],
                }
                for r in results
            ],
        }
        json_path = self.output_dir / "results.json"
        json_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
        return json_path

    def generate_junit_xml(self, results: List[ScenarioResult]) -> Path:
        testsuite = ET.Element("testsuite")
        testsuite.set("name", "HeadlessMobileBackendIntegrationTests")
        testsuite.set("tests", str(len(results)))
        testsuite.set("failures", str(sum(1 for r in results if r.status == "FAIL")))
        testsuite.set("time", str(sum(r.duration_ms for r in results) / 1000.0))

        for r in results:
            testcase = ET.SubElement(testsuite, "testcase")
            testcase.set("classname", f"mobile.{r.platform.value if hasattr(r.platform, 'value') else r.platform}")
            testcase.set("name", f"{r.scenario_id} - {r.scenario_name}")
            testcase.set("time", str(r.duration_ms / 1000.0))

            if r.status == "FAIL":
                failure = ET.SubElement(testcase, "failure")
                failure.set("message", r.failure_reason or "Assertion failed")
                failure.text = r.failure_reason

        xml_path = self.output_dir / "junit.xml"
        tree = ET.ElementTree(testsuite)
        tree.write(xml_path, encoding="utf-8", xml_declaration=True)
        return xml_path

    def generate_markdown_summary(self, results: List[ScenarioResult]) -> str:
        passed = sum(1 for r in results if r.status == "PASS")
        failed = sum(1 for r in results if r.status == "FAIL")
        total = len(results)

        lines = [
            "# Headless Mobile–Backend Integration Test Report",
            "",
            f"**Total Scenarios:** {total} | **Passed:** {passed} | **Failed:** {failed}",
            "",
            "| Scenario | Platform | Status | Duration (ms) | Notes |",
            "|---|---|---|---|---|",
        ]

        for r in results:
            plat = r.platform.value if hasattr(r.platform, "value") else str(r.platform)
            status_badge = "✅ PASS" if r.status == "PASS" else "❌ FAIL"
            notes = r.failure_reason or "All state and action assertions passed"
            lines.append(f"| `{r.scenario_id}` | `{plat}` | {status_badge} | {r.duration_ms:.1f}ms | {notes} |")

        lines.append("")
        summary_md = "\n".join(lines)
        md_path = self.output_dir / "summary.md"
        md_path.write_text(summary_md, encoding="utf-8")
        return summary_md
