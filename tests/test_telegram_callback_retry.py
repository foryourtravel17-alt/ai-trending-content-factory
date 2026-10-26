import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class PollerRetryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "output").mkdir()
        (self.root / "data").mkdir()
        self.cwd = os.getcwd()
        self.env = {k: os.environ.get(k) for k in (
            "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "TELEGRAM_APPROVER_USER_IDS",
            "POLL_SECONDS", "GITHUB_OUTPUT"
        )}
        os.chdir(self.root)
        os.environ.update({
            "TELEGRAM_BOT_TOKEN": "test-token",
            "TELEGRAM_CHAT_ID": "111",
            "TELEGRAM_APPROVER_USER_IDS": "111",
            "POLL_SECONDS": "5",
            "GITHUB_OUTPUT": str(self.root / "gh_output.txt"),
        })
        (self.root / "gh_output.txt").write_text("", encoding="utf-8")
        self.module = importlib.import_module("src.telegram_process")
        importlib.reload(self.module)

    def tearDown(self):
        os.chdir(self.cwd)
        for key, value in self.env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmp.cleanup()

    def seed(self, metadata=True, record=True):
        signals = {}
        if record:
            signals["draft_x_1"] = {
                "content_id": "draft_x_1", "content_type": "educational_reel",
                "status": "pending_approval", "approval_status": "pending",
                "human_approval_required": True,
                "approval": {"required": True, "status": "pending", "mode": "human_review"},
                "fact_check": {"status": "needs_human_review"},
            }
        (self.root / "data" / "state.json").write_text(
            json.dumps({"signals": signals, "runs": []}), encoding="utf-8")
        (self.root / "output" / "telegram_state.json").write_text(
            json.dumps({"update_offset": 100}), encoding="utf-8")
        (self.root / "output" / "approval_queue.json").write_text(
            json.dumps({"items": [], "telegram_sent": []}), encoding="utf-8")
        if metadata:
            (self.root / "output" / "draft_x_1.json").write_text(
                json.dumps({"content_id": "draft_x_1", "status": "pending_approval",
                            "approval": {"required": True, "status": "pending"},
                            "fact_check": {"status": "needs_human_review"}}), encoding="utf-8")

    def run_update(self):
        update = {"update_id": 500, "callback_query": {
            "id": "cb-1", "data": "market_approve:draft_x_1",
            "from": {"id": 111, "username": "bullseyetheory"},
            "message": {"chat": {"id": 111}, "message_id": 354}}}
        calls = []
        served = {"done": False}
        def fake_api(method, data=None, timeout=30):
            calls.append((method, data or {}))
            if method == "getUpdates":
                if served["done"]:
                    return []
                served["done"] = True
                return [update]
            return {"ok": True}
        self.module.api = fake_api
        self.module.main()
        return calls

    def offset(self):
        return json.loads((self.root / "output" / "telegram_state.json").read_text())["update_offset"]

    def test_missing_metadata_keeps_callback_retryable(self):
        self.seed(metadata=False)
        methods = [method for method, _ in self.run_update()]
        self.assertIn("answerCallbackQuery", methods)
        self.assertNotIn("editMessageReplyMarkup", methods)
        self.assertEqual(self.offset(), 500)
        state = json.loads((self.root / "data" / "state.json").read_text())
        self.assertEqual(state["signals"]["draft_x_1"]["approval_status"], "pending")
        poller_state = json.loads((self.root / "output" / "telegram_state.json").read_text())
        self.assertEqual(poller_state["callback_retries"]["500"], 1)

    def test_missing_record_keeps_callback_retryable(self):
        self.seed(metadata=True, record=False)
        methods = [method for method, _ in self.run_update()]
        self.assertNotIn("editMessageReplyMarkup", methods)
        self.assertEqual(self.offset(), 500)

    def test_successful_approval_commits_and_advances(self):
        self.seed(metadata=True)
        methods = [method for method, _ in self.run_update()]
        self.assertIn("editMessageReplyMarkup", methods)
        market = json.loads((self.root / "data" / "state.json").read_text())
        self.assertEqual(market["signals"]["draft_x_1"]["approval_status"], "approved")
        self.assertEqual(market["signals"]["draft_x_1"]["fact_check"]["status"], "approved")
        self.assertEqual(self.offset(), 501)
        self.assertIn("educational_approved_ids=draft_x_1",
                      (self.root / "gh_output.txt").read_text())
        metadata = json.loads((self.root / "output" / "draft_x_1.json").read_text())
        self.assertEqual(metadata["status"], "approved_for_publishing")

    def test_workflow_uses_autostash_and_retry_test_trigger(self):
        text = (ROOT / ".github" / "workflows" / "market_approval_poll.yml").read_text()
        self.assertIn("git pull --rebase --autostash origin main", text)
        self.assertIn("tests/test_telegram_callback_retry.py", text)
        self.assertIn("github.event_name == 'schedule' && '60' || '240'", text)


if __name__ == "__main__":
    unittest.main()
