#!/usr/bin/env python3
"""Build and send the daily Telegram automation summary from canonical shared state."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

STATE_PATH = Path("data/state.json")
TIMEOUT = 20


def _timestamp(record: dict):
    value = record.get("created_at") or record.get("generated_at")
    signal = record.get("signal") if isinstance(record.get("signal"), dict) else {}
    value = value or signal.get("as_of")
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def build_report(state: dict, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    now = now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now.astimezone(timezone.utc)
    cutoff = now - timedelta(hours=24)
    signals = state.get("signals", {}) if isinstance(state, dict) else {}
    recent = []
    if isinstance(signals, dict):
        for content_id, record in signals.items():
            if not isinstance(record, dict):
                continue
            created = _timestamp(record)
            if created is None or created < cutoff or created > now + timedelta(minutes=5):
                continue
            recent.append((str(content_id), record))

    approved = 0
    pending = 0
    reels = 0
    telegram = 0
    titles = []
    for content_id, record in recent:
        approval = str(record.get("approval_status") or
                       (record.get("approval") or {}).get("status", "")).lower()
        status = str(record.get("status", "")).lower()
        if approval == "approved":
            approved += 1
        if approval == "pending" or status == "pending_approval":
            pending += 1
        if record.get("content_type") == "educational_reel":
            reels += 1
        publishing = record.get("publishing") if isinstance(record.get("publishing"), dict) else {}
        telegram_status = str((publishing.get("telegram") or {}).get("status", "")).lower()
        if telegram_status == "published":
            telegram += 1
        signal = record.get("signal") if isinstance(record.get("signal"), dict) else {}
        topic = record.get("topic") if isinstance(record.get("topic"), dict) else {}
        title = signal.get("title") or topic.get("title") or signal.get("symbol") or content_id
        titles.append(str(title))

    lines = [
        "🎯 Bullseye Theory — Daily Automation Report",
        "",
        f"Last 24h generated: {len(recent)}",
        f"Approved: {approved}",
        f"Awaiting approval: {pending}",
        f"Educational Reels: {reels}",
        f"Telegram published: {telegram}",
        "",
        "Schedules (India time):",
        "Market cards: 09:15, 11:15, 13:30, 15:45 IST",
        "Educational Reels: 10:17, 14:17, 18:17 IST",
        "",
    ]
    if titles:
        lines.append("Recent content:")
        lines.extend(f"• {title}" for title in titles[-3:])
    else:
        lines.append("No new content was recorded in the last 24 hours.")
    lines.extend([
        "",
        "Market scenarios and educational content only; not financial advice.",
    ])
    return "\n".join(lines)


def load_state(path: Path = STATE_PATH) -> dict:
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"signals": {}}
    return state if isinstance(state, dict) else {"signals": {}}


def send_report(message: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat:
        raise SystemExit("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID.")
    payload = urllib.parse.urlencode({"chat_id": chat, "text": message}).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"Telegram report failed with HTTP {exc.code}; response redacted.") from None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise SystemExit(f"Telegram report request failed ({type(exc).__name__}); values redacted.") from None
    if not isinstance(result, dict) or result.get("ok") is not True:
        raise SystemExit("Telegram rejected the daily report; response redacted.")


def main() -> int:
    message = build_report(load_state())
    print(message)
    send_report(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
