import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import telegram_reel_publish as publisher


class TelegramReelPublisherTests(unittest.TestCase):
    def approved_record(self):
        return {
            "content_type": "educational_reel",
            "content_id": "draft_test_20261116",
            "status": "approved_for_publishing",
            "approval_status": "approved",
            "human_approval_required": True,
            "approval": {
                "required": True,
                "status": "approved",
                "mode": "human_review",
                "reviewed_at": "2026-11-16T10:00:00Z",
                "reviewed_by": "id:123",
            },
            "reviewed_at": "2026-11-16T10:00:00Z",
            "reviewed_by": "id:123",
            "fact_check": {"status": "approved"},
            "created_at": "2026-11-16T10:00:00Z",
            "social": {"caption": "Educational Reel", "hashtags": ["#BullseyeTheory"]},
            "video_url": "https://example.supabase.co/storage/v1/object/public/REELS/reels/draft_test_20261116.mp4",
            "video_content_id": "draft_test_20261116",
            "video_sha256": "a" * 64,
            "video_size_bytes": 100,
            "video_duration_seconds": 30.0,
            "publishing": {"telegram": {"status": "pending"}},
        }

    def test_only_explicitly_approved_record_is_published_to_telegram(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "draft_test_20261116.json"
            record = self.approved_record()
            with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "test-token", "SUPABASE_URL": "https://example.supabase.co"}, clear=True), patch.object(
                publisher, "verify_public_video_url", return_value=record["video_url"]
            ), patch.object(publisher, "_send_telegram_video", return_value=765) as send:
                result = publisher.publish_content_record(path, record)
            self.assertEqual(result["status"], "published")
            self.assertEqual(result["publishing"]["telegram"]["status"], "published")
            self.assertEqual(result["publishing"]["telegram"]["message_id"], 765)
            send.assert_called_once()
            self.assertNotIn("instagram", result["publishing"])

    def test_pending_record_is_blocked_before_send(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "draft_test_20261116.json"
            record = self.approved_record()
            record["approval"]["status"] = "pending"
            with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "test-token", "SUPABASE_URL": "https://example.supabase.co"}, clear=True), patch.object(
                publisher, "_send_telegram_video"
            ) as send:
                with self.assertRaisesRegex(RuntimeError, "explicit owner approval"):
                    publisher.publish_content_record(path, record)
            send.assert_not_called()

    def test_automated_policy_without_owner_review_is_blocked(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "draft_test_20261116.json"
            record = self.approved_record()
            record["human_approval_required"] = False
            record["approval"]["mode"] = "automated_policy"
            with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "test-token", "SUPABASE_URL": "https://example.supabase.co"}, clear=True), patch.object(
                publisher, "_send_telegram_video"
            ) as send:
                with self.assertRaisesRegex(RuntimeError, "explicit owner approval"):
                    publisher.publish_content_record(path, record)
            send.assert_not_called()

    def test_already_published_video_is_not_resent(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "draft_test_20261116.json"
            record = self.approved_record()
            record["publishing"]["telegram"] = {"status": "published", "message_id": 12}
            with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "test-token", "SUPABASE_URL": "https://example.supabase.co"}, clear=True), patch.object(
                publisher, "_send_telegram_video"
            ) as send:
                result = publisher.publish_content_record(path, record)
            self.assertEqual(result["status"], "published")
            send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
