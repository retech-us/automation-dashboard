import unittest

from core.task_scan_timeline import build_task_scan_timeline, normalize_scan_events


class TestTaskScanTimeline(unittest.TestCase):
    def test_normalizes_task_and_pre_post_photo_times(self):
        timeline = build_task_scan_timeline(
            {
                "created_at": "2026-09-01T10:00:00Z",
                "started_at": "2026-09-01T10:05:00Z",
                "completed_at": "2026-09-01T11:00:00Z",
            },
            [
                {
                    "id": 101,
                    "scan_type": "pre_photo",
                    "created_at": "2026-09-01T10:10:00Z",
                    "status": "done",
                },
                {
                    "id": 102,
                    "scan_type": "post_photo",
                    "created_at": "2026-09-01T10:55:00Z",
                    "status": "done",
                },
            ],
        )

        self.assertEqual(timeline.pre_scan.scan_id, 101)
        self.assertEqual(timeline.post_scan.scan_id, 102)
        self.assertEqual(timeline.task_duration_seconds, 3300)
        self.assertEqual(timeline.photo_duration_seconds, 2700)

    def test_does_not_guess_post_scan_from_id_order(self):
        events = normalize_scan_events(
            [
                {"id": 101, "scan_type": "pre_photo"},
                {"id": 102, "status": "done"},
            ]
        )
        timeline = build_task_scan_timeline({}, [event for event in []])

        self.assertEqual([event.scan_type for event in events], ["pre", "unknown"])
        self.assertIsNone(timeline.post_scan)

    def test_supports_boolean_photo_markers_and_timestamp_aliases(self):
        timeline = build_task_scan_timeline(
            {},
            [
                {
                    "scan_id": "201",
                    "is_pre_photo": True,
                    "uploaded_at": "2026-09-01T08:00:00+00:00",
                },
                {
                    "scan_id": "202",
                    "is_post_photo": True,
                    "upload_completed_at": "2026-09-01T09:15:00+00:00",
                },
            ],
        )

        self.assertEqual(timeline.pre_scan.scan_id, 201)
        self.assertEqual(timeline.post_scan.scan_id, 202)
        self.assertEqual(timeline.photo_duration_seconds, 4500)


if __name__ == "__main__":
    unittest.main()
