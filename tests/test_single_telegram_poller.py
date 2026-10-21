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
