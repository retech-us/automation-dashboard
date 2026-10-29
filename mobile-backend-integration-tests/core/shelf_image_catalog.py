"""
Shelf Image Catalog & Dynamic Image Engine.
Provides category-aware, planogram-aware real shelf photos with realistic
camera variability (EXIF metadata, timestamp, micro-lighting variance)
so that every test scan upload is uniquely distinct and matches real store conditions.
"""

import io
import os
import random
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

try:
    from PIL import Image, ImageEnhance
    import piexif
    HAS_PIEXIF = True
except ImportError:
    HAS_PIEXIF = False
    try:
        from PIL import Image, ImageEnhance
    except ImportError:
        Image = None
        ImageEnhance = None


class ShelfImageCatalog:
    """Manages multi-category real store photos and dynamic camera variation."""

    CATEGORY_MAP = {
        101: "beverages",
        102: "snacks",
        103: "dairy_frozen",
        104: "pasta_grocery",
        105: "cereals",
        9999: "general",
    }

    NAME_MAP = {
        "beverage": 101,
        "drink": 101,
        "energy": 101,
        "snack": 102,
        "confectionery": 102,
        "candy": 102,
        "dairy": 103,
        "frozen": 103,
        "yogurt": 103,
        "pasta": 104,
        "italian": 104,
        "sauce": 104,
        "cereal": 105,
        "breakfast": 105,
        "oats": 105,
    }

    def __init__(self, images_dir: Optional[Path] = None):
        if images_dir:
            self.base_dir = Path(images_dir)
        else:
            self.base_dir = Path(__file__).resolve().parent.parent / "test-data" / "images"
        self._ensure_category_structure()

    def _ensure_category_structure(self):
        """Creates categorized directories and indexes existing real photos."""
        if not self.base_dir.exists():
            self.base_dir.mkdir(parents=True, exist_ok=True)

        categories = ["beverages", "snacks", "dairy_frozen", "pasta_grocery", "cereals", "general"]
        for cat in categories:
            (self.base_dir / cat).mkdir(parents=True, exist_ok=True)

        # Distribute existing root images into appropriate category folders if needed
        mappings = [
            ("Pasta_Bay1.jpg", "pasta_grocery", "bay_01.jpg"),
            ("Pasta_bay2.jpg", "pasta_grocery", "bay_02.jpg"),
            ("bay_1_scan.jpg", "beverages", "bay_01.jpg"),
            ("bay_2_scan.jpg", "beverages", "bay_02.jpg"),
            ("bay_3_scan.jpg", "cereals", "bay_01.jpg"),
            ("bay_4_scan.jpg", "snacks", "bay_01.jpg"),
        ]
        for src_name, cat, dest_name in mappings:
            src_file = self.base_dir / src_name
            dest_file = self.base_dir / cat / dest_name
            if src_file.exists() and not dest_file.exists():
                try:
                    dest_file.write_bytes(src_file.read_bytes())
                except Exception:
                    pass

    def resolve_category_id(self, category_id: Optional[int] = None, category_name: Optional[str] = None) -> int:
        """Resolves category ID from id or text name."""
        if category_id and category_id in self.CATEGORY_MAP:
            return category_id
        if category_name:
            low = category_name.lower()
            for kw, cid in self.NAME_MAP.items():
                if kw in low:
                    return cid
        return category_id or 101

    def list_catalog(self) -> Dict[str, Any]:
        """Lists all available images categorized by department/planogram."""
        result = {}
        for cat_dir in self.base_dir.iterdir():
            if cat_dir.is_dir() and not cat_dir.name.startswith("."):
                images = [f.name for f in cat_dir.glob("*.jpg")] + [f.name for f in cat_dir.glob("*.jpeg")]
                result[cat_dir.name] = {
                    "count": len(images),
                    "files": images
                }
        return result

    def get_shelf_image(
        self,
        category_id: Optional[int] = None,
        category_name: Optional[str] = None,
        pog_id: Optional[int] = None,
        section_name: Optional[str] = None,
        store_id: int = 1088,
        dynamic_variation: bool = True,
        platform: str = "android"
    ) -> bytes:
        """
        Retrieves real shelf photo bytes matching the category, planogram, and bay.
        Applies realistic dynamic variation (EXIF metadata, micro-lighting variance)
        so every scan has a unique binary hash and timestamp, matching real store operations.
        """
        cat_id = self.resolve_category_id(category_id, category_name)
        cat_folder = self.CATEGORY_MAP.get(cat_id, "general")

        candidates: List[Path] = []

        # 1. Look for planogram-specific or bay-specific file in category folder
        cat_path = self.base_dir / cat_folder
        if cat_path.exists():
            if section_name:
                clean_sec = str(section_name).replace(" ", "_").lower()
                candidates.extend(cat_path.glob(f"*{clean_sec}*.jpg"))
            if pog_id:
                candidates.extend(cat_path.glob(f"*pog_{pog_id}*.jpg"))
            candidates.extend(cat_path.glob("*.jpg"))
            candidates.extend(cat_path.glob("*.jpeg"))

        # 2. Look in root directory for matching bay files
        if section_name:
            clean_sec = str(section_name).replace(" ", "_").lower()
            candidates.extend(self.base_dir.glob(f"*{clean_sec}*.jpg"))
            candidates.extend(self.base_dir.glob(f"bay_{section_name}_scan.jpg"))

        # 3. Fallback to any valid real photo in base directory
        candidates.extend(self.base_dir.glob("*.jpg"))
        candidates.extend(self.base_dir.glob("*.jpeg"))

        # Filter out 0-byte or corrupted files
        valid_candidates = [p for p in candidates if p.is_file() and p.stat().st_size > 1024]

        if not valid_candidates:
            # Fallback to sample scan in fixtures
            fixture_scan = self.base_dir.parent.parent / "backend" / "fixtures" / "media" / "sample_shelf_scan.jpg"
            if fixture_scan.exists() and fixture_scan.stat().st_size > 1024:
                valid_candidates.append(fixture_scan)

        if not valid_candidates:
            raise FileNotFoundError(
                f"[ShelfImageCatalog] No valid real shelf photo found for category '{cat_folder}' "
                f"(ID: {cat_id}) in {self.base_dir}. Real shelf images are required for verification."
            )

        selected_file = valid_candidates[0]
        base_bytes = selected_file.read_bytes()

        if not dynamic_variation or Image is None:
            return base_bytes

        # Apply realistic camera variation
        return self._apply_realistic_camera_variation(
            base_bytes,
            store_id=store_id,
            category_name=cat_folder,
            pog_id=pog_id or 5001,
            section_name=section_name or "Bay 01",
            platform=platform
        )

    def _apply_realistic_camera_variation(
        self,
        base_bytes: bytes,
        store_id: int,
        category_name: str,
        pog_id: int,
        section_name: str,
        platform: str
    ) -> bytes:
        """
        Applies subtle realistic mobile camera variations:
        - Micro-lighting variance (±1-2%) to simulate ambient aisle lighting
        - Injects mobile camera EXIF metadata with store timestamp & device info
        - Produces a distinct cryptographic hash on every run without altering image dimensions
        """
        try:
            with io.BytesIO(base_bytes) as in_buf:
                img = Image.open(in_buf)
                img = img.convert("RGB")

                # Subtle lighting variance
                enhancer = ImageEnhance.Brightness(img)
                factor = random.uniform(0.985, 1.015)
                img = enhancer.enhance(factor)

                out_buf = io.BytesIO()

                # Camera metadata
                device_model = "Samsung Galaxy S24 Enterprise" if platform.lower() == "android" else "Apple iPhone 15 Pro Max"
                now_str = datetime.now().strftime("%Y:%m:%d %H:%M:%S")
                scan_uuid = str(uuid.uuid4())

                comment = (
                    f"StoreIntelligenceMobile;store={store_id};pog={pog_id};"
                    f"bay={section_name};cat={category_name};scan_id={scan_uuid};captured={now_str}"
                )

                # Save with EXIF if piexif available, otherwise standard JPEG with comment
                if HAS_PIEXIF:
                    try:
                        zeroth_ifd = {
                            piexif.ImageIFD.Make: b"Store Intelligence Camera",
                            piexif.ImageIFD.Model: device_model.encode("utf-8"),
                            piexif.ImageIFD.Software: b"Store Intelligence Mobile v4.8",
                            piexif.ImageIFD.DateTime: now_str.encode("utf-8"),
                            piexif.ImageIFD.ImageDescription: comment.encode("utf-8"),
                        }
                        exif_ifd = {
                            piexif.ExifIFD.DateTimeOriginal: now_str.encode("utf-8"),
                            piexif.ExifIFD.DateTimeDigitized: now_str.encode("utf-8"),
                            piexif.ExifIFD.UserComment: piexif.helper.UserComment.dump(comment),
                        }
                        exif_dict = {"0th": zeroth_ifd, "Exif": exif_ifd}
                        exif_bytes = piexif.dump(exif_dict)
                        img.save(out_buf, format="JPEG", quality=92, exif=exif_bytes)
                    except Exception:
                        img.save(out_buf, format="JPEG", quality=92, comment=comment.encode("utf-8"))
                else:
                    img.save(out_buf, format="JPEG", quality=92, comment=comment.encode("utf-8"))

                return out_buf.getvalue()
        except Exception:
            # Fallback to pristine bytes if image processing encounters any unexpected exception
            return base_bytes


# Global Singleton Instance
image_catalog = ShelfImageCatalog()
