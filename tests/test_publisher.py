import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents.publisher import publish


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

if __name__ == "__main__":
    unittest.main()
