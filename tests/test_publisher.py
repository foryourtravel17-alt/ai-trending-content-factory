import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents.publisher import _instagram_publish, _meta_request, publish
from config.env import instagram_access_token


class PublisherTests(unittest.TestCase):
    def signal(self):
        return {"signal_id": "test-signal", "symbol": "TEST", "direction": "LONG"}

    def copy(self):
        return {"telegram_html": "<b>Test</b>", "instagram_caption": "Test caption"}

    def test_canonical_env_helper_matches_retry_token_precedence(self):
        env = {
            "INSTAGRAM_ACCESS_TOKEN": "preferred-token",
            "IG_ACCESS_TOKEN": "fallback-token",
            "META_SYSTEM_USER_TOKEN": "system-token",
        }
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(instagram_access_token(), "system-token")

    def test_instagram_token_precedence_matches_retry_workflow(self):
        env = {
            "INSTAGRAM_ACCESS_TOKEN": "preferred-token",
            "IG_ACCESS_TOKEN": "fallback-token",
            "META_SYSTEM_USER_TOKEN": "system-token",
            "IG_USER_ID": "123456",
        }

        def fake_meta_request(method, url, **kwargs):
            payload = kwargs.get("data") or kwargs.get("params") or {}
            if method == "GET" and url.endswith("/me/accounts"):
                self.assertEqual(payload.get("access_token"), "system-token")
                return {"data": [{"id": "page-1", "name": "Bullseye Theory", "access_token": "page-token", "instagram_business_account": {"id": "123456", "username": "bullseye_theory"}}]}
            self.assertEqual(payload.get("access_token"), "page-token")
            if method == "POST" and url.endswith("/media"):
                return {"id": "container-123"}
            if method == "GET" and url.endswith("/container-123"):
                return {"status_code": "FINISHED"}
            if method == "POST" and url.endswith("/media_publish"):
                return {"id": "media-456"}
            raise AssertionError(f"Unexpected Meta request: {method} {url}")

        with patch.dict(os.environ, env, clear=True):
            with patch("agents.publisher._meta_request", side_effect=fake_meta_request):
                media_id = _instagram_publish(
                    "https://example.com/card.png", "Test caption", {}
                )

        self.assertEqual(media_id, "media-456")

    def test_instagram_configured_id_mismatch_fails_closed(self):
        env = {"META_SYSTEM_USER_TOKEN": "test-token", "IG_USER_ID": "wrong-id"}
        with patch.dict(os.environ, env, clear=True), \
             patch("agents.publisher._resolve_linked_instagram_user_id", return_value=("right-id", "page-token")):
            with self.assertRaisesRegex(RuntimeError, "account ID mismatch"):
                _instagram_publish("https://example.com/card.png", "Test caption", {})

    def test_instagram_missing_token_fails_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "token is not configured"):
                _instagram_publish("https://example.com/card.png", "Test caption", {})

    def test_instagram_retry_reuses_creation_id_after_media_publish_error(self):
        record = {"publishing": {}}
        env = {
            "HUMAN_APPROVAL": "false",
            "TELEGRAM_BOT_TOKEN": "test-token",
            "INSTAGRAM_ACCESS_TOKEN": "preferred-token",
            "IG_ACCESS_TOKEN": "fallback-token",
            "IG_USER_ID": "123456",
        }
        container_calls = []
        publish_creation_ids = []

        def fake_meta_request(method, url, **kwargs):
            if method == "GET" and url.endswith("/me/accounts"):
                return {"data": [{"id": "page-1", "name": "Bullseye Theory", "access_token": "page-token", "instagram_business_account": {"id": "123456", "username": "bullseye_theory"}}]}
            if method == "POST" and url.endswith("/media"):
                container_calls.append(kwargs.get("data", {}).get("caption"))
                return {"id": "container-123"}
            if method == "GET" and url.endswith("/container-123"):
                return {"status_code": "FINISHED"}
            if method == "POST" and url.endswith("/media_publish"):
                publish_creation_ids.append(kwargs.get("data", {}).get("creation_id"))
                if len(publish_creation_ids) == 1:
                    raise RuntimeError(
                        "Meta API HTTP 400; code=190, subcode=460, "
                        "type=OAuthException; message redacted."
                    )
                return {"id": "media-456"}
            raise AssertionError(f"Unexpected Meta request: {method} {url}")

        with tempfile.TemporaryDirectory() as tmp:
            card = Path(tmp) / "card.png"
            card.write_bytes(b"test image bytes")
            with patch.dict(os.environ, env, clear=True):
                with patch("agents.publisher._accessible_image_url", return_value="https://example.com/card.png"):
                    with patch("agents.publisher._telegram", return_value={"message_id": 101}):
                        with patch("agents.publisher._meta_request", side_effect=fake_meta_request):
                            with self.assertRaisesRegex(RuntimeError, "publishing platforms failed"):
                                publish(self.signal(), self.copy(), card, record, dry_run=False)
                            self.assertEqual(
                                record["publishing"]["instagram"]["creation_id"],
                                "container-123",
                            )
                            self.assertEqual(record["publishing"]["instagram"]["status"], "failed")
                            publish(self.signal(), self.copy(), card, record, dry_run=False)

        self.assertEqual(len(container_calls), 1, "retry must not create a second container")
        self.assertEqual(publish_creation_ids, ["container-123", "container-123"])
        self.assertEqual(record["publishing"]["instagram"]["status"], "published")
        self.assertEqual(record["publishing"]["instagram"]["media_id"], "media-456")

    def test_missing_credentials_fail_instead_of_silent_success(self):
        record = {"publishing": {}}
        with patch.dict(os.environ, {"HUMAN_APPROVAL": "false"}, clear=True), \
             patch("agents.publisher._accessible_image_url", return_value="https://example.com/card.png"):
            with self.assertRaisesRegex(RuntimeError, "publishing platforms failed"):
                publish(self.signal(), self.copy(), Path("card.png"), record, dry_run=False)
        self.assertEqual(record["publishing"]["telegram"]["status"], "failed")
        self.assertEqual(record["publishing"]["instagram"]["status"], "failed")

    def test_partial_publish_retries_failed_platform_without_reposting_success(self):
        record = {"publishing": {}}
        env = {
            "HUMAN_APPROVAL": "false",
            "TELEGRAM_BOT_TOKEN": "test-token",
            "IG_ACCESS_TOKEN": "test-ig-token",
            "IG_USER_ID": "123456",
        }
        with tempfile.TemporaryDirectory() as tmp:
            card = Path(tmp) / "card.png"
            card.write_bytes(b"test image bytes")
            with patch.dict(os.environ, env, clear=True), \
                 patch("agents.publisher._accessible_image_url", return_value="https://example.com/card.png"), \
                 patch("agents.publisher._telegram", side_effect=[RuntimeError("temporary Telegram failure"), {"message_id": 456}]) as telegram, \
                 patch("agents.publisher._instagram_publish", return_value="media-123") as instagram:
                with self.assertRaisesRegex(RuntimeError, "publishing platforms failed"):
                    publish(self.signal(), self.copy(), card, record, dry_run=False)
                self.assertEqual(record["publishing"]["instagram"]["status"], "published")
                self.assertEqual(record["publishing"]["telegram"]["status"], "failed")
                publish(self.signal(), self.copy(), card, record, dry_run=False)
                self.assertEqual(record["status"], "published")
                self.assertEqual(record["publishing"]["telegram"]["message_id"], 456)
                self.assertEqual(telegram.call_count, 2)
                self.assertEqual(instagram.call_count, 1)

    def test_instagram_only_retry_never_calls_telegram(self):
        record = {"publishing": {"telegram": {"status": "published", "message_id": 73},
                                 "instagram": {"status": "failed", "error": "HTTP 400"}}}
        env = {
            "HUMAN_APPROVAL": "false",
            "MARKET_RETRY_INSTAGRAM_ONLY": "true",
            "IG_ACCESS_TOKEN": "test-ig-token",
            "IG_USER_ID": "123456",
        }
        with patch.dict(os.environ, env, clear=True), \
             patch("agents.publisher._accessible_image_url", return_value="https://example.com/card.png"), \
             patch("agents.publisher._telegram") as telegram, \
             patch("agents.publisher._instagram_publish", return_value="media-789") as instagram:
            publish(self.signal(), self.copy(), Path("card.png"), record, dry_run=False)
        telegram.assert_not_called()
        instagram.assert_called_once()
        self.assertEqual(record["publishing"]["telegram"]["message_id"], 73)
        self.assertEqual(record["publishing"]["instagram"]["status"], "published")

    def test_instagram_only_retry_blocks_if_telegram_not_already_published(self):
        record = {"publishing": {"telegram": {"status": "failed"}, "instagram": {"status": "failed"}}}
        with patch.dict(os.environ, {"HUMAN_APPROVAL": "false", "MARKET_RETRY_INSTAGRAM_ONLY": "true"}, clear=True), \
             patch("agents.publisher._telegram") as telegram, \
             patch("agents.publisher._instagram_publish") as instagram:
            with self.assertRaisesRegex(RuntimeError, "Telegram is not already marked published"):
                publish(self.signal(), self.copy(), Path("card.png"), record, dry_run=False)
        telegram.assert_not_called()
        instagram.assert_not_called()

    def test_instagram_only_retry_does_not_repost_already_published_instagram(self):
        record = {"publishing": {"telegram": {"status": "published", "message_id": 73},
                                 "instagram": {"status": "published", "media_id": "existing-media"}}}
        env = {"HUMAN_APPROVAL": "false", "MARKET_RETRY_INSTAGRAM_ONLY": "true"}
        with patch.dict(os.environ, env, clear=True), \
             patch("agents.publisher._telegram") as telegram, \
             patch("agents.publisher._instagram_publish") as instagram:
            result = publish(self.signal(), self.copy(), Path("card.png"), record, dry_run=False)
        telegram.assert_not_called()
        instagram.assert_not_called()
        self.assertEqual(result["publishing"]["telegram"]["message_id"], 73)
        self.assertEqual(result["publishing"]["instagram"]["media_id"], "existing-media")
        self.assertEqual(result["status"], "published")

    def test_meta_http_error_logs_only_safe_identifiers(self):
        class FakeResponse:
            ok = False
            status_code = 400

            def json(self):
                return {"error": {
                    "type": "OAuthException",
                    "code": 100,
                    "error_subcode": 36003,
                    "message": "sensitive details with access_token=DO_NOT_LEAK",
                }}

        with patch("agents.publisher.requests.request", return_value=FakeResponse()):
            with self.assertRaisesRegex(RuntimeError, r"HTTP 400; code=100, subcode=36003, type=OAuthException"):
                _meta_request("POST", "https://graph.facebook.com/test", data={"access_token": "DO_NOT_LEAK"})
        # The raised message must not include Meta's untrusted message or any token.
        try:
            with patch("agents.publisher.requests.request", return_value=FakeResponse()):
                _meta_request("POST", "https://graph.facebook.com/test", data={"access_token": "DO_NOT_LEAK"})
        except RuntimeError as exc:
            self.assertNotIn("DO_NOT_LEAK", str(exc))
            self.assertNotIn("sensitive details", str(exc))
            self.assertIn("code=100", str(exc))
            self.assertIn("subcode=36003", str(exc))


if __name__ == "__main__":
    unittest.main()
