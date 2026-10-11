"""Send weekly hypothetical signal outcomes and available Instagram Insights to Telegram.

This is scenario analysis from public OHLC, not broker execution or realized P&L.
"""
from __future__ import annotations
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests
import pandas as pd
import yfinance as yf

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
        print(f"Insights unavailable for media {media_id} ({type(exc).__name__}); request details redacted.")
        return None

def fetch_weekly_ohlc(symbol: str) -> pd.DataFrame | None:
    try:
        frame = yf.download(symbol, period="7d", interval="1h", auto_adjust=True,
                             progress=False, threads=False, timeout=20)
        if frame is None or frame.empty:
            return None
        if isinstance(frame.columns, pd.MultiIndex):
            matched = False
            for level in range(frame.columns.nlevels):
                if symbol in frame.columns.get_level_values(level):
                    frame = frame.xs(symbol, axis=1, level=level, drop_level=True)
                    matched = True
                    break
            if not matched:
                frame.columns = frame.columns.get_level_values(0)
        frame.columns = [str(c).title() for c in frame.columns]
        if not {"High", "Low"}.issubset(frame.columns):
            return None
        if frame.index.tz is None:
            frame.index = frame.index.tz_localize("UTC")
        else:
            frame.index = frame.index.tz_convert("UTC")
        return frame.sort_index()
    except Exception as exc:
        print(f"Outcome data unavailable for {symbol}: {exc}")
        return None

def evaluate_signal(signal: dict, frame: pd.DataFrame) -> tuple[float | None, str]:
    try:
        as_of = pd.Timestamp(signal["as_of"])
        as_of = as_of.tz_localize("UTC") if as_of.tzinfo is None else as_of.tz_convert("UTC")
        future = frame[frame.index > as_of]
        direction = signal["direction"]
        stop = float(signal["stop_loss"])
        targets = [float(signal[f"tp{i}"]) for i in (1, 2, 3)]
        if future.empty:
            return None, "open/no newer candles"
        for _, bar in future.iterrows():
            high, low = float(bar["High"]), float(bar["Low"])
            # Conservative rule: if stop and target were both touched in one bar, assume SL first.
            if direction == "LONG":
                if low <= stop:
                    return -1.0, "SL"
                if high >= targets[2]:
                    return 2.0, "TP3"
                if high >= targets[1]:
                    return 1.5, "TP2"
                if high >= targets[0]:
                    return 1.0, "TP1"
            else:
                if high >= stop:
                    return -1.0, "SL"
                if low <= targets[2]:
                    return 2.0, "TP3"
                if low <= targets[1]:
                    return 1.5, "TP2"
                if low <= targets[0]:
                    return 1.0, "TP1"
        return None, "open/no level touched"
    except (KeyError, TypeError, ValueError):
        return None, "invalid signal record"

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
    lines = [
        "🎯 Bullseye Theory — Weekly Automation Report",
        f"Period: {cutoff.date().isoformat()} to {now.date().isoformat()} (UTC)",
        "",
        f"Scenarios generated: {len(signals)}",
        f"Published/partial records: {len(published)}",
        f"Instagram posts confirmed: {sum(1 for r in published if r.get('publishing', {}).get('instagram', {}).get('status') == 'published')}",
        f"Telegram posts confirmed: {sum(1 for r in published if r.get('publishing', {}).get('telegram', {}).get('status') == 'published')}",
        f"Awaiting human review: {len(pending)}",
        "",
    ]

    # Approximate outcomes from OHLC bars after the scenario timestamp; not executed P&L.
    by_symbol = {}
    for record in published:
        signal = record.get("signal", {})
        symbol = signal.get("symbol")
        if symbol:
            by_symbol.setdefault(symbol, []).append(record)
    results = []
    open_count = 0
    for symbol, records in by_symbol.items():
        frame = fetch_weekly_ohlc(symbol)
        if frame is None:
            open_count += len(records)
            continue
        for record in records:
            result, label = evaluate_signal(record.get("signal", {}), frame)
            if result is None:
                open_count += 1
            else:
                results.append((result, label))
    if results:
        net_r = sum(result for result, _ in results)
        lines.append(f"Scenario outcome estimate: {len(results)} resolved, net {net_r:+.2f}R; SL {sum(1 for _, label in results if label == 'SL')}, targets {sum(1 for _, label in results if label.startswith('TP'))}.")
        lines.append("This is OHLC-based hypothetical scenario analysis, not actual broker P&L; same-candle SL/TP is counted as SL.")
    else:
        lines.append("Scenario outcome estimate: no resolved post-signal levels available yet.")
    lines.append(f"Open/unavailable scenarios: {open_count}.")

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
        "Targets are not counted as hits unless observed in post-signal candles.",
        "Educational market scenarios only — not financial advice.",
    ])
    message = "\n".join(lines)
    try:
        response = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                                 data={"chat_id": chat, "text": message}, timeout=30)
    except requests.RequestException as exc:
        raise SystemExit(f"Telegram report request failed ({type(exc).__name__}); bot token redacted.") from None
    if not response.ok:
        raise SystemExit(f"Telegram report failed with HTTP {response.status_code}; response redacted.")
    if not response.json().get("ok"):
        raise RuntimeError(f"Telegram rejected report: {response.text[:400]}")
    print(message)

if __name__ == "__main__":
    main()
