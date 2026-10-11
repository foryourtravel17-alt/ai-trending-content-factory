import importlib
import os
import tempfile
import io
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
from urllib.error import URLError

from config import env


class ApprovalGateTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def content(self, **overrides):
        item = {
            "content_id": "content_test_1",
            "status": "approved_for_publishing",
            "fact_check": {"status": "passed"},
            "safety_check": {"passed": True},
            "approval": {
                "required": True, "status": "approved",
                "version": 1, "content_hash": "a" * 64,
            },
        }
        item.update(overrides)
        return item

    def test_missing_approval_record_fails_closed(self):
        self.assertTrue(env.human_approval_required())
        self.assertFalse(env.content_is_approved(self.content(approval={})))

    def test_pending_approval_is_blocked(self):
        self.assertFalse(env.content_is_approved(self.content(
            status="pending_approval",
            approval={"required": True, "status": "pending", "version": 1, "content_hash": "a" * 64},
        )))

    def test_rejected_content_is_blocked(self):
        self.assertFalse(env.content_is_approved(self.content(
            status="rejected",
            approval={"required": True, "status": "rejected", "version": 1, "content_hash": "a" * 64},
        )))

    def test_expired_content_is_blocked(self):
        self.assertFalse(env.content_is_approved(self.content(
            status="expired",
            approval={"required": True, "status": "expired", "version": 1, "content_hash": "a" * 64},
        )))

    def test_bound_approved_content_is_allowed(self):
        self.assertTrue(env.content_is_approved(self.content()))

    def test_already_published_duplicate_is_blocked(self):
        self.assertFalse(env.content_is_approved(self.content(status="published_to_instagram")))

    def test_fact_check_review_required_blocks_automatic_mode(self):
        os.environ["HUMAN_APPROVAL"] = "false"
        self.assertFalse(env.content_is_approved(self.content(
            fact_check={"status": "review_required"},
            approval={"required": False, "status": "approved", "version": 1, "content_hash": "a" * 64},
        )))

    def test_credential_alias_precedence(self):
        os.environ["INSTAGRAM_USER_ID"] = "legacy-user"
        os.environ["META_SYSTEM_USER_TOKEN"] = "legacy-token"
        self.assertEqual(env.instagram_user_id(), "legacy-user")
        self.assertEqual(env.instagram_access_token(), "legacy-token")
        os.environ["IG_USER_ID"] = "canonical-user"
        os.environ["IG_ACCESS_TOKEN"] = "canonical-token"
        self.assertEqual(env.instagram_user_id(), "canonical-user")
        self.assertEqual(env.instagram_access_token(), "canonical-token")


class PublisherSafetyTests(unittest.TestCase):
    def test_dry_run_never_calls_external_publisher(self):
        from agents import publisher
        with patch.dict(os.environ, {"HUMAN_APPROVAL": "false"}, clear=False):
            with patch.object(publisher, "_telegram") as telegram, patch.object(publisher, "_instagram_publish") as instagram:
                result = publisher.publish(
                    {"signal_id": "sig-1"},
                    {"telegram_html": "draft", "instagram_caption": "draft"},
                    Path("does-not-need-to-exist.png"),
                    {"publishing": {}},
                    dry_run=True,
                )
                self.assertEqual(result["status"], "generated")
                telegram.assert_not_called()
                instagram.assert_not_called()

    def test_unreachable_public_image_url_fails_closed(self):
        from agents import publisher
        with patch.dict(os.environ, {"IMAGE_BASE_URL": "https://images.example.test/output"}, clear=True):
            with patch.object(publisher.requests, "head", return_value=Mock(status_code=404)):
                with self.assertRaises(RuntimeError):
                    publisher._accessible_image_url(Path("example_card.png"))

    def test_telegram_callback_api_failure_is_redacted(self):
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test-token"}, clear=False):
            import src.telegram_process as processor
            importlib.reload(processor)
            with patch("urllib.request.urlopen", side_effect=URLError("offline")):
                with self.assertRaisesRegex(RuntimeError, "credentials redacted|bot token redacted"):
                    processor.api("getUpdates", {"offset": 0}, timeout=1)

 
    def test_no_op_run_does_not_process_old_output(self):
        import src.main as main_module
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(main_module, "OUTPUT_DIR", Path(directory)):
                with patch.object(main_module, "trend_discovery", return_value=[]):
                    main_module.main()
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_topic_history_prevents_immediate_repeat(self):
        import src.main as main_module
        with tempfile.TemporaryDirectory() as directory:
            history_path = Path(directory) / "recent_topics.json"
            with patch.object(main_module, "OUTPUT_DIR", Path(directory)), patch.object(main_module, "TOPIC_HISTORY_PATH", history_path):
                first = main_module.trend_discovery()
                second = main_module.trend_discovery()
            self.assertTrue(first)
            self.assertTrue(second)
            self.assertNotEqual(first[0]["title"], second[0]["title"])

    def test_meta_api_failure_does_not_leak_token(self):
        import src.instagram_publish as instagram
        from urllib.error import HTTPError
        error = HTTPError("https://example.test", 500, "failure", {}, io.BytesIO(b"failure"))
        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaisesRegex(RuntimeError, "response redacted to protect credentials"):
                instagram.request("POST", "https://example.test", {"access_token": "never-print-this"})


if __name__ == "__main__":
    unittest.main()
