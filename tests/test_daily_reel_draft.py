import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts.daily_reel_draft import (
    SLOTS,
    TOPICS,
    build_draft,
    existing_draft_for_slot,
    resolve_slot,
)


class DailyReelDraftTests(unittest.TestCase):
    def test_auto_slot_matches_three_configured_utc_windows(self):
        self.assertEqual(resolve_slot(datetime(2026, 10, 23, 4, 45, tzinfo=timezone.utc), "auto"), "morning")
        self.assertEqual(resolve_slot(datetime(2026, 10, 23, 8, 45, tzinfo=timezone.utc), "auto"), "afternoon")
        self.assertEqual(resolve_slot(datetime(2026, 10, 23, 12, 45, tzinfo=timezone.utc), "auto"), "evening")

    def test_manual_slot_override_is_respected(self):
        now = datetime(2026, 10, 23, 4, 45, tzinfo=timezone.utc)
        for slot in SLOTS:
            with self.subTest(slot=slot):
                self.assertEqual(resolve_slot(now, slot), slot)

    def test_each_slot_creates_different_topic_and_stays_draft_only(self):
        now = datetime(2026, 10, 23, 4, 45, tzinfo=timezone.utc)
        drafts = [build_draft(now, slot) for slot in SLOTS]
        titles = [draft["topic"]["title"] for draft in drafts]
        self.assertEqual(len(set(titles)), 3)
        self.assertTrue(all(draft["approval"]["required"] for draft in drafts))
        self.assertTrue(all(draft["approval"]["status"] == "draft_only" for draft in drafts))
        self.assertTrue(all(draft["status"] == "draft_only" for draft in drafts))
        self.assertTrue(all("not financial advice" in draft["script"]["disclaimer"].lower() for draft in drafts))
        self.assertEqual([draft["schedule_slot"]["name"] for draft in drafts], list(SLOTS))

    def test_slot_guard_detects_persisted_draft_and_ignores_seed(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            slot = {"name": "morning", "utc_date": "2026-10-23", "index": 0}
            seed = out / "draft_seed.json"
            seed.write_text(json.dumps({"schedule_slot": slot}), encoding="utf-8")
            self.assertIsNone(existing_draft_for_slot(out, "2026-10-23", "morning"))

            record = out / "draft_test_content.json"
            record.write_text(
                json.dumps({"content_id": "draft_test_content", "schedule_slot": slot}),
                encoding="utf-8",
            )
            self.assertEqual(existing_draft_for_slot(out, "2026-10-23", "morning"), record)
            self.assertIsNone(existing_draft_for_slot(out, "2026-10-23", "afternoon"))


    def test_workflow_runs_three_times_but_only_sends_approval_requests(self):
        workflow = Path(".github/workflows/educational_reel_draft.yml").read_text(encoding="utf-8")
        self.assertIn("cron: '45 4 * * *'", workflow)
        self.assertIn("cron: '45 8 * * *'", workflow)
        self.assertIn("cron: '45 12 * * *'", workflow)
        self.assertIn("Send Telegram approval request", workflow)
        self.assertIn("Register draft in shared approval state", workflow)
        self.assertNotIn("Publish Approved Reel to Instagram", workflow)
        self.assertIn("if: steps.draft.outputs.skip != 'true'", workflow)
        self.assertIn("No-op when this slot already has a draft", workflow)

    def test_unsupported_slot_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_slot(datetime(2026, 10, 23, 4, 45, tzinfo=timezone.utc), "midnight")
        with self.assertRaises(ValueError):
            build_draft(datetime(2026, 10, 23, 4, 45, tzinfo=timezone.utc), "midnight")


if __name__ == "__main__":
    unittest.main()
