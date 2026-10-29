"""
Unit tests for ShelfImageCatalog.
Validates multi-category image resolution, dynamic camera variation,
and distinct cryptographic hashes on every upload.
"""

import sys
import unittest
from pathlib import Path

# Ensure mobile-backend-integration-tests is in path
CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.shelf_image_catalog import ShelfImageCatalog, image_catalog


class TestShelfImageCatalog(unittest.TestCase):
    def setUp(self):
        self.catalog = image_catalog

    def test_catalog_category_discovery(self):
        """Verifies categories are created and indexed."""
        overview = self.catalog.list_catalog()
        self.assertIn("beverages", overview)
        self.assertIn("pasta_grocery", overview)
        self.assertIn("cereals", overview)
        self.assertIn("snacks", overview)

    def test_beverage_category_image_resolution(self):
        """Verifies Category 101 (Beverages) resolves real image bytes."""
        img_bytes = self.catalog.get_shelf_image(category_id=101, section_name="1")
        self.assertGreater(len(img_bytes), 50000, "Beverage scan photo must be realistic high-res JPEG")

    def test_pasta_category_image_resolution(self):
        """Verifies Category 104 (Pasta & Italian Grocery) resolves real 3.5MB+ image."""
        img_bytes = self.catalog.get_shelf_image(category_name="Pasta", section_name="1")
        self.assertGreater(len(img_bytes), 1000000, "Pasta scan must be high-res real retailer photo")

    def test_dynamic_camera_variation_uniqueness(self):
        """Verifies two successive calls produce different hashes due to dynamic timestamp and EXIF."""
        img_a = self.catalog.get_shelf_image(category_id=101, dynamic_variation=True)
        img_b = self.catalog.get_shelf_image(category_id=101, dynamic_variation=True)
        self.assertNotEqual(img_a, img_b, "Dynamic variation must produce unique binary payload to simulate live camera capture")

    def test_category_id_fallback_resolution(self):
        """Verifies unknown category gracefully falls back without crashing."""
        img_bytes = self.catalog.get_shelf_image(category_id=9999, section_name="Bay 01")
        self.assertGreater(len(img_bytes), 10000)


if __name__ == "__main__":
    unittest.main()
