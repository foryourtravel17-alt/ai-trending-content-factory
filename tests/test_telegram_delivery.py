import unittest
from unittest.mock import patch

from src.telegram_delivery import (
    TelegramDeliveryUnknown,
    api_request,
    send_once,
)


class TelegramDeliveryTests(unittest.TestCase):
    def test_api_request_classifies_read_timeout_as_unknown_delivery(self):
        with patch("src.telegram_delivery.urllib.request.urlopen", side_effect=TimeoutError("read timed out")):
            with self.assertRaises(TelegramDeliveryUnknown):
                api_request(
                    "sendMessage",
                    {"chat_id": "test-chat", "text": "test"},
                    base_url="https://api.telegram.org/bottest-token",
                    timeout=30,
                )

    def test_timeout_persists_unknown_state_and_blocks_automatic_resend(self):
        record = {"publishing": {}}
        persisted = []
        attempts = []

        def persist():
            persisted.append(record["publishing"]["telegram_dm"].copy())

        def timed_out_send():
            attempts.append("send")
            raise TelegramDeliveryUnknown("read timeout")

        with self.assertRaises(TelegramDeliveryUnknown):
            send_once(record, timed_out_send, persist)

        self.assertEqual([item["status"] for item in persisted], ["sending", "unknown"])
        self.assertEqual(record["publishing"]["telegram_dm"]["status"], "unknown")

        result = send_once(record, timed_out_send, persist)
        self.assertIsNone(result)
        self.assertEqual(attempts, ["send"], "unknown outcome must never be resent automatically")

    def test_success_persists_message_id_and_marks_sent(self):
        record = {"publishing": {}}
        persisted = []
        result = send_once(
            record,
            lambda: {"message_id": 12345},
            lambda: persisted.append(record["publishing"]["telegram_dm"].copy()),
        )
        self.assertEqual(result["message_id"], 12345)
        self.assertEqual(record["publishing"]["telegram_dm"]["status"], "sent")
        self.assertEqual(record["publishing"]["telegram_dm"]["message_id"], 12345)
        self.assertEqual([item["status"] for item in persisted], ["sending", "sent"])

    def test_missing_telegram_message_id_is_ambiguous_and_not_retried(self):
        record = {"publishing": {}}
        attempts = []

        def send_without_id():
            attempts.append(1)
            return {"ok": True}

        with self.assertRaises(TelegramDeliveryUnknown):
            send_once(record, send_without_id, lambda: None)
        self.assertEqual(record["publishing"]["telegram_dm"]["status"], "unknown")
        self.assertIsNone(send_once(record, send_without_id, lambda: None))
        self.assertEqual(attempts, [1])


if __name__ == "__main__":
    unittest.main()
