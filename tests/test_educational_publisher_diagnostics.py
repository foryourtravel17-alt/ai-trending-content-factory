import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import publish_approved_educational_reels as MODULE


class EducationalPublisherDiagnosticTests(unittest.TestCase):
    def test_nameerror_logs_source_frame_and_identifier_without_message(self):
        content_id = "draft_diag_20261023"
        record = {
            "content_type": "educational_reel",
            "content_id": content_id,
            "status": "generated",
            "approval_status": "approved",
            "approval_mode": "automated_policy",
            "human_approval_required": False,
            "automated_review_at": "2026-10-23T00:00:00Z",
            "fact_check": {"status": "automated_passed"},
        }
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            state_path.write_text(json.dumps({"signals": {content_id: record}, "runs": []}), encoding="utf-8")
            output = io.StringIO()
            with patch.object(
                MODULE,
                "publish_approved_educational_reel",
                side_effect=NameError("sensitive exception text must not be printed", name="missing_helper"),
            ):
                with contextlib.redirect_stdout(output):
                    result = MODULE.publish_ids(content_id, state_path)

            text = output.getvalue()
            self.assertEqual(result, 1)
            self.assertIn("Safe diagnostic frame:", text)
            self.assertIn("Undefined Python identifier: missing_helper", text)
            self.assertNotIn("sensitive exception text must not be printed", text)
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["signals"][content_id]["last_publish_error"], "NameError")


if __name__ == "__main__":
    unittest.main()
