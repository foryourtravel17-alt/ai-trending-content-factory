import json
import os
import hashlib
from datetime import datetime, timezone, timedelta
import urllib.parse
import urllib.request
import urllib.error

from config.env import is_content_fresh

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
API = f"https://api.telegram.org/bot{TOKEN}"
STATE_FILE = "output/telegram_state.json"
QUEUE_FILE = "output/approval_queue.json"
MARKET_STATE_FILE = "data/state.json"


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
        raise RuntimeError(f"Telegram API error: {payload}")
    return payload["result"]


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, value):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(value, f, indent=2, ensure_ascii=False)
        f.write("\n")


def write_output(values):
    target = os.getenv("GITHUB_OUTPUT")
    if not target:
        return
    with open(target, "a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def main():
    import time

    state = load_json(STATE_FILE, {"update_offset": 0})
    queue = load_json(QUEUE_FILE, {"items": []})
    market_state = load_json(MARKET_STATE_FILE, {"signals": {}, "runs": []})
    market_state.setdefault("signals", {})
    offset = int(state.get("update_offset", 0))
    print(f"Starting offset: {offset}")

    queue_by_id = {item.get("content_id"): item for item in queue.get("items", [])}
    deadline = time.time() + max(5, int(os.getenv("POLL_SECONDS", "240")))
    processed_any = False
    market_approved_ids = []

    while time.time() < deadline:
        result = api(
            "getUpdates",
            {
                "offset": offset,
                "timeout": 5,
                "allowed_updates": json.dumps(["callback_query"]),
            },
            timeout=15,
        )
        print(f"Telegram updates received: {len(result)}")
        if not result:
            continue

        for update in result:
            update_id = int(update["update_id"])
            callback = update.get("callback_query")
            print(f"Processing update: {update_id}")

            if callback:
                data = callback.get("data", "")
                callback_id = callback.get("id", "")
                print(f"Callback received: {data}")

                if data.startswith("market_approve:") or data.startswith("market_reject:"):
                    parts = data.split(":")
                    if len(parts) != 4:
                        print("Rejected unbound market approval callback.")
                    else:
                        action, signal_id, version_text, fingerprint = parts
                        record = market_state["signals"].get(signal_id)
                        if record:
                            signal = record.get("signal") or {}
                            binding_payload = {key: signal.get(key) for key in (
                                "signal_id", "as_of", "symbol", "direction", "entry", "stop_loss", "tp1", "tp2", "tp3"
                            )}
                            expected_hash = hashlib.sha256(
                                json.dumps(binding_payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
                            ).hexdigest()
                            binding = record.get("approval_binding") or {}
                            valid = (
                                version_text == str(binding.get("version", ""))
                                and fingerprint == expected_hash[:16]
                                and binding.get("hash") == expected_hash
                            )
                            if not valid:
                                print(f"Rejected stale or mismatched market callback: {signal_id}")
                                response_text = "This market draft is stale. Request a fresh draft."
                            elif record.get("approval_status") in {"approved", "rejected"}:
                                print(f"Duplicate market callback ignored: {signal_id}")
                                response_text = "This decision has already been recorded."
                            elif action == "market_approve":
                                record["status"] = "generated"
                                record["approval_status"] = "approved"
                                record["approved_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                                if signal_id not in market_approved_ids:
                                    market_approved_ids.append(signal_id)
                                response_text = "Approved — publishing will start."
                                print(f"Market scenario approved: {signal_id}")
                            else:
                                record["status"] = "rejected"
                                record["approval_status"] = "rejected"
                                record["rejected_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                                response_text = "Rejected — no public post."
                                print(f"Market scenario rejected: {signal_id}")
                            save_json(MARKET_STATE_FILE, market_state)
                            try:
                                api("answerCallbackQuery", {
                                    "callback_query_id": callback_id,
                                    "text": response_text,
                                    "show_alert": "false",
                                })
                            except Exception as exc:
                                print(f"Callback acknowledgement skipped: {type(exc).__name__}")
                            message = callback.get("message") or {}
                            chat_id = message.get("chat", {}).get("id")
                            message_id = message.get("message_id")
                            if chat_id and message_id:
                                try:
                                    api("editMessageReplyMarkup", {
                                        "chat_id": chat_id, "message_id": message_id,
                                        "reply_markup": json.dumps({"inline_keyboard": []}),
                                    })
                                except Exception as exc:
                                    print(f"Button removal skipped: {type(exc).__name__}")
                        else:
                            print(f"Market signal not found in state: {signal_id}")
                            try:
                                api("answerCallbackQuery", {
                                    "callback_query_id": callback_id,
                                    "text": "This draft is no longer available.",
                                    "show_alert": "false",
                                })
                            except Exception:
                                pass
                else:
                    parts = data.split(":")
                    if len(parts) == 4 and parts[0] in ("approve", "reject"):
                        action, content_id, version_text, fingerprint = parts
                        content_path = f"output/{content_id}.json"
                        if os.path.exists(content_path):
                            content = load_json(content_path, {})
                            approval = content.get("approval") or {}
                            try:
                                version = int(version_text)
                                expected_version = int(approval.get("version", content.get("content_version", 1)))
                            except (TypeError, ValueError):
                                version, expected_version = -1, -2
                            basis = {
                                "content_id": content.get("content_id"),
                                "version": content.get("content_version", 1),
                                "created_at": content.get("created_at"),
                                "title": (content.get("topic") or {}).get("title"),
                                "hook": (content.get("script") or {}).get("hook"),
                                "body": (content.get("script") or {}).get("body"),
                            }
                            expected_hash = hashlib.sha256(
                                json.dumps(basis, sort_keys=True, ensure_ascii=False).encode("utf-8")
                            ).hexdigest()
                            valid_binding = (
                                content.get("content_id") == content_id
                                and version == expected_version
                                and fingerprint == expected_hash[:16]
                                and approval.get("content_hash") == expected_hash
                                and str((content.get("fact_check") or {}).get("status", "")).lower() in {"passed", "verified", "approved"}
                                and (content.get("safety_check") or {}).get("passed") is True
                                and approval.get("required") is True
                            )
                            if not valid_binding:
                                print(f"Rejected stale or mismatched approval callback for {content_id}.")
                                try:
                                    api("answerCallbackQuery", {
                                        "callback_query_id": callback_id,
                                        "text": "This approval button is stale or does not match this draft.",
                                        "show_alert": "true",
                                    })
                                except Exception:
                                    pass
                            elif content.get("status") in {"published_to_instagram", "published", "rejected", "expired"} or approval.get("status") in {"rejected", "expired"}:
                                print(f"Idempotent no-op for terminal content state: {content_id} ({content.get('status')}).")
                            elif approval.get("status") == "approved" and content.get("status") == "approved_for_publishing":
                                print(f"Duplicate approval callback ignored: {content_id}")
                            else:
                                created = content.get("created_at")
                                try:
                                    created_dt = datetime.fromisoformat(str(created).replace("Z", "+00:00"))
                                    if created_dt.tzinfo is None:
                                        created_dt = created_dt.replace(tzinfo=timezone.utc)
                                    age = datetime.now(timezone.utc) - created_dt.astimezone(timezone.utc)
                                except (TypeError, ValueError):
                                    age = timedelta(days=999)
                                fresh = is_content_fresh(created, max_age_hours=24)
                                if action == "approve" and not fresh:
                                    content["status"] = "expired"
                                    approval["status"] = "expired"
                                    content["expired_at"] = datetime.now(timezone.utc).isoformat()
                                    content["expiration_reason"] = "Approval received after the 24-hour content freshness limit."
                                    print(f"Expired stale approval target: {content_id}; age={age}.")
                                    response_text = "This draft expired. Generate a fresh one."
                                elif action == "approve":
                                    content["status"] = "approved_for_publishing"
                                    approval["status"] = "approved"
                                    approval["approved_at"] = datetime.now(timezone.utc).isoformat()
                                    content["approval_action"] = "approve"
                                    response_text = "Approved. The matching version is eligible for processing."
                                else:
                                    content["status"] = "rejected"
                                    approval["status"] = "rejected"
                                    approval["rejected_at"] = datetime.now(timezone.utc).isoformat()
                                    content["approval_action"] = "reject"
                                    response_text = "Rejected. No public post will be made."
                                content["approval"] = approval
                                save_json(content_path, content)
                                if content_id in queue_by_id:
                                    queue_by_id[content_id]["status"] = content["status"]
                                    queue_by_id[content_id]["processed"] = True
                                    queue_by_id[content_id]["content_version"] = content.get("content_version", 1)
                                    queue_by_id[content_id]["content_hash"] = approval.get("content_hash", "")
                                try:
                                    api("answerCallbackQuery", {
                                        "callback_query_id": callback_id,
                                        "text": response_text,
                                        "show_alert": "false",
                                    })
                                except Exception as exc:
                                    print(f"Callback acknowledgement failed after durable state update: {type(exc).__name__}")
                                message = callback.get("message") or {}
                                chat_id = message.get("chat", {}).get("id")
                                message_id = message.get("message_id")
                                if chat_id and message_id:
                                    try:
                                        api("editMessageReplyMarkup", {
                                            "chat_id": chat_id, "message_id": message_id,
                                            "reply_markup": json.dumps({"inline_keyboard": []}),
                                        })
                                    except Exception as exc:
                                        print(f"Button removal skipped: {type(exc).__name__}")
                        else:
                            print(f"Content file not found: {content_path}")
                    elif len(parts) == 2 and parts[0] in ("approve", "reject"):
                        print("Rejected legacy unbound approval callback: version/hash are required.")
                        try:
                            api("answerCallbackQuery", {
                                "callback_query_id": callback_id,
                                "text": "This button is outdated. Request a fresh approval message.",
                                "show_alert": "true",
                            })
                        except Exception:
                            pass
                    else:
                        print(f"Ignoring non-approval callback: {data}")
            offset = update_id + 1
            state["update_offset"] = offset
            processed_any = True
        if processed_any:
            break

    queue["items"] = list(queue_by_id.values())
    save_json(QUEUE_FILE, queue)
    save_json(STATE_FILE, state)
    write_output({
        "market_approved": "true" if market_approved_ids else "false",
        "market_signal_id": market_approved_ids[0] if market_approved_ids else "",
        "market_approved_ids": ",".join(market_approved_ids),
    })

    if processed_any:
        print(f"Saved next offset: {state['update_offset']}")
    else:
        print("No Telegram approval callbacks found during this run.")


if __name__ == "__main__":
    main()
