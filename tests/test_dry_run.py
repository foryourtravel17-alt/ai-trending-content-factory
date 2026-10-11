"""Synthetic end-to-end smoke test: render chart/card/copy and prove DRY_RUN never posts."""
import os
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from agents.scout import compute_indicators, make_signal
from agents.charts import render_chart
from agents.card import render_card
from agents.analyst import analyze
from agents.copy import build_copy
from agents.qa import validate
from agents.publisher import publish

class DryRunSmokeTest(unittest.TestCase):
    def test_agent_chain_renders_without_network_posts(self):
        os.environ["DRY_RUN"] = "1"
        count = 240
        idx = pd.date_range(end=pd.Timestamp.now(tz="UTC").floor("h"), periods=count, freq="h")
        t = np.arange(count, dtype=float)
        close = 100 + 0.03 * t + 0.5 * np.sin(t / 8.0)
        frame = pd.DataFrame({
            "Open": close - 0.03, "High": close + 0.35, "Low": close - 0.35,
            "Close": close, "Volume": np.full(count, 1000.0),
        }, index=idx)
        indicators = compute_indicators(frame)
        signal = make_signal("TEST", "Synthetic Test", "GLOBAL", indicators)
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
            result = publish(signal, copy, Path(card), record, dry_run=True)
            self.assertEqual(result["status"], "dry_run")
            self.assertEqual(result["publishing"], {})
            self.assertTrue(result["copy"]["instagram_caption"] if "copy" in result else copy["instagram_caption"])

if __name__ == "__main__":
    unittest.main()
