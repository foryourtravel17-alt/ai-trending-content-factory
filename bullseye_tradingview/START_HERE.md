# Bhai — Start Here

You do not need to become a coder. Learn just enough of the words below to know what the system is doing and when you must press a button.

## Six basic words
- **Chart:** a map of price over time.
- **Candle:** shows open, high, low and close for one time period.
- **Indicator:** a visual calculation on the chart. It cannot guarantee future price.
- **Pine Script:** TradingView's language for indicators and backtest strategies.
- **Backtest:** a simulation of rules on historical data; it is not proof of future profit.
- **Non-repaint:** a confirmed signal should not change later merely because an unfinished candle or unfinished higher-timeframe candle changed.

## The five pillars
1. **SCOPE:** previous completed H4 bar for forex/crypto, Daily for stocks. EMA 50 above EMA 200 = BULL; below = BEAR; FLAT = no setup.
2. **TARGET:** wait until price touches the blue band around EMA 21 ± 0.5 ATR.
3. **TRIGGER:** qualifying engulfing/pin candle intersects the band and closes outside it in the scope direction.
4. **SHIELD:** stop reference is 1.5 ATR beyond the band.
5. **BULLSEYE:** 50% reference exit at 1R, rest at 2R; original stop stays in place at 1R.

## Guardrails
Max two setups per India date; allowed session 12:00–20:00 IST; avoid high-impact news 15 minutes before/after; max planned risk 1% per setup. This build's news blackout is manual. Position sizing depends on the broker, symbol, contract size and account currency.

## What can be automated
GitHub can store files, run source tests, schedule existing workflows, and log errors. The existing Instagram/Telegram content workflows are separate from the trading indicator. Pine compilation and TradingView publication still need actions in your TradingView account.

## Your only manual steps — when I say the build is ready
1. Open https://www.tradingview.com/chart/ and choose a chart.
2. Paste the entire `Bullseye_Structure_Study.pine` file in Pine Editor, click Save, then Add to chart. If there is a compiler error, send the exact first error and line number.
3. Separately paste `Bullseye_Backtest_Strategy.pine`, add it to chart, open Strategy Tester, and set realistic symbol-specific costs.
4. Share the compiled chart plus Strategy Tester overview (hide private account info). We can fix issues and test again.
5. Only after tests and commercial rules are reviewed should you press the final public Publish button. No live trading or public publishing is enabled by this code.

## Why the publishing button needs you
Your account is the one that owns the TradingView profile. Code can be created and checked automatically, but I cannot claim a script has been published unless the account actually submits and confirms it.
