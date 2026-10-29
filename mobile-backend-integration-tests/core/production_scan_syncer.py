"""
Production Scan Syncer & Image Ingestion Tool.
Fetches real shelf scan records and high-resolution images from live production instances
(e.g., krcs.rebotics.net, harr.rebotics.net) and organizes them into category-aware test directories.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure repository root is on path
CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.dynamic_auth_client import DynamicAuthClient
from core.shelf_image_catalog import image_catalog


def clean_category_slug(category_name: str) -> str:
    """Normalizes category name like '038-FROZEN PIZZA' -> 'frozen_pizza'."""
    if not category_name:
        return "general"
    # Remove leading numbers and hyphens (e.g. '038-')
    cleaned = re.sub(r"^\d+\s*[-_:]\s*", "", category_name.strip())
    # Replace non-alphanumeric with underscore
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", cleaned).strip("_").lower()
    return slug or "general"


def clean_section_slug(section: Any) -> str:
    """Normalizes section/bay string into a safe file identifier."""
    if section is None:
        return "bay_01"
    s = str(section).strip().replace(" ", "_")
    s = re.sub(r"[^a-zA-Z0-9_-]+", "", s)
    if not s.lower().startswith("bay") and s.isdigit():
        return f"bay_{int(s):02d}"
    return s.lower() or "bay_01"


class ProductionScanSyncer:
    """Syncs real shelf images and metadata from administration/scans DRF endpoints."""

    def __init__(self, instance: str = "krcs", token: Optional[str] = None):
        self.instance = instance.lower().strip()
        self.base_url = f"https://{self.instance}.rebotics.net"
        self.token = token or self._resolve_token()
        self.images_root = REPO_ROOT / "test-data" / "images"

    def _resolve_token(self) -> str:
        """Resolves authentication token from environment or local config."""
        env_token = (
            os.environ.get(f"{self.instance.upper()}_TOKEN")
            or os.environ.get("REBOTICS_AUTH_TOKEN")
            or os.environ.get("REBOTICS_TOKEN")
            or os.environ.get("TEST_INGESTION_TOKEN")
        )
        if env_token:
            return env_token

        # Check local non-committed config/session-tokens.json
        tokens_file = REPO_ROOT / "config" / "session-tokens.json"
        if not tokens_file.exists():
            tokens_file = REPO_ROOT.parent / "data" / "session-tokens.json"

        if tokens_file.exists():
            try:
                data = json.loads(tokens_file.read_text(encoding="utf-8"))
                tokens = data.get("tokens", {})
                for host, tok in tokens.items():
                    if self.instance in host:
                        return tok
            except Exception:
                pass

        auth_client = DynamicAuthClient(base_url=self.base_url)
        return auth_client.get_auth_token()

    def query_scans(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        last_action_status: str = "done",
        section: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Queries live processing actions (scans) from the backend matching administration filters.
        """
        today_str = date.today().isoformat()
        f_date = from_date or today_str
        t_date = to_date or f_date

        params: Dict[str, Any] = {
            "from_date": f_date,
            "to_date": t_date,
            "last_action_status": last_action_status,
            "limit": limit,
        }
        if section:
            params["section"] = section

        query_str = urllib.parse.urlencode(params)
        url = f"{self.base_url}/api/v4/processing/actions/?{query_str}"

        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Automation-Dashboard/2.0; ShelfSync)",
        }
        if self.token:
            headers["Authorization"] = f"Token {self.token}"

        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                results = data.get("results", [])
                if category:
                    cat_clean = category.lower().strip()
                    results = [
                        r for r in results
                        if cat_clean in (r.get("category_name") or "").lower() or str(r.get("category_id")) == cat_clean
                    ]
                return results
        except Exception as e:
            raise IOError(f"Failed to query scans from {url}: {e}") from e

    def download_and_import_scans(
        self,
        scans: List[Dict[str, Any]],
        max_images: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Downloads high-resolution images and saves them into category directories.
        """
        downloaded = []
        for s in scans[:max_images]:
            scan_id = s.get("id")
            cat_name = s.get("category_name") or "general"
            cat_slug = clean_category_slug(cat_name)
            pog_id = s.get("planogram_id") or "nopog"
            sec_slug = clean_section_slug(s.get("section"))

            img_url = s.get("merged_image_jpeg") or s.get("merged_image")
            if not img_url:
                continue

            target_dir = self.images_root / cat_slug
            target_dir.mkdir(parents=True, exist_ok=True)
            filename = f"pog_{pog_id}_{sec_slug}.jpg"
            dest_path = target_dir / filename

            # Download binary image
            try:
                img_req = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(img_req, timeout=20) as resp:
                    img_bytes = resp.read()
                    if len(img_bytes) > 1024:
                        dest_path.write_bytes(img_bytes)
                        record = {
                            "scan_id": scan_id,
                            "category": cat_name,
                            "category_slug": cat_slug,
                            "planogram_id": pog_id,
                            "section": s.get("section"),
                            "saved_to": str(dest_path.relative_to(REPO_ROOT)),
                            "size_bytes": len(img_bytes),
                            "store_name": s.get("store_name"),
                            "captured_at": s.get("captured_at") or s.get("created"),
                        }
                        downloaded.append(record)
            except Exception as dl_err:
                print(f"[Warning] Failed to download scan #{scan_id} image: {dl_err}")

        # Update category metadata manifest
        if downloaded:
            manifest_file = self.images_root / "production_sync_manifest.json"
            existing = []
            if manifest_file.exists():
                try:
                    existing = json.loads(manifest_file.read_text(encoding="utf-8"))
                except Exception:
                    existing = []
            existing.extend(downloaded)
            manifest_file.write_text(json.dumps(existing, indent=2), encoding="utf-8")

        return downloaded


def main():
    parser = argparse.ArgumentParser(description="Sync real production scans and images from Kroger/Harris Teeter.")
    parser.add_argument("--instance", default="krcs", help="Target instance (e.g. krcs, harr)")
    parser.add_argument("--from-date", default=date.today().isoformat(), help="Start date (YYYY-MM-DD)")
    parser.add_argument("--to-date", default=date.today().isoformat(), help="End date (YYYY-MM-DD)")
    parser.add_argument("--status", default="done", help="Scan status filter (default: done)")
    parser.add_argument("--section", default=None, help="Optional section / bay filter")
    parser.add_argument("--category", default=None, help="Optional category name or id filter")
    parser.add_argument("--limit", type=int, default=10, help="Number of scans to download (default: 10)")
    parser.add_argument("--list-only", action="store_true", help="Only list available scans without downloading")

    args = parser.parse_args()

    syncer = ProductionScanSyncer(instance=args.instance)
    print(f"[*] Querying scans from {syncer.base_url} (Date: {args.from_date} to {args.to_date}, Status: {args.status})...")

    scans = syncer.query_scans(
        from_date=args.from_date,
        to_date=args.to_date,
        last_action_status=args.status,
        section=args.section,
        category=args.category,
        limit=max(args.limit * 2, 20),
    )
    print(f"[✓] Retrieved {len(scans)} matching scans.")

    if args.list_only:
        for s in scans[:args.limit]:
            print(f"  • Scan #{s.get('id')} | Cat: {s.get('category_name')} | Bay: {s.get('section')} | POG: {s.get('planogram_id')}")
        return

    print(f"[*] Downloading up to {args.limit} high-resolution shelf images...")
    imported = syncer.download_and_import_scans(scans, max_images=args.limit)
    print(f"\n[✓] Successfully imported {len(imported)} production shelf photos into category folders:")
    for item in imported:
        size_mb = item['size_bytes'] / (1024 * 1024)
        print(f"  • [{item['category']}] Bay {item['section']} -> {item['saved_to']} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    main()
