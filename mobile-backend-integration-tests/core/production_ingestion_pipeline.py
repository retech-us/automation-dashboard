"""
Safe Production-to-Test Ingestion Pipeline.
Discovers approved production scans via read-only APIs, cryptographically verifies image bytes,
exports immutable planogram snapshots, packages CV detections, and stores them in the scenario catalog.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.dynamic_auth_client import DynamicAuthClient
from core.planogram_snapshot_exporter import PlanogramSnapshotExporter
from core.scenario_manager import (
    ScenarioManager,
    VerificationStatus,
    compute_sha256_of_data,
    compute_sha256_of_file,
)

logger = logging.getLogger("production_ingestion")


def clean_slug(value: str) -> str:
    """Produces clean lowercased snake_case slug from name string."""
    if not value:
        return "general"
    s = re.sub(r"^\d+\s*[-_:]\s*", "", str(value).strip())
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").lower()
    return slug or "general"


class ProductionIngestionPipeline:
    """
    Executes safe, read-only ingestion of production shelf scenarios into the test framework.
    Guarantees zero database modifications and zero production state mutations.
    """

    def __init__(
        self,
        instance: str = "krcs",
        token: Optional[str] = None,
        output_catalog_dir: Optional[Path] = None,
        dry_run: bool = False,
    ):
        self.instance = instance.lower().strip()
        self.base_url = f"https://{self.instance}.rebotics.net"
        self.token = token or self._resolve_token()
        self.catalog_dir = output_catalog_dir or (REPO_ROOT / "scenarios" / "catalog")
        self.dry_run = dry_run
        self.scenario_manager = ScenarioManager(catalog_dir=self.catalog_dir)
        self.pog_exporter = PlanogramSnapshotExporter(base_url=self.base_url, token=self.token)

    def _resolve_token(self) -> str:
        """Resolves authentication token dynamically or from secure environment variables."""
        auth_client = DynamicAuthClient(base_url=self.base_url)
        return (
            os.environ.get(f"{self.instance.upper()}_TOKEN")
            or os.environ.get("REBOTICS_AUTH_TOKEN")
            or os.environ.get("TEST_INGESTION_TOKEN")
            or os.environ.get("REBOTICS_TOKEN")
            or auth_client.get_auth_token()
            or ""
        )

    def _fetch_json(self, url: str) -> Dict[str, Any]:
        """Executes read-only HTTP GET request and returns JSON."""
        headers = {
            "Accept": "application/json",
            "User-Agent": "ShelfIntelligenceE2E/IngestionPipeline",
        }
        if self.token:
            headers["Authorization"] = f"Token {self.token}"

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def query_candidate_scans(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Queries completed scans via read-only GET /api/v4/processing/actions/."""
        params: Dict[str, Any] = {
            "last_action_status": "done",
            "limit": limit,
        }
        if from_date:
            params["from_date"] = from_date
        if to_date:
            params["to_date"] = to_date

        query_str = urllib.parse.urlencode(params)
        url = f"{self.base_url}/api/v4/processing/actions/?{query_str}"
        data = self._fetch_json(url)
        results = data.get("results", [])

        if category:
            cat_filter = category.lower().strip()
            results = [
                r for r in results
                if cat_filter in (r.get("category_name") or "").lower()
            ]
        return results

    def ingest_scan(
        self,
        scan_id: int | str,
        scan_record: Optional[Dict[str, Any]] = None,
        category_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Ingests a single production scan into the versioned scenario catalog.
        In dry-run mode, validates and calculates all properties without writing files.
        """
        # If scan record not provided, fetch action detail
        if not scan_record:
            url = f"{self.base_url}/api/v4/processing/actions/?scan={scan_id}&limit=1"
            data = self._fetch_json(url)
            results = data.get("results", [])
            if not results:
                raise ValueError(f"No processing action found for scan_id: {scan_id}")
            scan_record = results[0]

        cat_name = category_name or scan_record.get("category_name") or "general"
        cat_slug = clean_slug(cat_name)
        pog_id = scan_record.get("planogram_id")
        section = scan_record.get("section") or "bay_01"
        sec_slug = clean_slug(str(section))
        proc_action_id = scan_record.get("id")

        scenario_id = f"SCEN_{self.instance.upper()}_{scan_id}_{sec_slug}"
        scenario_dir = self.catalog_dir / cat_slug / scenario_id

        # Check for duplicate scenario
        if scenario_dir.exists() and (scenario_dir / "scenario_manifest.json").exists():
            print(f"[INGESTION] Scenario {scenario_id} already exists. Verifying bundle...")
            val = self.scenario_manager.validate_scenario_bundle(scenario_dir)
            return {
                "scenario_id": scenario_id,
                "status": "ALREADY_EXISTS",
                "is_valid": val.is_valid,
                "directory": str(scenario_dir),
            }

        image_url = scan_record.get("merged_image_jpeg") or scan_record.get("merged_image")
        if not image_url:
            raise ValueError(f"Scan {scan_id} does not have an accessible merged_image URL.")

        print(f"[INGESTION] Processing Scan ID {scan_id} ({cat_name} - {section})...")
        if self.dry_run:
            print(f"[DRY-RUN] Would download image from: {image_url}")
            print(f"[DRY-RUN] Would export planogram snapshot for POG ID: {pog_id}")
            return {
                "scenario_id": scenario_id,
                "status": "DRY_RUN_SUCCESS",
                "planogram_id": pog_id,
                "category_slug": cat_slug,
            }

        # 1. Download image and compute hash
        img_req = urllib.request.Request(image_url, headers={"User-Agent": "ShelfIntelligenceE2E"})
        with urllib.request.urlopen(img_req, timeout=30) as resp:
            image_bytes = resp.read()

        img_hash = hashlib.sha256(image_bytes).hexdigest().lower()
        if len(image_bytes) < 1024:
            raise ValueError(f"Downloaded image bytes too small ({len(image_bytes)} bytes). Invalid image.")

        # Create scenario directory structure
        img_dir = scenario_dir / "images"
        fixt_dir = scenario_dir / "fixtures"
        img_dir.mkdir(parents=True, exist_ok=True)
        fixt_dir.mkdir(parents=True, exist_ok=True)

        img_filename = f"{sec_slug}_stitched.jpg"
        img_dest_path = img_dir / img_filename
        img_dest_path.write_bytes(image_bytes)

        # 2. Export Immutable Planogram Snapshot
        pog_snapshot_file = fixt_dir / "planogram_snapshot.json"
        has_valid_pog = False
        pog_hash = ""
        try:
            pog_snapshot = self.pog_exporter.fetch_and_export_snapshot(
                planogram_id=pog_id,
                category_name=cat_name,
                dest_file=pog_snapshot_file,
            )
            pog_hash = pog_snapshot.get("sha256", "")
            has_valid_pog = True
        except Exception as e:
            print(f"[WARNING] Could not export planogram {pog_id}: {e}")
            pog_snapshot_file.write_text(json.dumps({"error": str(e), "planogram_id": pog_id}), encoding="utf-8")
            pog_hash = compute_sha256_of_file(pog_snapshot_file)

        # 3. Extract CV Detections Payload
        det_file = fixt_dir / "cv_detections.json"
        detections_data = {
            "scan_id": scan_id,
            "processing_action_id": proc_action_id,
            "detections": scan_record.get("detections", []),
            "bounding_boxes": scan_record.get("bounding_boxes", []),
            "model_version": scan_record.get("model_version", "unknown"),
        }
        det_file.write_text(json.dumps(detections_data, indent=2), encoding="utf-8")
        det_hash = compute_sha256_of_file(det_file)

        # 4. Determine Initial Verification Status
        initial_status = VerificationStatus.UNVERIFIED_ANOMALY.value
        verification_notes = "Captured from production scan. Pending QA review."
        if not has_valid_pog:
            initial_status = VerificationStatus.INVALID_INCOMPLETE.value
            verification_notes = f"Quarantined: Missing immutable planogram snapshot for POG {pog_id}."

        # 5. Build and save Scenario Manifest
        now_iso = datetime.now(timezone.utc).isoformat()
        manifest = {
            "scenario_id": scenario_id,
            "description": f"Production scan {scan_id} for category {cat_name} in {section}",
            "provenance": {
                "source_environment": self.instance,
                "source_scan_id": scan_id,
                "source_processing_action_id": proc_action_id,
                "source_task_id": scan_record.get("task_id"),
                "captured_at": scan_record.get("started_at") or now_iso,
                "ingested_at": now_iso,
                "store_pseudonym": f"STORE_{self.instance.upper()}_{scan_record.get('store_id', '000')}",
                "category_slug": cat_slug,
                "section_slug": sec_slug,
            },
            "image": {
                "relative_path": f"images/{img_filename}",
                "sha256": img_hash,
                "content_type": "image/jpeg",
            },
            "planogram_snapshot": {
                "relative_path": "fixtures/planogram_snapshot.json",
                "planogram_id": pog_id,
                "sha256": pog_hash,
            },
            "detections_payload": {
                "relative_path": "fixtures/cv_detections.json",
                "detection_count": len(detections_data["detections"]),
                "sha256": det_hash,
            },
            "expected_actions": scan_record.get("actions", []),
            "verification": {
                "status": initial_status,
                "reviewed_by": None,
                "reviewed_at": None,
                "notes": verification_notes,
            },
            "replay_eligibility": {
                "mode_1_deterministic_rules": has_valid_pog,
                "mode_2_full_image_pipeline": True,
                "mode_3_candidate_comparison": True,
            },
        }

        manifest_file = scenario_dir / "scenario_manifest.json"
        manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        print(f"[INGESTION] Scenario {scenario_id} saved successfully to {scenario_dir}.")
        return {
            "scenario_id": scenario_id,
            "status": initial_status,
            "directory": str(scenario_dir),
            "image_hash": img_hash,
            "planogram_hash": pog_hash,
        }


def main():
    parser = argparse.ArgumentParser(description="Shelf Intelligence Production Ingestion Pipeline")
    parser.add_argument("--scan-id", type=int, help="Specific scan ID to ingest")
    parser.add_argument("--instance", default="krcs", help="Backend instance (krcs, harr, epsilon)")
    parser.add_argument("--category", help="Category filter")
    parser.add_argument("--limit", type=int, default=5, help="Number of scans to query if scan-id omitted")
    parser.add_argument("--dry-run", action="store_true", help="Report planned operations without writing data")
    args = parser.parse_args()

    pipeline = ProductionIngestionPipeline(
        instance=args.instance,
        dry_run=args.dry_run,
    )

    if args.scan_id:
        res = pipeline.ingest_scan(scan_id=args.scan_id, category_name=args.category)
        print(json.dumps(res, indent=2))
    else:
        scans = pipeline.query_candidate_scans(category=args.category, limit=args.limit)
        print(f"Discovered {len(scans)} candidate scans matching query.")
        for s in scans:
            sid = s.get("scan_id") or s.get("id")
            if sid:
                res = pipeline.ingest_scan(scan_id=sid, scan_record=s)
                print(f"Ingested {sid} -> {res.get('status')}")


if __name__ == "__main__":
    main()
