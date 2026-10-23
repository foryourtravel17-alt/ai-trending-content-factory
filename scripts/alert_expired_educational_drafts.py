#!/usr/bin/env python3
"""Send one private Telegram alert for each educational Reel draft that recently expired."""
from __future__ import annotations
import json, os, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

STATE_PATH = Path("data/state.json")
ALERT_WINDOW = timedelta(hours=24)

def parse_timestamp(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None

def collect_expired_drafts(state: dict, now: datetime | None = None) -> list[dict]:
    """Return recently expired educational drafts not already included in an alert."""
    now = now or datetime.now(timezone.utc)
    signals = state.get("signals", {})
    if not isinstance(signals, dict):
        return []
    alerted = state.get("expired_draft_alerted_ids", [])
    alerted = set(alerted if isinstance(alerted, list) else [])
    result = []
    for content_id, record in signals.items():
        if not isinstance(record, dict) or content_id in alerted:
            continue
        if record.get("content_type") != "educational_reel" or record.get("status") != "expired":
            continue
        expired_at = parse_timestamp(record.get("expired_at"))
        if expired_at is None or not (timedelta(0) <= now - expired_at <= ALERT_WINDOW):
            continue
        signal = record.get("signal") if isinstance(record.get("signal"), dict) else {}
        title = str(signal.get("title") or content_id).strip()
        result.append({"content_id": content_id, "title": title[:120], "expired_at": expired_at.isoformat()})
    return sorted(result, key=lambda item: item["expired_at"])

def format_alert(expired: list[dict]) -> str:
    lines = ["Bullseye Theory: approved Reel draft(s) expired in the last 24 hours:"]
    for item in expired[:8]:
        lines.append(f"• {item['title']} ({item['content_id']})")
    if len(expired) > 8:
        lines.append(f"• and {len(expired) - 8} more")
    lines.append("No post was made from an expired draft. Review and re-approve/regenerate as needed.")
    return "\n".join(lines)

def send_telegram_message(token: str, chat_id: str, message: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urllib.parse.urlencode({"chat_id": chat_id, "text": message}).encode()
    request = urllib.request.Request(url, data=payload, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        raise RuntimeError("Telegram expired-draft alert failed; credentials and response are redacted.") from None
    if result.get("ok") is not True:
        raise RuntimeError("Telegram expired-draft alert was not accepted; response is redacted.")

def main() -> int:
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print("No readable publishing state; no expiry alert sent.")
        return 0
    if not isinstance(state, dict):
        print("Unsupported publishing state; no expiry alert sent.")
        return 0
    expired = collect_expired_drafts(state)
    if not expired:
        print("No newly expired educational drafts in the last 24 hours.")
        return 0
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        raise SystemExit("Missing Telegram alert configuration; no expiry alert was sent.")
    send_telegram_message(token, chat_id, format_alert(expired))
    alerted = state.setdefault("expired_draft_alerted_ids", [])
    if not isinstance(alerted, list):
        alerted = []
    alerted_set = set(alerted)
    alerted.extend(item["content_id"] for item in expired if item["content_id"] not in alerted_set)
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Sent one private expiry notice covering {len(expired)} draft(s); IDs recorded to prevent repeat alerts.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
