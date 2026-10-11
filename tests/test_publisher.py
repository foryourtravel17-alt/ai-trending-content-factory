import os
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
        with patch.dict(os.environ, env, clear=True), \
             patch("agents.publisher._accessible_image_url", return_value="https://example.com/card.png"), \
             patch("agents.publisher._telegram", side_effect=[RuntimeError("temporary Telegram failure"), {"message_id": 456}]) as telegram, \
             patch("agents.publisher._instagram_publish", return_value="media-123") as instagram:
            with self.assertRaisesRegex(RuntimeError, "publishing platforms failed"):
                publish(self.signal(), self.copy(), Path("card.png"), record, dry_run=False)
            self.assertEqual(record["publishing"]["instagram"]["status"], "published")
            self.assertEqual(record["publishing"]["telegram"]["status"], "failed")
            publish(self.signal(), self.copy(), Path("card.png"), record, dry_run=False)
            self.assertEqual(record["status"], "published")
            self.assertEqual(record["publishing"]["telegram"]["message_id"], 456)
            self.assertEqual(telegram.call_count, 2)
            self.assertEqual(instagram.call_count, 1)

if __name__ == "__main__":
    unittest.main()
