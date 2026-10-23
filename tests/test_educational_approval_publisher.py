import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import publish_approved_educational_reels as MODULE


class EducationalApprovalPublisherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.state_path = Path(self.temp.name) / "data" / "state.json"
        self.record = {
            "content_type": "educational_reel",
            "content_id": "draft_approved_20261022",
            "human_approval_required": True,
            "approval_status": "approved",
            "status": "generated",
            "reviewed_at": "2026-10-22T00:00:00Z",
            "reviewed_by": "@owner",
            "fact_check": {"status": "approved", "reviewed_at": "2026-10-22T00:00:00Z", "reviewed_by": "@owner"},
        }
        self.write_state({"signals": {self.record["content_id"]: dict(self.record)}, "runs": []})

    def tearDown(self):
        self.temp.cleanup()

    def write_state(self, state):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(state), encoding="utf-8")

    def read_state(self):
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def test_authorized_educational_approval_reaches_adapter_and_persists_returned_status(self):
        def publish(record):
            record["status"] = "published"
            record["publishing"] = {
                "instagram": {"status": "published_to_instagram", "media_id": "ig-media-test"},
                "telegram": {"status": "published", "message_id": 321},
            }
            return record

        with patch.object(MODULE, "publish_approved_educational_reel", side_effect=publish) as adapter:
            result = MODULE.publish_ids(self.record["content_id"], self.state_path)
        self.assertEqual(result, 0)
        adapter.assert_called_once()
        state = self.read_state()
        saved = state["signals"][self.record["content_id"]]
        self.assertEqual(saved["status"], "published")
        self.assertEqual(saved["publishing"]["instagram"]["media_id"], "ig-media-test")
        self.assertEqual(saved["publishing"]["telegram"]["message_id"], 321)

    def test_automated_policy_record_reaches_publisher_without_human_review(self):
        auto = dict(self.record)
        auto.pop("reviewed_at", None)
        auto.pop("reviewed_by", None)
        auto.update({
            "human_approval_required": False,
            "approval_mode": "automated_policy",
            "automated_review_at": "2026-10-22T00:00:00Z",
            "fact_check": {
                "status": "automated_passed",
                "automated_review_at": "2026-10-22T00:00:00Z",
            },
        })
        self.write_state({"signals": {auto["content_id"]: auto}, "runs": []})
        with patch.object(MODULE, "publish_approved_educational_reel", side_effect=lambda record: dict(record, status="published")) as adapter:
            result = MODULE.publish_ids(auto["content_id"], self.state_path)
        self.assertEqual(result, 0)
        adapter.assert_called_once()
        saved = self.read_state()["signals"][auto["content_id"]]
        self.assertEqual(saved["status"], "published")
        self.assertEqual(saved["approval_mode"], "automated_policy")

    def test_pending_or_unapproved_record_is_blocked_before_adapter(self):
        state = self.read_state()
        state["signals"][self.record["content_id"]]["approval_status"] = "pending"
        self.write_state(state)
        with patch.object(MODULE, "publish_approved_educational_reel") as adapter:
            result = MODULE.publish_ids(self.record["content_id"], self.state_path)
        self.assertEqual(result, 1)
        adapter.assert_not_called()
        saved = self.read_state()["signals"][self.record["content_id"]]
        self.assertEqual(saved["last_publish_error"], "RuntimeError")
        self.assertEqual(saved["approval_status"], "pending")

    def test_failure_is_persisted_and_other_approved_ids_are_still_attempted(self):
        second = dict(self.record, content_id="draft_second_20261022")
        state = {"signals": {
            self.record["content_id"]: dict(self.record),
            second["content_id"]: second,
        }, "runs": []}
        self.write_state(state)

        def publish(record):
            if record["content_id"] == self.record["content_id"]:
                record["publishing"] = {"instagram": {"status": "published_to_instagram"}}
                raise RuntimeError("simulated failure")
            record["status"] = "published"
            return record

        with patch.object(MODULE, "publish_approved_educational_reel", side_effect=publish) as adapter:
            result = MODULE.publish_ids(
                f'{self.record["content_id"]},{second["content_id"]}', self.state_path
            )
        self.assertEqual(result, 1)
        self.assertEqual(adapter.call_count, 2)
        saved = self.read_state()["signals"]
        self.assertEqual(saved[self.record["content_id"]]["last_publish_error"], "RuntimeError")
        self.assertIn("publishing", saved[self.record["content_id"]])
        self.assertEqual(saved[second["content_id"]]["status"], "published")

    def test_duplicate_ids_in_one_dispatch_are_deduplicated(self):
        with patch.object(MODULE, "publish_approved_educational_reel", side_effect=lambda record: record) as adapter:
            result = MODULE.publish_ids(
                f'{self.record["content_id"]},{self.record["content_id"]}', self.state_path
            )
        self.assertEqual(result, 0)
        adapter.assert_called_once()


    def test_script_entrypoint_can_import_src_from_scripts_directory(self):
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
