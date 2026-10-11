"""Send a transparent weekly signal, outcome, and publishing summary to Telegram."""
from __future__ import annotations
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests

STATE = Path("data/state.json")

def fetch_engagement(media_id: str, token: str, version: str) -> dict | None:
    try:
        response = requests.get(
            f"https://graph.facebook.com/{version}/{media_id}/insights",
            params={"metric": "reach,likes,comments,saved,shares", "access_token": token},
            timeout=20,
        )
        response.raise_for_status()
        metrics = {}
        for item in response.json().get("data", []):
            values = item.get("values") or []
            value = values[0].get("value", 0) if values else item.get("value", 0)
            if isinstance(value, (int, float)):
                metrics[item.get("name", "unknown")] = int(value)
        return metrics
    except (requests.RequestException, ValueError, TypeError) as exc:
        print(f"Insights unavailable for media {media_id}: {exc}")
        return None

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat:
        raise SystemExit("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID.")
    try:
        state = json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        state = {"signals": {}, "runs": []}
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=7)
    signals = []
    for record in state.get("signals", {}).values():
        try:
            created = datetime.fromisoformat(str(record.get("created_at", "")).replace("Z", "+00:00"))
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if created >= cutoff:
                signals.append(record)
        except (TypeError, ValueError):
            continue
    published = [r for r in signals if r.get("status") in {"published", "partial"}]
    pending = [r for r in signals if r.get("status") == "pending_approval"]
    outcomes = [r.get("outcome", {}) for r in signals if isinstance(r.get("outcome"), dict)]
    r_values = []
    for outcome in outcomes:
        try:
            if outcome.get("r_multiple") is not None:
                r_values.append(float(outcome["r_multiple"]))
        except (TypeError, ValueError):
            continue
    total_r = sum(r_values) if r_values else None
    ig_count = sum(1 for r in published if r.get("publishing", {}).get("instagram", {}).get("status") == "published")
    tg_count = sum(1 for r in published if r.get("publishing", {}).get("telegram", {}).get("status") == "published")
    lines = [
        "🎯 Bullseye Theory — Weekly Automation Report",
        f"Period: {cutoff.date().isoformat()} to {now.date().isoformat()} (UTC)",
        "",
        f"Scenarios generated: {len(signals)}",
        f"Published records: {len(published)}",
        f"Instagram posts confirmed: {ig_count}",
        f"Telegram posts confirmed: {tg_count}",
        f"Awaiting human review: {len(pending)}",
        "",
    ]
    if total_r is None:
        lines.append("Outcome/P&L: not tracked — no explicit closed-outcome records were logged.")
    else:
        lines.append(f"Logged outcomes: {len(r_values)} closed scenario(s), net {total_r:+.2f}R (recorded outcomes only).")

    ig_token = os.getenv("IG_ACCESS_TOKEN", os.getenv("META_SYSTEM_USER_TOKEN", "")).strip()
    version = os.getenv("META_GRAPH_API_VERSION", "v23.0")
    engagement = []
    if ig_token:
        for record in published:
            media_id = record.get("publishing", {}).get("instagram", {}).get("media_id")
            if media_id:
                metrics = fetch_engagement(str(media_id), ig_token, version)
                if metrics is not None:
                    engagement.append(metrics)
    if engagement:
        totals = {}
        for row in engagement:
            for name, value in row.items():
                totals[name] = totals.get(name, 0) + value
        lines.append(f"Instagram Insights ({len(engagement)} media): " + ", ".join(f"{k} {v}" for k, v in sorted(totals.items())) + ".")
    else:
        lines.append("Engagement: Insights unavailable (check token permissions or configure IG_ACCESS_TOKEN).")
    lines.extend([
        "Targets are not counted as hits unless an outcome is explicitly recorded.",
        "Educational market scenarios only — not financial advice.",
    ])
    message = "\n".join(lines)
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat, "text": message},
        timeout=30,
    )
    response.raise_for_status()
    if not response.json().get("ok"):
        raise RuntimeError(f"Telegram rejected report: {response.text[:400]}")
    print(message)

if __name__ == "__main__":
    main()
