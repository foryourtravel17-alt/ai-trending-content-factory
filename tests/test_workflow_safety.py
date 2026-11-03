"""Guard the production workflow's safe defaults against accidental regression."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from scripts.preflight_publish_guard import should_publish
from src import orchestrator as ORCHESTRATOR


class WorkflowSafetyTests(unittest.TestCase):
    def test_manual_market_run_defaults_to_dry_run(self):
        workflow = Path(".github/workflows/market_content.yml").read_text(encoding="utf-8")
        self.assertIn('description: "Generate charts and captions without publishing"', workflow)
        self.assertRegex(workflow, r"(?m)^\s+default: true\s*$")

    def test_scheduled_market_workflow_auto_publishes_only_after_qa_and_image_verification(self):
        workflow = Path(".github/workflows/market_content.yml").read_text(encoding="utf-8")
        self.assertIn('HUMAN_APPROVAL: "false"', workflow)
        self.assertIn('GENERATE_ONLY: "true"', workflow)
        self.assertIn('PUBLISH_ONLY: "true"', workflow)
        self.assertIn("run: python -m src.orchestrator", workflow)
        self.assertLess(
            workflow.index("Commit generated approval drafts and state"),
            workflow.index("Publish eligible market scenarios after QA and image verification"),
        )
        self.assertIn("DRY_RUN: ${{ inputs.dry_run || '0' }}", workflow)
        self.assertIn("id: generate", workflow)
        self.assertIn("PUBLISH_ONLY_SIGNAL_IDS:", workflow)
        self.assertIn("if: always() && steps.publish.outcome != 'skipped'", workflow)
        self.assertIn("from agents.qa import", Path("src/orchestrator.py").read_text(encoding="utf-8"))
        orchestrator = Path("src/orchestrator.py").read_text(encoding="utf-8")
        self.assertIn('record.get("approval_status", "")).strip().lower() != "approved"', orchestrator)


    def test_unapproved_legacy_pending_market_items_are_never_auto_published(self):
        state = {
            "signals": {
                "legacy_pending": {
                    "status": "pending_approval",
                    "approval_status": "pending",
                    "signal": {"as_of": "2026-11-03T00:00:00+00:00"},
                    "copy": {},
                    "card_path": "missing.png",
                }
            }
        }
        with patch.multiple(ORCHESTRATOR, DRY_RUN=False, HUMAN_APPROVAL=False):
            with patch.object(ORCHESTRATOR, "publish") as publisher:
                ORCHESTRATOR._retry_pending(state)
        publisher.assert_not_called()
        self.assertEqual(state["signals"]["legacy_pending"]["status"], "pending_approval")

    def test_market_publish_phase_only_processes_current_run_ids(self):
        with TemporaryDirectory() as folder:
            card = Path(folder) / "market-card.png"
            card.write_bytes(b"test image")
            def record(signal_id):
                return {
                    "status": "generated",
                    "signal": {"signal_id": signal_id, "as_of": "2026-11-03T00:00:00+00:00"},
                    "copy": {"telegram_html": "educational", "instagram_caption": "educational"},
                    "card_path": str(card),
                }
            state = {"signals": {"new_today": record("new_today"), "old_dry_run": record("old_dry_run")}}
            with patch.multiple(
                ORCHESTRATOR,
                PUBLISH_ONLY_SIGNAL_ID="",
                PUBLISH_ONLY_SIGNAL_IDS="new_today",
                DRY_RUN=True,
            ):
                with patch.object(ORCHESTRATOR, "_expire_if_stale", return_value=False):
                    with patch.object(ORCHESTRATOR, "publish", side_effect=lambda signal, copy, path, item, dry_run=False: item) as publisher:
                        with patch.object(ORCHESTRATOR, "save_state"):
                            ORCHESTRATOR._publish_prepared(state)
            self.assertEqual(publisher.call_count, 1)
            self.assertEqual(publisher.call_args.args[0]["signal_id"], "new_today")
    def test_telegram_approval_polling_is_responsive_without_bypassing_approval(self):
        workflow = Path(".github/workflows/market_approval_poll.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "*/5 * * * *"', workflow)
        self.assertIn('workflows: ["Autonomous Market Content Factory"]', workflow)
        self.assertIn("github.event.workflow_run.conclusion == 'success'", workflow)
        self.assertIn("github.event_name == 'schedule' && '60' || '240'", workflow)
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

    def test_readme_states_scheduled_auto_policy_and_manual_review_fallback(self):
        readme = Path("README.md").read_text(encoding="utf-8")
        self.assertIn("Scheduled market scenarios and educational Reels publish automatically only after their configured quality, safety, freshness, media-integrity and duplicate checks pass.", readme)
        self.assertIn("Manual educational Reel dispatches still send a private Telegram review request.", readme)
        self.assertIn("Manual market dispatch defaults to dry-run.", readme)

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
