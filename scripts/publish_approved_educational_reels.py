#!/usr/bin/env python3
"""Publish exact educational Reel IDs eligible under human or automatic policy."""
from __future__ import annotations

import json
import os
import re
import sys
import traceback
from pathlib import Path

# Executing `python scripts/publish_approved_educational_reels.py` puts the
# scripts/ directory, not the repository root, at sys.path[0]. Ensure `src`
# remains importable in the actual GitHub Actions entrypoint.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

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
            if record.get("approval_status") != "approved":
                raise RuntimeError("Persisted publish-policy decision is missing.")
            fact_check = record.get("fact_check") if isinstance(record.get("fact_check"), dict) else {}
            approval_mode = str(record.get("approval_mode", "")).strip()
            automated_policy_ok = (
                approval_mode == "automated_policy"
                and record.get("human_approval_required") is False
                and bool(record.get("automated_review_at"))
                and fact_check.get("status") == "automated_passed"
            )
            human_policy_ok = (
                record.get("human_approval_required") is True
                and fact_check.get("status") == "approved"
                and bool(record.get("reviewed_at"))
                and bool(record.get("reviewed_by"))
            )
            if not (automated_policy_ok or human_policy_ok):
                raise RuntimeError("Neither the automated safety gate nor the legacy human-review gate is complete.")

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
            print(f"Educational Reel publish failed for {content_id}: {type(exc).__name__}; credentials and response bodies are not logged.")
            # Log only the source locations and, for NameError, the missing Python
            # identifier. Do not print exception messages or request/credential data.
            try:
                frames = traceback.extract_tb(exc.__traceback__)[-6:]
                for frame in frames:
                    print(f"Safe diagnostic frame: {Path(frame.filename).name}:{frame.lineno} in {frame.name}")
                if isinstance(exc, NameError):
                    missing_name = getattr(exc, "name", None)
                    if isinstance(missing_name, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", missing_name):
                        print(f"Undefined Python identifier: {missing_name}")
            except Exception:
                print("Safe diagnostic trace unavailable.")
        finally:
            # Save after every ID, including partial publication or an exception,
            # so recorded Instagram/Telegram IDs and ambiguous outcomes survive.
            save_state_atomic(path, state)

    return 1 if failed else 0


def main() -> int:
    return publish_ids(os.environ.get("EDUCATIONAL_APPROVED_IDS", ""))


if __name__ == "__main__":
    raise SystemExit(main())
