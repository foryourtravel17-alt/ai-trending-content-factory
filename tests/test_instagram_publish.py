import contextlib
import io
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("META_SYSTEM_USER_TOKEN", "test-token")
from src import instagram_publish as MODULE


class InstagramPublishDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.old_output = MODULE.OUTPUT_DIR
        MODULE.OUTPUT_DIR = self.root / "output"
        (MODULE.OUTPUT_DIR / "media").mkdir(parents=True)
        self.now = datetime.now(timezone.utc)

    def tearDown(self):
        MODULE.OUTPUT_DIR = self.old_output
        self.temp.cleanup()

    def write_record(self, content_id, *, status="approved_for_publishing",
                     fact_status="approved", created_at=None, published_at=None):
        created_at = created_at or self.now.isoformat()
        record = {
            "content_id": content_id,
            "status": status,
            "created_at": created_at,
            "fact_check": {"status": fact_status},
            "approval": {"required": True, "status": "approved", "reviewed_at": created_at, "reviewed_by": "@owner"},
            "social": {"caption": "Educational content only.", "hashtags": ["#BullseyeTheory"]},
        }
        if published_at:
            record["published_at"] = published_at
            record["status"] = "published_to_instagram"
        path = MODULE.OUTPUT_DIR / f"{content_id}.json"
        path.write_text(json.dumps(record), encoding="utf-8")
        (MODULE.OUTPUT_DIR / "media" / f"{content_id}.mp4").write_bytes(b"fake-mp4-for-discovery-test")
        return path

    def test_record_path_discovery_includes_both_legacy_and_draft_patterns(self):
        legacy = self.write_record("content_legacy_20261022")
        draft = self.write_record("draft_education_20261022")
        names = [p.name for p in MODULE.content_record_paths()]
        self.assertIn(legacy.name, names)
        self.assertIn(draft.name, names)

    def test_approved_draft_metadata_is_found_by_publisher(self):
        path = self.write_record("draft_education_20261022")
        selected, content = MODULE.load_newest_unpublished_approved()
        self.assertEqual(selected, path)
        self.assertEqual(content["content_id"], "draft_education_20261022")

    def test_fact_check_gate_blocks_never_approved_draft(self):
        self.write_record("draft_unreviewed_20261022", fact_status="needs_human_review")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            selected, content = MODULE.load_newest_unpublished_approved()
        self.assertIsNone(selected)
        self.assertIsNone(content)
        self.assertIn("Skipping draft requiring fact-check review", output.getvalue())

    def test_draft_older_than_24_hours_is_skipped_with_clear_log(self):
        old = (self.now - timedelta(hours=25)).isoformat()
        self.write_record("draft_stale_20261021", created_at=old)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            selected, content = MODULE.load_newest_unpublished_approved()
        self.assertIsNone(selected)
        self.assertIsNone(content)
        self.assertIn("Skipping stale/future-dated draft", output.getvalue())

    def test_daily_cap_counts_published_draft_records(self):
        today = datetime.now(MODULE.LOCAL_TZ).replace(hour=12, minute=0, second=0, microsecond=0).isoformat()
        for index in range(3):
            self.write_record(
                f"draft_published_{index}_20261022",
                status="published_to_instagram",
                published_at=today,
            )
        self.assertEqual(MODULE.published_today_count(), 3)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            selected, content = MODULE.load_newest_unpublished_approved()
        self.assertIsNone(selected)
        self.assertIsNone(content)
        self.assertIn("Daily publishing cap reached: 3/3", output.getvalue())




    def test_instagram_published_telegram_failed_retry_skips_instagram(self):
        content_id = "draft_partial_retry_20261022"
        path = self.write_record(content_id, status="published_to_instagram")
        record = json.loads(path.read_text(encoding="utf-8"))
        record["approval"] = {
            "required": True, "status": "approved",
            "reviewed_at": record["created_at"], "reviewed_by": "@owner",
        }
        record["video_url"] = f"https://example.supabase.co/storage/v1/object/public/REELS/reels/{content_id}.mp4"
        record["video_content_id"] = content_id
        record["video_sha256"] = "a" * 64
        record["video_size_bytes"] = 123
        record["video_duration_seconds"] = 42.29
        record["status"] = "published_to_instagram"
        record["instagram_media_id"] = "ig-media-123"
        record["publishing"] = {
            "instagram": {"status": "published_to_instagram", "media_id": "ig-media-123"},
            "telegram": {"status": "failed", "error": "temporary channel error"},
        }
        path.write_text(json.dumps(record), encoding="utf-8")
        with patch.dict(os.environ, {
            "SUPABASE_URL": "https://example.supabase.co",
            "TELEGRAM_BOT_TOKEN": "fake-test-token",
        }), patch.object(MODULE, "verify_public_video_url", return_value=record["video_url"]), \
             patch.object(MODULE, "publish_instagram_reel_container") as instagram, \
             patch.object(MODULE, "_send_telegram_video", return_value=555) as telegram:
            MODULE.publish_content_record(path, record)
        instagram.assert_not_called()
        telegram.assert_called_once()
        updated = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(updated["instagram_media_id"], "ig-media-123")
        self.assertEqual(updated["publishing"]["telegram"]["status"], "published")


if __name__ == "__main__":
    unittest.main()
