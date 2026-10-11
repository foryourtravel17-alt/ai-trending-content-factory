#!/usr/bin/env python3
"""Send pending generated content to Telegram for approval."""
import html
import json
import os
from pathlib import Path
import urllib.parse
import urllib.request

OUTPUT = Path("output")
QUEUE_FILE = OUTPUT / "approval_queue.json"
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

if not TOKEN or not CHAT_ID:
    raise SystemExit("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID secret.")

BASE = f"https://api.telegram.org/bot{TOKEN}"


def api(method, params):
    data = urllib.parse.urlencode(params).encode("utf-8")
    request = urllib.request.Request(
        f"{BASE}/{method}",
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Telegram API HTTP {exc.code}; response redacted to protect bot token.") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Telegram API request failed ({type(exc).__name__}); bot token redacted.") from None

    if not result.get("ok"):
        raise RuntimeError(f"Telegram API error in {method}: {result}")
    return result.get("result")


def load_json(path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_json(path, data):
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


queue = load_json(QUEUE_FILE)
if isinstance(queue, dict):
    items = queue.get("items", [])
elif isinstance(queue, list):
    items = queue
else:
    items = []

sent_ids = set(queue.get("telegram_sent", []) if isinstance(queue, dict) else [])

sent_count = 0

for item in items:
    content_id = item.get("content_id")
    if not content_id or content_id in sent_ids:
        continue

    content = load_json(OUTPUT / f"{content_id}.json")
    if not isinstance(content, dict):
        continue

    approval = content.get("approval", {})
    if approval.get("status") != "pending":
        continue

    topic = content.get("topic", {})
    script = content.get("script", {})
    social = content.get("social", {})

    title = topic.get("title", content_id)
    hook = script.get("hook", "")
    body = script.get("body", "")
    caption = social.get("caption", "")
    hashtags = " ".join(social.get("hashtags", []))

    text = (
        "<b>🐂 Bullseye Theory — Approval Required</b>\n\n"
        f"<b>Content:</b> {html.escape(str(content_id))}\n"
        f"<b>Topic:</b> {html.escape(str(title))}\n\n"
        f"<b>Hook:</b> {html.escape(str(hook))}\n\n"
        f"<b>Script:</b>\n{html.escape(str(body))}\n\n"
        f"<b>Caption:</b>\n{html.escape(str(caption))}\n\n"
        f"<b>Hashtags:</b> {html.escape(hashtags)}\n\n"
        "<i>For informational and research purposes only. "
        "This is not financial advice.</i>"
    )

    if len(text) > 3900:
        text = text[:3900] + "\n\n<i>[Message shortened]</i>"

    approval_meta = content.get("approval") or {}
    version = int(approval_meta.get("version", content.get("content_version", 1)))
    content_hash = str(approval_meta.get("content_hash", ""))
    if not content_hash:
        raise RuntimeError(f"Refusing approval request without a content hash: {content_id}")
    fingerprint = content_hash[:16]
    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ APPROVE", "callback_data": f"approve:{content_id}:{version}:{fingerprint}"},
            {"text": "❌ REJECT", "callback_data": f"reject:{content_id}:{version}:{fingerprint}"},
        ]]
    }

    result = api("sendMessage", {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": json.dumps(keyboard, separators=(",", ":")),
    })

    sent_ids.add(content_id)
    sent_count += 1
    print(f"Sent {content_id}, Telegram message {result.get('message_id')}.")

if isinstance(queue, dict):
    queue["items"] = items
    queue["telegram_sent"] = sorted(sent_ids)
    save_json(QUEUE_FILE, queue)

print(f"Telegram sender complete. Sent {sent_count} approval request(s).")
