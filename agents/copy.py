"""Generate Telegram-only market scenario captions."""
from html import escape


def build_copy(signal: dict, analyst: dict) -> dict:
    symbol = signal.get("symbol", "")
    is_global = signal.get("region") == "GLOBAL"
    ema_relation = "above" if signal["ema20"] > signal["ema50"] else "below"
    if is_global:
        body = (
            f"{signal['label']}: EMA20 is {ema_relation} EMA50 and RSI(14) is {signal['rsi14']:.1f}. "
            "This is a rule-based scenario, not a prediction."
        )
        hook = "Structure first. Risk always."
        if symbol == "GC=F":
            tags = "#GoldTrading #TechnicalAnalysis #RiskManagement #BullseyeTheory"
        elif symbol == "BTC-USD":
            tags = "#Bitcoin #CryptoTrading #TechnicalAnalysis #BullseyeTheory"
        elif symbol == "ETH-USD":
            tags = "#Ethereum #CryptoTrading #TechnicalAnalysis #BullseyeTheory"
        elif symbol == "EURUSD=X":
            tags = "#ForexTrading #EURUSD #TechnicalAnalysis #BullseyeTheory"
        elif symbol == "^NDX":
            tags = "#Nasdaq #USMarkets #TechnicalAnalysis #BullseyeTheory"
        else:
            tags = "#SPY #USMarkets #TechnicalAnalysis #BullseyeTheory"
    else:
        relation_hi = "EMA50 ke upar" if signal["ema20"] > signal["ema50"] else "EMA50 ke neeche"
        body = (
            f"{signal['label']}: EMA20 {relation_hi} hai aur RSI(14) {signal['rsi14']:.1f} hai. "
            "Ye rule-based scenario hai, prediction nahi."
        )
        hook = "Structure first. Risk always."
        if symbol == "^NSEI":
            tags = "#Nifty #IndianMarkets #PriceAction #RiskManagement #BullseyeTheory"
        elif symbol == "^NSEBANK":
            tags = "#BankNifty #IndianMarkets #PriceAction #RiskManagement #BullseyeTheory"
        else:
            tags = "#IndianStocks #PriceAction #RiskManagement #BullseyeTheory"
    view = str(analyst.get("view", "")).strip()[:260]
    caveat = str(analyst.get("caveat", "")).strip()[:130]
    telegram_html = (
        f"<b>🎯 Bullseye Theory · {escape(signal['label'])}</b>\n\n"
        f"<b>{escape(hook)}</b>\n\n{escape(view)}\n\n{escape(body)}\n\n"
        f"<b>Scenario:</b> {escape(signal['symbol'])} · {signal['direction']}\n\n"
        f"{escape(caveat)}\n\n"
        f"{escape(tags)}\n\n"
        "<i>Educational scenario only. Not financial advice; levels can fail.</i>"
    )
    return {"telegram_html": telegram_html[:1000], "hook": hook, "hashtags": tags.split()}
