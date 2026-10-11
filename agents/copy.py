"""Generate language-specific Telegram HTML and Instagram captions."""
from html import escape

def build_copy(signal: dict, analyst: dict) -> dict:
    is_global = signal.get("region") == "GLOBAL"
    if is_global:
        body = (
            f"I’m watching {signal['label']} through structure, momentum, and defined risk. "
            f"EMA20 is {'above' if signal['ema20'] > signal['ema50'] else 'below'} EMA50; "
            f"RSI(14) is {signal['rsi14']:.1f}. The setup can fail, and a risk/reward ratio is not a win probability."
        )
        hook = analyst.get("hook") or "Structure first. Risk always."
        tags = "#TradingEducation #TechnicalAnalysis #RiskManagement #BullseyeTheory"
    else:
        body = (
            f"Main {signal['label']} ko structure, momentum aur defined risk ke saath dekh raha hoon. "
            f"EMA20 {'EMA50 ke upar' if signal['ema20'] > signal['ema50'] else 'EMA50 ke neeche'} hai; "
            f"RSI(14) {signal['rsi14']:.1f} hai. Setup fail ho sakta hai — R:R win ki guarantee nahi."
        )
        hook = analyst.get("hook") or "Pehle structure, phir risk — no blind entries."
        tags = "#TradingEducation #Nifty #PriceAction #RiskManagement #BullseyeTheory"
    hook = str(hook).strip()[:100]
    view = str(analyst.get("view", "")).strip()[:260]
    caveat = str(analyst.get("caveat", "")).strip()[:130]
    caption = (
        f"{hook}\n\n{view}\n\n"
        f"Scenario: {signal['symbol']} · {signal['direction']}\n"
        f"RSI(14): {signal['rsi14']:.1f} | EMA20/50 structure\n\n"
        f"{caveat}\n"
        "Educational market commentary only. Not financial advice."
    )
    instagram = f"{caption}\n\n{tags}"
    telegram_html = (
        f"<b>🎯 Bullseye Theory · {escape(signal['label'])}</b>\n\n"
        f"<b>{escape(hook)}</b>\n\n{escape(view)}\n\n"
        f"<b>Scenario:</b> {escape(signal['symbol'])} · {signal['direction']}\n"
        f"<b>RSI(14):</b> {signal['rsi14']:.1f} · EMA20/50 structure aligned\n\n"
        f"{escape(caveat)}\n\n"
        "<i>Educational scenario only. Not financial advice; levels can fail.</i>"
    )
    return {"telegram_html": telegram_html[:1000], "instagram_caption": instagram[:2200],
            "hook": hook, "hashtags": tags.split()}
