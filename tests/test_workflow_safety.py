"""Guard the production workflow's safe defaults against accidental regression."""
from pathlib import Path
import unittest
from scripts.preflight_publish_guard import should_publish


class WorkflowSafetyTests(unittest.TestCase):
    def test_manual_market_run_defaults_to_dry_run(self):
        workflow = Path(".github/workflows/market_content.yml").read_text(encoding="utf-8")
        self.assertIn('description: "Generate charts and captions without publishing"', workflow)
        self.assertRegex(workflow, r"(?m)^\s+default: true\s*$")

    def test_market_workflow_routes_new_scenarios_through_telegram_owner_approval(self):
        workflow = Path(".github/workflows/market_content.yml").read_text(encoding="utf-8")
        self.assertIn('HUMAN_APPROVAL: "true"', workflow)
        self.assertIn('GENERATE_ONLY: "true"', workflow)
        self.assertIn('PUBLISH_ONLY: "true"', workflow)
        self.assertIn("run: python -m src.orchestrator", workflow)
        self.assertLess(
            workflow.index("Commit generated approval drafts and state"),
            workflow.index("Send prepared market scenarios to private Telegram for owner approval"),
        )
        self.assertIn("DRY_RUN: ${{ inputs.dry_run || '0' }}", workflow)
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
        self.assertIn('"Bullseye Daily Educational Reel Draft"', workflow)
        self.assertIn('"Bullseye Premium Daily Auto-Publish"', workflow)
        self.assertIn("github.event.workflow_run.conclusion == 'failure' || github.event.workflow_run.conclusion == 'cancelled'", workflow)

    def test_automated_approval_requires_fact_check_pass(self):
        source = Path("src/main.py").read_text(encoding="utf-8")
        self.assertIn('fact_check_data.get("status") == "passed"', source)
        self.assertIn("automated_approval_eligible", source)
        self.assertIn('"required": not automated_approval_eligible', source)

    def test_legacy_manual_pipeline_is_removed_and_documented_unsupported(self):
        root = Path(".github/workflows")
        self.assertFalse((root / "pipeline.yml").exists())
        self.assertFalse((root / "generate_approved_reel.yml").exists())
        self.assertFalse((root / "instagram_publish.yml").exists())
        readme = Path("README.md").read_text(encoding="utf-8")
        self.assertIn("The retired manual `pipeline.yml` and its legacy", readme)
        self.assertIn("are unsupported and have been removed", readme)
        self.assertIn("educational_reel_draft.yml", readme)

    def test_auto_published_market_record_cannot_pass_human_approval_preflight(self):
        auto_published = {
            "status": "published",
            "signal": {"signal_id": "market_auto_1", "as_of": "2026-10-24T00:00:00+00:00"},
            "publishing": {
                "telegram": {"status": "published"},
                "instagram": {"status": "published"},
            },
        }
        allowed, reason = should_publish(auto_published)
        self.assertFalse(allowed)
        self.assertEqual(reason, "signal is not human-approved")

    def test_readme_states_market_and_educational_approval_policies(self):
        readme = Path("README.md").read_text(encoding="utf-8")
        self.assertIn("Market cards are generated on schedule and sent to the owner private Telegram for approval; public posting happens only after an explicit approval button.", readme)

    def test_instagram_health_check_uses_publisher_token_priority_without_fallback(self):
        workflow = Path(".github/workflows/instagram_token_health.yml").read_text(encoding="utf-8")
        publisher = Path("agents/publisher.py").read_text(encoding="utf-8")
        self.assertIn("for source in META_SYSTEM_USER_TOKEN INSTAGRAM_ACCESS_TOKEN IG_ACCESS_TOKEN; do", workflow)
        self.assertIn('("META_SYSTEM_USER_TOKEN", "INSTAGRAM_ACCESS_TOKEN", "IG_ACCESS_TOKEN")', publisher)
        self.assertIn("selected publisher credential source", workflow)
        self.assertNotIn("trying next configured source", workflow)
        self.assertIn("credential values redacted", workflow)
        self.assertNotIn('echo "${response}"', workflow)
        self.assertNotIn('echo "${account_response}"', workflow)

    def test_instagram_health_check_blocks_missing_publish_scopes(self):
        workflow = Path(".github/workflows/instagram_token_health.yml").read_text(encoding="utf-8")
        self.assertIn("/me/permissions", workflow)
        self.assertIn('"pages_read_engagement"', workflow)
        self.assertIn('"instagram_content_publish"', workflow)
        self.assertIn("required Meta publishing permissions are missing or could not be verified", workflow)
        self.assertIn("Alert Telegram on invalid token, missing scopes, or broken Instagram link", workflow)
        self.assertIn("if: github.event_name != 'push'", workflow)
        self.assertIn("Scheduled and manual runs still perform the real credential/scope check", workflow)


if __name__ == "__main__":
    unittest.main()
