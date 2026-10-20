import unittest
from scripts.preflight_publish_guard import should_publish

class PublishGuardTests(unittest.TestCase):
    def approved(self):
        return {
            "approval_status": "approved",
            "status": "partial",
            "signal": {"signal_id": "test", "as_of": "2026-10-20T12:00:00Z"},
            "publishing": {},
        }

    def test_approved_unpublished_allows(self):
        self.assertTrue(should_publish(self.approved())[0])

    def test_fully_published_blocks(self):
        record = self.approved()
        record["publishing"] = {
            "telegram": {"status": "published"},
            "instagram": {"status": "published"},
        }
        allowed, reason = should_publish(record)
        self.assertFalse(allowed)
        self.assertIn("fully published", reason)

    def test_partial_publish_allows_retry(self):
        record = self.approved()
        record["publishing"] = {
            "telegram": {"status": "published"},
            "instagram": {"status": "failed"},
        }
        self.assertTrue(should_publish(record)[0])

    def test_missing_record_blocks(self):
        self.assertFalse(should_publish({})[0])

    def test_rejected_signal_blocks(self):
        record = self.approved()
        record["approval_status"] = "rejected"
        self.assertFalse(should_publish(record)[0])

    def test_incomplete_signal_blocks(self):
        record = self.approved()
        record["signal"] = {}
        self.assertFalse(should_publish(record)[0])

if __name__ == "__main__":
    unittest.main()
