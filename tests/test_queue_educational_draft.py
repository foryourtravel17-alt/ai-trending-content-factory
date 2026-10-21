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
        self.output = Path(self.temp.name)
        MODULE.OUTPUT = self.output
        MODULE.QUEUE_PATH = self.output / "approval_queue.json"

    def tearDown(self):
        self.temp.cleanup()

    def write_draft(self, content_id="draft_sample_20261021", status="draft_only", approval_status="draft_only"):
        path = self.output / f"{content_id}.json"
        path.write_text(json.dumps({
            "content_id": content_id,
            "created_at": "2026-10-21T05:11:51+00:00",
            "status": status,
            "approval": {"required": True, "status": approval_status},
            "fact_check": {"status": "needs_human_review", "notes": []},
        }), encoding="utf-8")
        return path

    def test_registers_real_renderer_filename_as_pending(self):
        source = self.write_draft()
        MODULE.main()
        record = json.loads(source.read_text(encoding="utf-8"))
        queue = json.loads(MODULE.QUEUE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(record["status"], "draft_only")
        self.assertEqual(record["approval"]["status"], "pending")
        self.assertEqual(record["fact_check"]["status"], "needs_human_review")
        self.assertEqual(queue["items"], [{
            "content_id": "draft_sample_20261021",
            "status": "pending",
            "processed": False,
        }])

    def test_refuses_to_reset_existing_approval_decision(self):
        source = self.write_draft(status="approved_for_publishing", approval_status="approved")
        with self.assertRaises(SystemExit):
            MODULE.main()
        record = json.loads(source.read_text(encoding="utf-8"))
        self.assertEqual(record["status"], "approved_for_publishing")
        self.assertEqual(record["approval"]["status"], "approved")
        self.assertFalse(MODULE.QUEUE_PATH.exists())

    def test_does_not_add_duplicate_queue_entry(self):
        source = self.write_draft()
        MODULE.QUEUE_PATH.write_text(json.dumps({
            "items": [{"content_id": "draft_sample_20261021", "status": "pending", "processed": False}],
            "telegram_sent": [],
        }), encoding="utf-8")
        MODULE.main()
        queue = json.loads(MODULE.QUEUE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(len(queue["items"]), 1)
        record = json.loads(source.read_text(encoding="utf-8"))
        self.assertEqual(record["approval"]["status"], "draft_only")


if __name__ == "__main__":
    unittest.main()
