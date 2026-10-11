"""Fetch market OHLC and calculate transparent technical indicators.

Signals are educational scenarios from a rule-based screen, not trade instructions.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
import yfinance as yf

log = logging.getLogger(__name__)

SYMBOLS = {
    "GLOBAL": {
        "GC=F": "Gold", "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum",
        "EURUSD=X": "EUR/USD", "^NDX": "Nasdaq 100", "SPY": "S&P 500 ETF",
    },
    "INDIA": {
        "^NSEI": "Nifty 50", "^NSEBANK": "Bank Nifty",
        "RELIANCE.NS": "Reliance", "HDFCBANK.NS": "HDFC Bank",
        "TCS.NS": "TCS", "INFY.NS": "Infosys", "SBIN.NS": "State Bank of India",
    },
}
MAX_PER_REGION = 3


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "market"


def _normalize_frame(frame: pd.DataFrame, symbol: str) -> pd.DataFrame:
    if frame is None or frame.empty:
        raise ValueError("Yahoo Finance returned no OHLC candles.")
    if isinstance(frame.columns, pd.MultiIndex):
        if symbol in frame.columns.get_level_values(-1):
            frame = frame.xs(symbol, axis=1, level=-1, drop_level=True)
        else:
            frame.columns = frame.columns.get_level_values(0)
    frame.columns = [str(c).title() for c in frame.columns]
    required = {"Open", "High", "Low", "Close"}
    if not required.issubset(set(frame.columns)):
        raise ValueError(f"OHLC columns missing; received {list(frame.columns)}")
    frame = frame.copy()
    frame = frame[~frame.index.duplicated(keep="last")].sort_index()
    for col in ("Open", "High", "Low", "Close", "Volume"):
        if col not in frame:
            frame[col] = np.nan if col == "Volume" else frame["Close"]
    frame = frame.dropna(subset=["Open", "High", "Low", "Close"])
    if len(frame) < 60:
        raise ValueError(f"Only {len(frame)} candles available; need at least 60.")
    return frame


def fetch_ohlc(symbol: str) -> pd.DataFrame:
    """Fetch 60 days of hourly candles. Per-symbol calls isolate provider failures."""
    log.info("Fetching hourly OHLC for %s", symbol)
    raw = yf.download(
        symbol, period="60d", interval="1h", auto_adjust=True,
        progress=False, threads=False, prepost=False, timeout=25,
    )
    return _normalize_frame(raw, symbol)


def compute_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    df = frame.copy()
    close = df["Close"]
    df["EMA20"] = close.ewm(span=20, adjust=False).mean()
    df["EMA50"] = close.ewm(span=50, adjust=False).mean()
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["RSI14"] = (100 - (100 / (1 + rs))).fillna(50)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_SIGNAL"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_HIST"] = df["MACD"] - df["MACD_SIGNAL"]
    prev_close = close.shift(1)
    true_range = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - prev_close).abs(),
        (df["Low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    df["ATR14"] = true_range.rolling(14).mean()
    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    vol = pd.to_numeric(df["Volume"], errors="coerce").fillna(0)
    if vol.sum() > 0:
        sessions = pd.Index(df.index.date)
        numerator = (typical * vol).groupby(sessions).cumsum()
        denominator = vol.groupby(sessions).cumsum().replace(0, np.nan)
        df["VWAP"] = numerator / denominator
    else:
        df["VWAP"] = np.nan
    df["SWING_HIGH"] = df["High"].rolling(20).max().shift(1)
    df["SWING_LOW"] = df["Low"].rolling(20).min().shift(1)
    return df.dropna(subset=["EMA50", "ATR14"])


def make_signal(symbol: str, label: str, region: str, frame: pd.DataFrame) -> dict[str, Any] | None:
    if frame.empty:
        return None
    row = frame.iloc[-1]
    entry = float(row["Close"])
    atr = float(row["ATR14"])
    rsi = float(row["RSI14"])
    hist = float(row["MACD_HIST"])
    if not all(np.isfinite(v) for v in (entry, atr, rsi, hist)) or entry <= 0 or atr <= 0:
        return None
    long_setup = row["EMA20"] > row["EMA50"] and 50 <= rsi <= 68 and hist > 0
    short_setup = row["EMA20"] < row["EMA50"] and 32 <= rsi <= 50 and hist < 0
    if not (long_setup or short_setup):
        log.info("%s: neutral/weak setup; skipped.", symbol)
        return None
    direction = "LONG" if long_setup else "SHORT"
    risk = 1.5 * atr
    if direction == "LONG":
        stop = entry - risk
        targets = [entry + risk, entry + 1.5 * risk, entry + 2.0 * risk]
    else:
        stop = entry + risk
        targets = [entry - risk, entry - 1.5 * risk, entry - 2.0 * risk]
    timestamp = frame.index[-1]
    if getattr(timestamp, "tzinfo", None) is None:
        timestamp = timestamp.tz_localize("UTC")
    timestamp_utc = timestamp.tz_convert("UTC").to_pydatetime()
    max_age_hours = 36 if symbol in {"BTC-USD", "ETH-USD"} else 96
    age_hours = (datetime.now(timezone.utc) - timestamp_utc).total_seconds() / 3600
    if age_hours > max_age_hours:
        raise ValueError(f"Latest candle is stale ({age_hours:.1f} hours old).")
    score = int(
        40
        + 20 * (abs(float(row["EMA20"] - row["EMA50"])) / max(entry * 0.002, 1e-9) > 1)
        + 20 * (abs(hist) / max(atr * 0.05, 1e-9) > 1)
        + 20 * (45 <= rsi <= 60 if direction == "LONG" else 40 <= rsi <= 55)
    )
    return {
        "signal_id": f"{slugify(symbol)}-{timestamp_utc.strftime('%Y%m%d%H')}-{direction.lower()}",
        "slug": f"{slugify(symbol)}-{timestamp_utc.strftime('%Y%m%d%H')}-{direction.lower()}",
        "symbol": symbol, "label": label, "region": region,
        "language": "English" if region == "GLOBAL" else "Hinglish",
        "direction": direction, "entry": entry, "stop_loss": stop,
        "targets": targets, "tp1": targets[0], "tp2": targets[1], "tp3": targets[2],
        "rr_tp2": abs(targets[1] - entry) / abs(entry - stop),
        "rsi14": rsi, "ema20": float(row["EMA20"]), "ema50": float(row["EMA50"]),
        "macd": float(row["MACD"]), "macd_signal": float(row["MACD_SIGNAL"]),
        "macd_hist": hist, "atr14": atr,
        "vwap": float(row["VWAP"]) if np.isfinite(row["VWAP"]) else None,
        "support": float(row["SWING_LOW"]) if np.isfinite(row["SWING_LOW"]) else None,
        "resistance": float(row["SWING_HIGH"]) if np.isfinite(row["SWING_HIGH"]) else None,
        "as_of": timestamp_utc.isoformat(), "score": score,
        "disclaimer": "Educational market scenario only; not financial advice. Levels can fail.",
    }


def scout_symbol(symbol: str, label: str, region: str) -> dict[str, Any]:
    frame = compute_indicators(fetch_ohlc(symbol))
    signal = make_signal(symbol, label, region, frame)
    return {"frame": frame, "signal": signal}
