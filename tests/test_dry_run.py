"""Synthetic end-to-end smoke tests: render images/copy and prove DRY_RUN never posts."""
import os
import tempfile
from datetime import datetime, timedelta, timezone
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from agents.scout import compute_indicators, make_signal
from agents.charts import render_chart
from agents.card import render_card
from agents.analyst import analyze
from agents.copy import build_copy
from agents.qa import validate
from agents.publisher import publish
import src.orchestrator as orchestrator


def synthetic_market():
    count = 240
    idx = pd.date_range(end=pd.Timestamp.now(tz="UTC").floor("h"), periods=count, freq="h")
    t = np.arange(count, dtype=float)
    close = 100 + 0.015 * t + 0.5 * np.sin((t - 195.0) / 8.0)
    frame = pd.DataFrame({
        "Open": close - 0.03, "High": close + 0.35, "Low": close - 0.35,
        "Close": close, "Volume": np.full(count, 1000.0),
    }, index=idx)
    indicators = compute_indicators(frame)
    signal = make_signal("TEST", "Synthetic Test", "GLOBAL", indicators)
    return indicators, signal


class DryRunSmokeTest(unittest.TestCase):
    def test_stale_prepared_signals_are_not_publishable(self):
        now = datetime.now(timezone.utc)
        self.assertTrue(orchestrator._signal_is_fresh({
            "symbol": "BTC-USD", "as_of": now.isoformat()
        }))
        self.assertFalse(orchestrator._signal_is_fresh({
            "symbol": "BTC-USD", "as_of": (now - timedelta(hours=50)).isoformat()
        }))
        self.assertFalse(orchestrator._signal_is_fresh({"symbol": "TEST"}))

    def test_agent_chain_renders_without_network_posts(self):
        os.environ["DRY_RUN"] = "1"
        indicators, signal = synthetic_market()
        self.assertIsNotNone(signal, "synthetic trend should produce a non-neutral scenario")
        with tempfile.TemporaryDirectory() as tmp:
            chart = render_chart(indicators, signal, tmp)
            card = render_card(signal, tmp)
            self.assertTrue(chart.is_file() and chart.stat().st_size > 1000)
            self.assertTrue(card.is_file() and card.stat().st_size > 1000)
            analyst = analyze(signal)
            copy = build_copy(signal, analyst)
            self.assertTrue(copy["telegram_html"])
            self.assertTrue(copy["instagram_caption"])
            ok, reason = validate(signal, {"signals": {}})
            self.assertTrue(ok, reason)
            record = {"signal": signal, "copy": copy, "publishing": {}}
            result = publish(signal, copy, Path(card), record, dry_run=os.getenv("DRY_RUN", "0") == "1")
            self.assertEqual(result["status"], "generated")
            self.assertEqual(result["last_run_mode"], "dry_run")
            self.assertEqual(result["publishing"], {})

    def test_orchestrator_end_to_end_dry_run(self):
        indicators, signal = synthetic_market()
        self.assertIsNotNone(signal)
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                state_path = Path(tmp) / "data" / "state.json"
                state_path.parent.mkdir(parents=True)
                state_path.write_text('{"signals": {}, "runs": []}', encoding="utf-8")
                with patch("agents.qa.STATE_PATH", state_path), \
                     patch.object(orchestrator, "STATE_PATH", state_path), \
                     patch.object(orchestrator, "SYMBOLS", {"GLOBAL": {"TEST": "Synthetic Test"}}), \
                     patch.object(orchestrator, "scout_symbol", return_value={"frame": indicators, "signal": signal}), \
                     patch.object(orchestrator, "DRY_RUN", True), \
                     patch.object(orchestrator, "GENERATE_ONLY", False), \
                     patch.object(orchestrator, "PUBLISH_ONLY", False), \
                     patch.object(orchestrator, "HUMAN_APPROVAL", False):
                    self.assertEqual(orchestrator.main(), 0)
                self.assertTrue(Path("output", f"{signal['slug']}.png").is_file())
                self.assertTrue(Path("output", f"{signal['slug']}_card.png").is_file())
                saved = __import__("json").loads(state_path.read_text(encoding="utf-8"))
                record = saved["signals"][signal["signal_id"]]
                self.assertEqual(record["status"], "generated")
                self.assertEqual(record["last_run_mode"], "dry_run")
                self.assertEqual(record["publishing"], {})
            finally:
                os.chdir(original_cwd)

if __name__ == "__main__":
    unittest.main()
