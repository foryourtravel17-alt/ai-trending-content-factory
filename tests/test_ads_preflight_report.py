import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.ads_preflight_report import (
    build_report,
    fetch_media_insights,
    load_published_posts,
    score_metrics,
)


class AdsPreflightTests(unittest.TestCase):
    def test_weighted_engagement_score_is_normalized_by_reach(self):
        score = score_metrics({
            "reach": 1000, "likes": 20, "comments": 5, "saved": 10, "shares": 4
        })
        self.assertIsNotNone(score)
        self.assertEqual(score["interactions"], 39)
        self.assertEqual(score["weighted_engagement"], 68)
        self.assertEqual(score["weighted_engagement_per_reach_pct"], 6.8)

    def test_zero_reach_is_not_ranked(self):
        self.assertIsNone(score_metrics({"reach": 0, "likes": 100}))

    def test_only_recent_published_instagram_content_is_selected(self):
        now = datetime(2026, 10, 12, 4, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            published = {
                "content_id": "post-1",
                "created_at": (now - timedelta(days=1)).isoformat(),
                "status": "published_to_instagram",
                "topic": {"title": "Risk before reward"},
                "script": {"hook": "Plan risk first"},
                "publishing": {
                    "instagram": {"status": "published_to_instagram", "media_id": "ig-1"}
                },
            }
            unposted = {
                "content_id": "draft-1",
                "created_at": (now - timedelta(hours=2)).isoformat(),
                "status": "approved_for_publishing",
                "topic": {"title": "Unposted draft"},
                "publishing": {"instagram": {"status": "pending"}},
            }
            stale = {
                **published,
                "content_id": "stale-1",
                "created_at": (now - timedelta(days=45)).isoformat(),
                "publishing": {"instagram": {"status": "published", "media_id": "ig-old"}},
            }
            (root / "content_1.json").write_text(json.dumps(published), encoding="utf-8")
            (root / "content_2.json").write_text(json.dumps(unposted), encoding="utf-8")
            (root / "content_3.json").write_text(json.dumps(stale), encoding="utf-8")

            result = load_published_posts(root, now=now)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["media_id"], "ig-1")
            self.assertEqual(result[0]["title"], "Risk before reward")

    @patch("scripts.ads_preflight_report.requests.get")
    def test_fetch_insights_parses_only_supported_numeric_metrics(self, get):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "data": [
                {"name": "reach", "values": [{"value": 500}]},
                {"name": "likes", "values": [{"value": 20}]},
                {"name": "comments", "values": [{"value": 3}]},
                {"name": "unsupported", "values": [{"value": 999}]},
            ]
        }
        get.return_value = response
        self.assertEqual(
            fetch_media_insights("media-1", "hidden-token"),
            {"reach": 500, "likes": 20, "comments": 3},
        )
        self.assertNotIn("hidden-token", repr(get.call_args))

    def test_report_never_says_campaign_was_launched(self):
        now = datetime(2026, 10, 12, 4, 0, tzinfo=timezone.utc)
        message = build_report([], {}, now=now)
        self.assertIn("READ-ONLY", message)
        self.assertIn("Campaign created/edited/activated: NO", message)
        self.assertIn("Budget changed: NO. Spend: NO.", message)
        self.assertIn("Owner must confirm the exact Meta ad account", message)

    def test_report_labels_engagement_as_not_sales(self):
        now = datetime(2026, 10, 12, 4, 0, tzinfo=timezone.utc)
        posts = [{
            "media_id": "ig-2",
            "title": "Trading journal",
            "created_at": now.isoformat(),
            "permalink": "",
            "hook": "",
            "content_role": "educational",
            "content_id": "post-2",
        }]
        message = build_report(posts, {"ig-2": {"reach": 100, "likes": 10}}, now=now)
        self.assertIn("does not establish course sales", message)
        self.assertIn("Trading journal", message)


if __name__ == "__main__":
    unittest.main()
