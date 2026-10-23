#!/usr/bin/env python3
"""One-time, duplicate-safe recovery of an approved educational Reel that failed before publish.

This utility is intentionally narrow:
- only previously approved automated-policy Reels,
- only a known pre-publish NameError with no platform outcome recorded,
- only while the exact uploaded MP4 is fresh and integrity metadata is present,
- one reservation per content ID, committed before any network publishing call.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

STATE_PATH = Path("data/state.json")
OUTPUT_DIR = Path("output")
MAX_AGE = timedelta(hours=24)
SAFE_ID = re.compile(r"^[A-Za-z0-9_-]+$")
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
KNOWN_SAFE_RETRY_ERROR = "NameError"


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def save_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(path)


def parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def safe_recovery_candidate(
    record: Any,
    metadata: Any,
    *,
    now: datetime | None = None,
) -> bool:
    """True only for the specific known pre-publish failure with no ambiguous outcome."""
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if not isinstance(record, dict) or not isinstance(metadata, dict):
        return False
    content_id = str(record.get("content_id", "")).strip()
    if not content_id or not SAFE_ID.fullmatch(content_id):
        return False
    if metadata.get("content_id") != content_id or record.get("content_type") != "educational_reel":
        return False
    if record.get("status") != "publish_failed" or record.get("last_publish_error") != KNOWN_SAFE_RETRY_ERROR:
        return False
    if record.get("approval_status") != "approved" or record.get("approval_mode") != "automated_policy":
        return False
    if record.get("human_approval_required") is not False or not record.get("automated_review_at"):
        return False
    fact = record.get("fact_check") if isinstance(record.get("fact_check"), dict) else {}
    if fact.get("status") != "automated_passed":
        return False
    if record.get("recovery_attempted_at"):
        return False

    # If the shared state already contains a platform result, treat it as ambiguous
    # and leave it to a human; this workflow does not retry partial or unknown sends.
    record_publishing = record.get("publishing") if isinstance(record.get("publishing"), dict) else {}
    for platform in ("instagram", "telegram"):
        platform_state = record_publishing.get(platform)
        if isinstance(platform_state, dict) and platform_state:
            return False
    if record.get("instagram_media_id") or record.get("published_at"):
        return False

    if metadata.get("status") != "approved_for_publishing":
        return False
    approval = metadata.get("approval") if isinstance(metadata.get("approval"), dict) else {}
    meta_fact = metadata.get("fact_check") if isinstance(metadata.get("fact_check"), dict) else {}
    safety = metadata.get("safety_check") if isinstance(metadata.get("safety_check"), dict) else {}
    if approval.get("status") != "approved" or approval.get("mode") != "automated_policy":
        return False
    if approval.get("required") is not False or not approval.get("automated_review_at"):
        return False
    if meta_fact.get("status") != "automated_passed" or safety.get("passed") is not True:
        return False

    publishing = metadata.get("publishing") if isinstance(metadata.get("publishing"), dict) else {}
    ig_state = publishing.get("instagram") if isinstance(publishing.get("instagram"), dict) else {}
    tg_state = publishing.get("telegram") if isinstance(publishing.get("telegram"), dict) else {}
    # The exact failed case is safe to retry only if it never reached either platform.
    if ig_state.get("status") != "ready_for_publish" or tg_state:
        return False
    if metadata.get("instagram_media_id") or metadata.get("published_at"):
        return False
    if not str(metadata.get("video_url", "")).startswith("https://"):
        return False
    if metadata.get("video_content_id") != content_id:
        return False
    if not SHA256_RE.fullmatch(str(metadata.get("video_sha256", ""))):
        return False
    try:
        if int(metadata.get("video_size_bytes", 0)) <= 0:
            return False
        if float(metadata.get("video_duration_seconds", 0)) <= 0:
            return False
    except (TypeError, ValueError):
        return False
    if not parse_time(metadata.get("video_uploaded_at")):
        return False

    created = parse_time(metadata.get("created_at"))
    if not created or created > now + timedelta(minutes=5) or now - created > MAX_AGE:
        return False
    return True


def find_candidate(
    state_path: Path = STATE_PATH,
    output_dir: Path = OUTPUT_DIR,
    *,
    now: datetime | None = None,
) -> tuple[str, dict, dict] | None:
    state = load_json(state_path)
    if not isinstance(state, dict) or not isinstance(state.get("signals"), dict):
        return None
    signals = state["signals"]
    rows = []
    for content_id, record in signals.items():
        if not isinstance(record, dict) or record.get("content_type") != "educational_reel":
            continue
        metadata_path = output_dir / f"{content_id}.json"
        metadata = load_json(metadata_path)
        if safe_recovery_candidate(record, metadata, now=now):
            created = parse_time(metadata.get("created_at")) or datetime.max.replace(tzinfo=timezone.utc)
            rows.append((created, str(content_id), record, metadata))
    if not rows:
        return None
    rows.sort(key=lambda row: row[0])  # Recover the oldest eligible item before it expires.
    _, content_id, record, metadata = rows[0]
    return content_id, record, metadata


def reserve_candidate(
    state_path: Path = STATE_PATH,
    output_dir: Path = OUTPUT_DIR,
    *,
    now: datetime | None = None,
    requested_id: str | None = None,
) -> str | None:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    candidate = find_candidate(state_path, output_dir, now=now)
    if not candidate:
        return None
    content_id, _, _ = candidate
    if requested_id and requested_id != content_id:
        return None
    state = load_json(state_path)
    record = state["signals"][content_id]
    # This reservation is written and committed before the publisher calls any API.
    record["recovery_attempted_at"] = now.isoformat()
    record["recovery_attempt_reason"] = "known NameError before platform publishing; no platform outcome recorded"
    record["recovery_attempt_count"] = 1
    save_json_atomic(state_path, state)
    return content_id


def write_output(content_id: str | None) -> None:
    output_path = os.getenv("GITHUB_OUTPUT", "").strip()
    if output_path:
        with open(output_path, "a", encoding="utf-8") as handle:
            handle.write(f"content_id={content_id or ''}\n")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    mode = argv[0] if argv else "reserve"
    requested_id = argv[1] if len(argv) > 1 else None
    if mode != "reserve":
        print("Usage: python scripts/recover_failed_educational_reel.py reserve [CONTENT_ID]")
        return 2
    if len(argv) > 2:
        print("Only one optional content ID may be provided.")
        return 2
    try:
        content_id = reserve_candidate(requested_id=requested_id)
    except Exception as exc:
        print(f"Recovery reservation failed ({type(exc).__name__}); no publishing call was made.")
        return 1
    write_output(content_id)
    if content_id:
        print(f"Reserved one fresh, previously approved educational Reel for a single recovery attempt: {content_id}")
    else:
        print("No safe recovery candidate. No content will be published.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
