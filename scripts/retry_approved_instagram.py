#!/usr/bin/env python3
"""Safely select and reserve a one-time retry for a recent, already-approved Instagram auth failure."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

STATE_PATH = Path(os.getenv("MARKET_STATE_FILE", "data/state.json"))
MAX_APPROVAL_AGE_HOURS = 24


def parse_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def record_is_eligible(record: dict, now: datetime) -> bool:
    if record.get("approval_status") != "approved":
        return False
    if record.get("status") not in {"publish_failed", "partial"}:
        return False

    publishing = record.get("publishing") or {}
    telegram = publishing.get("telegram") or {}
    instagram = publishing.get("instagram") or {}
    if telegram.get("status") != "published" or instagram.get("status") != "failed":
        return False
    if "code=190" not in str(instagram.get("error") or ""):
        return False
    if instagram.get("auto_recovery_attempted_at"):
        return False

    approved_at = parse_time(record.get("approved_at") or (record.get("approval") or {}).get("decided_at"))
    if approved_at is None:
        return False
    approval_age = (now - approved_at).total_seconds() / 3600
    if approval_age < -0.1 or approval_age > MAX_APPROVAL_AGE_HOURS:
        return False

    signal = record.get("signal") or {}
    as_of = parse_time(signal.get("as_of"))
    if as_of is None:
        return False
    signal_age = (now - as_of).total_seconds() / 3600
    max_signal_age = 36 if signal.get("symbol") in {"BTC-USD", "ETH-USD", "BTCUSD", "ETHUSD"} else 20
    if signal_age < -0.0833 or signal_age > max_signal_age:
        return False
    return True


def find_candidate(state: dict, now: datetime | None = None) -> str | None:
    now = now or datetime.now(timezone.utc)
    signals = state.get("signals") if isinstance(state, dict) else None
    if not isinstance(signals, dict):
        return None
    eligible = []
    for signal_id, record in signals.items():
        if isinstance(record, dict) and record_is_eligible(record, now):
            approval_time = parse_time(record.get("approved_at") or (record.get("approval") or {}).get("decided_at"))
            eligible.append((approval_time or datetime.min.replace(tzinfo=timezone.utc), str(signal_id)))
    return max(eligible)[1] if eligible else None


def reserve_retry(state: dict, signal_id: str, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    record = (state.get("signals") or {}).get(signal_id)
    if not isinstance(record, dict) or not record_is_eligible(record, now):
        return False
    publishing = record.setdefault("publishing", {})
    instagram = publishing.setdefault("instagram", {})
    instagram["auto_recovery_attempted_at"] = now.astimezone(timezone.utc).isoformat()
    instagram["auto_recovery_reason"] = "One-time retry after Meta OAuth error 190, using the health-checked system-user token first."
    return True


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp = STATE_PATH.with_suffix(STATE_PATH.suffix + ".tmp")
    temp.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(STATE_PATH)


def write_output(signal_id: str) -> None:
    output = os.getenv("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(f"signal_id={signal_id}\n")


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in {"peek", "reserve", "render"}:
        print("Usage: retry_approved_instagram.py peek | reserve SIGNAL_ID | render SIGNAL_ID")
        return 2
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print("No readable market state; no Instagram recovery will run.")
        if sys.argv[1] == "peek":
            write_output("")
            return 0
        return 1

    action = sys.argv[1]
    if action == "peek":
        signal_id = find_candidate(state)
        write_output(signal_id or "")
        print("Eligible, already-approved Instagram recovery found." if signal_id else
              "No recent approved Instagram-only auth failure needs recovery.")
        return 0

    if len(sys.argv) != 3:
        print("A signal ID is required.")
        return 2
    signal_id = sys.argv[2]
    record = (state.get("signals") or {}).get(signal_id)
    if not isinstance(record, dict):
        print("Signal not found; no recovery action taken.")
        return 1

    if action == "reserve":
        if not reserve_retry(state, signal_id):
            print("Signal is no longer eligible; no recovery reserved.")
            return 1
        save_state(state)
        print("Reserved one retry for an already-approved Instagram-only failure.")
        return 0

    # Render locally because Actions runners do not retain generated PNGs between runs.
    marker = ((record.get("publishing") or {}).get("instagram") or {}).get("auto_recovery_attempted_at")
    if not marker or record.get("approval_status") != "approved":
        print("Recovery reservation or human approval missing; no card rendered.")
        return 1
    from agents.card import render_card
    card_path = render_card(record["signal"], output_dir="output")
    record["card_path"] = str(card_path)
    save_state(state)
    print("Recreated the existing approved card for the Instagram-only retry.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
