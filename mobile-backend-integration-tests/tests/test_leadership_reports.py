import tempfile
import unittest
import zipfile
from pathlib import Path

from core.leadership_reports import generate_leadership_report, normalize_analysis, report_filename


class LeadershipReportTests(unittest.TestCase):
    def test_normalize_analysis_keeps_leadership_content(self):
        result = normalize_analysis({
            "question": "Are we ready to release?",
            "answer": "Release is on hold.",
            "verdict": "hold",
            "confidence": "high",
            "context_label": "Overview",
            "findings": [{
                "severity": "critical",
                "title": "Open blockers",
                "detail": "Two blockers remain.",
                "evidence": [{"source": "Jira", "value": 2}],
            }],
            "recommendations": ["Resolve the blockers."],
            "sources": ["Jira summary"],
            "generated_at": "2026-10-12T10:00:00+00:00",
            "run_id": "run-123",
        })

        self.assertEqual(result["title"], "Overview leadership analysis")
        self.assertEqual(result["executive_summary"], "Release is on hold.")
        self.assertEqual(result["findings"][0]["title"], "Open blockers")
        self.assertEqual(result["recommendations"], ["Resolve the blockers."])

    def test_normalize_analysis_redacts_credentials_and_signed_query_values(self):
        result = normalize_analysis({
            "question": "Show evidence",
            "answer": "Evidence collected.",
            "context_label": "Sentry",
            "findings": [{
                "title": "Unsafe evidence",
                "detail": "Do not leak credentials.",
                "evidence": [{
                    "source": "API",
                    "value": {
                        "token": "secret-token",
                        "password": "secret-password",
                        "url": "https://example.test/report?signature=secret&task=12",
                    },
                }],
            }],
        })

        serialized = str(result)
        self.assertNotIn("secret-token", serialized)
        self.assertNotIn("secret-password", serialized)
        self.assertNotIn("signature=secret", serialized)
        self.assertIn("[REDACTED]", serialized)

    def test_report_filename_is_safe_and_has_requested_extension(self):
        name = report_filename("Jira Quality & Delivery / Q4", "pptx")

        self.assertEqual(name, "jira-quality-delivery-q4-leadership-report.pptx")

    def test_unknown_export_format_is_rejected(self):
        with self.assertRaises(ValueError):
            report_filename("Overview", "pdf")

    def test_exports_use_symphonyai_format(self):
        workspace = Path(__file__).resolve().parents[2]
        analysis = {
            "question": "Are research & delivery ready?",
            "answer": "Release is on hold until blockers close.",
            "verdict": "hold",
            "confidence": "high",
            "context_label": "Overview",
            "findings": [{
                "severity": "critical",
                "title": "Open blockers",
                "detail": "Two blockers remain before release.",
                "evidence": [{"source": "Jira", "value": 2}],
            }],
            "recommendations": ["Resolve the blockers."],
            "sources": ["Jira summary"],
            "generated_at": "2026-10-12T10:00:00+00:00",
            "run_id": "run-123",
        }
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary)
            document = generate_leadership_report(analysis, "docx", output_dir, workspace)
            deck = generate_leadership_report(analysis, "pptx", output_dir, workspace)
            with zipfile.ZipFile(document) as archive:
                document_xml = archive.read("word/document.xml").decode("utf-8")
            self.assertIn("Arial", document_xml)
            self.assertIn("0074E8", document_xml)
            self.assertNotIn("13213C", document_xml)
            self.assertIn("Are research and delivery ready?", document_xml)
            with zipfile.ZipFile(deck) as archive:
                content_types = archive.read("[Content_Types].xml").decode("utf-8")
                slide_names = [
                    name for name in archive.namelist()
                    if name.startswith("ppt/slides/slide") and name.endswith(".xml")
                ]
                slide_xml = "\n".join(archive.read(name).decode("utf-8") for name in slide_names)
                layouts = [name for name in archive.namelist() if name.startswith("ppt/slideLayouts/slideLayout")]
            self.assertIn("presentationml.presentation.main+xml", content_types)
            self.assertNotIn("template.main+xml", content_types)
            self.assertGreaterEqual(len(layouts), 37)
            self.assertNotIn("PepsiCo", slide_xml)
            self.assertNotIn(">Title</a:t>", slide_xml)
            self.assertIn("Decision", slide_xml)
            self.assertIn("00EAC3", slide_xml)
            self.assertIn("Are research and delivery ready?", slide_xml)


if __name__ == "__main__":
    unittest.main()
