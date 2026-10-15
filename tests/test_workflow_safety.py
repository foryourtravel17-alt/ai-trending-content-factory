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

    def test_legacy_reel_pipeline_does_not_auto_approve_for_publishing(self):
        workflow = Path(".github/workflows/pipeline.yml").read_text(encoding="utf-8")
        self.assertIn('AUTO_PUBLISH_ENABLED: "false"', workflow)


if __name__ == "__main__":
    unittest.main()
