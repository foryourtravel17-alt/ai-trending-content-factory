#!/usr/bin/env python3
"""Generate a Bullseye Theory Premium lesson and optionally send it to Telegram.

Safe by default: no network request is made unless DRY_RUN=false AND
PREMIUM_TELEGRAM_AUTOPUBLISH=true. This publishes educational text only; it
is not a live market-data feed or a personalized trading recommendation.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

BRAND = "Bullseye Theory Premium"
DISCLAIMER = (
    "Educational content only — not investment advice. Markets involve risk. "
    "Verify market data independently and define risk before any trade."
)
LESSONS: list[dict[str, str]] = [
    {
        "pillar": "Market Structure",
        "title": "Read Structure Before the Candle",
        "body": (
            "1. Start on a higher timeframe and mark meaningful swing highs and lows.\n"
            "2. Higher highs plus higher lows suggest an uptrend; lower highs plus lower lows suggest a downtrend. Overlapping swings can indicate a range or transition.\n"
            "3. A wick through a level is a test, not proof of acceptance. Look for a candle close and follow-through.\n"
            "4. Write down what would invalidate the idea before considering an entry.\n"
            "5. Build three scenarios: continuation, failed breakout, and range rotation.\n\n"
            "Practice: mark two swing highs and two swing lows on a chart. Write the invalidation level for both bullish and bearish hypotheses. Avoid hindsight-based marking."
        ),
    },
    {
        "pillar": "Risk Management",
        "title": "Position Size: Risk First, Entry Second",
        "body": (
            "1. Choose a maximum account-risk amount before entering.\n"
            "2. Estimate position size from the distance between entry and the invalidation/stop level.\n"
            "3. Formula for a simple spot position: position size = planned monetary risk ÷ (entry price − stop price), for a long position when prices and units match. Fees, slippage, contract multipliers, and leverage can change the real result.\n"
            "4. If the stop distance makes the position too large or the setup unclear, reduce size or skip the trade. Never move a stop farther away just to avoid taking a loss.\n"
            "5. Record planned risk and actual outcome in a journal.\n\n"
            "Practice: calculate a hypothetical size on paper, include fees, then stress-test a gap or slippage scenario. This is a learning exercise, not a recommendation to trade."
        ),
    },
    {
        "pillar": "Trading Psychology",
        "title": "A Checklist Beats Impulse",
        "body": (
            "Before any hypothetical trade, answer: What is the market structure? What is the setup? Where is invalidation? What is the planned risk? What would make me stand aside?\n\n"
            "If any answer is vague, wait. Do not chase a move because a candle is large, recover a loss immediately, or increase risk after a win. A no-trade decision is a valid process outcome.\n\n"
            "Journal the plan before the outcome so the review measures decision quality, not just profit or loss."
        ),
    },
]


def build_post(index: int = 0) -> str:
    lesson = LESSONS[index % len(LESSONS)]
    day = datetime.now(timezone.utc).strftime("%d %b %Y UTC")
    return (
        f"🎯 {BRAND}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"LESSON | {lesson['pillar']}\n"
        f"{lesson['title']}\n\n"
        f"{lesson['body']}\n\n"
        f"📝 Bullseye Drill: write your answer in your journal before checking another chart.\n\n"
        f"{DISCLAIMER}\n"
        f"\n#BullseyeTheory #TradingEducation #RiskManagement\n"
        f"Prepared: {day}"
    )


def telegram_request(token: str, chat_id: str, text: str) -> dict[str, Any]:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            body = response.read().decode("utf-8", errors="replace")
            data = json.loads(body)
            if response.status >= 400 or not data.get("ok"):
                raise RuntimeError(f"Telegram API HTTP {response.status}; response={body}")
            return data
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        # Telegram errors generally include error_code and description; print full body.
        raise RuntimeError(f"Telegram API HTTP {exc.code}; response={body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Telegram network error: {exc!r}") from exc


def main() -> int:
    dry_run = os.getenv("DRY_RUN", "true").strip().lower() not in {"0", "false", "no"}
    allow_publish = os.getenv("PREMIUM_TELEGRAM_AUTOPUBLISH", "false").strip().lower() in {"1", "true", "yes"}
    try:
        lesson_index = int(os.getenv("LESSON_INDEX", "0"))
        post = build_post(lesson_index)
    except (ValueError, IndexError) as exc:
        print(f"CONFIG ERROR: invalid LESSON_INDEX: {exc}", file=sys.stderr)
        return 2

    print("=== PREMIUM TELEGRAM POST PREVIEW ===")
    print(post)
    print("=== END PREVIEW ===")
    print(json.dumps({"dry_run": dry_run, "autopublish_enabled": allow_publish}, indent=2))

    if dry_run:
        print("DRY RUN: no Telegram API request made.")
        return 0
    if not allow_publish:
        print("SAFE STOP: set PREMIUM_TELEGRAM_AUTOPUBLISH=true as well as DRY_RUN=false to permit publishing.", file=sys.stderr)
        return 3

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("PREMIUM_TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("CONFIG ERROR: TELEGRAM_BOT_TOKEN and PREMIUM_TELEGRAM_CHAT_ID are required.", file=sys.stderr)
        return 2
    try:
        result = telegram_request(token, chat_id, post)
        message = result.get("result", {})
        print(json.dumps({"published": True, "chat_id": str(chat_id), "message_id": message.get("message_id")}, indent=2))
        return 0
    except Exception as exc:
        print(f"PUBLISH ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
