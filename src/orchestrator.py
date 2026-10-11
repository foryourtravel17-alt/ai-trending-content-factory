"""Run the autonomous market-content chain; each symbol fails independently."""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from agents.analyst import analyze
from agents.card import render_card
from agents.charts import render_chart
from agents.copy import build_copy
from agents.qa import STATE_PATH, load_state, validate
from agents.publisher import publish
from agents.scout import SYMBOLS, MAX_PER_REGION, scout_symbol

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO),
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("orchestrator")
OUTPUT = Path("output")
DRY_RUN = os.getenv("DRY_RUN", "0").strip().lower() in {"1", "true", "yes"}
HUMAN_APPROVAL = os.getenv("HUMAN_APPROVAL", "false").strip().lower() == "true"


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp = STATE_PATH.with_suffix(".tmp")
    temp.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(STATE_PATH)


def _retry_pending(state: dict) -> None:
    """When approval mode is switched off, publish prior DM drafts without regenerating."""
    if HUMAN_APPROVAL or DRY_RUN:
        return
    for signal_id, record in list(state.get("signals", {}).items()):
        if record.get("status") != "pending_approval":
            continue
        try:
            card_path = Path(record.get("card_path", ""))
            if not card_path.exists():
                log.warning("Pending draft %s has no card image; skipping retry.", signal_id)
                continue
            updated = publish(record["signal"], record["copy"], card_path, record,
                              dry_run=DRY_RUN)
            state["signals"][signal_id] = updated
            save_state(state)
        except Exception:
            log.exception("Pending draft publish retry failed for %s.", signal_id)
            record["last_error"] = "Retry failed; see Actions logs."
            save_state(state)


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    state = load_state()
    _retry_pending(state)
    results = {"checked": 0, "signals": 0, "skipped": 0, "errors": 0}
    candidates = []
    for region, universe in SYMBOLS.items():
        region_candidates = []
        for symbol, label in universe.items():
            results["checked"] += 1
            try:
                analysis = scout_symbol(symbol, label, region)
                signal = analysis["signal"]
                if not signal:
                    results["skipped"] += 1
                    continue
                region_candidates.append((int(signal["score"]), signal, analysis["frame"]))
                log.info("%s: %s scenario, score=%s, as_of=%s",
                         symbol, signal["direction"], signal["score"], signal["as_of"])
            except Exception as exc:
                results["errors"] += 1
                log.warning("Symbol %s failed; continuing to next symbol: %s", symbol, exc)
        region_candidates.sort(key=lambda item: item[0], reverse=True)
        candidates.extend(region_candidates[:MAX_PER_REGION])

    for _, signal, frame in candidates:
        signal_id = signal["signal_id"]
        prior = state.setdefault("signals", {}).get(signal_id)
        if prior and prior.get("status") not in {"pending_approval"}:
            log.info("Duplicate signal %s already recorded with status=%s; skipped.",
                     signal_id, prior.get("status"))
            results["skipped"] += 1
            continue
        try:
            chart_path = render_chart(frame, signal)
            card_path = render_card(signal)
            analyst = analyze(signal)
            copy = build_copy(signal, analyst)
            record = prior or {
                "signal": signal, "analyst": analyst, "copy": copy,
                "chart_path": str(chart_path), "card_path": str(card_path),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "publishing": {},
            }
            ok, reason = validate(signal, state)
            if not ok and not (prior and prior.get("status") == "pending_approval" and not HUMAN_APPROVAL):
                log.info("QA rejected %s: %s", signal_id, reason)
                results["skipped"] += 1
                continue
            if prior and prior.get("status") == "pending_approval" and not HUMAN_APPROVAL:
                record["signal"] = signal
                record["analyst"] = analyst
                record["copy"] = copy
            else:
                results["signals"] += 1
            # Persist a pending record before network calls to reduce duplicate posts on retries.
            state["signals"][signal_id] = record
            save_state(state)
            updated = publish(signal, copy, card_path, record, dry_run=DRY_RUN)
            state["signals"][signal_id] = updated
            state.setdefault("runs", []).append({
                "at": datetime.now(timezone.utc).isoformat(),
                "signal_id": signal_id, "status": updated.get("status"),
                "dry_run": DRY_RUN,
            })
            save_state(state)
            log.info("Completed %s with status=%s.", signal_id, updated.get("status"))
        except Exception:
            results["errors"] += 1
            log.exception("Signal %s failed; other symbols continue.", signal_id)
            if signal_id in state.get("signals", {}):
                state["signals"][signal_id]["last_error"] = "See workflow logs for details."
                save_state(state)
    log.info("Run summary: %s; dry_run=%s; human_approval=%s", results, DRY_RUN, HUMAN_APPROVAL)
    if results["errors"] and results["signals"] == 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
