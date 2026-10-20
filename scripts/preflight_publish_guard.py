"""Preflight guard for human-approved market signal publishing."""
from __future__ import annotations
import json
import sys
from pathlib import Path

def should_publish(record: dict) -> tuple[bool, str]:
    if not record:
        return False, "signal missing from state"
    if record.get("approval_status") != "approved":
        return False, "signal is not human-approved"
    signal = record.get("signal", {})
    if not signal or not signal.get("signal_id") or not signal.get("as_of"):
        return False, "signal payload is incomplete"
    publishing = record.get("publishing", {})
    telegram = publishing.get("telegram", {}).get("status")
    instagram = publishing.get("instagram", {}).get("status")
    if telegram == "published" and instagram == "published":
        return False, "already fully published"
    if record.get("status") == "published":
        return False, "record already marked published"
    return True, f"retry allowed (telegram={telegram}, instagram={instagram})"

def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: preflight_publish_guard.py SIGNAL_ID")
        return 2
    state_path = Path("data/state.json")
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print("BLOCKED: state file missing or unreadable")
        return 1
    signal_id = sys.argv[1]
    allowed, reason = should_publish(state.get("signals", {}).get(signal_id, {}))
    print(f"{signal_id}: {reason}")
    return 0 if allowed else 1

if __name__ == "__main__":
    raise SystemExit(main())
