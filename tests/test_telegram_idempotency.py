import os
import unittest

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
from src.telegram_process import apply_market_decision

class TelegramIdempotencyTests(unittest.TestCase):
    def test_duplicate_approval_is_noop(self):
        record = {}
        self.assertTrue(apply_market_decision(record, "market_approve", "t1"))
        before = dict(record)
        self.assertFalse(apply_market_decision(record, "market_approve", "t2"))
        self.assertEqual(record, before)

    def test_rejection_after_approval_is_noop(self):
        record = {}
        apply_market_decision(record, "market_approve", "t1")
        self.assertFalse(apply_market_decision(record, "market_reject", "t2"))
        self.assertEqual(record["approval_status"], "approved")
        self.assertNotIn("rejected_at", record)

    def test_unknown_action_is_noop(self):
        record = {}
        self.assertFalse(apply_market_decision(record, "unknown", "t1"))
        self.assertEqual(record, {})

if __name__ == "__main__":
    unittest.main()
