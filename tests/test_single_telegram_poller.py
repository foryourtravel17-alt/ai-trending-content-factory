from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / ".github" / "workflows" / "telegram_approval.yml"
POLLER = ROOT / ".github" / "workflows" / "market_approval_poll.yml"


def workflow_triggers(text):
    parsed = yaml.safe_load(text)
    # PyYAML's YAML 1.1 resolver treats the unquoted key "on" as boolean True.
    return parsed.get("on", parsed.get(True, {}))


class SingleTelegramPollerTests(unittest.TestCase):
    def test_legacy_workflow_does_not_poll_or_consume_updates(self):
        text = LEGACY.read_text(encoding="utf-8")
        triggers = workflow_triggers(text)
        self.assertIn("workflow_dispatch", triggers)
        self.assertNotIn("schedule", triggers)
        self.assertNotIn("src/telegram_process.py", text)

    def test_educational_approvals_reach_the_explicit_reel_publisher(self):
        text = POLLER.read_text(encoding="utf-8")
        parsed = yaml.safe_load(text)
        job = parsed["jobs"]["poll-and-publish-approved"]
        step = next(item for item in job["steps"] if item.get("name") == "Publish approved educational Reels")
        self.assertIn("educational_approved_ids", step.get("if", ""))
        self.assertEqual(step["run"], "python scripts/publish_approved_educational_reels.py")
        self.assertNotIn("src.orchestrator", step["run"])
        self.assertIn('HUMAN_APPROVAL: "true"', text)
        self.assertIn("EDUCATIONAL_APPROVED_IDS", step.get("env", {}))

    def test_market_poller_is_single_scheduled_callback_consumer(self):
        text = POLLER.read_text(encoding="utf-8")
        triggers = workflow_triggers(text)
        self.assertIn("schedule", triggers)
        self.assertIn('cron: "*/5 * * * *"', text)
        self.assertIn("group: market-state", text)
        self.assertIn("run: python src/telegram_process.py", text)
        self.assertIn("Guard and publish approved market scenarios", text)
        self.assertIn("data/state.json", text)
        self.assertIn("draft_*.json", text)


if __name__ == "__main__":
    unittest.main()
