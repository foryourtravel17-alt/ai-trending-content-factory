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


    def test_live_run_recovers_signal_saved_by_prior_dry_run(self):
        indicators, signal = synthetic_market()
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                state_path = Path(tmp) / "data" / "state.json"
                output_dir = Path(tmp) / "output"
                output_dir.mkdir(parents=True)
                chart_path = output_dir / f"{signal['slug']}.png"
                card_path = output_dir / f"{signal['slug']}_card.png"
                chart_path.write_bytes(b"chart")
                card_path.write_bytes(b"card")
                prior = {
                    "signal": signal,
                    "analyst": {"view": "old dry-run view"},
                    "copy": {"telegram_html": "old draft", "instagram_caption": "old draft"},
                    "chart_path": str(chart_path),
                    "card_path": str(card_path),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "status": "generated",
                    "last_run_mode": "dry_run",
                    "publishing": {},
                }
                state_path.parent.mkdir(parents=True)
                state_path.write_text(
                    __import__("json").dumps(
                        {"signals": {signal["signal_id"]: prior}, "runs": []}
                    ),
                    encoding="utf-8",
                )
                publish_calls = []

                def fake_publish(signal_arg, copy_arg, card_path_arg, record_arg, dry_run=False):
                    publish_calls.append(signal_arg["signal_id"])
                    self.assertFalse(dry_run)
                    record_arg["status"] = "pending_approval"
                    record_arg.setdefault("publishing", {})["telegram_dm"] = {
                        "status": "sent",
                        "message_id": 123,
                    }
                    return record_arg

                with patch("agents.qa.STATE_PATH", state_path), \
                     patch.object(orchestrator, "STATE_PATH", state_path), \
                     patch.object(orchestrator, "SYMBOLS", {"GLOBAL": {"TEST": "Synthetic Test"}}), \
                     patch.object(orchestrator, "scout_symbol", return_value={"frame": indicators, "signal": signal}), \
                     patch.object(orchestrator, "render_chart", return_value=chart_path), \
                     patch.object(orchestrator, "render_card", return_value=card_path), \
                     patch.object(orchestrator, "analyze", return_value={"view": "fresh view"}), \
                     patch.object(orchestrator, "build_copy", return_value={"telegram_html": "draft", "instagram_caption": "caption"}), \
                     patch.object(orchestrator, "publish", side_effect=fake_publish), \
                     patch.object(orchestrator, "DRY_RUN", False), \
                     patch.object(orchestrator, "GENERATE_ONLY", False), \
                     patch.object(orchestrator, "PUBLISH_ONLY", False), \
                     patch.object(orchestrator, "HUMAN_APPROVAL", True):
                    self.assertEqual(orchestrator.main(), 0)

                self.assertEqual(publish_calls, [signal["signal_id"]])
                saved = __import__("json").loads(state_path.read_text(encoding="utf-8"))
                recovered = saved["signals"][signal["signal_id"]]
                self.assertEqual(recovered["status"], "pending_approval")
                self.assertEqual(recovered["publishing"]["telegram_dm"]["status"], "sent")
            finally:
                os.chdir(original_cwd)

if __name__ == "__main__":
    unittest.main()
