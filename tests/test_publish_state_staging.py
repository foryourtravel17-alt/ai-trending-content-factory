import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGER = ROOT / "scripts" / "stage_publish_state.sh"


class PublishStateStagingTests(unittest.TestCase):
    def test_stages_state_and_json_when_content_glob_is_empty_without_staging_mp4(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)

            (root / "data").mkdir()
            (root / "output" / "media").mkdir(parents=True)
            (root / "data" / "state.json").write_text("{}", encoding="utf-8")
            (root / "output" / "draft_test.json").write_text("{}", encoding="utf-8")
            (root / "output" / "media" / "draft_test.mp4").write_bytes(b"video")
            (root / "output" / "media" / "draft_test.publish.json").write_text("{}", encoding="utf-8")

            run = subprocess.run(
                ["bash", str(STAGER)], cwd=root, text=True, capture_output=True, check=False
            )
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            staged = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                cwd=root, text=True, capture_output=True, check=True,
            ).stdout.splitlines()
            self.assertIn("data/state.json", staged)
            self.assertIn("output/draft_test.json", staged)
            self.assertIn("output/media/draft_test.publish.json", staged)
            self.assertNotIn("output/media/draft_test.mp4", staged)

    def test_no_matching_files_is_a_successful_noop(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            run = subprocess.run(
                ["bash", str(STAGER)], cwd=root, text=True, capture_output=True, check=False
            )
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn("No publish-state files found to stage.", run.stdout)


if __name__ == "__main__":
    unittest.main()
