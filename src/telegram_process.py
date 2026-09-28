import json
import os
import urllib.parse
import urllib.request
import urllib.error

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
API = f"https://api.telegram.org/bot{TOKEN}"
STATE_FILE = "output/telegram_state.json"
QUEUE_FILE = "output/approval_queue.json"


def api(method, data=None, timeout=30):
    data = data or {}
    encoded = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(f"{API}/{method}", data=encoded, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            payload = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        raise RuntimeError(f"Telegram API HTTP {exc.code}: {body}") from exc

    if not payload.get("ok"):
        raise RuntimeError(f"Telegram API error: {payload}")
    return payload["result"]


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, value):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(value, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main():
    import time

    state = load_json(STATE_FILE, {"update_offset": 0})
    queue = load_json(QUEUE_FILE, {"items": []})
    offset = int(state.get("update_offset", 0))
    print(f"Starting offset: {offset}")

    queue_by_id = {item.get("content_id"): item for item in queue.get("items", [])}
    deadline = time.time() + 55
    processed_any = False

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

                parts = data.split(":", 1)
                if len(parts) == 2 and parts[0] in ("approve", "reject"):
                    action, content_id = parts
                    content_path = f"output/{content_id}.json"

                    if os.path.exists(content_path):
                        content = load_json(content_path, {})
                        new_status = (
                            "approved_for_publishing"
                            if action == "approve"
                            else "rejected"
                        )
                        content["status"] = new_status
                        content["approval_action"] = action
                        save_json(content_path, content)
                        print(f"{action.title()}d {content_id}")

                        if content_id in queue_by_id:
                            queue_by_id[content_id]["status"] = (
                                "approved" if action == "approve" else "rejected"
                            )
                            queue_by_id[content_id]["processed"] = True

                        try:
                            api("answerCallbackQuery", {
                                "callback_query_id": callback_id,
                                "text": "Approved" if action == "approve" else "Rejected",
                                "show_alert": "false",
                            })
                            print("Callback acknowledged.")
                        except Exception as exc:
                            print(f"Callback acknowledgement skipped: {exc}")

                        message = callback.get("message") or {}
                        chat_id = message.get("chat", {}).get("id")
                        message_id = message.get("message_id")
                        if chat_id and message_id:
                            try:
                                api("editMessageReplyMarkup", {
                                    "chat_id": chat_id,
                                    "message_id": message_id,
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

    if processed_any:
        print(f"Saved next offset: {state['update_offset']}")
    else:
        print("No Telegram approval callbacks found during this run.")


if __name__ == "__main__":
    main()
