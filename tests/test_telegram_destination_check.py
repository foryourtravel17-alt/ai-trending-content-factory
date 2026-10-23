import unittest
from unittest.mock import patch

from scripts.telegram_destination_check import check_destination, describe_chat_id


class TelegramDestinationCheckTests(unittest.TestCase):
    def test_describe_chat_id_accepts_channel_style_and_hides_value(self):
        diagnostic = describe_chat_id("-1004254873594")
        self.assertIn("channel_or_supergroup_style=True", diagnostic)
        self.assertIn("problems=none", diagnostic)
        self.assertNotIn("4254873594", diagnostic)

    def test_describe_chat_id_flags_unicode_minus_quotes_spaces_and_links(self):
        self.assertIn("contains_non_ascii_char", describe_chat_id("\u22121004254873594"))
        self.assertIn("contains_quote", describe_chat_id('"-1004254873594"'))
        self.assertIn("contains_inner_space", describe_chat_id("-100 4254873594"))
        self.assertIn("not_a_plain_signed_integer", describe_chat_id("t.me/c/4254873594/3"))

    def test_describe_chat_id_flags_missing_minus_prefix(self):
        diagnostic = describe_chat_id("4254873594")
        self.assertIn("leading_minus=False", diagnostic)
        self.assertIn("channel_or_supergroup_style=False", diagnostic)

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

    def test_chat_not_found_still_prints_bot_identity_without_secrets(self):
        def fake_api(token, method, params=None):
            if method == "getMe":
                return {"result": {"id": 123, "username": "actual_bot_name"}}
            if method == "getChat":
                raise RuntimeError("Telegram getChat request failed (HTTP 400): Bad Request: chat not found")
            raise AssertionError(f"Unexpected Telegram method: {method}")

        with patch("scripts.telegram_destination_check.telegram_api", side_effect=fake_api):
            with patch("builtins.print") as output:
                self.assertEqual(check_destination("redacted-token", "-100123"), 1)

        rendered = "\n".join(str(call.args[0]) for call in output.call_args_list if call.args)
        self.assertIn("@actual_bot_name", rendered)
        self.assertNotIn("redacted-token", rendered)
        self.assertNotIn("-100123", rendered)
        self.assertNotIn("sendMessage", rendered)

    def test_api_error_from_getme_fails_safely(self):
        with patch("scripts.telegram_destination_check.telegram_api", side_effect=RuntimeError("invalid token")):
            with patch("builtins.print"):
                self.assertEqual(check_destination("redacted-token", "-100123"), 1)


if __name__ == "__main__":
    unittest.main()
