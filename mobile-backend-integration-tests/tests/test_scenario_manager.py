"""
Unit tests for ScenarioManager: schema validation, cryptographic hashing, and lifecycle states.
"""

import json
import tempfile
import unittest
from pathlib import Path

from core.scenario_manager import (
    ScenarioManager,
    VerificationStatus,
    compute_sha256_of_data,
    compute_sha256_of_file,
)


class ScenarioManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.catalog_dir = Path(self.temp_dir.name)
        self.manager = ScenarioManager(catalog_dir=self.catalog_dir)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_sha256_computation_of_data(self):
        data = "ShelfIntelligenceTest"
        h = compute_sha256_of_data(data)
        self.assertEqual(len(h), 64)
        self.assertEqual(h, compute_sha256_of_data(data))

    def test_validate_manifest_dict_valid(self):
        manifest = {
            "scenario_id": "SCEN_TEST_001",
            "provenance": {
                "source_environment": "test",
                "source_scan_id": 100,
                "captured_at": "2026-10-24T10:00:00Z",
                "ingested_at": "2026-10-24T10:00:00Z",
            },
            "image": {
                "relative_path": "images/test.jpg",
                "sha256": "a" * 64,
                "content_type": "image/jpeg",
            },
            "planogram_snapshot": {
                "relative_path": "fixtures/pog.json",
                "planogram_id": 1,
                "sha256": "b" * 64,
            },
            "detections_payload": {
                "relative_path": "fixtures/det.json",
            },
            "expected_actions": [],
            "verification": {
                "status": "UNVERIFIED_ANOMALY",
            },
            "replay_eligibility": {
                "mode_1_deterministic_rules": True,
            },
        }
        is_valid, errors = self.manager.validate_manifest_dict(manifest)
        self.assertTrue(is_valid, f"Validation failed with: {errors}")
        self.assertEqual(len(errors), 0)

    def test_validate_manifest_dict_missing_property(self):
        manifest = {
            "scenario_id": "SCEN_INVALID",
            # missing required provenance, image, etc.
        }
        is_valid, errors = self.manager.validate_manifest_dict(manifest)
        self.assertFalse(is_valid)
        self.assertTrue(any("Missing required" in e for e in errors))

    def test_validate_scenario_bundle_with_hashes(self):
        scenario_dir = self.catalog_dir / "frozen_pizza" / "SCEN_TEST_002"
        img_dir = scenario_dir / "images"
        fixt_dir = scenario_dir / "fixtures"
        img_dir.mkdir(parents=True)
        fixt_dir.mkdir(parents=True)

        img_file = img_dir / "bay.jpg"
        img_file.write_bytes(b"TEST_IMAGE_BYTES_1234567890")
        img_hash = compute_sha256_of_file(img_file)

        pog_file = fixt_dir / "pog.json"
        pog_file.write_text('{"planogram_id": 101}', encoding="utf-8")
        pog_hash = compute_sha256_of_file(pog_file)

        det_file = fixt_dir / "det.json"
        det_file.write_text('{"detections": []}', encoding="utf-8")
        det_hash = compute_sha256_of_file(det_file)

        manifest = {
            "scenario_id": "SCEN_TEST_002",
            "provenance": {
                "source_environment": "test",
                "source_scan_id": 200,
                "captured_at": "2026-10-24T10:00:00Z",
                "ingested_at": "2026-10-24T10:00:00Z",
            },
            "image": {
                "relative_path": "images/bay.jpg",
                "sha256": img_hash,
                "content_type": "image/jpeg",
            },
            "planogram_snapshot": {
                "relative_path": "fixtures/pog.json",
                "planogram_id": 101,
                "sha256": pog_hash,
            },
            "detections_payload": {
                "relative_path": "fixtures/det.json",
                "sha256": det_hash,
            },
            "expected_actions": [],
            "verification": {
                "status": "UNVERIFIED_ANOMALY",
            },
            "replay_eligibility": {
                "mode_1_deterministic_rules": True,
            },
        }
        (scenario_dir / "scenario_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        res = self.manager.validate_scenario_bundle(scenario_dir)
        self.assertTrue(res.is_valid, f"Validation failed: {res.errors}")
        self.assertTrue(res.image_hash_matches)
        self.assertTrue(res.pog_hash_matches)
        self.assertTrue(res.detections_hash_matches)

    def test_promote_verification_status(self):
        scenario_dir = self.catalog_dir / "frozen_pizza" / "SCEN_TEST_003"
        (scenario_dir / "images").mkdir(parents=True)
        (scenario_dir / "fixtures").mkdir(parents=True)

        img_file = scenario_dir / "images" / "bay.jpg"
        img_file.write_bytes(b"BYTES")
        pog_file = scenario_dir / "fixtures" / "pog.json"
        pog_file.write_text("{}", encoding="utf-8")

        manifest = {
            "scenario_id": "SCEN_TEST_003",
            "provenance": {
                "source_environment": "test",
                "source_scan_id": 300,
                "captured_at": "2026-10-24T10:00:00Z",
                "ingested_at": "2026-10-24T10:00:00Z",
            },
            "image": {
                "relative_path": "images/bay.jpg",
                "sha256": compute_sha256_of_file(img_file),
                "content_type": "image/jpeg",
            },
            "planogram_snapshot": {
                "relative_path": "fixtures/pog.json",
                "planogram_id": 101,
                "sha256": compute_sha256_of_file(pog_file),
            },
            "detections_payload": {
                "relative_path": "fixtures/pog.json",
            },
            "expected_actions": [],
            "verification": {
                "status": "UNVERIFIED_ANOMALY",
            },
            "replay_eligibility": {
                "mode_1_deterministic_rules": True,
            },
        }
        (scenario_dir / "scenario_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        promoted = self.manager.promote_verification_status(
            scenario_dir=scenario_dir,
            new_status=VerificationStatus.VERIFIED_BASELINE,
            reviewer_name="QA_Lead",
            notes="Sign-off complete",
        )
        self.assertEqual(promoted["verification"]["status"], "VERIFIED_BASELINE")
        self.assertEqual(promoted["verification"]["reviewed_by"], "QA_Lead")


if __name__ == "__main__":
    unittest.main()
