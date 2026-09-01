"""Planogram/category-aware scan image catalog lookup."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG_PATH = REPO_ROOT / "docs" / "regression" / "data" / "image-catalog.yaml"


class ImageCatalogError(ValueError):
    pass


@dataclass(frozen=True)
class ImageEntry:
    id: str
    file: str
    categories: tuple[str, ...]
    bay: int
    stage: str
    absolute_path: Path

    def as_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "file": self.file,
            "categories": list(self.categories),
            "bay": self.bay,
            "stage": self.stage,
            "absolute_path": str(self.absolute_path),
            "exists": self.absolute_path.is_file(),
        }


@dataclass(frozen=True)
class ImageResolution:
    category: str
    bay: int
    stage: str
    entry: ImageEntry


class ImageCatalog:
    def __init__(self, entries: Sequence[ImageEntry], *, repo_root: Path = REPO_ROOT):
        self._entries = list(entries)
        self.repo_root = repo_root

    @classmethod
    def load(cls, catalog_path: Optional[Path] = None, *, repo_root: Path = REPO_ROOT) -> "ImageCatalog":
        path = catalog_path or DEFAULT_CATALOG_PATH
        if not path.is_file():
            raise ImageCatalogError(f"Image catalog not found: {path}")
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        images = raw.get("images") or []
        entries: List[ImageEntry] = []
        for item in images:
            rel = str(item["file"])
            abs_path = (repo_root / rel).resolve()
            entries.append(
                ImageEntry(
                    id=str(item["id"]),
                    file=rel,
                    categories=tuple(str(c).lower() for c in item.get("categories") or []),
                    bay=int(item["bay"]),
                    stage=str(item["stage"]).lower(),
                    absolute_path=abs_path,
                )
            )
        return cls(entries, repo_root=repo_root)

    def resolve(
        self,
        *,
        category: str,
        bay: int,
        stage: str,
        require_file_exists: bool = True,
    ) -> ImageResolution:
        cat = (category or "").strip().lower()
        st = (stage or "").strip().lower()
        if not cat:
            raise ImageCatalogError("planogram category is required for image selection")
        if not st:
            raise ImageCatalogError("scan stage is required (e.g. pre_photo, post_photo)")

        matches = [
            e
            for e in self._entries
            if e.bay == int(bay) and e.stage == st and cat in e.categories
        ]
        if not matches:
            available = sorted({c for e in self._entries for c in e.categories})
            raise ImageCatalogError(
                f"No catalog image for category={category!r} bay={bay} stage={stage!r}. "
                f"Do not fall back to an unrelated bay scan. Known categories: {available}"
            )
        # Prefer exact id stability: first match in catalog order
        entry = matches[0]
        if require_file_exists and not entry.absolute_path.is_file():
            raise ImageCatalogError(
                f"Catalog entry {entry.id!r} points to missing file: {entry.absolute_path}"
            )
        return ImageResolution(category=cat, bay=int(bay), stage=st, entry=entry)

    def resolve_bays(
        self,
        *,
        category: str,
        bays: Sequence[int],
        stage: str,
        require_file_exists: bool = True,
    ) -> List[ImageResolution]:
        return [
            self.resolve(
                category=category,
                bay=bay,
                stage=stage,
                require_file_exists=require_file_exists,
            )
            for bay in bays
        ]
