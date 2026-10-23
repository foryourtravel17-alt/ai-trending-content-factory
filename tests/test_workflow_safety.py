"""Guard the production workflow's safe defaults against accidental regression."""
from pathlib import Path
import unittest


class WorkflowSafetyTests(unittest.TestCase):
    def test_manual_market_run_defaults_to_dry_run(self):
        workflow = Path(".github/workflows/market_content.yml").read_text(encoding="utf-8")
        self.assertIn('description: "Generate charts and captions without publishing"', workflow)
        self.assertRegex(workflow, r"(?m)^\s+default: true\s*$")

    def test_market_workflow_requires_approval_by_default(self):
        workflow = Path(".github/workflows/market_content.yml").read_text(encoding="utf-8")
        self.assertIn('HUMAN_APPROVAL: "true"', workflow)

    def test_market_workflow_never_publishes_without_approval_callback(self):
        workflow = Path(".github/workflows/market_content.yml").read_text(encoding="utf-8")
        self.assertIn("HUMAN_APPROVAL: \"true\"", workflow)
        self.assertIn("run: python -m src.orchestrator", workflow)
        self.assertNotIn("PUBLISH_ONLY: \"true\"", workflow)
        self.assertNotIn("Publish committed cards to Telegram and Instagram", workflow)
        self.assertNotIn("HUMAN_APPROVAL: \"false\"", workflow)

    def test_telegram_approval_polling_is_responsive_without_bypassing_approval(self):
        workflow = Path(".github/workflows/market_approval_poll.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "*/5 * * * *"', workflow)
        self.assertIn('workflows: ["Autonomous Market Content Factory"]', workflow)
        self.assertIn("github.event.workflow_run.conclusion == 'success'", workflow)
        self.assertIn("github.event_name == 'schedule' && '15' || '240'", workflow)
        self.assertIn("push:", workflow)
        self.assertIn(".github/workflows/market_approval_poll.yml", workflow)
        self.assertIn("id: approval", workflow)
        self.assertIn("market_approve:", Path("src/telegram_process.py").read_text(encoding="utf-8"))

    def test_legacy_telegram_approve_reject_path_is_removed(self):
        source = Path("src/telegram_process.py").read_text(encoding="utf-8")
        self.assertNotIn('parts[0] in ("approve", "reject")', source)
        self.assertIn("Ignoring unsupported Telegram callback type", source)

    def test_watchdog_monitors_new_daily_content_workflows(self):
        workflow = Path(".github/workflows/automation_failure_watchdog.yml").read_text(encoding="utf-8")
        self.assertIn('"Generate Educational Reel Draft (No Publish)"', workflow)
        self.assertIn('"Bullseye Premium Daily Auto-Publish"', workflow)
        self.assertIn("github.event.workflow_run.conclusion == 'failure' || github.event.workflow_run.conclusion == 'cancelled'", workflow)

    def test_legacy_reel_pipeline_does_not_auto_approve_for_publishing(self):
        workflow = Path(".github/workflows/pipeline.yml").read_text(encoding="utf-8")
        self.assertIn('AUTO_PUBLISH_ENABLED: "false"', workflow)


if __name__ == "__main__":
    unittest.main()
