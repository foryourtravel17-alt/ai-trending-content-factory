import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents.publisher import publish, TelegramDeliveryUnknown


class TelegramPublisherTests(unittest.TestCase):
    def card(self, folder):
        path = Path(folder) / "card.png"
        path.write_bytes(b"\x89PNG\r\n\x1a\n")
        return path

    def test_dry_run_never_calls_telegram(self):
        with tempfile.TemporaryDirectory() as folder, patch("agents.publisher._telegram") as send:
            record = publish(
                {"signal_id": "dry-1"},
                {"telegram_html": "<b>dry</b>"},
                self.card(folder),
                {},
                dry_run=True,
            )
        self.assertEqual(record["status"], "generated")
        send.assert_not_called()

    def test_market_card_requests_owner_approval_before_public_channel_post(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "test-bot", "TELEGRAM_CHAT_ID": "123"}, clear=True):
                with patch("agents.publisher._telegram", return_value={"message_id": 10}) as send:
                    record = publish(
                        {"signal_id": "market-1"},
                        {"telegram_html": "<b>draft</b>"},
                        self.card(folder),
                        {"publishing": {}},
                    )
            self.assertEqual(record["status"], "pending_approval")
            self.assertEqual(record["publishing"]["telegram_dm"]["status"], "sent")
            self.assertEqual(send.call_count, 1)
            self.assertEqual(send.call_args.args[0], "sendPhoto")
            self.assertIn("market_approve:market-1", send.call_args.args[1]["reply_markup"])

    def test_approved_market_card_is_sent_to_public_telegram(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "test-bot"}, clear=True):
                with patch("agents.publisher._telegram", return_value={"message_id": 25}) as send:
                    record = publish(
                        {"signal_id": "market-2"},
                        {"telegram_html": "<b>approved</b>"},
                        self.card(folder),
                        {
                            "approval_status": "approved",
                            "publishing": {"telegram_dm": {"status": "sent"}},
                        },
                    )
            self.assertEqual(record["status"], "published")
            self.assertEqual(record["publishing"]["telegram"]["message_id"], 25)
            self.assertEqual(send.call_args.args[1]["chat_id"], "@bullseye_theory")

    def test_rejected_market_card_is_never_sent(self):
        with tempfile.TemporaryDirectory() as folder, patch("agents.publisher._telegram") as send:
            record = publish(
                {"signal_id": "market-3"}, {"telegram_html": "no"}, self.card(folder),
                {"approval_status": "rejected", "publishing": {}},
            )
        self.assertEqual(record["status"], "rejected")
        send.assert_not_called()

    def test_ambiguous_telegram_state_blocks_duplicate_send(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(
            "os.environ", {"TELEGRAM_BOT_TOKEN": "test-bot"}, clear=True
        ), patch("agents.publisher._telegram") as send:
            with self.assertRaises(TelegramDeliveryUnknown):
                publish(
                    {"signal_id": "market-4"}, {"telegram_html": "x"}, self.card(folder),
                    {"approval_status": "approved", "publishing": {"telegram": {"status": "unknown"}}},
                )
        send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
