#!/usr/bin/env python3
"""Process Telegram approval button clicks for Bullseye Theory.

Polls Telegram getUpdates for callback_query events, updates the matching
content JSON and approval queue, acknowledges the button click, and removes
the inline buttons. No trading or order execution is performed.
"""

import json
import os
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

OUTPUT_DIR = Path("output")
STATE_FILE = OUTPUT_DIR / "telegram_state.json"
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()


def api(method, payload=None):
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")

    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    data = urllib.parse.urlencode(payload or {}).encode()

    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Telegram API HTTP {exc.code}: {body}") from exc

    if not result.get("ok"):
        raise RuntimeError(f"Telegram API error: {result}")

    return result


def load_offset():
    if not STATE_FILE.exists():
        return 0

    try:
        return int(json.loads(STATE_FILE.read_text(encoding="utf-8")).get("update_offset", 0))
    except Exception:
        return 0


def save_offset(offset):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps({"update_offset": offset}, indent=2),
        encoding="utf-8",
    )


def set_status(content_id, approved):
    content_path = OUTPUT_DIR / f"{content_id}.json"
    if not content_path.exists():
        print(f"SKIP {content_id}: content file not found")
        return False

    data = json.loads(content_path.read_text(encoding="utf-8"))

    status = "approved" if approved else "rejected"
    data["approval"]["status"] = status
    data["approval"]["approved_at"] = datetime.now(timezone.utc).isoformat()
    data["status"] = "approved_for_publishing" if approved else "rejected"

    data.setdefault("publishing", {}).setdefault("telegram", {})
    data["publishing"]["telegram"]["status"] = "approval_received"

    content_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    queue_path = OUTPUT_DIR / "approval_queue.json"
    if queue_path.exists():
        queue = json.loads(queue_path.read_text(encoding="utf-8"))

        for item in queue.get("items", []):
            if item.get("content_id") == content_id:
                item["status"] = status
                item["approval_status"] = status

        queue_path.write_text(
            json.dumps(queue, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    return True


def main():
    if not TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN secret is missing")

    offset = load_offset()

    payload = {
        "offset": offset,
        "limit": 100,
        "timeout": 0,
        "allowed_updates": json.dumps(["callback_query"]),
    }

    result = api("getUpdates", payload)
    updates = result.get("result", [])

    print(f"Telegram updates received: {len(updates)}")
    print(f"Starting offset: {offset}")

    if not updates:
        print("No Telegram approval updates found.")
        save_offset(offset)
        return

    highest = offset

    for update in updates:
        update_id = int(update.get("update_id", 0))
        highest = max(highest, update_id + 1)

        callback = update.get("callback_query")
        if not callback:
            continue

        callback_id = callback.get("id", "")
        callback_data = str(callback.get("data", ""))

        message = callback.get("message") or {}
        chat = message.get("chat") or {}
        callback_chat_id = str(chat.get("id", ""))

        print(
            f"Callback received: data={callback_data!r}, "
            f"chat_id={callback_chat_id or 'missing'}"
        )

        if CHAT_ID and callback_chat_id != CHAT_ID:
            print("SKIP callback: chat ID does not match TELEGRAM_CHAT_ID")
            continue

        if ":" not in callback_data:
            print("SKIP callback: invalid callback data")
            continue

        action, content_id = callback_data.split(":", 1)

        if action not in ("approve", "reject"):
            print(f"SKIP callback: unknown action {action!r}")
            continue

        approved = action == "approve"

        if set_status(content_id, approved):
            answer = (
                "Approved for publishing."
                if approved
                else "Rejected."
            )

            api(
                "answerCallbackQuery",
                {
                    "callback_query_id": callback_id,
                    "text": answer,
                },
            )

            try:
                api(
                    "editMessageReplyMarkup",
                    {
                        "chat_id": callback_chat_id,
                        "message_id": str(message.get("message_id", "")),
                        "reply_markup": json.dumps(
                            {"inline_keyboard": []}
                        ),
                    },
                )
            except Exception as exc:
                print(f"Button removal warning: {exc}")

            print(f"SUCCESS: {content_id} -> {action}")
        else:
            print(f"SKIP {content_id}: state was not updated")

    save_offset(highest)
    print(f"Saved Telegram update offset: {highest}")


if __name__ == "__main__":
    main()
