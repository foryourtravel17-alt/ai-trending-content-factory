"""Render dark candlestick charts with EMA overlays, RSI, and volume."""
from pathlib import Path

import mplfinance as mpf
import pandas as pd

def render_chart(frame: pd.DataFrame, signal: dict, output_dir: str = "output") -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{signal['slug']}.png"
    view = frame.tail(120).copy()
    colors = mpf.make_marketcolors(up="#B8FF5C", down="#FF647C", edge="inherit",
                                   wick="inherit", volume="inherit")
    style = mpf.make_mpf_style(
        base_mpf_style="nightclouds", marketcolors=colors,
        facecolor="#07111F", figcolor="#07111F", gridcolor="#263448",
        gridstyle="-", y_on_right=True,
        rc={"axes.labelcolor": "#EAF0F7", "xtick.color": "#B6C2D1",
            "ytick.color": "#B6C2D1", "text.color": "#EAF0F7"},
    )
    ap = [
        mpf.make_addplot(view["EMA20"], panel=0, color="#B8FF5C", width=1.1),
        mpf.make_addplot(view["EMA50"], panel=0, color="#D9B76E", width=1.1),
        mpf.make_addplot(view["RSI14"], panel=2, color="#69B7FF", width=1.0,
                         ylabel="RSI 14", ylim=(0, 100)),
    ]
    mpf.plot(
        view, type="candle", style=style, volume=True, addplot=ap,
        panel_ratios=(6, 2, 2), figsize=(14, 10), title=f"{signal['label']} ({signal['symbol']}) · {signal['direction']} scenario",
        ylabel="Price", datetime_format="%d %b %H:%M", xrotation=12,
        hlines={"hlines": [signal["entry"], signal["stop_loss"], signal["tp2"]],
                "colors": ["#69B7FF", "#FF647C", "#B8FF5C"], "linestyle": "--", "linewidths": 0.7},
        savefig={"fname": str(path), "dpi": 150, "bbox_inches": "tight", "facecolor": "#07111F"},
        warn_too_much_data=2000,
    )
    return path
