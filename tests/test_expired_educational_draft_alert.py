import unittest
from datetime import datetime, timezone
from scripts.alert_expired_educational_drafts import collect_expired_drafts, format_alert

class ExpiredEducationalDraftAlertTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 24, 12, 0, tzinfo=timezone.utc)

    def test_collects_recent_expired_reel_once(self):
        state = {"signals": {"draft_one": {
            "content_type": "educational_reel", "status": "expired",
            "expired_at": "2026-10-24T11:00:00+00:00",
            "signal": {"title": "Market Structure Basics"},
        }}}
        found = collect_expired_drafts(state, self.now)
        self.assertEqual([item["content_id"] for item in found], ["draft_one"])
        state["expired_draft_alerted_ids"] = ["draft_one"]
        self.assertEqual(collect_expired_drafts(state, self.now), [])

    def test_ignores_old_future_and_non_reel_records(self):
        state = {"signals": {
            "old": {"content_type": "educational_reel", "status": "expired", "expired_at": "2026-10-22T10:00:00+00:00"},
            "future": {"content_type": "educational_reel", "status": "expired", "expired_at": "2026-10-24T13:00:00+00:00"},
            "market": {"content_type": "market_signal", "status": "expired", "expired_at": "2026-10-24T11:00:00+00:00"},
        }}
        self.assertEqual(collect_expired_drafts(state, self.now), [])

    def test_alert_contains_titles_and_does_not_claim_publication(self):
        message = format_alert([{"title": "Risk Management", "content_id": "draft_risk"}])
        self.assertIn("Risk Management", message)
        self.assertIn("draft_risk", message)
        self.assertIn("No post was made", message)

if __name__ == "__main__":
    unittest.main()
