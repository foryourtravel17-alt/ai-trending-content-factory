import json
import unittest
from unittest.mock import patch

from scripts.telegram_destination_check import check_destination


class TelegramDestinationCheckTests(unittest.TestCase):
    def test_channel_admin_with_post_permission_passes_without_sending(self):
        responses = {
            "getMe": {"result": {"id": 123, "username": "bullseye_test_bot"}},
            "getChat": {"result": {"id": -100123, "type": "channel", "title": "Bullseye Theory Premium"}},
            "getChatMember": {"result": {"status": "administrator", "can_post_messages": True}},
        }
        calls = []

        def fake_api(token, method, params=None):
            calls.append(method)
            return responses[method]

        with patch("scripts.telegram_destination_check.telegram_api", side_effect=fake_api):
            with patch("builtins.print"):
                self.assertEqual(check_destination("redacted-token", "-100123"), 0)

        self.assertEqual(calls, ["getMe", "getChat", "getChatMember"])
        self.assertNotIn("sendMessage", calls)

    def test_channel_admin_without_post_permission_fails(self):
        responses = {
            "getMe": {"result": {"id": 123, "username": "bullseye_test_bot"}},
            "getChat": {"result": {"id": -100123, "type": "channel", "title": "Premium"}},
            "getChatMember": {"result": {"status": "administrator", "can_post_messages": False}},
        }

        with patch("scripts.telegram_destination_check.telegram_api", side_effect=lambda token, method, params=None: responses[method]):
            with patch("builtins.print"):
                self.assertEqual(check_destination("redacted-token", "-100123"), 1)

    def test_supergroup_member_requires_send_permission(self):
        responses = {
            "getMe": {"result": {"id": 123, "username": "bullseye_test_bot"}},
            "getChat": {"result": {"id": -100123, "type": "supergroup", "title": "Premium", "permissions": {"can_send_messages": True}}},
            "getChatMember": {"result": {"status": "member"}},
        }

        with patch("scripts.telegram_destination_check.telegram_api", side_effect=lambda token, method, params=None: responses[method]):
            with patch("builtins.print"):
                self.assertEqual(check_destination("redacted-token", "-100123"), 0)

    def test_api_error_fails_safely(self):
        with patch("scripts.telegram_destination_check.telegram_api", side_effect=RuntimeError("chat not found")):
            with patch("builtins.print"):
                self.assertEqual(check_destination("redacted-token", "-100123"), 1)


if __name__ == "__main__":
    unittest.main()
