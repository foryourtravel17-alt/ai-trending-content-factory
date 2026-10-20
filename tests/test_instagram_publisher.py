import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import instagram_publish as legacy


class LegacyInstagramRetryTests(unittest.TestCase):
    def test_ambiguous_publish_error_reuses_persisted_reel_container(self):
        with tempfile.TemporaryDirectory() as tmp:
            content_path = Path(tmp) / "content_test.json"
            approved = {
                "content_id": "content_test",
                "status": "approved_for_publishing",
                "publishing": {"instagram": {"status": "not_published"}},
            }
            content_path.write_text(
                json.dumps(approved), encoding="utf-8"
            )

            media_create_calls = []
            publish_creation_ids = []

            def first_attempt(method, url, params):
                if method == "POST" and url.endswith("/media"):
                    media_create_calls.append(params.copy())
                    return {"id": "container-123"}
                if method == "GET" and url.endswith("/container-123"):
                    return {"status_code": "FINISHED"}
                if method == "POST" and url.endswith("/media_publish"):
                    publish_creation_ids.append(params.get("creation_id"))
                    raise RuntimeError("simulated network interruption after publish request")
                raise AssertionError(f"Unexpected mocked request: {method} {url}")

            with patch("src.instagram_publish.request", side_effect=first_attempt):
                with self.assertRaisesRegex(RuntimeError, "simulated network interruption"):
                    legacy.publish_instagram_reel_container(
                        "ig-user-123",
                        "https://example.com/test.mp4",
                        "test caption",
                        approved,
                        content_path,
                    )

            persisted = json.loads(content_path.read_text(encoding="utf-8"))
            self.assertEqual(
                persisted["publishing"]["instagram"]["creation_id"],
                "container-123",
            )
            self.assertEqual(persisted["publishing"]["instagram"]["status"], "container_created")
            self.assertEqual(len(media_create_calls), 1)
            self.assertEqual(publish_creation_ids, ["container-123"])

            def retry_attempt(method, url, params):
                if method == "POST" and url.endswith("/media"):
                    media_create_calls.append(params.copy())
                    return {"id": "container-should-not-be-created"}
                if method == "GET" and url.endswith("/container-123"):
                    return {"status_code": "FINISHED"}
                if method == "POST" and url.endswith("/media_publish"):
                    publish_creation_ids.append(params.get("creation_id"))
                    return {"id": "media-456"}
                raise AssertionError(f"Unexpected mocked request: {method} {url}")

            with patch("src.instagram_publish.request", side_effect=retry_attempt):
                media_id = legacy.publish_instagram_reel_container(
                    "ig-user-123",
                    "https://example.com/test.mp4",
                    "test caption",
                    persisted,
                    content_path,
                )

            self.assertEqual(media_id, "media-456")
            self.assertEqual(len(media_create_calls), 1, "retry must not create a second Reel container")
            self.assertEqual(publish_creation_ids, ["container-123", "container-123"])

    def test_expired_container_is_kept_for_manual_reconciliation(self):
        with tempfile.TemporaryDirectory() as tmp:
            content_path = Path(tmp) / "content_test.json"
            approved = {
                "content_id": "content_test",
                "publishing": {"instagram": {"creation_id": "container-expired"}},
            }
            with patch(
                "src.instagram_publish.request",
                return_value={"status_code": "EXPIRED"},
            ):
                with self.assertRaisesRegex(RuntimeError, "EXPIRED"):
                    legacy.publish_instagram_reel_container(
                        "ig-user-123",
                        "https://example.com/test.mp4",
                        "test caption",
                        approved,
                        content_path,
                    )
            self.assertEqual(
                approved["publishing"]["instagram"]["creation_id"],
                "container-expired",
            )


if __name__ == "__main__":
    unittest.main()
