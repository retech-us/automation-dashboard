"""
Shelf Intelligence Quality Automation — API Contract Verifier.
Validates HTTP response structures, data types, status codes, and mandatory schema
fields across all Shelf Intelligence backend API contracts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ContractVerificationResult:
    endpoint: str
    is_valid: bool
    status_code: int = 200
    field_errors: List[str] = field(default_factory=list)
    missing_fields: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    checked_fields_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ApiContractVerifier:
    """Verifies schema contracts against Shelf Intelligence backend responses."""

    @staticmethod
    def verify_auth_contract(data: Any, status_code: int = 200) -> ContractVerificationResult:
        """Verifies POST /api/v1/2fa/verify/ or /api/v1/users/token/ contract."""
        errors: List[str] = []
        missing: List[str] = []
        checked = 0

        if not isinstance(data, dict):
            return ContractVerificationResult(
                endpoint="2fa/verify",
                is_valid=False,
                status_code=status_code,
                field_errors=[f"Expected JSON object, got {type(data).__name__}"],
            )

        # Expected fields: 'token' or 'access'/'key'
        has_token = any(k in data for k in ("token", "key", "access_token", "access"))
        checked += 1
        if not has_token:
            missing.append("token (or access_token/key)")

        if "user" in data:
            checked += 1
            if not isinstance(data["user"], dict):
                errors.append("Field 'user' must be an object")
            else:
                for req in ("id", "username"):
                    checked += 1
                    if req not in data["user"]:
                        missing.append(f"user.{req}")

        return ContractVerificationResult(
            endpoint="2fa/verify",
            is_valid=(len(errors) == 0 and len(missing) == 0),
            status_code=status_code,
            field_errors=errors,
            missing_fields=missing,
            checked_fields_count=checked,
        )

    @staticmethod
    def verify_user_profile_contract(data: Any, status_code: int = 200) -> ContractVerificationResult:
        """Verifies GET /api/v1/users/profile/ contract."""
        errors: List[str] = []
        missing: List[str] = []
        checked = 0

        if not isinstance(data, dict):
            return ContractVerificationResult(
                endpoint="users/profile",
                is_valid=False,
                status_code=status_code,
                field_errors=[f"Expected JSON object, got {type(data).__name__}"],
            )

        for req in ("id", "username"):
            checked += 1
            if req not in data:
                missing.append(req)

        return ContractVerificationResult(
            endpoint="users/profile",
            is_valid=(len(errors) == 0 and len(missing) == 0),
            status_code=status_code,
            field_errors=errors,
            missing_fields=missing,
            checked_fields_count=checked,
        )

    @staticmethod
    def verify_task_details_contract(data: Any, status_code: int = 200) -> ContractVerificationResult:
        """Verifies GET /api/v1/tasks/{id}/ contract."""
        errors: List[str] = []
        missing: List[str] = []
        checked = 0

        if not isinstance(data, dict):
            return ContractVerificationResult(
                endpoint="tasks/details",
                is_valid=False,
                status_code=status_code,
                field_errors=[f"Expected JSON object, got {type(data).__name__}"],
            )

        for req in ("id", "title"):
            checked += 1
            if req not in data:
                missing.append(req)

        # store and planogram references
        checked += 2
        if "store" not in data and "store_id" not in data:
            missing.append("store or store_id")
        if "planogram" not in data and "planogram_id" not in data:
            missing.append("planogram or planogram_id")

        return ContractVerificationResult(
            endpoint="tasks/details",
            is_valid=(len(errors) == 0 and len(missing) == 0),
            status_code=status_code,
            field_errors=errors,
            missing_fields=missing,
            checked_fields_count=checked,
        )

    @staticmethod
    def verify_planogram_categories_contract(data: Any, status_code: int = 200) -> ContractVerificationResult:
        """Verifies GET /api/v1/planograms/categories/ contract."""
        errors: List[str] = []
        missing: List[str] = []
        checked = 0

        categories = data
        if isinstance(data, dict) and "results" in data:
            categories = data["results"]

        if not isinstance(categories, list):
            return ContractVerificationResult(
                endpoint="planograms/categories",
                is_valid=False,
                status_code=status_code,
                field_errors=[f"Expected list of categories, got {type(data).__name__}"],
            )

        checked += 1
        for idx, cat in enumerate(categories):
            if not isinstance(cat, dict):
                errors.append(f"Category item [{idx}] must be an object")
                continue
            for req in ("id", "name"):
                checked += 1
                if req not in cat:
                    missing.append(f"category[{idx}].{req}")

        return ContractVerificationResult(
            endpoint="planograms/categories",
            is_valid=(len(errors) == 0 and len(missing) == 0),
            status_code=status_code,
            field_errors=errors,
            missing_fields=missing,
            checked_fields_count=checked,
        )

    @staticmethod
    def verify_action_list_contract(data: Any, status_code: int = 200) -> ContractVerificationResult:
        """
        Verifies GET /api/v1/tasks/{id}/action-list/retailer/ contract.
        Ensures row-level structure: id, action, state, current_position, expected_position.
        """
        errors: List[str] = []
        missing: List[str] = []
        checked = 0

        rows = data
        if isinstance(data, dict):
            checked += 1
            if "results" in data and isinstance(data["results"], list):
                rows = data["results"]
            elif "count" in data and not rows:
                rows = []

        if not isinstance(rows, list):
            return ContractVerificationResult(
                endpoint="tasks/action-list/retailer",
                is_valid=False,
                status_code=status_code,
                field_errors=[f"Expected list of actions, got {type(data).__name__}"],
            )

        checked += 1
        for idx, row in enumerate(rows):
            if not isinstance(row, dict):
                errors.append(f"Action row [{idx}] must be an object")
                continue

            # Core mandatory identifiers
            for req in ("id", "state"):
                checked += 1
                if req not in row:
                    missing.append(f"action[{idx}].{req}")

            # Positions validation
            for pos_key in ("current_position", "expected_position"):
                checked += 1
                pos = row.get(pos_key)
                if pos is not None and not isinstance(pos, dict):
                    errors.append(f"action[{idx}].{pos_key} must be an object or null")
                elif isinstance(pos, dict):
                    checked += 3
                    # Section info
                    if "section_info" in pos and pos["section_info"] is not None:
                        if not isinstance(pos["section_info"], dict):
                            errors.append(f"action[{idx}].{pos_key}.section_info must be an object")
                        elif "name" not in pos["section_info"] and "id" not in pos["section_info"]:
                            missing.append(f"action[{idx}].{pos_key}.section_info.name or id")

        return ContractVerificationResult(
            endpoint="tasks/action-list/retailer",
            is_valid=(len(errors) == 0 and len(missing) == 0),
            status_code=status_code,
            field_errors=errors,
            missing_fields=missing,
            checked_fields_count=checked,
        )

    @staticmethod
    def verify_ai_processing_contract(data: Any, status_code: int = 200) -> ContractVerificationResult:
        """Verifies GET /api/v4/processing/actions/{id}/ contract."""
        errors: List[str] = []
        missing: List[str] = []
        checked = 0

        if not isinstance(data, dict):
            return ContractVerificationResult(
                endpoint="processing/actions",
                is_valid=False,
                status_code=status_code,
                field_errors=[f"Expected JSON object, got {type(data).__name__}"],
            )

        checked += 1
        if "status" not in data:
            missing.append("status")
        else:
            valid_statuses = (
                "pending", "queued", "processing", "analyzing",
                "done", "completed", "succeeded", "finished", "failed"
            )
            if str(data["status"]).lower() not in valid_statuses:
                errors.append(f"Invalid AI processing status: '{data['status']}'")

        return ContractVerificationResult(
            endpoint="processing/actions",
            is_valid=(len(errors) == 0 and len(missing) == 0),
            status_code=status_code,
            field_errors=errors,
            missing_fields=missing,
            checked_fields_count=checked,
        )
