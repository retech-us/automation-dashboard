"""
Unit tests for Shelf Intelligence API Contract Verifier.
Validates HTTP response schema assertions, data type checking, and error diagnostics.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.api_contract_verifier import ApiContractVerifier, ContractVerificationResult


class ApiContractVerifierTests(unittest.TestCase):

    def test_verify_auth_contract_valid(self):
        valid_payload = {
            "token": "secret_abc123",
            "user": {"id": 101, "username": "field_user"},
        }
        res = ApiContractVerifier.verify_auth_contract(valid_payload, 200)
        self.assertTrue(res.is_valid)
        self.assertEqual(len(res.field_errors), 0)
        self.assertEqual(len(res.missing_fields), 0)

    def test_verify_auth_contract_missing_token(self):
        invalid_payload = {"user": {"id": 101, "username": "field_user"}}
        res = ApiContractVerifier.verify_auth_contract(invalid_payload, 200)
        self.assertFalse(res.is_valid)
        self.assertTrue(any("token" in m for m in res.missing_fields))

    def test_verify_user_profile_contract_valid(self):
        payload = {"id": 42, "username": "qa_operator", "email": "qa@rebotics.net"}
        res = ApiContractVerifier.verify_user_profile_contract(payload, 200)
        self.assertTrue(res.is_valid)

    def test_verify_user_profile_contract_missing_id(self):
        payload = {"username": "qa_operator"}
        res = ApiContractVerifier.verify_user_profile_contract(payload, 200)
        self.assertFalse(res.is_valid)
        self.assertIn("id", res.missing_fields)

    def test_verify_task_details_contract_valid(self):
        payload = {
            "id": 8601238,
            "title": "Intelligent Reset - Ice Cream",
            "store": 810,
            "planogram": 86738,
        }
        res = ApiContractVerifier.verify_task_details_contract(payload, 200)
        self.assertTrue(res.is_valid)

    def test_verify_planogram_categories_contract_valid(self):
        payload = {
            "results": [
                {"id": 1, "name": "Confections", "sections": [1, 2]},
                {"id": 2, "name": "Beverages", "sections": [3]},
            ]
        }
        res = ApiContractVerifier.verify_planogram_categories_contract(payload, 200)
        self.assertTrue(res.is_valid)

    def test_verify_action_list_contract_valid(self):
        payload = {
            "count": 1,
            "results": [
                {
                    "id": 501,
                    "action": "fix_position_in_bay",
                    "state": "STATE_IDLE",
                    "current_position": {
                        "shelf": 2,
                        "position": 1,
                        "section_info": {"id": 1, "name": "1"},
                    },
                    "expected_position": {
                        "shelf": 2,
                        "position": 3,
                        "section_info": {"id": 1, "name": "1"},
                    },
                }
            ],
        }
        res = ApiContractVerifier.verify_action_list_contract(payload, 200)
        self.assertTrue(res.is_valid)

    def test_verify_action_list_contract_missing_state(self):
        payload = {
            "results": [
                {
                    "id": 501,
                    # missing 'state'
                    "current_position": {"shelf": 1, "position": 1},
                }
            ]
        }
        res = ApiContractVerifier.verify_action_list_contract(payload, 200)
        self.assertFalse(res.is_valid)
        self.assertTrue(any("state" in m for m in res.missing_fields))

    def test_verify_ai_processing_contract_valid(self):
        for status in ("processing", "analyzing", "done", "completed"):
            res = ApiContractVerifier.verify_ai_processing_contract({"status": status, "id": 12}, 200)
            self.assertTrue(res.is_valid)

    def test_verify_ai_processing_contract_invalid_status(self):
        res = ApiContractVerifier.verify_ai_processing_contract({"status": "unknown_err"}, 200)
        self.assertFalse(res.is_valid)
        self.assertTrue(any("Invalid AI processing status" in e for e in res.field_errors))


if __name__ == "__main__":
    unittest.main()
