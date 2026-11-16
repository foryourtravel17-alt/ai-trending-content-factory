import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents import publisher


class TelegramOnlyMarketPublisherTests(unittest.TestCase):
    def card(self, folder):
        path = Path(folder) / "card.png"
        path.write_bytes(b"\x89PNG\r\n\x1a\n")
        return path

    def test_unapproved_market_card_is_sent_to_private_telegram_for_approval(self):
        with tempfile.TemporaryDirectory() as folder:
            record = {"publishing": {}}
            env = {"TELEGRAM_BOT_TOKEN": "bot-token", "TELEGRAM_CHAT_ID": "123"}
            with patch.dict("os.environ", env, clear=True), patch.object(
                publisher, "_telegram", return_value={"message_id": 42}
            ) as send:
                result = publisher.publish(
                    {"signal_id": "market-1"},
                    {"telegram_html": "<b>draft</b>"},
                    self.card(folder),
                    record,
                )
            self.assertEqual(result["status"], "pending_approval")
            self.assertEqual(result["publishing"]["telegram_dm"]["status"], "sent")
            self.assertEqual(send.call_args.args[0], "sendPhoto")
            keyboard = send.call_args.args[1]["reply_markup"]
            self.assertIn("market_approve:market-1", keyboard)
            self.assertIn("market_reject:market-1", keyboard)

    def test_approved_market_card_publishes_to_telegram_channel_only(self):
        with tempfile.TemporaryDirectory() as folder:
            record = {"approval_status": "approved", "publishing": {"telegram_dm": {"status": "sent"}}}
            with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "bot-token"}, clear=True), patch.object(
                publisher, "_telegram", return_value={"message_id": 99}
            ) as send:
                result = publisher.publish(
                    {"signal_id": "market-2"},
                    {"telegram_html": "<b>approved</b>"},
                    self.card(folder),
                    record,
                )
            self.assertEqual(result["status"], "published")
            self.assertEqual(result["publishing"]["telegram"]["status"], "published")
            self.assertEqual(result["publishing"]["telegram"]["message_id"], 99)
            self.assertEqual(send.call_args.args[0], "sendPhoto")
            self.assertEqual(send.call_args.args[1]["chat_id"], "@bullseye_theory")

    def test_rejected_record_never_sends_to_channel(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(publisher, "_telegram") as send:
            result = publisher.publish(
                {"signal_id": "market-rejected"},
                {"telegram_html": "not for publish"},
                self.card(folder),
                {"approval_status": "rejected", "publishing": {}},
            )
        self.assertEqual(result["status"], "rejected")
        send.assert_not_called()

    def test_ambiguous_telegram_send_is_not_automatically_retried(self):
        with tempfile.TemporaryDirectory() as folder:
            record = {"approval_status": "approved", "publishing": {"telegram": {"status": "unknown"}}}
            with patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "bot-token"}, clear=True), patch.object(
                publisher, "_telegram"
            ) as send:
                with self.assertRaises(publisher.TelegramDeliveryUnknown):
                    publisher.publish({"signal_id": "market-3"}, {"telegram_html": "x"}, self.card(folder), record)
            send.assert_not_called()

    def test_dry_run_does_not_call_telegram(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(publisher, "_telegram") as send:
            result = publisher.publish(
                {"signal_id": "market-dry"},
                {"telegram_html": "dry"},
                self.card(folder),
                {},
                dry_run=True,
            )
        self.assertEqual(result["status"], "generated")
        send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
