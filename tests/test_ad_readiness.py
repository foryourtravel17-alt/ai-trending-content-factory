import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.ad_readiness import build_report, load_recent_published_posts, rank_candidates


class OrganicAdsReadinessTests(unittest.TestCase):
    def test_load_filters_recent_published_instagram_media(self):
        now = datetime(2026, 10, 12, 10, 0, tzinfo=timezone.utc)
        records = [
            {
                "content_id": "good",
                "created_at": (now - timedelta(hours=3)).isoformat(),
                "status": "published_to_instagram",
                "topic": {"title": "Risk before reward"},
                "publishing": {"instagram": {"status": "published_to_instagram", "media_id": "111"}},
            },
            {
                "content_id": "stale",
                "created_at": (now - timedelta(days=30)).isoformat(),
                "status": "published_to_instagram",
                "publishing": {"instagram": {"status": "published_to_instagram", "media_id": "222"}},
            },
            {
                "content_id": "telegram_only",
                "created_at": (now - timedelta(hours=1)).isoformat(),
                "status": "published",
                "publishing": {"telegram": {"status": "published"}},
            },
            {
                "content_id": "failed",
                "created_at": (now - timedelta(hours=1)).isoformat(),
                "status": "publish_failed",
                "publishing": {"instagram": {"status": "failed", "media_id": "333"}},
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for record in records:
                (root / f"content_{record['content_id']}.json").write_text(
                    json.dumps(record), encoding="utf-8"
                )
            posts = load_recent_published_posts(root, lookback_days=14, now=now)

        self.assertEqual([post["content_id"] for post in posts], ["good"])
        self.assertEqual(posts[0]["media_id"], "111")
        self.assertEqual(posts[0]["title"], "Risk before reward")

    def test_rank_prefers_save_and_share_rate(self):
        posts = [
            {"content_id": "broad", "media_id": "broad", "title": "Broad reach"},
            {"content_id": "quality", "media_id": "quality", "title": "Saved and shared"},
        ]
        metrics = {
            "broad": {"reach": 2000, "likes": 80, "comments": 5, "saved": 1, "shares": 0},
            "quality": {"reach": 200, "likes": 16, "comments": 2, "saved": 12, "shares": 8},
        }
        ranked = rank_candidates(posts, metrics)
        self.assertEqual(ranked[0]["content_id"], "quality")
        self.assertGreater(ranked[0]["save_share_rate"], ranked[1]["save_share_rate"])

    def test_report_requires_more_data_before_boost_recommendation(self):
        report = build_report(
            [{"title": "One post", "reach": 100, "likes": 10, "comments": 1, "saved": 0,
              "shares": 0, "engagement_rate": 0.11}],
            published_count=1,
        )
        self.assertIn("STATUS: EARLY DATA", report)
        self.assertIn("No ad, campaign, audience, budget, or payment was created or changed", report)
        self.assertIn("approve the complete campaign preview", report)

    def test_empty_data_is_hold_not_an_ad_recommendation(self):
        report = build_report([], published_count=0)
        self.assertIn("STATUS: HOLD", report)
        self.assertIn("missing data", report.lower())


if __name__ == "__main__":
    unittest.main()
