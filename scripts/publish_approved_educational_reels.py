#!/usr/bin/env python3
"""Publish only exact educational Reel IDs newly approved by the Telegram poller."""
from __future__ import annotations

import json
import os
from pathlib import Path

from src.instagram_publish import publish_approved_educational_reel

STATE_PATH = Path("data/state.json")
SAFE_ID = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")


def save_state_atomic(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(path)


def read_state(path: Path) -> dict:
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise RuntimeError("Shared approval state is missing or unreadable.") from None
    if not isinstance(state, dict) or not isinstance(state.get("signals"), dict):
        raise RuntimeError("Shared approval state has an unsupported format.")
    return state


def publish_ids(raw_ids: str, state_path: Path | None = None) -> int:
    path = state_path or STATE_PATH
    ids = list(dict.fromkeys(part.strip() for part in raw_ids.split(",") if part.strip()))
    if not ids:
        print("No newly approved educational Reel IDs were supplied; nothing to publish.")
        return 0

    state = read_state(path)
    signals = state["signals"]
    failed = False

    for content_id in ids:
        record = signals.get(content_id)
        try:
            if not content_id or any(ch not in SAFE_ID for ch in content_id):
                raise RuntimeError("Unsafe content ID.")
            if not isinstance(record, dict) or record.get("content_id") != content_id:
                raise RuntimeError("Matching shared-state record is missing.")
            if record.get("content_type") != "educational_reel":
                raise RuntimeError("Record is not an educational Reel.")
            if record.get("human_approval_required") is not True:
                raise RuntimeError("Human approval is not marked as required.")
            if record.get("approval_status") != "approved":
                raise RuntimeError("Persisted human approval is missing.")
            fact_check = record.get("fact_check") if isinstance(record.get("fact_check"), dict) else {}
            if (
                fact_check.get("status") != "approved"
                or not record.get("reviewed_at")
                or not record.get("reviewed_by")
            ):
                raise RuntimeError("Persisted human fact-check review is incomplete.")

            updated = publish_approved_educational_reel(record)
            if not isinstance(updated, dict):
                raise RuntimeError("Educational publisher returned an invalid record.")
            signals[content_id] = updated
            updated.pop("last_publish_error", None)
            print(f"Educational Reel publisher completed for {content_id}; state persisted.")
        except Exception as exc:
            failed = True
            if isinstance(record, dict):
                record["last_publish_error"] = type(exc).__name__
                signals[content_id] = record
            print(f"Educational Reel publish failed for {content_id}: {type(exc).__name__}; see Actions logs.")
        finally:
            # Save after every ID, including partial publication or an exception,
            # so recorded Instagram/Telegram IDs and ambiguous outcomes survive.
            save_state_atomic(path, state)

    return 1 if failed else 0


def main() -> int:
    return publish_ids(os.environ.get("EDUCATIONAL_APPROVED_IDS", ""))


if __name__ == "__main__":
    raise SystemExit(main())
