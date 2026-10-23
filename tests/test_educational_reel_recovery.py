import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.recover_failed_educational_reel import (
    find_candidate,
    reserve_candidate,
    safe_recovery_candidate,
)

NOW = datetime(2026, 10, 23, 18, 0, tzinfo=timezone.utc)
CID = "draft_risk-per-trade_evening_20261023_134943"

def fixture_record(now=NOW):
    created = now - timedelta(hours=4)
    record = {
        "content_type": "educational_reel",
        "content_id": CID,
        "status": "publish_failed",
        "approval_status": "approved",
        "approval_mode": "automated_policy",
        "automated_review_at": (created + timedelta(minutes=1)).isoformat(),
        "human_approval_required": False,
        "created_at": created.isoformat(),
        "last_publish_error": "NameError",
        "publishing": {},
        "fact_check": {"status": "automated_passed"},
    }
    metadata = {
        "content_id": CID,
        "status": "approved_for_publishing",
        "created_at": created.isoformat(),
        "approval": {"status": "approved", "mode": "automated_policy", "required": False,
                     "automated_review_at": record["automated_review_at"]},
        "fact_check": {"status": "automated_passed"},
        "safety_check": {"passed": True},
        "publishing": {"instagram": {"status": "ready_for_publish"}},
        "video_url": "https://example.invalid/reel.mp4",
        "video_content_id": CID,
        "video_sha256": "a" * 64,
        "video_size_bytes": 12345,
        "video_duration_seconds": 44.5,
        "video_uploaded_at": (created + timedelta(minutes=1)).isoformat(),
    }
    return record, metadata


def write_fixture(tmp, record, metadata):
    state_path = Path(tmp) / "data" / "state.json"
    out_dir = Path(tmp) / "output"
    state_path.parent.mkdir(parents=True)
    out_dir.mkdir(parents=True)
    state_path.write_text(json.dumps({"signals": {CID: record}, "runs": []}), encoding="utf-8")
    (out_dir / f"{CID}.json").write_text(json.dumps(metadata), encoding="utf-8")
    return state_path, out_dir


class EducationalReelRecoveryTests(unittest.TestCase):
    def test_known_pre_publish_nameerror_with_fresh_verified_media_is_eligible(self):
        record, metadata = fixture_record()
        self.assertTrue(safe_recovery_candidate(record, metadata, now=NOW))

    def test_stale_candidate_is_rejected(self):
        stale_now = NOW + timedelta(days=2)
        record, metadata = fixture_record(now=NOW)
        self.assertFalse(safe_recovery_candidate(record, metadata, now=stale_now))

    def test_non_nameerror_is_not_auto_retried(self):
        record, metadata = fixture_record()
        record["last_publish_error"] = "RuntimeError"
        self.assertFalse(safe_recovery_candidate(record, metadata, now=NOW))

    def test_published_or_ambiguous_platform_state_is_not_auto_retried(self):
        record, metadata = fixture_record()
        record["publishing"] = {"telegram": {"status": "published", "message_id": 7}}
        self.assertFalse(safe_recovery_candidate(record, metadata, now=NOW))
        record, metadata = fixture_record()
        metadata["publishing"]["telegram"] = {"status": "unknown"}
        self.assertFalse(safe_recovery_candidate(record, metadata, now=NOW))

    def test_wrong_media_integrity_or_policy_blocks_recovery(self):
        record, metadata = fixture_record()
        metadata["video_sha256"] = "bad"
        self.assertFalse(safe_recovery_candidate(record, metadata, now=NOW))
        record, metadata = fixture_record()
        metadata["safety_check"]["passed"] = False
        self.assertFalse(safe_recovery_candidate(record, metadata, now=NOW))

    def test_reservation_can_happen_only_once(self):
        record, metadata = fixture_record()
        with tempfile.TemporaryDirectory() as tmp:
            state_path, out_dir = write_fixture(tmp, record, metadata)
            self.assertIsNotNone(find_candidate(state_path, out_dir, now=NOW))
            self.assertEqual(reserve_candidate(state_path, out_dir, now=NOW), CID)
            self.assertIsNone(find_candidate(state_path, out_dir, now=NOW))
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["signals"][CID]["recovery_attempt_count"], 1)

    def test_workflow_has_explicit_opt_in_and_scheduled_default_off(self):
        workflow = Path(".github/workflows/educational_reel_recovery.yml").read_text(encoding="utf-8")
        self.assertIn('default: false', workflow)
        self.assertIn("vars.ENABLE_REEL_RECOVERY == 'true'", workflow)
        self.assertIn("confirm_live_publish == true", workflow)
        self.assertIn("reserve exactly one safe candidate", workflow.lower())


if __name__ == "__main__":
    unittest.main()
