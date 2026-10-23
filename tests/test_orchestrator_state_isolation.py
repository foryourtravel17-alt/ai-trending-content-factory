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
