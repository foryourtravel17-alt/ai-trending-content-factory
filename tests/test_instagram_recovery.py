import unittest
from datetime import datetime, timezone

from scripts.retry_approved_instagram import find_candidate, record_is_eligible, reserve_retry


class InstagramRecoverySelectionTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 22, 3, 0, tzinfo=timezone.utc)

    def approved_failure(self, *, approved_at="2026-10-22T02:49:20Z",
                         as_of="2026-10-22T02:00:00Z", error="Meta API HTTP 400; code=190"):
        return {
            "status": "publish_failed",
            "approval_status": "approved",
            "approved_at": approved_at,
            "signal": {"signal_id": "eurusd-x-2026102202-long", "symbol": "EURUSD=X", "as_of": as_of},
            "publishing": {
                "telegram": {"status": "published", "message_id": 83},
                "instagram": {"status": "failed", "error": error},
            },
        }

    def test_selects_only_fresh_human_approved_instagram_auth_failure(self):
        candidate = self.approved_failure()
        state = {"signals": {
            "approved-failure": candidate,
            "rejected": {
                **self.approved_failure(),
                "approval_status": "rejected",
            },
            "non-auth-failure": self.approved_failure(error="image upload timeout"),
            "stale": self.approved_failure(approved_at="2026-10-20T00:00:00Z"),
        }}
        self.assertEqual(find_candidate(state, self.now), "approved-failure")

    def test_reserved_signal_cannot_be_selected_or_reserved_twice(self):
        record = self.approved_failure()
        state = {"signals": {"approved-failure": record}}
        self.assertTrue(reserve_retry(state, "approved-failure", self.now))
        self.assertEqual(record["publishing"]["instagram"]["auto_recovery_attempted_at"],
                         self.now.isoformat())
        self.assertIsNone(find_candidate(state, self.now))
        self.assertFalse(reserve_retry(state, "approved-failure", self.now))

    def test_old_market_signal_is_not_recovered_even_when_approved(self):
        record = self.approved_failure(as_of="2026-10-21T00:00:00Z")
        self.assertFalse(record_is_eligible(record, self.now))


if __name__ == "__main__":
    unittest.main()
