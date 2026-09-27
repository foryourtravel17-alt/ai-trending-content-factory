#!/usr/bin/env python3
"""Process Telegram approval button clicks.

The workflow polls Telegram getUpdates every few minutes.
Approved/rejected state is written to output/*.json.
No trading or order execution is performed.
"""

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

OUTPUT_DIR = Path("output")
STATE_FILE = OUTPUT_DIR / "telegram_state.json"
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()

def api(method, payload=None):
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    payload = payload or {}
    data = urllib.parse.urlencode(payload).encode()
    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as r:
            result = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Telegram API HTTP {e.code}: {body}"
        ) from e
    if not result.get("ok"):
        raise RuntimeError(f"Telegram API error: {result}")
    return result

def load_offset():
    if not STATE_FILE.exists():
        return 0
    try:
        return int(json.loads(STATE_FILE.read_text()).get("update_offset", 0))
    except Exception:
        return 0

def save_offset(offset):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({"update_offset": offset}, indent=2), encoding="utf-8")

def set_status(cid, approved):
    path = OUTPUT_DIR / f"{cid}.json"
    if not path.exists():
        return False
    data = json.loads(path.read_text(encoding="utf-8"))
    status = "approved" if approved else "rejected"
    data["approval"]["status"] = status
    data["approval"]["approved_at"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    data["status"] = "approved_for_publishing" if approved else "rejected"
    data["publishing"]["telegram"]["status"] = "approval_received"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    qpath = OUTPUT_DIR / "approval_queue.json"
    if qpath.exists():
        q = json.loads(qpath.read_text(encoding="utf-8"))
        for item in q.get("items", []):
            if item.get("content_id") == cid:
                item["status"] = status
                item["approval_status"] = status
        qpath.write_text(json.dumps(q, indent=2, ensure_ascii=False), encoding="utf-8")
    return True

def main():
    if not TOKEN:
        print("Telegram approval processor skipped: secret not configured.")
        return

    offset = load_offset()
    # Use the simplest getUpdates request. We filter callback_query locally.
    # This avoids API 400 errors caused by malformed/unsupported optional parameters.
    result = api("getUpdates", {
        "offset": offset,
        "limit": 100,
        "timeout": 0,
    })

    updates = result.get("result", [])
    if not updates:
        print("No Telegram approval updates.")
        return

    highest = offset
    for update in updates:
        highest = max(highest, update["update_id"] + 1)
        callback = update.get("callback_query", {})
        data = callback.get("data", "")
        if ":" not in data:
            continue

        action, cid = data.split(":", 1)
        if action not in ("approve", "reject"):
            continue

        approved = action == "approve"
        if set_status(cid, approved):
            answer = "✅ Approved for publishing." if approved else "❌ Rejected."
            api("answerCallbackQuery", {
                "callback_query_id": callback["id"],
                "text": answer
            })
            try:
                api("editMessageReplyMarkup", {
                    "chat_id": str(callback["message"]["chat"]["id"]),
                    "message_id": str(callback["message"]["message_id"]),
                    "reply_markup": json.dumps({"inline_keyboard": []})
                })
            except Exception:
                pass
            print(f"{cid}: {answer}")

    save_offset(highest)

if __name__ == "__main__":
    main()
