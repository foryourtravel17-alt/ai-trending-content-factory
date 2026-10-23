import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "queue_educational_draft.py"
SPEC = importlib.util.spec_from_file_location("queue_educational_draft", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class QueueEducationalDraftTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        MODULE.OUTPUT = self.root / "output"
        MODULE.OUTPUT.mkdir()
        MODULE.QUEUE_PATH = MODULE.OUTPUT / "approval_queue.json"
        MODULE.STATE_PATH = self.root / "data" / "state.json"

    def tearDown(self):
        self.temp.cleanup()

    def write_draft(self, content_id="draft_sample_20261022", status="draft_only", approval_status="draft_only"):
        path = MODULE.OUTPUT / f"{content_id}.json"
        path.write_text(json.dumps({
            "content_id": content_id,
            "created_at": "2026-10-22T02:00:00+00:00",
            "status": status,
            "approval": {"required": True, "status": approval_status},
            "fact_check": {"status": "needs_human_review", "notes": []},
            "safety_check": {"passed": True, "blocked_phrases": []},
            "topic": {"title": "Trading journal"},
            "social": {"caption": "Record the decision, not just profit.", "hashtags": ["#BullseyeTheory"]},
            "video": f"output/media/{content_id}.mp4",
        }), encoding="utf-8")
        return path

    def test_registers_real_renderer_filename_in_shared_market_state(self):
        source = self.write_draft()
        MODULE.main()
        content = json.loads(source.read_text(encoding="utf-8"))
        queue = json.loads(MODULE.QUEUE_PATH.read_text(encoding="utf-8"))
        state = json.loads(MODULE.STATE_PATH.read_text(encoding="utf-8"))
        record = state["signals"]["draft_sample_20261022"]
        self.assertEqual(content["status"], "pending_approval")
        self.assertEqual(content["approval"]["status"], "pending")
        self.assertEqual(content["approval"]["mode"], "human_review")
        self.assertTrue(content["approval"]["required"])
        self.assertEqual(queue["items"][0]["content_id"], "draft_sample_20261022")
        self.assertEqual(record["content_type"], "educational_reel")
        self.assertEqual(record["approval_status"], "pending")
        self.assertEqual(record["approval_mode"], "human_review")
        self.assertTrue(record["human_approval_required"])
        self.assertEqual(record["status"], "pending_approval")
        self.assertEqual(record["signal"]["signal_id"], "draft_sample_20261022")
        self.assertEqual(record["fact_check"]["status"], "needs_human_review")

    def test_blocks_registration_when_automated_safety_screen_fails(self):
        source = self.write_draft()
        record = json.loads(source.read_text(encoding="utf-8"))
        record["safety_check"]["passed"] = False
        source.write_text(json.dumps(record), encoding="utf-8")
        with self.assertRaises(SystemExit):
            MODULE.main()
        self.assertFalse(MODULE.STATE_PATH.exists())
        self.assertFalse(MODULE.QUEUE_PATH.exists())

    def test_refuses_to_reset_existing_approval_decision(self):
        source = self.write_draft(status="approved_for_publishing", approval_status="approved")
        with self.assertRaises(SystemExit):
            MODULE.main()
        content = json.loads(source.read_text(encoding="utf-8"))
        self.assertEqual(content["approval"]["status"], "approved")
        self.assertFalse(MODULE.QUEUE_PATH.exists())
        self.assertFalse(MODULE.STATE_PATH.exists())

    def test_does_not_duplicate_pending_queue_or_reset_state(self):
        self.write_draft()
        state = {
            "signals": {
                "draft_sample_20261022": {
                    "content_type": "educational_reel",
                    "content_id": "draft_sample_20261022",
                    "status": "pending_approval",
                    "approval_status": "pending",
                    "signal": {"signal_id": "draft_sample_20261022", "as_of": "2026-10-22T02:00:00+00:00"},
                }
            },
            "runs": [],
        }
        MODULE.STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        MODULE.STATE_PATH.write_text(json.dumps(state), encoding="utf-8")
        MODULE.QUEUE_PATH.write_text(json.dumps({
            "items": [{"content_id": "draft_sample_20261022", "status": "pending", "processed": False}],
            "telegram_sent": [],
        }), encoding="utf-8")
        MODULE.main()
        queue = json.loads(MODULE.QUEUE_PATH.read_text(encoding="utf-8"))
        state = json.loads(MODULE.STATE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(len(queue["items"]), 1)
        self.assertEqual(queue["items"][0]["status"], "pending_approval")
        self.assertFalse(queue["items"][0]["processed"])
        self.assertEqual(state["signals"]["draft_sample_20261022"]["approval_status"], "pending")
        self.assertEqual(state["signals"]["draft_sample_20261022"]["approval_mode"], "human_review")


if __name__ == "__main__":
    unittest.main()
