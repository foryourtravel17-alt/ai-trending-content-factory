import os
import unittest
from unittest.mock import patch

from scripts.premium_telegram import DISCLAIMER, LESSONS, build_post, main


class PremiumTelegramTests(unittest.TestCase):
    def test_build_post_contains_brand_lesson_and_disclaimer(self):
        post = build_post(0)
        self.assertIn("Bullseye Theory Premium", post)
        self.assertIn(LESSONS[0]["title"], post)
        self.assertIn(DISCLAIMER, post)

    def test_lesson_index_cycles(self):
        self.assertIn(LESSONS[0]["title"], build_post(len(LESSONS)))

    def test_dry_run_does_not_send(self):
        with patch.dict(os.environ, {"DRY_RUN": "true", "PREMIUM_TELEGRAM_AUTOPUBLISH": "true"}, clear=False):
            with patch("scripts.premium_telegram.telegram_request") as send:
                self.assertEqual(main(), 0)
                send.assert_not_called()

    def test_publish_gate_blocks_when_autopublish_disabled(self):
        with patch.dict(os.environ, {"DRY_RUN": "false", "PREMIUM_TELEGRAM_AUTOPUBLISH": "false"}, clear=False):
            with patch("scripts.premium_telegram.telegram_request") as send:
                self.assertEqual(main(), 3)
                send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
