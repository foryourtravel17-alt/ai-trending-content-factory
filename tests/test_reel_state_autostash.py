from pathlib import Path
import unittest


class EducationalReelStatePersistenceTests(unittest.TestCase):
    def test_reel_state_commit_autostashes_unrelated_tracked_changes_before_rebase(self):
        workflow = Path(".github/workflows/educational_reel_draft.yml").read_text(encoding="utf-8")
        self.assertIn("git pull --rebase --autostash origin main", workflow)
        self.assertNotIn("git pull --rebase origin main", workflow)


if __name__ == "__main__":
    unittest.main()
