import os
import tempfile
import unittest
from pathlib import Path
import json

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
from src import telegram_process as MODULE


class TelegramProcessApprovalTests(unittest.TestCase):
    def setUp(self):
        self.now = "2026-10-22T00:00:00Z"

    def test_educational_approval_records_fact_check_review(self):
        record = {
            "content_type": "educational_reel",
            "content_id": "draft_sample_20261022",
            "status": "pending_approval",
            "approval_status": "pending",
            "fact_check": {"status": "needs_human_review", "notes": []},
        }
        self.assertTrue(MODULE.apply_market_decision(record, "market_approve", self.now, "@owner"))
        self.assertEqual(record["status"], "generated")
        self.assertEqual(record["approval_status"], "approved")
        self.assertEqual(record["fact_check"]["status"], "approved")
        self.assertEqual(record["fact_check"]["reviewed_at"], self.now)
        self.assertEqual(record["fact_check"]["reviewed_by"], "@owner")
        self.assertEqual(record["approval"]["reviewed_by"], "@owner")

    def test_reject_sets_fact_check_rejected_and_does_not_publish(self):
        record = {
            "content_type": "educational_reel",
            "content_id": "draft_sample_20261022",
            "status": "pending_approval",
            "approval_status": "pending",
            "fact_check": {"status": "needs_human_review", "notes": []},
        }
        self.assertTrue(MODULE.apply_market_decision(record, "market_reject", self.now, "id:123"))
        self.assertEqual(record["status"], "rejected")
        self.assertEqual(record["approval_status"], "rejected")
        self.assertEqual(record["fact_check"]["status"], "rejected")
        self.assertEqual(record["fact_check"]["reviewed_by"], "id:123")

    def test_second_conflicting_click_cannot_overwrite_approval(self):
        record = {
            "content_type": "educational_reel",
            "content_id": "draft_sample_20261022",
            "status": "pending_approval",
            "approval_status": "pending",
            "fact_check": {"status": "needs_human_review", "notes": []},
        }
        self.assertTrue(MODULE.apply_market_decision(record, "market_approve", self.now, "@owner"))
        self.assertFalse(MODULE.apply_market_decision(record, "market_reject", "2026-10-22T00:01:00Z", "@other"))
        self.assertEqual(record["approval_status"], "approved")
        self.assertEqual(record["fact_check"]["status"], "approved")

    def test_metadata_mirror_updates_reviewed_by_and_status(self):
        with tempfile.TemporaryDirectory() as temp:
            old_dir = MODULE.OUTPUT_DIR
            try:
                MODULE.OUTPUT_DIR = Path(temp)
                content_id = "draft_sample_20261022"
                path = MODULE.OUTPUT_DIR / f"{content_id}.json"
                path.write_text(json.dumps({
                    "content_id": content_id,
                    "status": "draft_only",
                    "approval": {"required": True, "status": "pending"},
                    "fact_check": {"status": "needs_human_review", "notes": []},
                }), encoding="utf-8")
                self.assertTrue(MODULE.sync_educational_metadata(content_id, "market_approve", self.now, "@owner"))
                content = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(content["status"], "approved_for_publishing")
                self.assertEqual(content["fact_check"]["status"], "approved")
                self.assertEqual(content["fact_check"]["reviewed_at"], self.now)
                self.assertEqual(content["fact_check"]["reviewed_by"], "@owner")
            finally:
                MODULE.OUTPUT_DIR = old_dir


if __name__ == "__main__":
    unittest.main()
