#!/usr/bin/env python3
"""Register the latest rendered educational Reel in the human approval queue.

The renderer writes output/<content_id>.json where content_id starts with
'draft_'. Keep that file as the single source of truth and never publish here.
"""
import json
from pathlib import Path

OUTPUT = Path("output")
QUEUE_PATH = OUTPUT / "approval_queue.json"
SAFE_ID = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")


def load_json(path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def main():
    candidates = []
    for path in OUTPUT.glob("draft_*.json"):
        if path.name == "draft_seed.json":
            continue
        data = load_json(path)
        if isinstance(data, dict) and str(data.get("content_id", "")).strip() == path.stem:
            candidates.append((path, data))

    if not candidates:
        raise SystemExit("No rendered output/draft_<content_id>.json found.")

    source, content = max(candidates, key=lambda pair: pair[0].stat().st_mtime)
    content_id = str(content.get("content_id", "")).strip()
    if not content_id or any(ch not in SAFE_ID for ch in content_id):
        raise SystemExit("Draft has a missing or unsafe content_id.")

    status = str(content.get("status", "")).strip()
    approval = content.get("approval") if isinstance(content.get("approval"), dict) else {}
    if status in {"approved_for_publishing", "published_to_instagram", "rejected"} or approval.get("status") in {"approved", "rejected"}:
        raise SystemExit(f"Refusing to overwrite existing decision for {content_id}.")

    queue = load_json(QUEUE_PATH, {"items": [], "telegram_sent": []})
    if isinstance(queue, list):
        queue = {"items": queue, "telegram_sent": []}
    if not isinstance(queue, dict):
        raise SystemExit("Approval queue has an unsupported format.")
    items = queue.setdefault("items", [])
    if not isinstance(items, list):
        raise SystemExit("Approval queue items must be a list.")
    if not isinstance(queue.setdefault("telegram_sent", []), list):
        raise SystemExit("Approval queue telegram_sent must be a list.")

    existing_item = next((item for item in items if isinstance(item, dict) and item.get("content_id") == content_id), None)
    if existing_item:
        print(f"Draft {content_id} is already in the approval queue; leaving it unchanged.")
        return

    content["status"] = "draft_only"
    content["approval"] = {
        **approval,
        "required": True,
        "status": "pending",
        "mode": "human_review",
    }
    content["fact_check"] = {
        **(content.get("fact_check") if isinstance(content.get("fact_check"), dict) else {}),
        "status": "needs_human_review",
        "notes": ["Human reviewer must verify the educational claims before approval."],
    }
    source.write_text(json.dumps(content, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    items.append({"content_id": content_id, "status": "pending", "processed": False})
    QUEUE_PATH.write_text(json.dumps(queue, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Queued {content_id} for human review. No publishing was attempted.")


if __name__ == "__main__":
    main()
