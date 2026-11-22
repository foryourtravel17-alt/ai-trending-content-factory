from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "educational_reel_draft.yml"
QUEUE_SCRIPT = ROOT / "scripts" / "queue_educational_draft.py"
PIPELINE = ROOT / ".github" / "workflows" / "pipeline.yml"
PREMIUM = ROOT / ".github" / "workflows" / "premium_daily_autopublish.yml"
MATRIX = ROOT / "docs" / "APPROVAL_MATRIX.md"
TEST_CHANNEL = ROOT / ".github" / "workflows" / "test_telegram_channel.yml"


class EducationalReelWorkflowApprovalGateTests(unittest.TestCase):
    def test_generation_workflow_requests_human_approval_instead_of_publishing(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("Send private Telegram approval request (no public publishing)", workflow)
        self.assertIn("run: python -m src.telegram_send", workflow)
        self.assertNotIn("run: python scripts/publish_approved_educational_reels.py", workflow)
        self.assertNotIn("Publish eligible educational Reel to Instagram and Telegram automatically", workflow)

    def test_manual_telegram_recovery_uses_package_module(self):
        workflow = (ROOT / ".github" / "workflows" / "telegram-approval-recovery.yml").read_text(encoding="utf-8")
        self.assertIn("run: python -m src.telegram_send", workflow)
        self.assertNotIn("run: python src/telegram_send.py", workflow)

    def test_legacy_manual_pipeline_is_removed_and_premium_exception_is_explicit(self):
        premium = PREMIUM.read_text(encoding="utf-8")
        self.assertFalse(PIPELINE.exists())
        self.assertIn("explicit exception", premium)
        self.assertIn("PREMIUM_TELEGRAM_CHAT_ID", premium)

    def test_public_telegram_test_post_requires_explicit_confirmation(self):
        workflow = TEST_CHANNEL.read_text(encoding="utf-8")
        self.assertIn("confirm_test_post", workflow)
        self.assertIn("default: false", workflow)
        self.assertIn("inputs.confirm_test_post == true", workflow)

    def test_approval_matrix_lists_every_workflow(self):
        matrix = MATRIX.read_text(encoding="utf-8")
        workflow_files = list((ROOT / ".github" / "workflows").glob("*.yml"))
        for workflow in workflow_files:
            with self.subTest(workflow=workflow.name):
                self.assertIn(workflow.name, matrix)

    def test_approval_matrix_has_one_recovery_row_and_no_literal_escape(self):
        matrix = MATRIX.read_text(encoding="utf-8")
        self.assertNotIn(r"\\n| telegram_approval.yml", matrix)
        self.assertEqual(matrix.count("telegram-approval-recovery.yml"), 1)

    def test_queue_script_does_not_mark_safety_screen_as_publish_approval(self):
        queue = QUEUE_SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"approval_status": "pending"', queue)
        self.assertIn('"human_approval_required": True', queue)
        self.assertIn('"status": "needs_human_review"', queue)
        self.assertNotIn('"status": "auto_publish_ready"', queue)
        self.assertNotIn('"required": False', queue)


if __name__ == "__main__":
    unittest.main()
