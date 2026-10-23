from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "bullseye_tradingview"

class BullseyeEducationAssetTests(unittest.TestCase):
    def test_course_contains_eleven_lessons_and_answer_checks(self):
        text = (BASE / "Student_Course_Full.md").read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r"^## Lesson \d+ —", text, re.M)), 11)
        self.assertGreaterEqual(len(re.findall(r"^### Practice$", text, re.M)), 11)
        self.assertGreaterEqual(len(re.findall(r"^### Check yourself$", text, re.M)), 11)
        self.assertIn("does not guarantee future", text.lower())

    def test_telegram_calendar_has_thirty_educational_posts(self):
        text = (BASE / "Telegram_30_Educational_Posts.md").read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r"^## Day \d+ —", text, re.M)), 30)
        self.assertIn("not a live signal", text.lower())
        self.assertIn("pinned note", text.lower())

    def test_marketing_hooks_have_thirty_ideas_and_disclaimers(self):
        text = (BASE / "Marketing_30_Reel_Hooks.md").read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r"^## \d+\.", text, re.M)), 30)
        self.assertIn("Educational only", text)
        self.assertIn("Visual:", text)
        self.assertIn("Takeaway:", text)

    def test_landing_page_retains_prelaunch_placeholders(self):
        html = (BASE / "landing-page.html").read_text(encoding="utf-8")
        for placeholder in ["[COURSE DELIVERY LINK]", "[VERIFIED UPI / PAYMENT LINK]", "[SUPPORT CHANNEL]", "[REFUND POLICY]"]:
            self.assertIn(placeholder, html)
        self.assertIn("template", html.lower())
        self.assertIn("not personalized financial advice", html.lower())

    def test_launch_checklist_does_not_claim_tradingview_compile(self):
        text = (BASE / "LAUNCH_CHECKLIST.md").read_text(encoding="utf-8")
        self.assertIn("Compile both Pine files in TradingView", text)
        self.assertIn("prototype", text.lower())
        self.assertIn("no live account orders", text.lower())

if __name__ == "__main__":
    unittest.main()
