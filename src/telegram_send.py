#!/usr/bin/env python3
"""Send pending educational Reel drafts to the owner's Telegram approval chat."""
import html
import json
import os
from pathlib import Path
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone

OUTPUT = Path("output")
QUEUE_FILE = OUTPUT / "approval_queue.json"
STATE_FILE = Path("data/state.json")
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

if not TOKEN or not CHAT_ID:
    raise SystemExit("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID secret.")

BASE = f"https://api.telegram.org/bot{TOKEN}"


def api(method, params):
    data = urllib.parse.urlencode(params).encode("utf-8")
    request = urllib.request.Request(f"{BASE}/{method}", data=data, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Telegram API HTTP {exc.code}; response redacted to protect bot token.") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Telegram API request failed ({type(exc).__name__}); bot token redacted.") from None
    if not result.get("ok"):
        raise RuntimeError(f"Telegram API error in {method}; details redacted.")
    return result.get("result")


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(path)


queue = load_json(QUEUE_FILE, {"items": [], "telegram_sent": []})
if isinstance(queue, list):
    queue = {"items": queue, "telegram_sent": []}
if not isinstance(queue, dict):
    raise SystemExit("Approval queue has an unsupported format.")
items = queue.get("items", [])
sent_ids = set(queue.get("telegram_sent", []))
state = load_json(STATE_FILE, {"signals": {}, "runs": []})
signals = state.get("signals", {}) if isinstance(state, dict) else {}
sent_count = 0

for item in items:
    if not isinstance(item, dict):
        continue
    content_id = str(item.get("content_id", "")).strip()
    if not content_id or content_id in sent_ids:
        continue
    record = signals.get(content_id, {})
    if record.get("content_type") != "educational_reel" or record.get("approval_status") != "pending":
        continue
    content = load_json(OUTPUT / f"{content_id}.json", None)
    if not isinstance(content, dict):
        continue
    approval = content.get("approval", {})
    if not isinstance(approval, dict) or approval.get("status") != "pending":
        continue

    topic = content.get("topic", {}) if isinstance(content.get("topic"), dict) else {}
    script = content.get("script", {}) if isinstance(content.get("script"), dict) else {}
    social = content.get("social", {}) if isinstance(content.get("social"), dict) else {}
    title = topic.get("title", content_id)
    hook = script.get("hook", "")
    body = script.get("body", "")
    caption = social.get("caption", content.get("caption", ""))
    hashtags = social.get("hashtags", content.get("hashtags", []))
    if isinstance(hashtags, list):
        hashtags = " ".join(str(tag) for tag in hashtags)

    text = (
        "<b>🐂 Bullseye Theory — Approval Required</b>\n\n"
        f"<b>Content:</b> {html.escape(content_id)}\n"
        f"<b>Topic:</b> {html.escape(str(title))}\n\n"
        f"<b>Hook:</b> {html.escape(str(hook))}\n\n"
        f"<b>Script:</b>\n{html.escape(str(body))}\n\n"
        f"<b>Caption:</b>\n{html.escape(str(caption))}\n\n"
        f"<b>Hashtags:</b> {html.escape(str(hashtags))}\n\n"
        "<b>Before approving:</b> review educational claims, risk wording, caption and hashtags. "
        "Approval records your decision; publication remains subject to freshness, media-match, "
        "duplicate and technical checks. Reject anything inaccurate.\n\n"
        "<i>Educational content only; not financial advice.</i>"
    )
    if len(text) > 3900:
        text = text[:3900] + "\n\n<i>[Message shortened]</i>"
    keyboard = {"inline_keyboard": [[
        {"text": "✅ APPROVE", "callback_data": f"market_approve:{content_id}"},
        {"text": "❌ REJECT", "callback_data": f"market_reject:{content_id}"},
    ]]}
    result = api("sendMessage", {
        "chat_id": CHAT_ID, "text": text, "parse_mode": "HTML",
        "reply_markup": json.dumps(keyboard, separators=(",", ":")),
    })
    sent_ids.add(content_id)
    record["publishing"] = record.get("publishing", {})
    record["publishing"]["telegram_dm"] = {
        "status": "sent",
        "message_id": result.get("message_id"),
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }
    sent_count += 1
    print(f"Sent {content_id} to the configured approval chat; message ID recorded.")

queue["telegram_sent"] = sorted(sent_ids)
save_json(QUEUE_FILE, queue)
save_json(STATE_FILE, state)
print(f"Telegram approval sender complete. Sent {sent_count} request(s). No public post was made.")
