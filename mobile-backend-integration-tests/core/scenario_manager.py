"""
Scenario Manager & Manifest Validator for Shelf Intelligence E2E Framework.
Manages versioned test scenarios, cryptographic SHA-256 verification,
provenance tracking, and review lifecycle states.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parent
DEFAULT_SCHEMA_PATH = REPO_ROOT / "scenarios" / "schema" / "scenario_schema.json"
DEFAULT_CATALOG_DIR = REPO_ROOT / "scenarios" / "catalog"


class VerificationStatus(str, Enum):
    VERIFIED_BASELINE = "VERIFIED_BASELINE"
    VERIFIED_DEFECT = "VERIFIED_DEFECT"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    UNVERIFIED_ANOMALY = "UNVERIFIED_ANOMALY"
    INVALID_INCOMPLETE = "INVALID_INCOMPLETE"


@dataclass
class ScenarioValidationResult:
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    image_hash_matches: bool = False
    pog_hash_matches: bool = False
    detections_hash_matches: bool = False


def compute_sha256_of_file(file_path: Path) -> str:
    """Computes SHA-256 hexadecimal digest of a binary file."""
    if not file_path.exists() or not file_path.is_file():
        raise FileNotFoundError(f"File not found for hash calculation: {file_path}")
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().lower()


def compute_sha256_of_data(data: str | bytes) -> str:
    """Computes SHA-256 digest of string or bytes."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest().lower()


class ScenarioManager:
    """
    Manages loading, validating, hash-checking, and lifecycle promotion
    of Shelf Intelligence scenario bundles.
    """

    def __init__(
        self,
        catalog_dir: Optional[Path] = None,
        schema_path: Optional[Path] = None,
    ):
        self.catalog_dir = catalog_dir or DEFAULT_CATALOG_DIR
        self.schema_path = schema_path or DEFAULT_SCHEMA_PATH
        self._schema_cache: Optional[Dict[str, Any]] = None

    def get_schema(self) -> Dict[str, Any]:
        if self._schema_cache is None:
            if self.schema_path.exists():
                self._schema_cache = json.loads(self.schema_path.read_text(encoding="utf-8"))
            else:
                self._schema_cache = {}
        return self._schema_cache

    def validate_manifest_dict(self, manifest: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validates manifest dictionary structure and required keys."""
        errors: List[str] = []

        required_top_level = [
            "scenario_id",
            "provenance",
            "image",
            "planogram_snapshot",
            "detections_payload",
            "expected_actions",
            "verification",
            "replay_eligibility",
        ]
        for key in required_top_level:
            if key not in manifest:
                errors.append(f"Missing required top-level property: '{key}'")

        if "scenario_id" in manifest:
            sid = str(manifest["scenario_id"])
            if not re.match(r"^SCEN_[A-Za-z0-9_-]+$", sid):
                errors.append(
                    f"Invalid scenario_id format: '{sid}'. Must match pattern '^SCEN_[A-Za-z0-9_-]+$'"
                )

        if "verification" in manifest:
            status = manifest["verification"].get("status")
            valid_statuses = [s.value for s in VerificationStatus]
            if status not in valid_statuses:
                errors.append(
                    f"Invalid verification status: '{status}'. Must be one of {valid_statuses}"
                )

        # Attempt jsonschema validation if installed
        try:
            import jsonschema
            schema = self.get_schema()
            if schema:
                validator = jsonschema.Draft7Validator(schema)
                for err in validator.iter_errors(manifest):
                    errors.append(f"Schema error at '{err.json_path}': {err.message}")
        except ImportError:
            pass  # Fall back to native required keys validation

        return len(errors) == 0, errors

    def validate_scenario_bundle(self, scenario_dir: Path) -> ScenarioValidationResult:
        """
        Performs full verification of a scenario directory:
        1. Validates scenario_manifest.json structure
        2. Verifies presence and SHA-256 hashes of image, planogram snapshot, and detections
        """
        res = ScenarioValidationResult(is_valid=True)
        manifest_file = scenario_dir / "scenario_manifest.json"
        if not manifest_file.exists():
            res.is_valid = False
            res.errors.append(f"Manifest not found: {manifest_file}")
            return res

        try:
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        except Exception as e:
            res.is_valid = False
            res.errors.append(f"Failed to parse scenario_manifest.json: {e}")
            return res

        is_dict_valid, schema_errors = self.validate_manifest_dict(manifest)
        if not is_dict_valid:
            res.is_valid = False
            res.errors.extend(schema_errors)

        # Check Image Integrity
        img_info = manifest.get("image", {})
        img_rel = img_info.get("relative_path")
        expected_img_hash = img_info.get("sha256", "").lower()
        if img_rel:
            img_path = scenario_dir / img_rel
            if not img_path.exists():
                res.is_valid = False
                res.errors.append(f"Referenced image file does not exist: {img_path}")
            elif expected_img_hash:
                actual_img_hash = compute_sha256_of_file(img_path)
                if actual_img_hash == expected_img_hash:
                    res.image_hash_matches = True
                else:
                    res.is_valid = False
                    res.errors.append(
                        f"Image SHA-256 mismatch! Expected {expected_img_hash}, got {actual_img_hash}"
                    )

        # Check Planogram Snapshot Integrity
        pog_info = manifest.get("planogram_snapshot", {})
        pog_rel = pog_info.get("relative_path")
        expected_pog_hash = pog_info.get("sha256", "").lower()
        if pog_rel:
            pog_path = scenario_dir / pog_rel
            if not pog_path.exists():
                res.is_valid = False
                res.errors.append(f"Referenced planogram snapshot does not exist: {pog_path}")
            elif expected_pog_hash:
                actual_pog_hash = compute_sha256_of_file(pog_path)
                if actual_pog_hash == expected_pog_hash:
                    res.pog_hash_matches = True
                else:
                    res.is_valid = False
                    res.errors.append(
                        f"Planogram snapshot SHA-256 mismatch! Expected {expected_pog_hash}, got {actual_pog_hash}"
                    )

        # Check Detections Payload
        det_info = manifest.get("detections_payload", {})
        det_rel = det_info.get("relative_path")
        expected_det_hash = det_info.get("sha256", "").lower()
        if det_rel:
            det_path = scenario_dir / det_rel
            if not det_path.exists():
                res.is_valid = False
                res.errors.append(f"Referenced detections payload does not exist: {det_path}")
            elif expected_det_hash:
                actual_det_hash = compute_sha256_of_file(det_path)
                if actual_det_hash == expected_det_hash:
                    res.detections_hash_matches = True
                else:
                    res.is_valid = False
                    res.errors.append(
                        f"Detections payload SHA-256 mismatch! Expected {expected_det_hash}, got {actual_det_hash}"
                    )
            else:
                res.detections_hash_matches = True

        return res

    def promote_verification_status(
        self,
        scenario_dir: Path,
        new_status: VerificationStatus,
        reviewer_name: str,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Promotes scenario to VERIFIED_BASELINE or VERIFIED_DEFECT.
        Requires explicit reviewer identity and enforces valid bundle checks.
        """
        if not reviewer_name or not reviewer_name.strip():
            raise ValueError("A valid reviewer name is mandatory to promote verification status.")

        validation = self.validate_scenario_bundle(scenario_dir)
        if not validation.is_valid and new_status in (
            VerificationStatus.VERIFIED_BASELINE,
            VerificationStatus.VERIFIED_DEFECT,
        ):
            raise ValueError(
                f"Cannot promote invalid scenario bundle. Errors: {'; '.join(validation.errors)}"
            )

        manifest_file = scenario_dir / "scenario_manifest.json"
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))

        manifest["verification"] = {
            "status": new_status.value,
            "reviewed_by": reviewer_name.strip(),
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "notes": notes or manifest.get("verification", {}).get("notes", ""),
        }

        manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return manifest

    def discover_scenarios(
        self,
        category: Optional[str] = None,
        status: Optional[VerificationStatus] = None,
        mode: Optional[str] = None,
    ) -> List[Tuple[Path, Dict[str, Any]]]:
        """Discovers all scenario bundles matching filter criteria."""
        results: List[Tuple[Path, Dict[str, Any]]] = []
        if not self.catalog_dir.exists():
            return results

        for manifest_path in self.catalog_dir.glob("**/scenario_manifest.json"):
            scenario_dir = manifest_path.parent
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception:
                continue

            if category:
                cat_slug = manifest.get("provenance", {}).get("category_slug", "").lower()
                if category.lower() not in cat_slug:
                    continue

            if status:
                st = manifest.get("verification", {}).get("status")
                if st != status.value:
                    continue

            if mode:
                eligibility = manifest.get("replay_eligibility", {})
                if not eligibility.get(mode, False):
                    continue

            results.append((scenario_dir, manifest))

        return sorted(results, key=lambda x: str(x[0]))
