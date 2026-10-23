from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "educational_reel_draft.yml"
QUEUE_SCRIPT = ROOT / "scripts" / "queue_educational_draft.py"
PIPELINE = ROOT / ".github" / "workflows" / "pipeline.yml"
PREMIUM = ROOT / ".github" / "workflows" / "premium_daily_autopublish.yml"
MATRIX = ROOT / "docs" / "APPROVAL_MATRIX.md"


class EducationalReelWorkflowApprovalGateTests(unittest.TestCase):
    def test_generation_workflow_requests_human_approval_instead_of_publishing(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("Send private Telegram approval request (no public publishing)", workflow)
        self.assertIn("run: python src/telegram_send.py", workflow)
        self.assertNotIn("run: python scripts/publish_approved_educational_reels.py", workflow)
        self.assertNotIn("Publish eligible educational Reel to Instagram and Telegram automatically", workflow)

    def test_manual_legacy_pipeline_is_draft_only_and_premium_exception_is_explicit(self):
        pipeline = PIPELINE.read_text(encoding="utf-8")
        premium = PREMIUM.read_text(encoding="utf-8")
        self.assertIn("Approval stance: manual dispatch is draft-only", pipeline)
        self.assertIn('AUTO_PUBLISH_ENABLED: "false"', pipeline)
        self.assertNotIn('AUTO_PUBLISH_ENABLED: "true"', pipeline)
        self.assertIn("explicit exception", premium)
        self.assertIn("PREMIUM_TELEGRAM_CHAT_ID", premium)

    def test_approval_matrix_lists_every_workflow(self):
        matrix = MATRIX.read_text(encoding="utf-8")
        workflow_files = list((ROOT / ".github" / "workflows").glob("*.yml"))
        for workflow in workflow_files:
            with self.subTest(workflow=workflow.name):
                self.assertIn(workflow.name, matrix)

    def test_queue_script_does_not_mark_safety_screen_as_publish_approval(self):
        queue = QUEUE_SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"approval_status": "pending"', queue)
        self.assertIn('"human_approval_required": True', queue)
        self.assertIn('"status": "needs_human_review"', queue)
        self.assertNotIn('"status": "auto_publish_ready"', queue)
        self.assertNotIn('"required": False', queue)


if __name__ == "__main__":
    unittest.main()
