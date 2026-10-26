from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
API = f"https://api.telegram.org/bot{TOKEN}"
STATE_FILE = Path("output/telegram_state.json")
QUEUE_FILE = Path("output/approval_queue.json")
MARKET_STATE_FILE = Path("data/state.json")
OUTPUT_DIR = Path("output")
SAFE_ID = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
MAX_CALLBACK_RETRIES = 12


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(path)


def api(method, data=None, timeout=30):
    data = data or {}
    encoded = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(f"{API}/{method}", data=encoded, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            payload = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Telegram API HTTP {exc.code}; response redacted to protect bot token.") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Telegram API request failed ({type(exc).__name__}); bot token redacted.") from None
    if not payload.get("ok"):
        raise RuntimeError("Telegram API returned an unsuccessful response; details redacted.")
    return payload["result"]




def send_decision_confirmation(callback: dict, text: str) -> None:
    """Send durable chat confirmation even when Telegram's callback toast fails."""
    message = (callback or {}).get("message") or {}
    chat_id = (message.get("chat") or {}).get("id")
    if not chat_id:
        return
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    message_id = message.get("message_id")
    if message_id:
        payload["reply_parameters"] = json.dumps({
            "message_id": message_id,
            "allow_sending_without_reply": True,
        })
    try:
        api("sendMessage", payload)
    except Exception as exc:
        print(f"Confirmation message skipped: {type(exc).__name__}")


def _reviewer_label(callback):
    actor = (callback or {}).get("from") or {}
    username = str(actor.get("username") or "").strip()
    user_id = str(actor.get("id") or "").strip()
    return f"@{username}" if username else (f"id:{user_id}" if user_id else "unknown")

def is_authorized_callback(callback: dict) -> bool:
    """Accept buttons only from the configured approval chat and owner/allowlist."""
    expected_chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not expected_chat or not isinstance(callback, dict):
        return False
    message = callback.get("message") or {}
    chat_id = str((message.get("chat") or {}).get("id") or "").strip()
    actor_id = str(((callback.get("from") or {}).get("id")) or "").strip()
    if chat_id != expected_chat or not actor_id:
        return False

    configured_ids = os.environ.get("TELEGRAM_APPROVER_USER_IDS", "").strip()
    if configured_ids:
        allowed_ids = {part.strip() for part in configured_ids.split(",") if part.strip()}
    else:
        # In a private Telegram chat, the chat ID equals the owner's user ID.
        # Group chats must configure TELEGRAM_APPROVER_USER_IDS explicitly.
        allowed_ids = {expected_chat}
    return actor_id in allowed_ids


def apply_market_decision(record: dict, action: str, now: str, reviewed_by: str = "unknown") -> bool:
    """Apply a single approval decision without allowing conflicting clicks to overwrite it."""
    if record.get("approval_status") in ("approved", "rejected"):
        return False
    if action not in ("market_approve", "market_reject"):
        return False

    approved = action == "market_approve"
    record["status"] = "generated" if approved else "rejected"
    record["approval_status"] = "approved" if approved else "rejected"
    record["approved_at" if approved else "rejected_at"] = now
    record["reviewed_at"] = now
    record["reviewed_by"] = reviewed_by
    record["approval"] = {
        **(record.get("approval") if isinstance(record.get("approval"), dict) else {}),
        "required": True,
        "status": "approved" if approved else "rejected",
        "mode": "human_review",
        "decided_at": now,
        "reviewed_at": now,
        "reviewed_by": reviewed_by,
    }

    if record.get("content_type") == "educational_reel":
        fact_check = record.get("fact_check")
        if not isinstance(fact_check, dict):
            fact_check = {}
            record["fact_check"] = fact_check
        fact_check["status"] = "approved" if approved else "rejected"
        fact_check["reviewed_at"] = now
        fact_check["reviewed_by"] = reviewed_by
        notes = fact_check.get("notes")
        if not isinstance(notes, list):
            notes = []
            fact_check["notes"] = notes
        note = (
            "Human reviewer approved the displayed educational draft in Telegram."
            if approved else "Human reviewer rejected the displayed educational draft in Telegram."
        )
        if note not in notes:
            notes.append(note)
    return True


def sync_educational_metadata(content_id: str, action: str, now: str, reviewed_by: str) -> bool:
    """Mirror the shared-state decision to the matching Reel metadata file."""
    if not content_id or any(ch not in SAFE_ID for ch in content_id):
        return False
    path = OUTPUT_DIR / f"{content_id}.json"
    content = load_json(path, None)
    if not isinstance(content, dict) or content.get("content_id") != content_id:
        return False

    approved = action == "market_approve"
    if action not in ("market_approve", "market_reject"):
        return False
    content["status"] = "approved_for_publishing" if approved else "rejected"
    approval = content.get("approval")
    if not isinstance(approval, dict):
        approval = {}
        content["approval"] = approval
    approval.update({
        "required": True,
        "status": "approved" if approved else "rejected",
        "mode": "human_review",
        "decided_at": now,
        "reviewed_at": now,
        "reviewed_by": reviewed_by,
    })
    fact_check = content.get("fact_check")
    if not isinstance(fact_check, dict):
        fact_check = {}
        content["fact_check"] = fact_check
    fact_check["status"] = "approved" if approved else "rejected"
    fact_check["reviewed_at"] = now
    fact_check["reviewed_by"] = reviewed_by
    notes = fact_check.get("notes")
    if not isinstance(notes, list):
        notes = []
        fact_check["notes"] = notes
    note = (
        "Human reviewer approved the displayed educational draft in Telegram."
        if approved else "Human reviewer rejected the displayed educational draft in Telegram."
    )
    if note not in notes:
        notes.append(note)
    content["approval_action"] = "approve" if approved else "reject"
    content["approval_action_at"] = now
    save_json(path, content)
    return True


def write_output(values):
    target = os.getenv("GITHUB_OUTPUT")
    if not target:
        return
    with open(target, "a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def main():
    state = load_json(STATE_FILE, {"update_offset": 0})
    queue = load_json(QUEUE_FILE, {"items": [], "telegram_sent": []})
    market_state = load_json(MARKET_STATE_FILE, {"signals": {}, "runs": []})
    if isinstance(queue, list):
        queue = {"items": queue, "telegram_sent": []}
    if not isinstance(queue, dict):
        queue = {"items": [], "telegram_sent": []}
    market_state.setdefault("signals", {})
    if not isinstance(market_state["signals"], dict):
        market_state["signals"] = {}
    queue_by_id = {
        item.get("content_id"): item
        for item in queue.get("items", [])
        if isinstance(item, dict) and item.get("content_id")
    }
    offset = int(state.get("update_offset", 0))
    retries = state.setdefault("callback_retries", {})
    if not isinstance(retries, dict):
        retries = {}
        state["callback_retries"] = retries
    deadline = time.time() + max(5, int(os.getenv("POLL_SECONDS", "240")))
    processed_any = False
    market_approved_ids = []
    educational_approved_ids = []

    print(f"Starting offset: {offset}")
    while time.time() < deadline:
        result = api(
            "getUpdates",
            {"offset": offset, "timeout": 5, "allowed_updates": json.dumps(["callback_query"])},
            timeout=15,
        )
        print(f"Telegram updates received: {len(result)}")
        if not result:
            continue

        next_offset = offset
        blocked = False
        for update in result:
            update_id = int(update["update_id"])
            callback = update.get("callback_query")
            retryable = False
            strip_buttons = False
            if callback and not is_authorized_callback(callback):
                callback_id = str(callback.get("id", ""))
                try:
                    api("answerCallbackQuery", {
                        "callback_query_id": callback_id,
                        "text": "Not authorized. No decision was saved.",
                        "show_alert": "true",
                    })
                except Exception as exc:
                    print(f"Unauthorized callback acknowledgement skipped: {type(exc).__name__}")
                print("Ignored Telegram approval callback from unauthorized chat/user.")
                callback = None
            if callback:
                data = str(callback.get("data", ""))
                callback_id = str(callback.get("id", ""))
                reviewer = _reviewer_label(callback)

                if data.startswith("market_approve:") or data.startswith("market_reject:"):
                    action, signal_id = data.split(":", 1)
                    record = market_state["signals"].get(signal_id)
                    if not record:
                        answer = "This draft is no longer available. No decision was saved."
                        retryable = True
                    elif record.get("content_type") == "educational_reel" and not sync_metadata_preflight(signal_id):
                        answer = "Draft metadata is missing or mismatched. No decision was saved."
                        print(f"Blocked approval for missing/mismatched educational metadata: {signal_id}")
                        retryable = True
                    else:
                        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                        changed = apply_market_decision(record, action, now, reviewer)
                        if not changed:
                            answer = "Already decided. The earlier decision was preserved."
                            print(f"Duplicate/conflicting callback ignored: {signal_id}")
                        else:
                            if record.get("content_type") == "educational_reel":
                                synced = sync_educational_metadata(signal_id, action, now, reviewer)
                                if not synced:
                                    # Fail closed; this should be prevented by preflight above.
                                    record["status"] = "pending_approval"
                                    record["approval_status"] = "pending"
                                    record["approval"] = {"required": True, "status": "pending", "mode": "human_review"}
                                    answer = "Draft metadata could not be updated. No decision was committed."
                                    print(f"Metadata write failed for educational draft: {signal_id}")
                                    record["fact_check"] = {"status": "needs_human_review"}
                                    retryable = True
                                    changed = False
                                else:
                                    if signal_id in queue_by_id:
                                        queue_by_id[signal_id]["status"] = "approved" if action == "market_approve" else "rejected"
                                        queue_by_id[signal_id]["processed"] = True
                                        queue_by_id[signal_id]["decided_at"] = now
                                    if action == "market_approve" and signal_id not in educational_approved_ids:
                                        educational_approved_ids.append(signal_id)
                                    answer = (
                                        "Approval recorded. Reel is queued for the publishing eligibility checks."
                                        if action == "market_approve"
                                        else "Rejected — no public post."
                                    )
                                    save_json(MARKET_STATE_FILE, market_state)
                                    print(f"Educational Reel decision recorded: {signal_id} ({record['approval_status']}).")
                            else:
                                if action == "market_approve" and signal_id not in market_approved_ids:
                                    market_approved_ids.append(signal_id)
                                answer = (
                                    "Approved — publishing eligibility checks will run."
                                    if action == "market_approve" else "Rejected — no public post."
                                )
                                save_json(MARKET_STATE_FILE, market_state)
                                print(f"Market scenario decision recorded: {signal_id} ({record['approval_status']}).")

                    try:
                        api("answerCallbackQuery", {
                            "callback_query_id": callback_id, "text": answer, "show_alert": "false",
                        })
                    except Exception as exc:
                        print(f"Callback acknowledgement skipped: {type(exc).__name__}")
                    # Persisted decisions deserve a durable chat message; callback toasts expire.
                    if not retryable and answer:
                        send_decision_confirmation(callback, answer)
                    strip_buttons = not retryable
                    message = callback.get("message") or {}
                    chat_id = (message.get("chat") or {}).get("id")
                    message_id = message.get("message_id")
                    if strip_buttons and chat_id and message_id:
                        try:
                            api("editMessageReplyMarkup", {
                                "chat_id": chat_id, "message_id": message_id,
                                "reply_markup": json.dumps({"inline_keyboard": []}),
                            })
                        except Exception as exc:
                            print(f"Button removal skipped: {type(exc).__name__}")

                else:
                    print("Ignoring unsupported Telegram callback type; no decision was saved.")
                    try:
                        api("answerCallbackQuery", {
                            "callback_query_id": callback_id,
                            "text": "Unsupported approval button. No decision was saved.",
                            "show_alert": "false",
                        })
                    except Exception as exc:
                        print(f"Callback acknowledgement skipped: {type(exc).__name__}")

            attempts = int(retries.get(str(update_id), 0))
            consume = not retryable
            if retryable:
                attempts += 1
                retries[str(update_id)] = attempts
                if attempts >= MAX_CALLBACK_RETRIES:
                    consume = True
                    print(f"Callback {update_id} remained blocked after {attempts} attempts; consuming to prevent a permanent stall.")
                    if callback:
                        message = callback.get("message") or {}
                        chat_id = (message.get("chat") or {}).get("id")
                        message_id = message.get("message_id")
                        if chat_id and message_id:
                            try:
                                api("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": message_id, "reply_markup": json.dumps({"inline_keyboard": []})})
                            except Exception as exc:
                                print(f"Button removal after retry cap skipped: {type(exc).__name__}")
            if consume:
                retries.pop(str(update_id), None)
                if not blocked:
                    next_offset = update_id + 1
            else:
                blocked = True
                next_offset = update_id
            processed_any = True
        if next_offset != offset:
            offset = next_offset
            state["update_offset"] = offset
        if processed_any:
            break

    queue["items"] = list(queue_by_id.values())
    save_json(QUEUE_FILE, queue)
    save_json(STATE_FILE, state)
    if processed_any:
        print(f"Saved next offset: {state['update_offset']}")
    else:
        print("No Telegram approval callbacks found during this run.")
    write_output({
        "market_approved": "true" if market_approved_ids else "false",
        "market_signal_id": market_approved_ids[0] if market_approved_ids else "",
        "market_approved_ids": ",".join(market_approved_ids),
        "educational_approved": "true" if educational_approved_ids else "false",
        "educational_approved_ids": ",".join(educational_approved_ids),
    })


def sync_metadata_preflight(content_id: str) -> bool:
    if not content_id or any(ch not in SAFE_ID for ch in content_id):
        return False
    content = load_json(OUTPUT_DIR / f"{content_id}.json", None)
    return isinstance(content, dict) and content.get("content_id") == content_id


if __name__ == "__main__":
    main()
