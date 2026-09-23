import json
import unittest
import urllib.error
from pathlib import Path

from core.digital_report_client import (
    fetch_section_product_reports,
    fetch_section_product_reports_for_scans,
    normalize_section_product_reports,
)


FIXTURES = Path(__file__).parent / "fixtures"


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


class TestDigitalReportClient(unittest.TestCase):
    def test_normalizes_results_envelope_and_empty_action_taken(self):
        payload = json.loads(
            (FIXTURES / "section_product_reports_ok.json").read_text(encoding="utf-8")
        )

        items = normalize_section_product_reports(payload, scan_id=16920444)

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].scan_id, 16920444)
        self.assertEqual(items[0].upc, "840093104403")
        self.assertEqual(items[0].action_type, "ok")
        self.assertEqual(items[0].action_taken, "-")

    def test_normalizes_live_r07_shape(self):
        payload = json.loads(
            (FIXTURES / "section_product_reports_live.json").read_text(encoding="utf-8")
        )

        items = normalize_section_product_reports(payload, scan_id=3768606)

        self.assertEqual(len(items), 3)
        fixed, restocked, unidentified = items

        self.assertEqual(fixed.scan_id, 3768606)
        self.assertEqual(fixed.upc, "644911005220")
        self.assertEqual(fixed.product_name, "PERESONAL FRAGRANCE BODYMIST Q 1 EA")
        self.assertEqual(fixed.section, "1")
        self.assertEqual(fixed.pog_position, "7:1")
        self.assertEqual(fixed.action_type, "ok")
        self.assertEqual(fixed.action_taken, "Fixed Item")

        self.assertEqual(restocked.action_type, "oos")
        self.assertEqual(restocked.action_taken, "Restocked Item")

        self.assertEqual(unidentified.upc, "")
        self.assertEqual(unidentified.pog_position, "1:4")
        self.assertEqual(unidentified.action_type, "unidentified")

    def test_normalizes_array_and_camel_case_aliases(self):
        payload = [{
            "scanId": 7,
            "productName": "Sample",
            "pogPosition": "1:2",
            "rogPosition": "1:3",
            "upc": 12345,
            "actionType": "Move",
            "actionTaken": None,
        }]

        item = normalize_section_product_reports(payload, scan_id=99)[0]

        self.assertEqual(item.scan_id, 7)
        self.assertEqual(item.product_name, "Sample")
        self.assertEqual(item.pog_position, "1:2")
        self.assertEqual(item.rog_position, "1:3")
        self.assertEqual(item.upc, "12345")
        self.assertEqual(item.action_taken, "-")

    def test_placeholder_product_code_is_treated_as_missing_upc(self):
        items = normalize_section_product_reports(
            [{
                "product": {
                    "name": "Product with code #PLU not found",
                    "product_code": "PLU not found",
                },
                "on_shelf_position": "2:1",
                "report_product_status": "invader",
                "reason": "Removed Item",
            }],
            scan_id=3768606,
        )

        self.assertEqual(items[0].upc, "")
        self.assertEqual(items[0].pog_position, "2:1")
        self.assertEqual(items[0].action_taken, "Removed Item")

    def test_invalid_row_scan_id_uses_requested_scan_id(self):
        items = normalize_section_product_reports(
            [{"scan_id": "not-a-number", "upc": "123"}],
            scan_id=42,
        )

        self.assertEqual(items[0].scan_id, 42)

    def test_fetch_uses_scan_id_and_token_authentication(self):
        captured = {}

        def opener(request, timeout):
            captured["url"] = request.full_url
            captured["auth"] = request.headers["Authorization"]
            captured["timeout"] = timeout
            return FakeResponse([])

        result = fetch_section_product_reports(
            "https://harr.rebotics.net", "secret", 16920444, opener=opener
        )

        self.assertTrue(result.ok)
        self.assertIn("scan_id=16920444", captured["url"])
        self.assertEqual(captured["auth"], "Token secret")
        self.assertEqual(captured["timeout"], 15)

    def test_fetch_returns_structured_error_for_http_failure(self):
        def opener(request, timeout):
            raise urllib.error.HTTPError(
                request.full_url, 401, "Unauthorized", hdrs=None, fp=None
            )

        result = fetch_section_product_reports(
            "https://harr.rebotics.net", "invalid", 1, opener=opener
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.status_code, 401)
        self.assertIn("Unauthorized", result.error)

    def test_fetches_each_unique_scan_id_and_merges_rows(self):
        requested_scan_ids = []

        def opener(request, timeout):
            scan_id = int(request.full_url.rsplit("=", 1)[1])
            requested_scan_ids.append(scan_id)
            return FakeResponse([{"scan_id": scan_id, "upc": str(scan_id)}])

        result = fetch_section_product_reports_for_scans(
            "https://harr.rebotics.net",
            "secret",
            [8, 7, 8],
            opener=opener,
        )

        self.assertTrue(result.ok)
        self.assertEqual(requested_scan_ids, [7, 8])
        self.assertEqual([item.scan_id for item in result.items], [7, 8])

    def test_partial_failure_keeps_successful_scan_rows_and_warning(self):
        def opener(request, timeout):
            scan_id = int(request.full_url.rsplit("=", 1)[1])
            if scan_id == 8:
                raise urllib.error.HTTPError(
                    request.full_url, 500, "Server Error", hdrs=None, fp=None
                )
            return FakeResponse([{"scan_id": scan_id, "upc": str(scan_id)}])

        result = fetch_section_product_reports_for_scans(
            "https://harr.rebotics.net",
            "secret",
            [7, 8],
            opener=opener,
        )

        self.assertTrue(result.ok)
        self.assertEqual([item.scan_id for item in result.items], [7])
        self.assertIn("scan_id 8", result.error)
        self.assertEqual(result.failed_scan_ids, [8])


if __name__ == "__main__":
    unittest.main()
