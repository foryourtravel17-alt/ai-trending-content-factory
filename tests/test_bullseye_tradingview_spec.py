from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDICATOR = (ROOT / "bullseye_tradingview" / "Bullseye_Structure_Study.pine").read_text(encoding="utf-8")
STRATEGY = (ROOT / "bullseye_tradingview" / "Bullseye_Backtest_Strategy.pine").read_text(encoding="utf-8")
RULEBOOK = (ROOT / "bullseye_tradingview" / "Rulebook.md").read_text(encoding="utf-8")

class BullseyeSpecTests(unittest.TestCase):
    def test_five_pillar_status_and_scope_inputs(self):
        for item in ["SCOPE", "TARGET", "TRIGGER", "SHIELD", "BULLSEYE", "GUARDRAILS"]:
            self.assertIn(item, INDICATOR)
        self.assertIn('input.timeframe("240"', INDICATOR)
        self.assertIn('input.int(50, "Scope EMA fast"', INDICATOR)
        self.assertIn('input.int(200, "Scope EMA slow"', INDICATOR)
        self.assertIn('input.int(21, "Pullback EMA"', INDICATOR)

    def test_completed_htf_candles_and_confirmed_trigger(self):
        self.assertGreaterEqual(INDICATOR.count("request.security("), 2)
        self.assertIn("ta.ema(close, scopeFastLen)[1]", INDICATOR)
        self.assertIn("ta.ema(close, scopeSlowLen)[1]", INDICATOR)
        self.assertGreaterEqual(INDICATOR.count("lookahead=barmerge.lookahead_on"), 2)
        self.assertIn("barstate.isconfirmed", INDICATOR)

    def test_zone_session_daily_cap_and_news_guard(self):
        self.assertIn("zoneMult", INDICATOR)
        self.assertIn("stopAtr", INDICATOR)
        self.assertIn('input.session("1200-2000:1234567"', INDICATOR)
        self.assertIn("newsBlackout", INDICATOR)
        self.assertIn("setupsToday < maxPerDay", INDICATOR)
        self.assertIn("Asia/Kolkata", INDICATOR)

    def test_backtest_has_risk_and_split_exits(self):
        self.assertIn("riskPct", STRATEGY)
        self.assertIn("qty_percent=partialPct", STRATEGY)
        self.assertIn("qty_percent=100.0 - partialPct", STRATEGY)
        self.assertIn("targetR", STRATEGY)

    def test_disclaimer_and_rules_present(self):
        self.assertIn("Past behaviour does not guarantee future results", RULEBOOK)
        self.assertIn("Maximum two", RULEBOOK)
        self.assertIn("15 minutes", RULEBOOK)

if __name__ == "__main__":
    unittest.main()
