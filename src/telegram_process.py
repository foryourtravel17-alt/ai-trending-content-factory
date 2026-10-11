import json
import os
import urllib.parse
import urllib.request
import urllib.error

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
    market_approved = None

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
                    action, signal_id = data.split(":", 1)
                    record = market_state["signals"].get(signal_id)
                    if record:
                        if action == "market_approve":
                            record["status"] = "generated"
                            record["approval_status"] = "approved"
                            record["approved_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                            market_approved = signal_id
                            print(f"Market scenario approved: {signal_id}")
                        else:
                            record["status"] = "rejected"
                            record["approval_status"] = "rejected"
                            record["rejected_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                            print(f"Market scenario rejected: {signal_id}")
                        save_json(MARKET_STATE_FILE, market_state)
                        try:
                            api("answerCallbackQuery", {
                                "callback_query_id": callback_id,
                                "text": "Approved — publishing will start." if action == "market_approve" else "Rejected — no public post.",
                                "show_alert": "false",
                            })
                        except Exception as exc:
                            print(f"Callback acknowledgement skipped: {exc}")
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
                                print(f"Button removal skipped: {exc}")
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
                    parts = data.split(":", 1)
                    if len(parts) == 2 and parts[0] in ("approve", "reject"):
                        action, content_id = parts
                        content_path = f"output/{content_id}.json"
                        if os.path.exists(content_path):
                            content = load_json(content_path, {})
                            content["status"] = "approved_for_publishing" if action == "approve" else "rejected"
                            content["approval_action"] = action
                            save_json(content_path, content)
                            print(f"{action.title()}d {content_id}")
                            if content_id in queue_by_id:
                                queue_by_id[content_id]["status"] = "approved" if action == "approve" else "rejected"
                                queue_by_id[content_id]["processed"] = True
                            try:
                                api("answerCallbackQuery", {
                                    "callback_query_id": callback_id,
                                    "text": "Approved" if action == "approve" else "Rejected",
                                    "show_alert": "false",
                                })
                            except Exception as exc:
                                print(f"Callback acknowledgement skipped: {exc}")
                            message = callback.get("message") or {}
                            chat_id = message.get("chat", {}).get("id")
                            message_id = message.get("message_id")
                            if chat_id and message_id:
                                try:
                                    api("editMessageReplyMarkup", {
                                        "chat_id": chat_id, "message_id": message_id,
                                        "reply_markup": json.dumps({"inline_keyboard": []}),
                                    })
                                    print("Telegram buttons removed.")
                                except Exception as exc:
                                    print(f"Button removal skipped: {exc}")
                        else:
                            print(f"Content file not found: {content_path}")
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
    if market_approved:
        write_output({"market_approved": "true", "market_signal_id": market_approved})
    else:
        write_output({"market_approved": "false", "market_signal_id": ""})

    if processed_any:
        print(f"Saved next offset: {state['update_offset']}")
    else:
        print("No Telegram approval callbacks found during this run.")


if __name__ == "__main__":
    main()
