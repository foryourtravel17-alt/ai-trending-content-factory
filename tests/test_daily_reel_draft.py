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

    def test_manual_slot_override_is_respected_even_when_cron_fires_late(self):
        delayed_morning_run = datetime(2026, 10, 23, 7, 5, tzinfo=timezone.utc)
        self.assertEqual(resolve_slot(delayed_morning_run, "morning"), "morning")
        for slot in SLOTS:
            with self.subTest(slot=slot):
                self.assertEqual(resolve_slot(delayed_morning_run, slot), slot)

    def test_delayed_auto_run_stays_in_most_recent_cron_slot(self):
        self.assertEqual(resolve_slot(datetime(2026, 10, 23, 7, 5, tzinfo=timezone.utc), "auto"), "morning")

    def test_auto_fallback_chooses_next_slot_before_first_cron_window(self):
        self.assertEqual(resolve_slot(datetime(2026, 10, 23, 3, 0, tzinfo=timezone.utc), "auto"), "morning")

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

            malformed = out / "draft_malformed.json"
            malformed.write_text("[]", encoding="utf-8")
            self.assertEqual(existing_draft_for_slot(out, "2026-10-23", "morning"), record)


    def test_workflow_runs_three_times_and_requires_human_approval(self):
        workflow = Path(".github/workflows/educational_reel_draft.yml").read_text(encoding="utf-8")
        self.assertIn("cron: '47 4 * * *'", workflow)
        self.assertIn("cron: '47 8 * * *'", workflow)
        self.assertIn("cron: '47 12 * * *'", workflow)
        self.assertIn("SLOT_INPUT:", workflow)
        self.assertIn("github.event.schedule == '47 4 * * *' && 'morning'", workflow)
        self.assertIn("github.event.schedule == '47 8 * * *' && 'afternoon'", workflow)
        self.assertIn("github.event.schedule == '47 12 * * *' && 'evening'", workflow)
        self.assertIn("Send private Telegram approval request (no public publishing)", workflow)
        self.assertIn("run: python src/telegram_send.py", workflow)
        self.assertIn("Register Reel for owner approval", workflow)
        self.assertNotIn("run: python scripts/publish_approved_educational_reels.py", workflow)
        self.assertNotIn("EDUCATIONAL_APPROVED_IDS: ${{ steps.queue.outputs.content_id }}", workflow)
        self.assertNotIn("Bullseye Daily Educational Reel Auto-Publish", workflow)
        self.assertIn("id: queue", workflow)
        self.assertNotIn("Upload draft for review (no publishing)", workflow)
        self.assertIn("if: steps.draft.outputs.skip != 'true'", workflow)
        self.assertIn("if: always() && steps.draft.outcome == 'success' && steps.draft.outputs.skip != 'true'", workflow)
        self.assertIn("No-op when this slot already has a draft", workflow)
        self.assertIn("approval_queue.json", workflow)

    def test_unsupported_slot_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_slot(datetime(2026, 10, 23, 4, 45, tzinfo=timezone.utc), "midnight")
        with self.assertRaises(ValueError):
            build_draft(datetime(2026, 10, 23, 4, 45, tzinfo=timezone.utc), "midnight")


if __name__ == "__main__":
    unittest.main()
