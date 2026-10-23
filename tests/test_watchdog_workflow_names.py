"""Ensure every failure-watchdog trigger references a real workflow name."""
from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = ROOT / ".github" / "workflows"
WATCHDOG = WORKFLOWS_DIR / "automation_failure_watchdog.yml"


class WatchdogWorkflowNameTests(unittest.TestCase):
    def test_every_watchdog_entry_matches_a_current_workflow_name(self):
        actual_names = set()
        for path in WORKFLOWS_DIR.glob("*.yml"):
            parsed = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader) or {}
            name = parsed.get("name")
            if isinstance(name, str) and name.strip():
                actual_names.add(name.strip())

        watchdog = yaml.load(WATCHDOG.read_text(encoding="utf-8"), Loader=yaml.BaseLoader) or {}
        configured = watchdog.get("on", {}).get("workflow_run", {}).get("workflows", [])
        missing = sorted(set(configured) - actual_names)
        self.assertFalse(missing, "Watchdog references missing workflow name(s): " + ", ".join(missing))
        self.assertEqual(len(configured), len(set(configured)), "Watchdog contains duplicate workflow names")


if __name__ == "__main__":
    unittest.main()
