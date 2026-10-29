"""
Planogram Snapshot Exporter & Compatibility Comparator.
Extracts, canonicalizes, and hashes immutable planogram snapshots.
Provides Mode C compatibility comparison between planogram versions (v1 vs v2).
"""

from __future__ import annotations

import hashlib
import json
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def canonical_json_dump(data: Any) -> str:
    """Produces deterministic, whitespace-normalized JSON string with sorted keys."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_planogram_hash(snapshot_dict: Dict[str, Any]) -> str:
    """Computes SHA-256 hash of the canonical planogram representation."""
    canonical_str = canonical_json_dump(snapshot_dict)
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest().lower()


@dataclass
class PlanogramDiffResult:
    is_identical: bool
    planogram_v1_id: Any
    planogram_v2_id: Any
    added_upcs: List[str] = field(default_factory=list)
    removed_upcs: List[str] = field(default_factory=list)
    moved_upcs: List[Dict[str, Any]] = field(default_factory=list)
    facing_changes: List[Dict[str, Any]] = field(default_factory=list)
    summary: str = ""


class PlanogramSnapshotExporter:
    """
    Exports planogram items via DRF endpoints into immutable snapshot JSON,
    and compares two planogram versions to audit merchandising resets.
    """

    def __init__(self, base_url: str = "https://krcs.rebotics.net", token: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.token = token

    def build_canonical_snapshot(
        self,
        planogram_id: int | str,
        category_name: str,
        category_id: Optional[int] = None,
        items: Optional[List[Dict[str, Any]]] = None,
        sections_data: Optional[List[Dict[str, Any]]] = None,
        validity_start: Optional[str] = None,
        validity_end: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Builds a structured, sorted, canonical planogram dictionary.
        Normalizes items into sections, shelves, and positions.
        """
        raw_items = items or []
        sections_map: Dict[str, Dict[str, Any]] = {}

        for item in raw_items:
            sec_name = str(item.get("section") or item.get("section_name") or "Bay 01").strip()
            if sec_name not in sections_map:
                sections_map[sec_name] = {
                    "section_name": sec_name,
                    "shelves": {},
                }

            shelf_num = item.get("shelf")
            if shelf_num is None:
                shelf_num = 1
            shelf_key = int(shelf_num)

            shelves = sections_map[sec_name]["shelves"]
            if shelf_key not in shelves:
                shelves[shelf_key] = {
                    "shelf_number": shelf_key,
                    "items": [],
                }

            # Normalize product metadata
            prod = item.get("product") or {}
            upc = (
                item.get("upc")
                or item.get("primary_product_code")
                or prod.get("custom_id")
                or prod.get("primary_product_code")
                or ""
            )
            title = item.get("product_name") or prod.get("name") or ""
            pos = item.get("position")

            shelves[shelf_key]["items"].append({
                "position": int(pos) if pos is not None else 1,
                "upc": str(upc).strip(),
                "product_name": str(title).strip(),
                "horizontal_facing": int(item.get("horizontal_facing") or 1),
                "vertical_facing": int(item.get("vertical_facing") or 1),
                "depth_facing": int(item.get("depth_facing") or 1),
            })

        # Sort sections, shelves, and item positions deterministically
        canonical_sections = []
        for sec_name in sorted(sections_map.keys()):
            shelves_dict = sections_map[sec_name]["shelves"]
            canonical_shelves = []
            for shelf_key in sorted(shelves_dict.keys()):
                shelf_info = shelves_dict[shelf_key]
                sorted_items = sorted(
                    shelf_info["items"],
                    key=lambda x: (x["position"], x["upc"]),
                )
                canonical_shelves.append({
                    "shelf_number": shelf_key,
                    "items": sorted_items,
                })
            canonical_sections.append({
                "section_name": sec_name,
                "shelves": canonical_shelves,
            })

        snapshot = {
            "schema_version": "1.0",
            "planogram_id": planogram_id,
            "category_name": category_name,
            "category_id": category_id,
            "validity_range": {
                "start": validity_start,
                "end": validity_end,
            },
            "sections": canonical_sections,
        }
        snapshot["sha256"] = compute_planogram_hash(snapshot)
        return snapshot

    def fetch_and_export_snapshot(
        self,
        planogram_id: int | str,
        category_name: str = "general",
        dest_file: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Queries live read-only endpoint GET /api/v1/planograms/{planogram_id}/items/
        and writes immutable snapshot JSON.
        """
        url = f"{self.base_url}/api/v1/planograms/{planogram_id}/items/?limit=1000"
        headers = {
            "Accept": "application/json",
            "User-Agent": "ShelfIntelligenceE2E/SnapshotExporter",
        }
        if self.token:
            headers["Authorization"] = f"Token {self.token}"

        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                items = data.get("results", data if isinstance(data, list) else [])
        except Exception as e:
            raise IOError(f"Failed to fetch planogram items from {url}: {e}") from e

        snapshot = self.build_canonical_snapshot(
            planogram_id=planogram_id,
            category_name=category_name,
            items=items,
        )

        if dest_file:
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            dest_file.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

        return snapshot

    @staticmethod
    def compare_planogram_snapshots(
        v1_snapshot: Dict[str, Any],
        v2_snapshot: Dict[str, Any],
    ) -> PlanogramDiffResult:
        """
        Mode C Planogram Evolution Comparator.
        Compares two immutable planograms and computes differences in products, positions, and facings.
        """
        pog1_id = v1_snapshot.get("planogram_id")
        pog2_id = v2_snapshot.get("planogram_id")

        hash1 = v1_snapshot.get("sha256") or compute_planogram_hash(v1_snapshot)
        hash2 = v2_snapshot.get("sha256") or compute_planogram_hash(v2_snapshot)

        if hash1 == hash2:
            return PlanogramDiffResult(
                is_identical=True,
                planogram_v1_id=pog1_id,
                planogram_v2_id=pog2_id,
                summary=f"Planograms {pog1_id} and {pog2_id} are structurally identical.",
            )

        # Build position and facing lookup tables: upc -> (section, shelf, position, facing)
        def index_pog(pog: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
            idx: Dict[str, Dict[str, Any]] = {}
            for sec in pog.get("sections", []):
                s_name = sec.get("section_name", "Bay 01")
                for shelf in sec.get("shelves", []):
                    sh_num = shelf.get("shelf_number", 1)
                    for itm in shelf.get("items", []):
                        upc = itm.get("upc")
                        if upc:
                            idx[upc] = {
                                "section": s_name,
                                "shelf": sh_num,
                                "position": itm.get("position"),
                                "facing": itm.get("horizontal_facing", 1),
                                "product_name": itm.get("product_name", ""),
                            }
            return idx

        idx1 = index_pog(v1_snapshot)
        idx2 = index_pog(v2_snapshot)

        upcs1 = set(idx1.keys())
        upcs2 = set(idx2.keys())

        added = sorted(list(upcs2 - upcs1))
        removed = sorted(list(upcs1 - upcs2))
        moved = []
        facing_diffs = []

        common = upcs1 & upcs2
        for upc in sorted(common):
            p1 = idx1[upc]
            p2 = idx2[upc]

            # Position check
            if (p1["section"], p1["shelf"], p1["position"]) != (p2["section"], p2["shelf"], p2["position"]):
                moved.append({
                    "upc": upc,
                    "product_name": p1.get("product_name"),
                    "from_location": f"{p1['section']} Shelf {p1['shelf']} Pos {p1['position']}",
                    "to_location": f"{p2['section']} Shelf {p2['shelf']} Pos {p2['position']}",
                })

            # Facing check
            if p1["facing"] != p2["facing"]:
                facing_diffs.append({
                    "upc": upc,
                    "product_name": p1.get("product_name"),
                    "from_facing": p1["facing"],
                    "to_facing": p2["facing"],
                })

        summary_parts = []
        if added:
            summary_parts.append(f"{len(added)} products added")
        if removed:
            summary_parts.append(f"{len(removed)} products removed")
        if moved:
            summary_parts.append(f"{len(moved)} products relocated")
        if facing_diffs:
            summary_parts.append(f"{len(facing_diffs)} facing modifications")

        return PlanogramDiffResult(
            is_identical=False,
            planogram_v1_id=pog1_id,
            planogram_v2_id=pog2_id,
            added_upcs=added,
            removed_upcs=removed,
            moved_upcs=moved,
            facing_changes=facing_diffs,
            summary="; ".join(summary_parts) or "Structural coordinate differences detected.",
        )
