import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import publish_approved_educational_reels as MODULE


class TelegramEducationalApprovalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.state_path = Path(self.temp.name) / "data" / "state.json"
        self.content_id = "draft_approved_20261116"
        self.record = {
            "content_type": "educational_reel",
            "content_id": self.content_id,
            "human_approval_required": True,
            "approval_status": "approved",
            "approval_mode": "human_review",
            "status": "generated",
            "reviewed_at": "2026-11-16T08:00:00Z",
            "reviewed_by": "id:123",
            "fact_check": {"status": "approved"},
        }
        self.write_state({"signals": {self.content_id: dict(self.record)}, "runs": []})

    def tearDown(self):
        self.temp.cleanup()

    def write_state(self, value):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(value), encoding="utf-8")

    def read_state(self):
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def test_approved_reel_calls_telegram_adapter_and_persists_message(self):
        def publish(record):
            record["status"] = "published"
            record["publishing"] = {"telegram": {"status": "published", "message_id": 321}}
            return record
        with patch.object(MODULE, "publish_approved_educational_reel", side_effect=publish) as adapter:
            result = MODULE.publish_ids(self.content_id, self.state_path)
        self.assertEqual(result, 0)
        adapter.assert_called_once()
        saved = self.read_state()["signals"][self.content_id]
        self.assertEqual(saved["status"], "published")
        self.assertEqual(saved["publishing"]["telegram"]["message_id"], 321)
        self.assertNotIn("instagram_media_id", saved)

    def test_missing_human_approval_blocks_automated_policy_record(self):
        auto = dict(self.record)
        auto.update({
            "human_approval_required": False,
            "approval_mode": "automated_policy",
            "reviewed_at": None,
            "reviewed_by": None,
            "fact_check": {"status": "automated_passed"},
        })
        self.write_state({"signals": {self.content_id: auto}, "runs": []})
        with patch.object(MODULE, "publish_approved_educational_reel") as adapter:
            result = MODULE.publish_ids(self.content_id, self.state_path)
        self.assertEqual(result, 1)
        adapter.assert_not_called()
        saved = self.read_state()["signals"][self.content_id]
        self.assertEqual(saved["approval_status"], "approved")
        self.assertEqual(saved["last_publish_error"], "RuntimeError")

    def test_pending_record_never_reaches_telegram_adapter(self):
        pending = dict(self.record, approval_status="pending")
        self.write_state({"signals": {self.content_id: pending}, "runs": []})
        with patch.object(MODULE, "publish_approved_educational_reel") as adapter:
            result = MODULE.publish_ids(self.content_id, self.state_path)
        self.assertEqual(result, 1)
        adapter.assert_not_called()

    def test_rejects_non_educational_record(self):
        market = dict(self.record, content_type="market_signal")
        self.write_state({"signals": {self.content_id: market}, "runs": []})
        with patch.object(MODULE, "publish_approved_educational_reel") as adapter:
            result = MODULE.publish_ids(self.content_id, self.state_path)
        self.assertEqual(result, 1)
        adapter.assert_not_called()

    def test_duplicate_ids_in_one_dispatch_are_deduplicated(self):
        with patch.object(MODULE, "publish_approved_educational_reel", side_effect=lambda record: record) as adapter:
            result = MODULE.publish_ids(f"{self.content_id},{self.content_id}", self.state_path)
        self.assertEqual(result, 0)
        adapter.assert_called_once()

    def test_script_entrypoint_without_ids_is_a_safe_noop(self):
        env = os.environ.copy()
        env["EDUCATIONAL_APPROVED_IDS"] = ""
        result = subprocess.run(
            [sys.executable, "scripts/publish_approved_educational_reels.py"],
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("No newly approved educational Reel IDs", result.stdout)


if __name__ == "__main__":
    unittest.main()
