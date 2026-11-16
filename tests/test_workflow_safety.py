"""Guard Telegram-only publishing and approval safety invariants."""
from pathlib import Path
import unittest

from scripts.preflight_publish_guard import should_publish


class WorkflowSafetyTests(unittest.TestCase):
    def test_market_generation_defaults_to_dry_run_and_requires_telegram_approval(self):
        workflow = Path(".github/workflows/market_content.yml").read_text(encoding="utf-8")
        self.assertIn('default: true', workflow)
        self.assertIn('HUMAN_APPROVAL: "true"', workflow)
        self.assertIn('GENERATE_ONLY: "true"', workflow)
        self.assertIn("run: python -m src.orchestrator", workflow)
        self.assertIn("Send prepared market scenarios to private Telegram for owner approval", workflow)
        self.assertNotIn("META_SYSTEM_USER_TOKEN", workflow)
        self.assertNotIn("INSTAGRAM_ACCESS_TOKEN", workflow)
        self.assertNotIn("IG_ACCESS_TOKEN", workflow)

    def test_market_approval_poller_is_five_minute_telegram_only(self):
        workflow = Path(".github/workflows/market_approval_poll.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "*/5 * * * *"', workflow)
        self.assertIn('workflows: ["Autonomous Market Content Factory"]', workflow)
        self.assertIn("Poll Telegram approval buttons", workflow)
        self.assertIn("market_approve:", Path("src/telegram_process.py").read_text(encoding="utf-8"))
        self.assertNotIn("INSTAGRAM_ACCESS_TOKEN", workflow)
        self.assertNotIn("META_SYSTEM_USER_TOKEN", workflow)

    def test_approved_market_retry_needs_owner_approval_and_fresh_signal(self):
        approved = {
            "approval_status": "approved",
            "signal": {"signal_id": "s1", "as_of": "2026-11-16T10:00:00+00:00"},
            "publishing": {"telegram": {"status": "failed"}},
        }
        self.assertTrue(should_publish(approved)[0])
        pending = dict(approved, approval_status="pending")
        self.assertFalse(should_publish(pending)[0])
        sent = dict(approved, publishing={"telegram": {"status": "published"}})
        self.assertFalse(should_publish(sent)[0])
        unknown = dict(approved, publishing={"telegram": {"status": "unknown"}})
        self.assertFalse(should_publish(unknown)[0])

    def test_educational_reels_require_human_approval_and_no_meta_workflow(self):
        workflow = Path(".github/workflows/educational_reel_draft.yml").read_text(encoding="utf-8")
        self.assertIn("Register Reel for owner approval", workflow)
        self.assertIn("Send private Telegram approval request", workflow)
        self.assertNotIn("META_SYSTEM_USER_TOKEN", workflow)
        self.assertNotIn("IG_ACCESS_TOKEN", workflow)
        script = Path("scripts/publish_approved_educational_reels.py").read_text(encoding="utf-8")
        self.assertIn("from src.telegram_reel_publish import", script)
        self.assertNotIn("instagram", script.lower())

    def test_meta_publishing_workflows_and_modules_are_removed(self):
        workflow_dir = Path(".github/workflows")
        for path in workflow_dir.glob("*.yml"):
            self.assertNotIn("graph.facebook.com", path.read_text(encoding="utf-8"))
            self.assertNotIn("META_SYSTEM_USER_TOKEN", path.read_text(encoding="utf-8"))
            self.assertNotIn("INSTAGRAM_ACCESS_TOKEN", path.read_text(encoding="utf-8"))
        self.assertFalse(Path("src/instagram_publish.py").exists())
        self.assertFalse(Path(".github/workflows/instagram_token_health.yml").exists())
        self.assertFalse(Path(".github/workflows/instagram_credential_diagnostic.yml").exists())
        self.assertFalse(Path(".github/workflows/instagram_publish_recovery.yml").exists())

    def test_market_retry_workflow_has_no_meta_steps(self):
        workflow = Path(".github/workflows/market_publish_retry.yml").read_text(encoding="utf-8")
        self.assertIn("PUBLISH_ONLY_SIGNAL_ID", workflow)
        self.assertIn("TELEGRAM_BOT_TOKEN", workflow)
        self.assertNotIn("graph.facebook.com", workflow)
        self.assertNotIn("META_SYSTEM_USER_TOKEN", workflow)

    def test_readme_and_architecture_describe_telegram_only_social_publishing(self):
        readme = Path("README.md").read_text(encoding="utf-8").lower()
        self.assertIn("telegram is the only social publishing destination", readme)
        self.assertIn("facebook and instagram are disconnected", readme)
        publisher = Path("agents/publisher.py").read_text(encoding="utf-8").lower()
        self.assertNotIn("instagram", publisher)
        self.assertNotIn("meta", publisher)


if __name__ == "__main__":
    unittest.main()
