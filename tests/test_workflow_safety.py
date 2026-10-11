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


if __name__ == "__main__":
    unittest.main()
