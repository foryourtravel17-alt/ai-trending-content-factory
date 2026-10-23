#!/usr/bin/env python3
"""Register a rendered educational Reel in the existing market approval state."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

OUTPUT = Path("output")
QUEUE_PATH = OUTPUT / "approval_queue.json"
STATE_PATH = Path("data/state.json")
SAFE_ID = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def save_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(path)


def main():
    candidates = []
    for path in OUTPUT.glob("draft_*.json"):
        if path.name == "draft_seed.json":
            continue
        data = load_json(path, None)
        if isinstance(data, dict) and str(data.get("content_id", "")).strip() == path.stem:
            candidates.append((path, data))
    if not candidates:
        raise SystemExit("No rendered output/draft_<content_id>.json found.")

    source, content = max(candidates, key=lambda pair: pair[0].stat().st_mtime)
    safety_check = content.get("safety_check") if isinstance(content.get("safety_check"), dict) else {}
    if safety_check.get("passed") is not True:
        raise SystemExit("Automated safety screen did not pass; automatic publishing is blocked.")
    content_id = str(content.get("content_id", "")).strip()
    safety_screened_at = datetime.now(timezone.utc).isoformat()
    if not content_id or any(ch not in SAFE_ID for ch in content_id):
        raise SystemExit("Draft has a missing or unsafe content_id.")

    created_at = (
        content.get("created_at")
        or content.get("generated_at")
        or datetime.fromtimestamp(source.stat().st_mtime, timezone.utc).isoformat()
    )
    state = load_json(STATE_PATH, {"signals": {}, "runs": []})
    if not isinstance(state, dict):
        raise SystemExit("data/state.json has an unsupported format.")
    signals = state.setdefault("signals", {})
    if not isinstance(signals, dict):
        raise SystemExit("data/state.json signals must be an object.")

    existing = signals.get(content_id)
    if existing:
        decision = str(existing.get("approval_status", "")).lower()
        if decision in {"approved", "rejected"} or existing.get("status") in {
            "generated", "published", "partial", "publish_failed", "rejected"
        }:
            raise SystemExit(f"Refusing to overwrite an existing decision/state for {content_id}.")
        if existing.get("content_type") != "educational_reel":
            raise SystemExit(f"Content ID collision with non-Reel market record: {content_id}.")

    approval = content.get("approval") if isinstance(content.get("approval"), dict) else {}
    status = str(content.get("status", "")).strip().lower()
    if status in {"approved_for_publishing", "published_to_instagram", "rejected"} or approval.get("status") in {"approved", "rejected"}:
        raise SystemExit(f"Refusing to re-queue a decided draft: {content_id}.")

    topic = content.get("topic", {}) if isinstance(content.get("topic"), dict) else {}
    script = content.get("script", {}) if isinstance(content.get("script"), dict) else {}
    social = content.get("social", {}) if isinstance(content.get("social"), dict) else {}
    caption = str(social.get("caption", content.get("caption", "")))
    hashtags = social.get("hashtags", content.get("hashtags", []))
    if isinstance(hashtags, list):
        caption = (caption + "\n\n" + " ".join(str(tag) for tag in hashtags)).strip()

    signals[content_id] = {
        **(existing if isinstance(existing, dict) else {}),
        "content_type": "educational_reel",
        "content_id": content_id,
        "metadata_path": str(source),
        "status": "pending_approval",
        "approval_status": "pending",
        "approval_mode": "human_review",
        "safety_screened_at": safety_screened_at,
        "created_at": created_at,
        "human_approval_required": True,
        "signal": {
            "signal_id": content_id,
            "symbol": "EDUCATIONAL_REEL",
            "as_of": created_at,
            "title": str(topic.get("title", content_id)),
        },
        "copy": {
            "telegram_html": caption,
            "instagram_caption": caption,
        },
        "card_path": str(content.get("video", f"output/media/{content_id}.mp4")),
        "fact_check": {
            "status": "needs_human_review",
            "safety_screened_at": safety_screened_at,
            "notes": [
                "Automated safety/format screen passed; this is not a fact-check or publishing approval.",
                "Owner must review the exact script, caption, hashtags and matching video before publication.",
            ],
        },
        "publishing": (existing.get("publishing", {}) if isinstance(existing, dict) else {}),
    }

    content["status"] = "pending_approval"
    content["approval"] = {
        **approval,
        "required": True,
        "status": "pending",
        "mode": "human_review",
        "safety_screened_at": safety_screened_at,
    }
    content["fact_check"] = {
        **(content.get("fact_check") if isinstance(content.get("fact_check"), dict) else {}),
        "status": "needs_human_review",
        "safety_screened_at": safety_screened_at,
        "notes": [
            "Automated safety/format screen passed; this is not a fact-check or publishing approval.",
            "Owner must review the exact script, caption, hashtags and matching video before publication.",
        ],
    }
    save_json(source, content)

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
    if not any(isinstance(item, dict) and item.get("content_id") == content_id for item in items):
        items.append({"content_id": content_id, "status": "pending_approval", "processed": False})
    else:
        for item in items:
            if isinstance(item, dict) and item.get("content_id") == content_id:
                item.update({"status": "pending_approval", "processed": False})
    save_json(STATE_PATH, state)
    save_json(QUEUE_PATH, queue)
    target = os.getenv("GITHUB_OUTPUT", "").strip()
    if target:
        with open(target, "a", encoding="utf-8") as handle:
            handle.write(f"content_id={content_id}\n")
    print(f"Registered {content_id} as pending human approval after the automated safety screen. No publishing was authorized.")


if __name__ == "__main__":
    main()
