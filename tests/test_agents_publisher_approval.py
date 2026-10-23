import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents import publisher


def _card(tmp):
    path = Path(tmp) / "card.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\n")
    return path


class PublisherApprovalGateTests(unittest.TestCase):
    def test_instagram_prefers_health_checked_system_user_token(self):
        calls = []

        def fake_meta_request(method, url, **kwargs):
            calls.append((method, url, kwargs))
            if method == "GET" and url.endswith("/me/accounts"):
                return {"data": [{"id": "page-1", "name": "Bullseye Theory", "instagram_business_account": {"id": "resolved-ig-user", "username": "bullseye_theory"}}]}
            if method == "POST" and url.endswith("/media"):
                return {"id": "container-123"}
            if method == "GET" and url.endswith("/container-123"):
                return {"status_code": "FINISHED"}
            if method == "POST" and url.endswith("/media_publish"):
                return {"id": "media-456"}
            raise AssertionError(f"Unexpected Meta request: {method} {url}")

        with patch.dict("os.environ", {
            "META_SYSTEM_USER_TOKEN": "known-valid-system-token",
            "INSTAGRAM_ACCESS_TOKEN": "stale-instagram-token",
            "IG_ACCESS_TOKEN": "older-fallback-token",
            "IG_USER_ID": "stale-ig-user",
        }):
            with patch.object(publisher, "_meta_request", side_effect=fake_meta_request):
                media_id = publisher._instagram_publish(
                    "https://example.com/card.png", "Educational caption", {}
                )

        self.assertEqual(media_id, "media-456")
        self.assertTrue(any(url.endswith("/resolved-ig-user/media") for method, url, _ in calls))
        self.assertFalse(any(url.endswith("/stale-ig-user/media") for method, url, _ in calls))
        tokens = [
            kwargs.get("data", {}).get("access_token")
            or kwargs.get("params", {}).get("access_token")
            for _, _, kwargs in calls
        ]
        self.assertTrue(tokens)
        self.assertTrue(all(token == "known-valid-system-token" for token in tokens))

    def test_approved_record_publishes_when_human_approval_env_is_true(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = {
                "status": "generated",
                "approval_status": "approved",
                "publishing": {"telegram_dm": {"status": "sent", "message_id": 1}},
            }
            copy = {"telegram_html": "t", "instagram_caption": "c"}
            with patch.dict("os.environ", {
                "HUMAN_APPROVAL": "true",
                "TELEGRAM_BOT_TOKEN": "x",
                "IG_USER_ID": "test-user",
                "IG_ACCESS_TOKEN": "test-token",
            }):
                with patch.object(publisher, "_telegram", return_value={"message_id": 9}):
                    with patch.object(publisher, "_accessible_image_url", return_value="https://x/i.png"):
                        with patch.object(publisher, "_instagram_publish", return_value="m1"):
                            updated = publisher.publish(
                                {"signal_id": "sig1"}, copy, _card(tmp), record
                            )
            self.assertEqual(updated["status"], "published")
            self.assertEqual(updated["publishing"]["telegram"]["status"], "published")
            self.assertEqual(updated["publishing"]["instagram"]["status"], "published")

    def test_unapproved_draft_gets_dm_and_stays_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = {"publishing": {}}
            with patch.dict("os.environ", {
                "HUMAN_APPROVAL": "true",
                "TELEGRAM_CHAT_ID": "1",
            }):
                with patch.object(publisher, "_telegram", return_value={"message_id": 5}) as telegram:
                    updated = publisher.publish(
                        {"signal_id": "s"}, {"telegram_html": "t"}, _card(tmp), record
                    )
            self.assertEqual(updated["status"], "pending_approval")
            self.assertEqual(updated["publishing"]["telegram_dm"]["status"], "sent")
            telegram.assert_called_once()

    def test_rejected_record_never_publishes_even_when_human_approval_is_true(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = {"status": "rejected", "approval_status": "rejected", "publishing": {}}
            with patch.dict("os.environ", {"HUMAN_APPROVAL": "true"}):
                with patch.object(publisher, "_telegram") as telegram:
                    with patch.object(publisher, "_instagram_publish") as instagram:
                        updated = publisher.publish(
                            {"signal_id": "rejected-1"}, {"telegram_html": "t"},
                            _card(tmp), record,
                        )
            self.assertEqual(updated["status"], "rejected")
            telegram.assert_not_called()
            instagram.assert_not_called()


if __name__ == "__main__":
    unittest.main()
