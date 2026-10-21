#!/usr/bin/env python3
"""Register the latest educational Reel draft in the existing human approval queue.

The MP4 remains a GitHub Actions artifact; only review metadata is written to the
repository. This script never publishes content.
"""
import json
from pathlib import Path

OUTPUT = Path("output")
QUEUE_PATH = OUTPUT / "approval_queue.json"


def load_json(path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def main():
    candidates = sorted(OUTPUT.glob("content_draft_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise SystemExit("No rendered educational content_draft_*.json found.")

    source = candidates[0]
    content = load_json(source)
    if not isinstance(content, dict):
        raise SystemExit(f"Invalid draft JSON: {source.name}")
    content_id = str(content.get("content_id", "")).strip()
    if not content_id or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for ch in content_id):
        raise SystemExit("Draft has a missing or unsafe content_id.")

    # Never overwrite an existing approval decision or reuse an ID.
    target = OUTPUT / f"{content_id}.json"
    existing = load_json(target)
    if isinstance(existing, dict):
        print(f"Approval record already exists for {content_id}; leaving it unchanged.")
        return

    content["status"] = "draft_only"
    content["approval"] = {
        **(content.get("approval") if isinstance(content.get("approval"), dict) else {}),
        "required": True,
        "status": "pending",
        "mode": "human_review",
    }
    content["fact_check"] = {
        **(content.get("fact_check") if isinstance(content.get("fact_check"), dict) else {}),
        "status": "needs_human_review",
        "notes": ["Human reviewer must verify the educational claims before approval."],
    }
    target.write_text(json.dumps(content, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    queue = load_json(QUEUE_PATH, {"items": [], "telegram_sent": []})
    if isinstance(queue, list):
        queue = {"items": queue, "telegram_sent": []}
    if not isinstance(queue, dict):
        raise SystemExit("Approval queue has an unsupported format.")
    items = queue.setdefault("items", [])
    if not isinstance(items, list):
        raise SystemExit("Approval queue items must be a list.")
    if not any(isinstance(item, dict) and item.get("content_id") == content_id for item in items):
        items.append({"content_id": content_id, "status": "pending", "processed": False})
    queue.setdefault("telegram_sent", [])
    QUEUE_PATH.write_text(json.dumps(queue, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Queued {content_id} for human review. No publishing was attempted.")


if __name__ == "__main__":
    main()
