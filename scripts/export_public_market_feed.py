"""Export a minimal public Market Lab feed containing only fresh, human-approved observations.

Never export numerical trading levels, pending drafts, raw copy, or internal state.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE_PATH = Path("data/state.json")
OUTPUT_PATH = Path("data/approved_market_feed.json")
BLOCKED_STATUSES = {"pending_approval", "rejected", "expired"}


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def build_public_feed(
    state: dict[str, Any],
    now: datetime | None = None,
    max_age_hours: int = 8,
) -> dict[str, Any]:
    """Return an allow-listed public payload, excluding levels and internal fields."""
    if not isinstance(max_age_hours, int) or not 1 <= max_age_hours <= 24:
        raise ValueError("max_age_hours must be an integer between 1 and 24")
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    current = current.astimezone(timezone.utc)

    rows: list[dict[str, Any]] = []
    signals = state.get("signals", {}) if isinstance(state, dict) else {}
    if not isinstance(signals, dict):
        signals = {}

    for signal_id, record in signals.items():
        if not isinstance(record, dict):
            continue
        if record.get("approval_status") != "approved":
            continue
        status = str(record.get("status", "")).strip().lower()
        if status in BLOCKED_STATUSES:
            continue

        signal = record.get("signal")
        analyst = record.get("analyst")
        if not isinstance(signal, dict) or not isinstance(analyst, dict):
            continue
        as_of = _parse_timestamp(signal.get("as_of"))
        if as_of is None:
            continue
        age_hours = (current - as_of).total_seconds() / 3600
        if age_hours < -1 or age_hours > max_age_hours:
            continue

        symbol = signal.get("symbol")
        label = signal.get("label") or symbol
        view = analyst.get("view")
        caveat = analyst.get("caveat")
        direction = str(signal.get("direction", "")).upper()
        if not all(isinstance(v, str) and v.strip() for v in (symbol, label, view, caveat)):
            continue
        if direction not in {"LONG", "SHORT"}:
            continue

        # Explicit allow-list: do not pass through signal, copy, publishing, paths or price levels.
        rows.append({
            "id": str(signal_id),
            "symbol": symbol.strip(),
            "label": label.strip(),
            "direction": direction,
            "as_of": as_of.isoformat(),
            "view": view.strip(),
            "caveat": caveat.strip(),
            "approvalStatus": "approved",
        })

    rows.sort(key=lambda item: item["as_of"], reverse=True)
    return {
        "schemaVersion": 1,
        "generatedAt": current.isoformat(),
        "source": "Bullseye Theory educational market factory",
        "dataStatus": "human_approved_observations",
        "maxObservationAgeHours": max_age_hours,
        "disclaimer": (
            "Educational structure observations only. Not a forecast or a recommendation "
            "to buy, sell, or hold. Conditions can change; scenarios can fail."
        ),
        "records": rows[:12],
    }


def export_public_feed(
    state_path: Path = STATE_PATH,
    output_path: Path = OUTPUT_PATH,
    max_age_hours: int = 8,
) -> dict[str, Any]:
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        state = {"signals": {}}
    if not isinstance(state, dict):
        state = {"signals": {}}
    feed = build_public_feed(state, max_age_hours=max_age_hours)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    temp_path.write_text(json.dumps(feed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp_path.replace(output_path)
    print(f"Exported {len(feed['records'])} fresh approved Market Lab observations to {output_path}")
    return feed


if __name__ == "__main__":
    configured_age = int(os.environ.get("PUBLIC_MARKET_FEED_MAX_AGE_HOURS", "8"))
    export_public_feed(max_age_hours=configured_age)
