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


def _safe_api_description(raw: bytes) -> str:
    """Return Telegram's human-readable error without exposing request credentials."""
    try:
        payload = json.loads(raw.decode("utf-8", errors="replace"))
        description = " ".join(str(payload.get("description") or "").split())
    except (ValueError, TypeError, AttributeError):
        description = ""
    # Telegram descriptions contain API diagnostics, not the bot token or request URL.
    # Still redact any accidental credential echo before logging.
    if TOKEN:
        description = description.replace(TOKEN, "[REDACTED]")
    return description[:180]


def api(method, params):
    data = urllib.parse.urlencode(params).encode("utf-8")
    request = urllib.request.Request(f"{BASE}/{method}", data=data, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = _safe_api_description(exc.read())
        suffix = f": {detail}" if detail else ""
        raise RuntimeError(f"Telegram API HTTP {exc.code} in {method}{suffix}; bot token redacted.") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Telegram API request failed ({type(exc).__name__}); bot token redacted.") from None
    if not result.get("ok"):
        detail = _safe_api_description(json.dumps(result).encode("utf-8"))
        suffix = f": {detail}" if detail else ""
        raise RuntimeError(f"Telegram API error in {method}{suffix}; details redacted.")
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
message_ids = queue.get("telegram_message_ids", {})
if not isinstance(message_ids, dict):
    message_ids = {}
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
    publishing = record.get("publishing", {}) if isinstance(record.get("publishing"), dict) else {}
    previous_dm = publishing.get("telegram_dm", {}) if isinstance(publishing.get("telegram_dm"), dict) else {}
    if previous_dm.get("status") == "sent" and previous_dm.get("message_id"):
        sent_ids.add(content_id)
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

    message_text = (
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
    if len(message_text) > 3900:
        message_text = message_text[:3900] + "\n\n<i>[Message shortened]</i>"
    approve_callback = f"a:{content_id}"
    reject_callback = f"r:{content_id}"
    if max(len(approve_callback.encode("utf-8")), len(reject_callback.encode("utf-8"))) > 64:
        raise RuntimeError(f"Telegram callback identifier is too long for {content_id}; no approval message was sent.")
    keyboard = {"inline_keyboard": [[
        {"text": "✅ APPROVE", "callback_data": approve_callback},
        {"text": "❌ REJECT", "callback_data": reject_callback},
    ]]}
    result = api("sendMessage", {
        "chat_id": CHAT_ID, "text": message_text, "parse_mode": "HTML",
        "reply_markup": json.dumps(keyboard, separators=(",", ":")),
    })
    sent_ids.add(content_id)
    message_ids[content_id] = result.get("message_id")
    queue["telegram_message_ids"] = message_ids
    record["publishing"] = record.get("publishing", {})
    record["publishing"]["telegram_dm"] = {
        "status": "sent",
        "message_id": result.get("message_id"),
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }
    sent_count += 1
    # Persist each successful message immediately. If a later Telegram request
    # fails, the next run must not resend messages that Telegram already accepted.
    save_json(STATE_FILE, state)
    queue["telegram_sent"] = sorted(sent_ids)
    save_json(QUEUE_FILE, queue)
    print(f"Sent {content_id} to the configured approval chat; message ID recorded.")

queue["telegram_sent"] = sorted(sent_ids)
save_json(STATE_FILE, state)
save_json(QUEUE_FILE, queue)
print(f"Telegram approval sender complete. Sent {sent_count} request(s). No public post was made.")
