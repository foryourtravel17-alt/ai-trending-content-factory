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

    def write_rendered_draft(self, content_id="draft_sample_20261021", **overrides):
        record = {
            "content_id": content_id,
            "status": "draft_only",
            "approval": {"required": True, "status": "draft_only"},
            "fact_check": {"status": "needs_human_review"},
        }
        record.update(overrides)
        source = self.output / f"{content_id}.json"
        source.write_text(json.dumps(record), encoding="utf-8")
        return source

    def test_registers_actual_renderer_filename_as_pending_without_publishing(self):
        # reel_generator.build() writes output/<content_id>.json, where the ID
        # starts with draft_; it does not write content_draft_<id>.json.
        source = self.write_rendered_draft()
        MODULE.main()

        record = json.loads(source.read_text(encoding="utf-8"))
        queue = json.loads(MODULE.QUEUE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(record["status"], "draft_only")
        self.assertEqual(record["approval"]["status"], "pending")
        self.assertEqual(record["fact_check"]["status"], "needs_human_review")
        self.assertEqual(queue["items"][0]["content_id"], "draft_sample_20261021")
        self.assertEqual(queue["items"][0]["status"], "pending")

    def test_does_not_overwrite_existing_approval_decision(self):
        source = self.write_rendered_draft(
            status="approved_for_publishing",
            approval={"required": True, "status": "approved"},
        )
        with self.assertRaises(SystemExit):
            MODULE.main()
        record = json.loads(source.read_text(encoding="utf-8"))
        self.assertEqual(record["status"], "approved_for_publishing")
        self.assertEqual(record["approval"]["status"], "approved")

    def test_does_not_add_duplicate_queue_entry(self):
        source = self.write_rendered_draft()
        MODULE.QUEUE_PATH.write_text(json.dumps({
            "items": [{"content_id": "draft_sample_20261021", "status": "pending", "processed": False}],
            "telegram_sent": [],
        }), encoding="utf-8")
        MODULE.main()
        queue = json.loads(MODULE.QUEUE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(len(queue["items"]), 1)
        self.assertEqual(json.loads(source.read_text(encoding="utf-8"))["approval"]["status"], "draft_only")


if __name__ == "__main__":
    unittest.main()
