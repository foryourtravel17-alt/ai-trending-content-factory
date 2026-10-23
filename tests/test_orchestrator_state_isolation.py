import unittest
from unittest.mock import patch

from src import orchestrator


class MarketPublisherStateIsolationTests(unittest.TestCase):
    def test_educational_reel_record_is_not_sent_to_market_publisher(self):
        reel = {
            "content_type": "educational_reel",
            "status": "publish_failed",
            "card_path": "output/media/draft_example.mp4",
            "publishing": {},
        }
        with patch.object(orchestrator, "publish") as publish:
            errors = orchestrator._publish_prepared({"signals": {"draft_example": reel}})
        self.assertEqual(errors, 0)
        publish.assert_not_called()
        self.assertEqual(reel["status"], "publish_failed")

    def test_missing_market_asset_is_skipped_without_mutating_status_or_counting_error(self):
        record = {
            "status": "generated",
            "signal": {"signal_id": "missing-card", "symbol": "TEST", "as_of": "2026-10-24T00:00:00+00:00"},
            "copy": {"telegram_html": "test", "instagram_caption": "test"},
            "card_path": "output/media/missing-card.mp4",
        }
        with patch.object(orchestrator, "_signal_is_fresh", return_value=True), \
             patch.object(orchestrator, "save_state") as save_state, \
             patch.object(orchestrator, "publish") as publish:
            errors = orchestrator._publish_prepared({"signals": {"missing-card": record}})
        self.assertEqual(errors, 0)
        self.assertEqual(record["status"], "generated")
        publish.assert_not_called()
        save_state.assert_not_called()

    def test_malformed_shared_state_record_is_skipped(self):
        with patch.object(orchestrator, "publish") as publish:
            errors = orchestrator._publish_prepared({"signals": {"bad_record": {
                "status": "generated",
                "card_path": "output/media/not_a_market_card.mp4",
            }}})
        self.assertEqual(errors, 0)
        publish.assert_not_called()


if __name__ == "__main__":
    unittest.main()
