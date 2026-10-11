"""Generate language-specific Telegram HTML and Instagram captions."""
from html import escape

def build_copy(signal: dict, analyst: dict) -> dict:
    is_global = signal.get("region") == "GLOBAL"
    if is_global:
        body = (
            f"I’m tracking {signal['label']} with a {signal['direction'].lower()} scenario. "
            f"Entry reference: {signal['entry']:.4f}; invalidation: {signal['stop_loss']:.4f}. "
            f"TP2 gives about {signal['rr_tp2']:.1f}R if reached, but a ratio is not a win probability."
        )
        hook = analyst.get("hook") or "Structure first. Risk always."
        tags = "#TradingEducation #TechnicalAnalysis #RiskManagement #BullseyeTheory"
    else:
        body = (
            f"Main {signal['label']} par {signal['direction'].lower()} scenario track kar raha hoon. "
            f"Entry reference {signal['entry']:.4f}, invalidation {signal['stop_loss']:.4f}. "
            f"TP2 tak planned R:R lagbhag {signal['rr_tp2']:.1f}R hai — target hit hone ki guarantee nahi."
        )
        hook = analyst.get("hook") or "Pehle structure, phir risk — no blind entries."
        tags = "#TradingEducation #Nifty #PriceAction #RiskManagement #BullseyeTheory"
    caption = (
        f"{hook}\n\n{analyst.get('view', '')}\n\n"
        f"Scenario: {signal['symbol']} · {signal['direction']}\n"
        f"RSI(14): {signal['rsi14']:.1f} | EMA20/50 structure aligned\n\n"
        f"{analyst.get('caveat', '')}\n"
        "Educational market commentary only. Not financial advice."
    )
    instagram = f"{caption}\n\n{tags}"
    telegram_html = (
        f"<b>🎯 Bullseye Theory · {escape(signal['label'])}</b>\n\n"
        f"<b>{escape(hook)}</b>\n\n{escape(analyst.get('view', ''))}\n\n"
        f"<b>Scenario:</b> {escape(signal['symbol'])} · {signal['direction']}\n"
        f"<b>Entry ref:</b> {signal['entry']:.4f}\n"
        f"<b>SL / invalidation:</b> {signal['stop_loss']:.4f}\n"
        f"<b>TP1 / TP2 / TP3:</b> {signal['tp1']:.4f} / {signal['tp2']:.4f} / {signal['tp3']:.4f}\n"
        f"<b>RSI(14):</b> {signal['rsi14']:.1f} · <b>Planned R:R to TP2:</b> {signal['rr_tp2']:.1f}R\n\n"
        f"{escape(analyst.get('caveat', ''))}\n\n"
        "<i>Educational scenario only. Not financial advice; levels can fail.</i>"
    )
    return {"telegram_html": telegram_html, "instagram_caption": instagram[:2200],
            "hook": hook, "hashtags": tags.split()}
