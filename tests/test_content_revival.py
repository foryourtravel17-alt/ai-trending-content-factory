import unittest

from src import main as factory


class ContentRevivalTests(unittest.TestCase):
    def test_topic_library_covers_required_content_pillars(self):
        markets = {str(topic.get("market", "")).lower() for topic in factory.TOPICS}
        titles = " ".join(topic["title"].lower() for topic in factory.TOPICS)
        self.assertTrue(any("crypto" in market for market in markets))
        self.assertTrue(any("dollar" in market for market in markets))
        self.assertIn("course preview", titles)
        self.assertIn("liquidity sweep", titles)
        self.assertGreaterEqual(len(factory.TOPICS), 25)

    def test_topics_have_real_educational_payload(self):
        for topic in factory.TOPICS:
            with self.subTest(title=topic["title"]):
                self.assertTrue(topic.get("hook", "").strip())
                self.assertTrue(topic.get("body", "").strip())
                self.assertGreaterEqual(len(topic.get("visuals", [])), 3)
                self.assertTrue(topic.get("hashtags"))

    def test_caption_uses_hook_and_soft_cta(self):
        topic = {
            "title": "Example topic",
            "hook": "A useful first-second hook.",
            "body": "A practical educational takeaway.",
            "hashtags": ["#BullseyeTheory"],
        }
        script = {
            "hook": "Stop treating one candle as confirmation.",
            "body": "Study the close, context, and follow-through.",
            "cta": "Save this checklist for your next chart review.",
        }
        result = factory.caption_and_hashtags(topic, script)
        self.assertIn(script["hook"], result["caption"])
        self.assertIn(script["body"], result["caption"])
        self.assertIn(script["cta"], result["caption"])
        self.assertIn(factory.DISCLAIMER, result["caption"])
        self.assertEqual(result["hashtags"], topic["hashtags"])

    def test_topic_library_does_not_claim_live_signals(self):
        for topic in factory.TOPICS:
            with self.subTest(title=topic["title"]):
                self.assertNotIn("buy now", topic.get("hook", "").lower())
                self.assertNotIn("guaranteed profit", topic.get("body", "").lower())


if __name__ == "__main__":
    unittest.main()
