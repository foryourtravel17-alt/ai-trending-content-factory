import unittest
from datetime import datetime, timedelta, timezone

from scripts.daily_automation_report import build_report


class DailyAutomationReportTests(unittest.TestCase):
    def test_report_counts_market_and_reel_records_from_shared_state(self):
        now = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)
        state = {
            "signals": {
                "market-published": {
                    "created_at": (now - timedelta(hours=2)).isoformat(),
                    "status": "published",
                    "approval_status": "approved",
                    "signal": {"title": "Nifty market setup"},
                    "publishing": {"telegram": {"status": "published"}},
                },
                "reel-pending": {
                    "content_type": "educational_reel",
                    "created_at": (now - timedelta(hours=1)).isoformat(),
                    "status": "pending_approval",
                    "approval_status": "pending",
                    "signal": {"title": "Risk management"},
                    "publishing": {"telegram": {"status": "pending"}},
                },
                "reel-published": {
                    "content_type": "educational_reel",
                    "created_at": (now - timedelta(hours=3)).isoformat(),
                    "status": "published",
                    "approval_status": "approved",
                    "signal": {"title": "Trading journal"},
                    "publishing": {"telegram": {"status": "published"}},
                },
                "old-record": {
                    "created_at": (now - timedelta(days=2)).isoformat(),
                    "status": "published",
                    "approval_status": "approved",
                    "signal": {"title": "Old setup"},
                    "publishing": {"telegram": {"status": "published"}},
                },
            }
        }
        report = build_report(state, now)
        self.assertIn("Last 24h generated: 3", report)
        self.assertIn("Approved: 2", report)
        self.assertIn("Awaiting approval: 1", report)
        self.assertIn("Educational Reels: 2", report)
        self.assertIn("Telegram published: 2", report)
        self.assertIn("Market cards: 09:15, 11:15, 13:30, 15:45 IST", report)
        self.assertIn("Educational Reels: 10:17, 14:17, 18:17 IST", report)
        self.assertNotIn("Old setup", report)

    def test_report_handles_missing_or_invalid_timestamps(self):
        now = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)
        state = {"signals": {
            "missing-time": {"status": "published", "signal": {"title": "No timestamp"}},
            "bad-time": {"created_at": "not-a-date", "status": "published"},
        }}
        report = build_report(state, now)
        self.assertIn("Last 24h generated: 0", report)
        self.assertIn("Telegram published: 0", report)


if __name__ == "__main__":
    unittest.main()
