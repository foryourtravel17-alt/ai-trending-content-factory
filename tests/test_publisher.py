import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents.publisher import publish, _meta_request


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

    def test_instagram_only_retry_never_calls_telegram(self):
        record = {"publishing": {"telegram": {"status": "published", "message_id": 73},
                                 "instagram": {"status": "failed", "error": "HTTP 400"}}}
        env = {
            "HUMAN_APPROVAL": "false",
            "MARKET_RETRY_INSTAGRAM_ONLY": "true",
            "IG_ACCESS_TOKEN": "test-ig-token",
            "IG_USER_ID": "123456",
        }
        with patch.dict(os.environ, env, clear=True), \
             patch("agents.publisher._accessible_image_url", return_value="https://example.com/card.png"), \
             patch("agents.publisher._telegram") as telegram, \
             patch("agents.publisher._instagram_publish", return_value="media-789") as instagram:
            publish(self.signal(), self.copy(), Path("card.png"), record, dry_run=False)
        telegram.assert_not_called()
        instagram.assert_called_once()
        self.assertEqual(record["publishing"]["telegram"]["message_id"], 73)
        self.assertEqual(record["publishing"]["instagram"]["status"], "published")

    def test_instagram_only_retry_blocks_if_telegram_not_already_published(self):
        record = {"publishing": {"telegram": {"status": "failed"}, "instagram": {"status": "failed"}}}
        with patch.dict(os.environ, {"HUMAN_APPROVAL": "false", "MARKET_RETRY_INSTAGRAM_ONLY": "true"}, clear=True), \
             patch("agents.publisher._telegram") as telegram, \
             patch("agents.publisher._instagram_publish") as instagram:
            with self.assertRaisesRegex(RuntimeError, "Telegram is not already marked published"):
                publish(self.signal(), self.copy(), Path("card.png"), record, dry_run=False)
        telegram.assert_not_called()
        instagram.assert_not_called()

    def test_instagram_only_retry_does_not_repost_already_published_instagram(self):
        record = {"publishing": {"telegram": {"status": "published", "message_id": 73},
                                 "instagram": {"status": "published", "media_id": "existing-media"}}}
        env = {"HUMAN_APPROVAL": "false", "MARKET_RETRY_INSTAGRAM_ONLY": "true"}
        with patch.dict(os.environ, env, clear=True), \
             patch("agents.publisher._telegram") as telegram, \
             patch("agents.publisher._instagram_publish") as instagram:
            result = publish(self.signal(), self.copy(), Path("card.png"), record, dry_run=False)
        telegram.assert_not_called()
        instagram.assert_not_called()
        self.assertEqual(result["publishing"]["telegram"]["message_id"], 73)
        self.assertEqual(result["publishing"]["instagram"]["media_id"], "existing-media")
        self.assertEqual(result["status"], "published")

    def test_meta_http_error_logs_only_safe_identifiers(self):
        class FakeResponse:
            ok = False
            status_code = 400

            def json(self):
                return {"error": {
                    "type": "OAuthException",
                    "code": 100,
                    "error_subcode": 36003,
                    "message": "sensitive details with access_token=DO_NOT_LEAK",
                }}

        with patch("agents.publisher.requests.request", return_value=FakeResponse()):
            with self.assertRaisesRegex(RuntimeError, r"HTTP 400 .*code=100, subcode=36003"):
                _meta_request("POST", "https://graph.facebook.com/test", data={"access_token": "DO_NOT_LEAK"})
        # The raised message must not include Meta's untrusted message or any token.
        try:
            with patch("agents.publisher.requests.request", return_value=FakeResponse()):
                _meta_request("POST", "https://graph.facebook.com/test", data={"access_token": "DO_NOT_LEAK"})
        except RuntimeError as exc:
            self.assertNotIn("DO_NOT_LEAK", str(exc))
            self.assertNotIn("sensitive details", str(exc))
            self.assertIn("code=100", str(exc))
            self.assertIn("subcode=36003", str(exc))


if __name__ == "__main__":
    unittest.main()
