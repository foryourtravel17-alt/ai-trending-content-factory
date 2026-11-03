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
    def test_scheduled_workflow_uses_policy_publish_and_manual_dispatch_keeps_review(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("AUTO_PUBLISH_POLICY:", workflow)
        self.assertIn("github.event_name == 'schedule'", workflow)
        self.assertIn("github.event_name != 'schedule'", workflow)
        self.assertIn("Send private Telegram approval request (manual dispatch only)", workflow)
        self.assertIn("run: python src/telegram_send.py", workflow)
        self.assertIn("Publish policy-approved educational Reel to Instagram and Telegram", workflow)
        self.assertIn("run: python scripts/publish_approved_educational_reels.py", workflow)

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

    def test_queue_script_requires_safety_pass_and_distinguishes_review_from_policy(self):
        queue = QUEUE_SCRIPT.read_text(encoding="utf-8")
        self.assertIn('if safety_check.get("passed") is not True:', queue)
        self.assertIn('AUTO_PUBLISH_POLICY', queue)
        self.assertIn('"approval_status": approval_status', queue)
        self.assertIn('"human_approval_required": human_approval_required', queue)
        self.assertIn('approval_status = "pending"', queue)
        self.assertIn('approval_status = "approved"', queue)
        self.assertIn('"status": "needs_human_review"', queue)
        self.assertIn('"status": "automated_passed"', queue)
        self.assertIn('"mode": "human_review"', queue)
        self.assertIn('"mode": "automated_policy"', queue)
        self.assertIn("This automated screen is not independent factual verification", queue)
        self.assertIn("if not auto_policy:", queue)
        self.assertNotIn('"status": "auto_publish_ready"', queue)


if __name__ == "__main__":
    unittest.main()
