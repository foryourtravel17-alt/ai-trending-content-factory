"""Validate market scenarios and deduplicate using data/state.json."""
from __future__ import annotations
import json
import math
from pathlib import Path

STATE_PATH = Path("data/state.json")

def load_state() -> dict:
    if not STATE_PATH.exists():
        return {"signals": {}, "runs": []}
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.setdefault("signals", {})
            data.setdefault("runs", [])
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {"signals": {}, "runs": []}

def validate(signal: dict, state: dict) -> tuple[bool, str]:
    required = ("signal_id", "symbol", "direction", "entry", "stop_loss", "tp1", "tp2", "tp3", "rr_tp2")
    if any(k not in signal for k in required):
        return False, "required field missing"
    try:
        entry, stop = float(signal["entry"]), float(signal["stop_loss"])
        targets = [float(signal[f"tp{i}"]) for i in (1, 2, 3)]
    except (TypeError, ValueError):
        return False, "levels must be numeric"
    if not all(math.isfinite(x) and x > 0 for x in [entry, stop, *targets]):
        return False, "levels must be finite positive prices"
    direction = str(signal["direction"]).upper()
    if direction == "LONG":
        if not stop < entry < targets[0] < targets[1] < targets[2]:
            return False, "LONG level ordering invalid"
    elif direction == "SHORT":
        if not stop > entry > targets[0] > targets[1] > targets[2]:
            return False, "SHORT level ordering invalid"
    else:
        return False, "neutral or unknown direction is not publishable"
    risk = abs(entry - stop)
    rr = abs(targets[1] - entry) / risk
    if risk <= 0 or rr < 1.5 - 1e-9:
        return False, f"risk/reward to TP2 below 1.5 ({rr:.4f})"
    prior = state.get("signals", {})
    if signal["signal_id"] in prior:
        return False, "duplicate signal_id"
    for existing in prior.values():
        if (existing.get("symbol") == signal["symbol"]
                and existing.get("as_of") == signal.get("as_of")
                and existing.get("direction") == direction):
            return False, "same symbol/direction/bar already recorded"
    return True, "passed"
