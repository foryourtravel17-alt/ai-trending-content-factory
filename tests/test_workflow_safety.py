"""Guard the production workflow's safe defaults against accidental regression."""
from pathlib import Path
import unittest


class WorkflowSafetyTests(unittest.TestCase):
    def test_manual_market_run_defaults_to_dry_run(self):
        workflow = Path(".github/workflows/market_content.yml").read_text(encoding="utf-8")
        self.assertIn('description: "Generate charts and captions without publishing"', workflow)
        self.assertRegex(workflow, r"(?m)^\s+default: true\s*$")

    def test_market_workflow_commits_public_images_before_live_publish(self):
        workflow = Path(".github/workflows/market_content.yml").read_text(encoding="utf-8")
        self.assertIn('HUMAN_APPROVAL: "false"', workflow)
        self.assertIn('GENERATE_ONLY: "true"', workflow)
        self.assertIn('PUBLISH_ONLY: "true"', workflow)
        self.assertIn("run: python -m src.orchestrator", workflow)
        self.assertNotIn('HUMAN_APPROVAL: "true"', workflow)
        self.assertLess(
            workflow.index("Commit generated approval drafts and state"),
            workflow.index("Publish prepared market signals after generated images are public"),
        )
        self.assertIn("DRY_RUN: \${{ inputs.dry_run || '0' }}", workflow)
        self.assertIn("if: always() && steps.publish.outcome != 'skipped'", workflow)
        self.assertIn("from agents.qa import", Path("src/orchestrator.py").read_text(encoding="utf-8"))

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
        self.assertIn('"Bullseye Daily Educational Reel Auto-Publish"', workflow)
        self.assertIn('"Bullseye Premium Daily Auto-Publish"', workflow)
        self.assertIn("github.event.workflow_run.conclusion == 'failure' || github.event.workflow_run.conclusion == 'cancelled'", workflow)

    def test_legacy_manual_fallback_uses_automated_policy_without_extra_schedule(self):
        workflow = Path(".github/workflows/pipeline.yml").read_text(encoding="utf-8")
        self.assertIn('AUTO_PUBLISH_ENABLED: "true"', workflow)
        self.assertNotIn("schedule:", workflow)
        self.assertNotIn("Send pending content to Telegram", workflow)
        reel_workflow = Path(".github/workflows/generate_approved_reel.yml").read_text(encoding="utf-8")
        self.assertIn('workflows: ["AI Trading Content Pipeline (Automatic Publish)"]', reel_workflow)
        self.assertIn('safety_check.get("passed") is True', reel_workflow)


if __name__ == "__main__":
    unittest.main()
