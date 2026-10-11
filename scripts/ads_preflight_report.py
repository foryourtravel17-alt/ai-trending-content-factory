"""Read-only organic-to-paid preflight report for Bullseye Theory.

This module reads recent published-content records, optionally fetches Instagram
media insights, ranks posts by an explicitly described engagement heuristic, and
sends a private Telegram review. It never calls Ads Manager write endpoints and
never creates, activates, or budgets a campaign.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

GRAPH_VERSION = os.getenv("META_GRAPH_API_VERSION", "v23.0")
GRAPH_ROOT = f"https://graph.facebook.com/{GRAPH_VERSION}"
OUTPUT_DIR = Path("output")
CONTENT_GLOB = "content_*.json"
MAX_POSTS_TO_CHECK = 12
TELEGRAM_MESSAGE_LIMIT = 3800


def parse_datetime(value: Any) -> datetime | None:
    """Parse ISO timestamps into timezone-aware UTC datetimes."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def load_published_posts(
    output_dir: Path = OUTPUT_DIR,
    days: int = 30,
    limit: int = MAX_POSTS_TO_CHECK,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Return newest published Instagram content records; no private metrics are saved."""
    now_utc = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    cutoff = now_utc - timedelta(days=days)
    posts: list[dict[str, Any]] = []
    seen_media: set[str] = set()

    for path in output_dir.glob(CONTENT_GLOB):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        created = parse_datetime(record.get("created_at"))
        if created is None or created < cutoff or created > now_utc + timedelta(minutes=5):
            continue

        publishing = record.get("publishing") or {}
        instagram = publishing.get("instagram") or {}
        media_id = str(instagram.get("media_id") or record.get("instagram_media_id") or "").strip()
        status = str(instagram.get("status") or record.get("status") or "").lower()
        published_status = status in {
            "published", "success", "published_to_instagram",
        } or bool(media_id)
        if not published_status or not media_id or media_id in seen_media:
            continue
        seen_media.add(media_id)

        topic = record.get("topic") or {}
        script = record.get("script") or {}
        posts.append({
            "content_id": str(record.get("content_id") or path.stem),
            "created_at": created.isoformat(),
            "media_id": media_id,
            "title": str(topic.get("title") or path.stem),
            "hook": str(script.get("hook") or ""),
            "content_role": str(record.get("content_role") or "educational"),
            "permalink": str(instagram.get("permalink") or ""),
        })

    posts.sort(key=lambda item: item["created_at"], reverse=True)
    return posts[: max(0, limit)]


def fetch_media_insights(media_id: str, access_token: str) -> dict[str, int] | None:
    """Read supported post metrics. Do not log request URLs or any token."""
    try:
        response = requests.get(
            f"{GRAPH_ROOT}/{media_id}/insights",
            params={
                "metric": "reach,likes,comments,saved,shares",
                "access_token": access_token,
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError, TypeError) as exc:
        # Avoid printing exception text: provider errors may include request details.
        print(f"Instagram Insights unavailable for one media item ({type(exc).__name__}).")
        return None

    metrics: dict[str, int] = {}
    for item in payload.get("data", []):
        name = str(item.get("name") or "")
        values = item.get("values") or []
        value = values[0].get("value", 0) if values else item.get("value", 0)
        if name in {"reach", "likes", "comments", "saved", "shares"}:
            try:
                metrics[name] = max(0, int(value or 0))
            except (TypeError, ValueError, OverflowError):
                continue
    return metrics or None


def score_metrics(metrics: dict[str, int]) -> dict[str, float | int] | None:
    """Rank by weighted meaningful interactions per reach; this is not a sales metric."""
    reach = int(metrics.get("reach", 0) or 0)
    if reach <= 0:
        return None
    likes = int(metrics.get("likes", 0) or 0)
    comments = int(metrics.get("comments", 0) or 0)
    saves = int(metrics.get("saved", 0) or 0)
    shares = int(metrics.get("shares", 0) or 0)
    interactions = likes + comments + saves + shares
    weighted = likes + (2 * comments) + (3 * saves) + (3 * shares)
    return {
        "reach": reach,
        "likes": likes,
        "comments": comments,
        "saves": saves,
        "shares": shares,
        "interactions": interactions,
        "weighted_engagement": weighted,
        "weighted_engagement_per_reach_pct": round((weighted / reach) * 100, 3),
    }


def build_report(
    posts: list[dict[str, Any]],
    insights: dict[str, dict[str, int] | None],
    now: datetime | None = None,
) -> str:
    """Build a private review note, explicitly distinguishing engagement from conversions."""
    now_utc = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    ranked: list[dict[str, Any]] = []
    failed = 0
    for post in posts:
        metrics = insights.get(post["media_id"])
        scored = score_metrics(metrics or {})
        if scored is None:
            failed += 1
            continue
        ranked.append({**post, "metrics": scored})

    ranked.sort(
        key=lambda item: (
            item["metrics"]["weighted_engagement_per_reach_pct"],
            item["metrics"]["interactions"],
        ),
        reverse=True,
    )

    lines = [
        "Bullseye Theory — Organic → Paid Preflight",
        f"Generated: {now_utc.strftime('%d %b %Y %H:%M UTC')}",
        "Mode: READ-ONLY. No Ads Manager changes or spend.",
        "",
        f"Recent published posts reviewed: {len(posts)} (last 30 days; max 12)",
    ]

    if ranked:
        lines.extend([
            "",
            "Best organic engagement candidates (not proof of sales):",
        ])
        for index, item in enumerate(ranked[:3], start=1):
            m = item["metrics"]
            title = item["title"][:100]
            lines.append(
                f"{index}. {title} — weighted engagement/reach {m['weighted_engagement_per_reach_pct']:.3f}%; "
                f"reach {m['reach']}; interactions {m['interactions']} "
                f"(likes {m['likes']}, comments {m['comments']}, saves {m['saves']}, shares {m['shares']})."
            )
            if item.get("permalink"):
                lines.append(f"   Post: {item['permalink']}")
        lines.extend([
            "",
            "AI recommendation: review the top post as a candidate for a small, approval-gated test. "
            "Engagement efficiency alone does not establish course sales or return on ad spend.",
        ])
    else:
        lines.extend([
            "",
            "No reliable winner selected: recent media insights were missing, unavailable, or had no reach value.",
            "AI recommendation: do not boost a post based on guesses. Restore Insights access or gather enough "
            "organic data, then re-run this report.",
        ])

    lines.extend([
        "",
        "Pre-launch blockers:",
        "• Owner must confirm the exact Meta ad account before any campaign is created.",
        "• Verify the destination (course page, lead form, or Telegram funnel), offer copy, and end-to-end tracking.",
        "• Set and record a daily budget, campaign dates, and a hard total spend cap.",
        "• Choose objective only after the destination/event is verified; engagement is not the same as leads or sales.",
        "• Owner's explicit final approval is required for the first live campaign.",
        "",
        "Targeting status: not finalized. After account confirmation, compare a broad eligible audience with only "
        "platform-validated trading-education interests in the intended market. Do not target sensitive financial "
        "circumstances or claim guaranteed returns.",
        "",
        "This report is sent privately to Telegram; post-level performance metrics are not committed to this public repo.",
        "Campaign created/edited/activated: NO. Budget changed: NO. Spend: NO.",
    ])
    return "\n".join(lines)[:TELEGRAM_MESSAGE_LIMIT]


def send_telegram(message: str, bot_token: str, chat_id: str) -> None:
    """Send the report to the configured private Telegram chat without logging secrets."""
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            data={
                "chat_id": chat_id,
                "text": message,
                "disable_web_page_preview": "true",
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            raise RuntimeError("Telegram rejected the report.")
    except (requests.RequestException, ValueError, TypeError) as exc:
        raise RuntimeError(
            f"Could not deliver the private ads preflight report ({type(exc).__name__}); credentials redacted."
        ) from None


def main() -> int:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not bot_token or not chat_id:
        raise SystemExit("Missing Telegram credentials; report not sent.")

    posts = load_published_posts()
    access_token = (
        os.getenv("IG_ACCESS_TOKEN", "").strip()
        or os.getenv("META_SYSTEM_USER_TOKEN", "").strip()
    )
    insights: dict[str, dict[str, int] | None] = {}
    if access_token:
        for post in posts:
            media_id = post["media_id"]
            if media_id not in insights:
                insights[media_id] = fetch_media_insights(media_id, access_token)
    else:
        insights = {post["media_id"]: None for post in posts}

    report = build_report(posts, insights)
    send_telegram(report, bot_token, chat_id)
    # Only emit non-sensitive delivery metadata into public Actions logs.
    winners = sum(1 for post in posts if score_metrics(insights.get(post["media_id"]) or {}))
    print(f"Ads preflight report sent privately. Posts reviewed: {len(posts)}; measurable candidates: {winners}.")
    print("Read-only workflow complete; no advertising changes or spending performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
