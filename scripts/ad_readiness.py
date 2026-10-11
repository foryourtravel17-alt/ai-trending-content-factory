"""Read-only organic-to-paid readiness review for Bullseye Theory.

Ranks recently published Instagram posts from available Insights and sends a
private Telegram review. It never creates, changes, enables, or budgets ads.
"""
from __future__ import annotations

import json
import math
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

OUTPUT_DIR = Path("output")
METRICS = ("reach", "likes", "comments", "saved", "shares")
DEFAULT_LOOKBACK_DAYS = 14
MAX_INSIGHT_CALLS = 30
API_VERSION = os.getenv("META_GRAPH_API_VERSION", "v23.0").strip() or "v23.0"


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _number(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, number) if math.isfinite(number) else 0.0


def load_recent_published_posts(
    output_dir: Path = OUTPUT_DIR,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Read published Instagram content records without modifying them."""
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    cutoff = current - timedelta(days=max(1, int(lookback_days)))
    posts: list[dict[str, Any]] = []
    if not output_dir.exists():
        return posts

    for path in output_dir.glob("content_*.json"):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(record, dict):
            continue

        published_time = _parse_time(record.get("published_at") or record.get("created_at"))
        if published_time is None or not (cutoff <= published_time <= current + timedelta(minutes=5)):
            continue

        publishing = record.get("publishing")
        publishing = publishing if isinstance(publishing, dict) else {}
        instagram = publishing.get("instagram")
        instagram = instagram if isinstance(instagram, dict) else {}
        state = str(instagram.get("status") or record.get("status") or "").lower()
        media_id = str(instagram.get("media_id") or record.get("instagram_media_id") or "").strip()
        if state not in {"published", "published_to_instagram"} or not media_id:
            continue

        topic = record.get("topic")
        topic = topic if isinstance(topic, dict) else {}
        script = record.get("script")
        script = script if isinstance(script, dict) else {}
        title = topic.get("title") or script.get("hook") or record.get("content_id") or path.stem
        posts.append({
            "content_id": str(record.get("content_id") or path.stem),
            "title": str(title).strip(),
            "media_id": media_id,
            "published_at": published_time.isoformat(),
            "content_role": str(record.get("content_role") or "unspecified"),
        })

    posts.sort(key=lambda item: item["published_at"], reverse=True)
    return posts[:MAX_INSIGHT_CALLS]


def fetch_engagement(media_id: str, token: str, version: str = API_VERSION) -> dict[str, int] | None:
    """Fetch only media Insights; never log credentials or response bodies."""
    try:
        response = requests.get(
            f"https://graph.facebook.com/{version}/{media_id}/insights",
            params={"metric": ",".join(METRICS), "access_token": token},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        result: dict[str, int] = {}
        for item in payload.get("data", []):
            if not isinstance(item, dict):
                continue
            values = item.get("values") or []
            value = values[0].get("value", 0) if values else item.get("value", 0)
            name = str(item.get("name") or "")
            if name in METRICS:
                result[name] = int(_number(value))
        return result
    except (requests.RequestException, ValueError, TypeError) as exc:
        print(f"Instagram Insights unavailable for media {media_id} ({type(exc).__name__}); response and credentials redacted.")
        return None


def rank_candidates(posts: list[dict[str, Any]], metrics_by_media: dict[str, dict[str, Any] | None]) -> list[dict[str, Any]]:
    """Rank candidates using 70% save/share rate and 30% total engagement rate."""
    ranked: list[dict[str, Any]] = []
    for post in posts:
        metrics = metrics_by_media.get(str(post.get("media_id", "")))
        if not isinstance(metrics, dict):
            continue
        row = {name: int(_number(metrics.get(name, 0))) for name in METRICS}
        total = row["likes"] + row["comments"] + row["saved"] + row["shares"]
        saves_shares = row["saved"] + row["shares"]
        reach = row["reach"]
        if reach > 0:
            engagement_rate = total / reach
            save_share_rate = saves_shares / reach
            score = 0.7 * save_share_rate + 0.3 * engagement_rate
        else:
            engagement_rate = None
            save_share_rate = None
            score = None
        ranked.append({
            **post, **row, "total_engagements": total,
            "engagement_rate": engagement_rate,
            "save_share_rate": save_share_rate,
            "screening_score": score,
        })

    ranked.sort(key=lambda item: (
        item["screening_score"] if item["screening_score"] is not None else -1.0,
        item["saved"] + item["shares"], item["comments"], item["likes"], item["reach"],
    ), reverse=True)
    return ranked


def build_report(candidates: list[dict[str, Any]], published_count: int, lookback_days: int = DEFAULT_LOOKBACK_DAYS) -> str:
    lines = [
        "Bullseye Theory — Organic → Paid Readiness",
        f"Lookback: last {lookback_days} days",
        f"Recent published Instagram posts found: {published_count}",
        f"Posts with readable Insights: {len(candidates)}",
        "",
    ]
    if not candidates:
        lines.append("STATUS: HOLD — no usable post-level Insights were returned. Keep organic-first; do not choose a paid creative from missing data.")
    elif len(candidates) < 3:
        lines.append("STATUS: EARLY DATA — fewer than 3 posts have readable Insights. This list is informational only; wait for a larger baseline before recommending a boost.")
    else:
        lines.append("STATUS: HUMAN REVIEW — these are organic creative candidates only, not a forecast or an approved campaign.")

    for index, item in enumerate(candidates[:3], start=1):
        title = " ".join(str(item.get("title", "Untitled post")).split())
        if len(title) > 86:
            title = title[:83].rstrip() + "..."
        rate = item.get("engagement_rate")
        rate_text = f"{rate * 100:.2f}%" if isinstance(rate, (int, float)) else "n/a"
        lines.append(
            f"{index}. {title}\n"
            f"   Reach {item['reach']:,} · Likes {item['likes']:,} · Comments {item['comments']:,} · "
            f"Saves {item['saved']:,} · Shares {item['shares']:,} · Engagement/reach {rate_text}"
        )

    lines.extend([
        "",
        "Guardrail: read-only review. No ad, campaign, audience, budget, or payment was created or changed.",
        "Before any paid test: confirm the correct ad account, verify the destination and tracking, set a hard total spend cap, and approve the complete campaign preview.",
        "Trading education only: no guaranteed-return, fake-performance, or unsupported testimonial claims.",
    ])
    return "\n".join(lines)


def send_telegram_message(token: str, chat_id: str, text: str) -> None:
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
        timeout=20,
    )
    try:
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError):
        status = getattr(response, "status_code", "unknown")
        raise RuntimeError(f"Telegram review delivery failed (HTTP {status}); response details redacted.") from None
    if not payload.get("ok"):
        raise RuntimeError("Telegram rejected the review message; response details redacted.")


def main() -> None:
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    telegram_chat = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not telegram_token or not telegram_chat:
        raise SystemExit("Missing Telegram delivery configuration; credentials are not printed.")

    try:
        lookback_days = max(1, min(30, int(os.getenv("LOOKBACK_DAYS", str(DEFAULT_LOOKBACK_DAYS)))))
    except ValueError:
        lookback_days = DEFAULT_LOOKBACK_DAYS

    posts = load_recent_published_posts(lookback_days=lookback_days)
    if not posts:
        send_telegram_message(telegram_token, telegram_chat, build_report([], 0, lookback_days))
        print("No recent published Instagram posts; sent an informational review.")
        return

    meta_token = os.getenv("IG_ACCESS_TOKEN", "").strip() or os.getenv("META_SYSTEM_USER_TOKEN", "").strip()
    if not meta_token:
        raise SystemExit("No Meta/Instagram read token configured; credentials are not printed.")

    metrics_by_media: dict[str, dict[str, int] | None] = {}
    for post in posts:
        metrics_by_media[post["media_id"]] = fetch_engagement(post["media_id"], meta_token)

    candidates = rank_candidates(posts, metrics_by_media)
    send_telegram_message(telegram_token, telegram_chat, build_report(candidates, len(posts), lookback_days))
    print(f"Read-only paid-readiness review delivered: {len(candidates)} posts scored from {len(posts)} recent published posts.")


if __name__ == "__main__":
    main()
