from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "educational_reel_draft.yml"
QUEUE_SCRIPT = ROOT / "scripts" / "queue_educational_draft.py"


class EducationalReelWorkflowApprovalGateTests(unittest.TestCase):
    def test_generation_workflow_requests_human_approval_instead_of_publishing(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("Send private Telegram approval request (no public publishing)", workflow)
        self.assertIn("run: python src/telegram_send.py", workflow)
        self.assertNotIn("run: python scripts/publish_approved_educational_reels.py", workflow)
        self.assertNotIn("Publish eligible educational Reel to Instagram and Telegram automatically", workflow)

    def test_queue_script_does_not_mark_safety_screen_as_publish_approval(self):
        queue = QUEUE_SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"approval_status": "pending"', queue)
        self.assertIn('"human_approval_required": True', queue)
        self.assertIn('"status": "needs_human_review"', queue)
        self.assertNotIn('"status": "auto_publish_ready"', queue)
        self.assertNotIn('"required": False', queue)


if __name__ == "__main__":
    unittest.main()
