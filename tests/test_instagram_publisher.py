import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import instagram_publish as legacy


class LegacyInstagramRetryTests(unittest.TestCase):
    def test_ambiguous_publish_outcome_is_fail_closed_and_not_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            content_path = Path(tmp) / "content_test.json"
            approved = {
                "content_id": "content_test",
                "status": "approved_for_publishing",
                "publishing": {"instagram": {"status": "not_published"}},
            }
            content_path.write_text(json.dumps(approved), encoding="utf-8")

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
                with self.assertRaises(legacy.InstagramPublishUnknown):
                    legacy.publish_instagram_reel_container(
                        "ig-user-123", "https://example.com/test.mp4",
                        "test caption", approved, content_path,
                    )

            persisted = json.loads(content_path.read_text(encoding="utf-8"))
            instagram = persisted["publishing"]["instagram"]
            self.assertEqual(instagram["creation_id"], "container-123")
            self.assertEqual(instagram["status"], "publish_outcome_unknown")
            self.assertEqual(len(media_create_calls), 1)
            self.assertEqual(publish_creation_ids, ["container-123"])
            self.assertFalse(legacy.is_already_published(persisted))

            def second_run(method, url, params):
                raise AssertionError(f"Second run made an API call: {method} {url}")

            with patch("src.instagram_publish.request", side_effect=second_run):
                with self.assertRaises(legacy.InstagramPublishUnknown):
                    legacy.publish_instagram_reel_container(
                        "ig-user-123", "https://example.com/test.mp4",
                        "test caption", persisted, content_path,
                    )

    def test_confirmed_publish_records_media_id_and_is_not_repeated(self):
        with tempfile.TemporaryDirectory() as tmp:
            content_path = Path(tmp) / "content_test.json"
            approved = {
                "content_id": "content_test",
                "status": "approved_for_publishing",
                "publishing": {"instagram": {"status": "not_published"}},
            }
            content_path.write_text(json.dumps(approved), encoding="utf-8")

            def success(method, url, params):
                if method == "POST" and url.endswith("/media"):
                    return {"id": "container-ok"}
                if method == "GET" and url.endswith("/container-ok"):
                    return {"status_code": "FINISHED"}
                if method == "POST" and url.endswith("/media_publish"):
                    return {"id": "media-777"}
                raise AssertionError(f"Unexpected mocked request: {method} {url}")

            with patch("src.instagram_publish.request", side_effect=success):
                media_id = legacy.publish_instagram_reel_container(
                    "ig-user-123", "https://example.com/test.mp4",
                    "test caption", approved, content_path,
                )
            self.assertEqual(media_id, "media-777")
            persisted = json.loads(content_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["publishing"]["instagram"]["status"], "published_to_instagram")
            self.assertEqual(persisted["publishing"]["instagram"]["media_id"], "media-777")
            self.assertTrue(legacy.is_already_published(persisted))

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
