import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents.publisher import _meta_request, publish


class PublisherTests(unittest.TestCase):
    def signal(self):
        return {"signal_id": "test-signal", "symbol": "TEST", "direction": "LONG"}

    def copy(self):
        return {"telegram_html": "<b>Test</b>", "instagram_caption": "Test caption"}

    def test_missing_credentials_fail_instead_of_silent_success(self):
        record = {"publishing": {}}
        with patch.dict(os.environ, {"HUMAN_APPROVAL": "false"}, clear=True), \
             patch("agents.publisher._accessible_image_url", return_value="https://example.com/card.png"):
            with self.assertRaisesRegex(RuntimeError, "publishing platforms failed"):
                publish(self.signal(), self.copy(), Path("card.png"), record, dry_run=False)
        self.assertEqual(record["publishing"]["telegram"]["status"], "failed")
        self.assertEqual(record["publishing"]["instagram"]["status"], "failed")

    def test_partial_publish_retries_failed_platform_without_reposting_success(self):
        record = {"publishing": {}}
        env = {
            "HUMAN_APPROVAL": "false",
            "TELEGRAM_BOT_TOKEN": "test-token",
            "IG_ACCESS_TOKEN": "test-ig-token",
            "IG_USER_ID": "123456",
        }
        with tempfile.TemporaryDirectory() as tmp:
            card = Path(tmp) / "card.png"
            card.write_bytes(b"test image bytes")
            with patch.dict(os.environ, env, clear=True), \
                 patch("agents.publisher._accessible_image_url", return_value="https://example.com/card.png"), \
                 patch("agents.publisher._telegram", side_effect=[RuntimeError("temporary Telegram failure"), {"message_id": 456}]) as telegram, \
                 patch("agents.publisher._instagram_publish", return_value="media-123") as instagram:
                with self.assertRaisesRegex(RuntimeError, "publishing platforms failed"):
                    publish(self.signal(), self.copy(), card, record, dry_run=False)
                self.assertEqual(record["publishing"]["instagram"]["status"], "published")
                self.assertEqual(record["publishing"]["telegram"]["status"], "failed")
                publish(self.signal(), self.copy(), card, record, dry_run=False)
                self.assertEqual(record["status"], "published")
                self.assertEqual(record["publishing"]["telegram"]["message_id"], 456)
                self.assertEqual(telegram.call_count, 2)
                self.assertEqual(instagram.call_count, 1)

    def test_instagram_retry_reuses_creation_id_after_media_publish_error(self):
        record = {"publishing": {}}
        env = {
            "HUMAN_APPROVAL": "false",
            "TELEGRAM_BOT_TOKEN": "test-token",
            "IG_ACCESS_TOKEN": "test-ig-token",
            "IG_USER_ID": "123456",
        }
        container_calls = []
        publish_creation_ids = []

        def fake_meta_request(method, url, **kwargs):
            if method == "POST" and url.endswith("/media"):
                container_calls.append(kwargs.get("data", {}).get("caption"))
                return {"id": "container-123"}
            if method == "GET" and url.endswith("/container-123"):
                return {"status_code": "FINISHED"}
            if method == "POST" and url.endswith("/media_publish"):
                publish_creation_ids.append(kwargs.get("data", {}).get("creation_id"))
                if len(publish_creation_ids) == 1:
                    raise RuntimeError(
                        "Meta API HTTP 400; code=190, subcode=460, "
                        "type=OAuthException; message redacted."
                    )
                return {"id": "media-456"}
            raise AssertionError(f"Unexpected Meta request: {method} {url}")

        with tempfile.TemporaryDirectory() as tmp:
            card = Path(tmp) / "card.png"
            card.write_bytes(b"test image bytes")
            with patch.dict(os.environ, env, clear=True), \
                 patch("agents.publisher._accessible_image_url", return_value="https://example.com/card.png"), \
                 patch("agents.publisher._telegram", return_value={"message_id": 101}), \
                 patch("agents.publisher._meta_request", side_effect=fake_meta_request):
                with self.assertRaisesRegex(RuntimeError, "publishing platforms failed"):
                    publish(self.signal(), self.copy(), card, record, dry_run=False)
                self.assertEqual(record["publishing"]["instagram"]["creation_id"], "container-123")
                self.assertEqual(record["publishing"]["instagram"]["status"], "failed")

                publish(self.signal(), self.copy(), card, record, dry_run=False)

        self.assertEqual(len(container_calls), 1, "retry must not create a second container")
        self.assertEqual(publish_creation_ids, ["container-123", "container-123"])
        self.assertEqual(record["publishing"]["instagram"]["status"], "published")
        self.assertEqual(record["publishing"]["instagram"]["media_id"], "media-456")

    def test_meta_errors_include_safe_ids_but_not_response_message(self):
        class FakeResponse:
            ok = False
            status_code = 400

            @staticmethod
            def json():
                return {
                    "error": {
                        "code": 190,
                        "error_subcode": 460,
                        "type": "OAuthException",
                        "message": "NEVER_LOG_THIS_META_MESSAGE",
                    }
                }

        with patch("agents.publisher.requests.request", return_value=FakeResponse()):
            with self.assertRaises(RuntimeError) as raised:
                _meta_request(
                    "POST", "https://graph.facebook.com/v23.0/me",
                    data={"access_token": "NEVER_LOG_THIS_TOKEN"},
                )
        message = str(raised.exception)
        self.assertIn("code=190", message)
        self.assertIn("subcode=460", message)
        self.assertIn("type=OAuthException", message)
        self.assertNotIn("NEVER_LOG_THIS_META_MESSAGE", message)
        self.assertNotIn("NEVER_LOG_THIS_TOKEN", message)

if __name__ == "__main__":
    unittest.main()
