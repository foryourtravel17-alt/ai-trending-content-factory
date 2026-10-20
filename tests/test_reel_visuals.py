import unittest

from PIL import Image, ImageDraw

from src.reel_generator import chart_style_for_scene, draw_chart, topic_takeaway


class ReelVisualTests(unittest.TestCase):
    def test_chart_style_matches_educational_topic(self):
        cases = [
            ("Support and Resistance Are Zones", "A zone is not a magic line.", "MARK THE ZONE", "zones"),
            ("Liquidity Sweep", "Price moves through a prior swing.", "Wait for evidence", "sweep"),
            ("Retest After Breakout", "A retest can fail.", "RETEST ZONE", "retest"),
            ("CHOCH vs BOS", "Market structure labels need context.", "Change of character", "choch"),
            ("False Breakouts", "Wait for the close and follow-through.", "Define invalidation", "break"),
            ("Position Sizing Starts With Risk", "Set the amount at risk.", "Exposure", "risk"),
        ]
        for title, body, visual, expected in cases:
            with self.subTest(title=title):
                self.assertEqual(chart_style_for_scene(title, body, visual), expected)

    def test_support_resistance_chart_style_renders(self):
        image = Image.new("RGB", (1080, 1920), (8, 14, 27))
        draw = ImageDraw.Draw(image)
        draw_chart(draw, (80, 1230, 1000, 1595), "zones")
        self.assertIsNotNone(image.getbbox())

    def test_topic_takeaway_is_not_hardcoded_to_ema_crossovers(self):
        takeaway = topic_takeaway("Trading Psychology", "Review the plan, risk and execution.")
        self.assertNotIn("crossover", takeaway.lower())
        self.assertIn("context", takeaway.lower())
        self.assertIn("invalidation", takeaway.lower())

    def test_topic_takeaway_matches_risk_topic(self):
        takeaway = topic_takeaway("Position Sizing", "Risk and exposure matter.")
        self.assertIn("Position size", takeaway)
        self.assertIn("risk limits", takeaway)


if __name__ == "__main__":
    unittest.main()
