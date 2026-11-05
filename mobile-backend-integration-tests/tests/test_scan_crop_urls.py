import unittest

import runner_server


class ScanCropInstanceTests(unittest.TestCase):
    def test_crop_urls_name_the_instance_that_owns_the_scan(self):
        flow = {
            "action_batches": {
                "b1": {
                    "items": [
                        {
                            "image": "/api/runner/scan_crop?scan_id=18383171&item_id=9&shelf=9&pos=1",
                            "crop_image_url": "/api/runner/scan_crop?scan_id=18383171&item_id=9&shelf=9&pos=1",
                        },
                        {"image": "https://bucket.example/real.png", "crop_image_url": "https://bucket.example/real.png"},
                    ]
                }
            },
            "metadata": {"task_id": 45081427},
        }
        result = runner_server.add_instance_to_crop_urls(flow, "krcs")
        items = result["action_batches"]["b1"]["items"]
        self.assertEqual(
            items[0]["crop_image_url"],
            "/api/runner/scan_crop?scan_id=18383171&item_id=9&shelf=9&pos=1&instance=krcs",
        )
        self.assertEqual(items[0]["image"], items[0]["crop_image_url"])
        self.assertEqual(items[1]["image"], "https://bucket.example/real.png")
        self.assertEqual(result["metadata"]["task_id"], 45081427)

    def test_a_crop_url_that_already_names_an_instance_is_left_alone(self):
        url = "/api/runner/scan_crop?scan_id=1&instance=harr"
        self.assertEqual(runner_server.add_instance_to_crop_urls({"image": url}, "krcs")["image"], url)

    def test_instance_is_url_encoded(self):
        result = runner_server.add_instance_to_crop_urls(
            ["/api/runner/scan_crop?scan_id=1"], "https://custom.example.com/"
        )
        self.assertEqual(
            result[0],
            "/api/runner/scan_crop?scan_id=1&instance=https%3A%2F%2Fcustom.example.com%2F",
        )


if __name__ == "__main__":
    unittest.main()
