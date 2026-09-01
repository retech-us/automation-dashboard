"""Unit tests for Slice 5 domain count parity."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from regression.domain_parity import (
    assert_count_parity,
    run_domain_parity,
    transform_via_interim_mapper,
)

CAT1_FIXTURE = ROOT / "regression" / "tests" / "fixtures" / "domain_cat1_t5_mixed.json"


class Cat1ParityTests(unittest.TestCase):
    def test_mapper_produces_android_cat1_t5_counts(self):
        raw = json.loads(CAT1_FIXTURE.read_text(encoding="utf-8"))
        domain = transform_via_interim_mapper(raw)
        mismatches = assert_count_parity(
            domain,
            expected_domain_total=6,
            expected_by_type={
                "Remove": 1,
                "FixInBay": 1,
                "SetAside": 2,
                "AddItems": 2,
            },
        )
        self.assertEqual(mismatches, [], mismatches)

    def test_run_domain_parity_baseline_case(self):
        result = run_domain_parity(env="epsilon", case="cat1_t5_mixed")
        self.assertTrue(result.ok, result.as_dict())
        self.assertEqual(result.domain_card_count, 6)
        self.assertEqual(result.counts_by_type_android_normalized.get("AddItems"), 2)
        self.assertEqual(result.source, "baseline_case:cat1_t5_mixed")

    def test_fixture_override_asserts(self):
        raw = json.loads(CAT1_FIXTURE.read_text(encoding="utf-8"))
        result = run_domain_parity(
            env="epsilon",
            payload_override=raw,
            case="cat1_t5_mixed",
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.source, "fixture")

    def test_mismatch_detected(self):
        bad = [
            {
                "id": 1,
                "upc": "1",
                "displayed_upc": "1",
                "product_title": "X",
                "product_id": 1,
                "source_id": 1,
                "store_planogram_id": 1,
                "action": "remove",
                "state": "STATE_IDLE",
                "current_position": {
                    "action": "remove",
                    "shelf": 1,
                    "position": "1",
                    "section_info": {"id": 1, "name": "1"},
                },
                "expected_position": None,
            }
        ]
        result = run_domain_parity(
            env="epsilon",
            payload_override=bad,
            case="cat1_t5_mixed",
        )
        self.assertFalse(result.ok)
        self.assertTrue(any("domain_total" in m for m in result.mismatches))


class CliDomainParityTests(unittest.TestCase):
    def test_cli_baseline_case(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "regression" / "cli.py"),
                "domain-parity",
                "--env=epsilon",
                "--case=cat1_t5_mixed",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        data = json.loads(proc.stdout)
        self.assertTrue(data["ok"])
        self.assertEqual(data["domain_card_count"], 6)

    def test_cli_fixture(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "regression" / "cli.py"),
                "domain-parity",
                "--env=epsilon",
                f"--fixture={CAT1_FIXTURE}",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)


if __name__ == "__main__":
    unittest.main()
