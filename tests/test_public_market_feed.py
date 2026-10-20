"""Tests for the safe, approved-only public Market Lab feed."""
from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.export_public_market_feed import build_public_feed, export_public_feed


NOW = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)


def make_record(*, approval="approved", status="published", as_of="2026-10-20T10:00:00Z"):
    return {
        "approval_status": approval,
        "status": status,
        "signal": {
            "signal_id": "secret-internal-id",
            "symbol": "ETH-USD",
            "label": "Ethereum",
            "direction": "SHORT",
            "entry": 2400.08,
            "stop_loss": 2425.03,
            "tp1": 2375.13,
            "tp2": 2362.66,
            "tp3": 2350.18,
            "as_of": as_of,
        },
        "analyst": {
            "view": "Structure and risk observation.",
            "caveat": "Rule-based educational scenario; conditions can change.",
        },
        "copy": {"telegram_html": "internal caption"},
        "card_path": "output/private.png",
        "publishing": {"telegram": {"status": "published"}},
    }


class PublicFeedTests(unittest.TestCase):
    def test_exports_fresh_approved_observation_without_level_or_internal_fields(self):
        feed = build_public_feed({"signals": {"s1": make_record()}}, now=NOW)
        self.assertEqual(len(feed["records"]), 1)
        row = feed["records"][0]
        self.assertEqual(row["approvalStatus"], "approved")
        self.assertEqual(row["symbol"], "ETH-USD")
        self.assertEqual(row["direction"], "SHORT")
        for forbidden in ("entry", "stop_loss", "tp1", "tp2", "tp3", "copy", "publishing", "card_path"):
            self.assertNotIn(forbidden, row)
        self.assertEqual(set(row.keys()), {"id", "symbol", "label", "direction", "as_of", "view", "caveat", "approvalStatus"})

    def test_pending_and_rejected_are_never_exported(self):
        state = {"signals": {
            "pending": make_record(approval=None, status="pending_approval"),
            "rejected": make_record(approval="rejected", status="rejected"),
            "expired": make_record(approval="approved", status="expired"),
        }}
        self.assertEqual(build_public_feed(state, now=NOW)["records"], [])

    def test_stale_and_invalid_timestamps_are_never_exported(self):
        state = {"signals": {
            "stale": make_record(as_of="2026-10-19T00:00:00Z"),
            "invalid": make_record(as_of="not-a-time"),
        }}
        self.assertEqual(build_public_feed(state, now=NOW)["records"], [])

    def test_far_future_observations_are_never_exported(self):
        state = {"signals": {
            "future": make_record(as_of="2026-10-20T15:00:00Z"),
        }}
        self.assertEqual(build_public_feed(state, now=NOW)["records"], [])

    def test_age_window_is_bounded(self):
        with self.assertRaises(ValueError):
            build_public_feed({"signals": {}}, now=NOW, max_age_hours=48)

    def test_export_does_not_change_timestamp_or_create_commit_churn_for_same_feed(self):
        now = datetime.now(timezone.utc)
        record = make_record(as_of=(now - timedelta(hours=1)).isoformat())
        state = {"signals": {"s1": record}}
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            output_path = Path(tmp) / "approved_market_feed.json"
            state_path.write_text(json.dumps(state), encoding="utf-8")
            initial = build_public_feed(state, now=now)
            output_path.write_text(json.dumps(initial, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            exported = export_public_feed(state_path, output_path)
            self.assertEqual(exported["generatedAt"], initial["generatedAt"])
            self.assertEqual(output_path.read_text(encoding="utf-8"), json.dumps(initial, indent=2, ensure_ascii=False) + "\n")



if __name__ == "__main__":
    unittest.main()
