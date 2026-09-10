"""
QC Counter Manager - Manages QC-100, QC-101, QC-102... numbering for generated test cases
"""

import json
import os
import logging
from pathlib import Path
from threading import Lock

logger = logging.getLogger(__name__)


class QCCounter:
    """Manages incrementing QC issue numbers"""

    def __init__(self, counter_file: str = None):
        """Initialize QC counter"""
        if counter_file is None:
            counter_file = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'data',
                'qc-counter.json'
            )

        self.counter_file = counter_file
        self.lock = Lock()
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Create counter file if it doesn't exist"""
        if not os.path.exists(self.counter_file):
            os.makedirs(os.path.dirname(self.counter_file), exist_ok=True)
            with open(self.counter_file, 'w') as f:
                json.dump({
                    "last_qc_number": 99,
                    "instances": {}
                }, f, indent=2)
            logger.info(f"✓ Created QC counter file: {self.counter_file}")

    def _read_counter(self) -> dict:
        """Read counter data from file"""
        try:
            with open(self.counter_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading counter file: {e}")
            return {"last_qc_number": 99, "instances": {}}

    def _write_counter(self, data: dict):
        """Write counter data to file"""
        try:
            with open(self.counter_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error writing counter file: {e}")

    def get_next_qc_number(self) -> str:
        """Get next QC issue number (QC-100, QC-101, etc.)"""
        with self.lock:
            data = self._read_counter()
            next_num = data.get("last_qc_number", 99) + 1
            data["last_qc_number"] = next_num
            self._write_counter(data)

            qc_key = f"QC-{next_num}"
            logger.info(f"✓ Generated QC key: {qc_key}")
            return qc_key

    def get_current_qc_number(self) -> int:
        """Get current highest QC number"""
        data = self._read_counter()
        return data.get("last_qc_number", 99)

    def reset_counter(self, start_at: int = 100):
        """Reset counter to start number (for testing)"""
        with self.lock:
            data = {"last_qc_number": start_at - 1, "instances": {}}
            self._write_counter(data)
            logger.warning(f"⚠️ QC counter reset to start at {start_at}")


# Global instance
_qc_counter = None


def get_qc_counter() -> QCCounter:
    """Get or create global QC counter instance"""
    global _qc_counter
    if _qc_counter is None:
        _qc_counter = QCCounter()
    return _qc_counter
