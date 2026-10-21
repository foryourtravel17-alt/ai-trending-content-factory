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

    def test_registers_draft_as_pending_without_publishing(self):
        source = self.output / "content_draft_sample.json"
        source.write_text(json.dumps({
            "content_id": "draft_sample_20261021",
            "status": "draft_only",
            "approval": {"required": True, "status": "draft_only"},
            "fact_check": {"status": "needs_human_review"},
        }), encoding="utf-8")

        MODULE.main()

        record = json.loads((self.output / "draft_sample_20261021.json").read_text(encoding="utf-8"))
        queue = json.loads(MODULE.QUEUE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(record["status"], "draft_only")
        self.assertEqual(record["approval"]["status"], "pending")
        self.assertEqual(record["fact_check"]["status"], "needs_human_review")
        self.assertEqual(queue["items"][0]["content_id"], "draft_sample_20261021")
        self.assertEqual(queue["items"][0]["status"], "pending")

    def test_existing_record_is_not_overwritten(self):
        source = self.output / "content_draft_sample.json"
        source.write_text(json.dumps({"content_id": "draft_sample"}), encoding="utf-8")
        target = self.output / "draft_sample.json"
        target.write_text(json.dumps({"content_id": "draft_sample", "status": "approved_for_publishing"}), encoding="utf-8")

        MODULE.main()

        self.assertEqual(json.loads(target.read_text(encoding="utf-8"))["status"], "approved_for_publishing")


if __name__ == "__main__":
    unittest.main()
