# Bullseye Theory Rulebook — Original Five-Pillar Rules v0.2

This is the initial research hypothesis, not a proven profitable strategy or personalized recommendation. Change rules only in a new version and test changes separately.

## SCOPE — direction first
- Forex/crypto: use the previous completed H4 candle by default. Stocks: select Daily (1D).
- EMA 50 above EMA 200 = BULL; EMA 50 below EMA 200 = BEAR; equal/unresolved = FLAT.
- No setup against the scope. The higher-timeframe values use a completed candle.

## TARGET — pullback zone
- Chart-timeframe EMA 21.
- Blue zone = EMA 21 plus/minus 0.5 × ATR(14).
- Price must touch the zone. Do not chase if it never revisits.

## TRIGGER — confirmed candle
- The candle intersects the zone and closes beyond the far edge in the scope direction.
- Accept either an engulfing candle with body >= 55% of high-low range, or a pin/rejection candle using the configured wick/body ratio.
- Only confirmed/closed chart candles qualify.

## SHIELD — risk boundary
- ATR length 14.
- Long reference stop = lower edge of the zone − 1.5 × ATR.
- Short reference stop = upper edge of the zone + 1.5 × ATR.
- The indicator shows reference levels only; it never places orders or knows a user's broker account.

## BULLSEYE — planned outcome
- Initial final target = 2R (twice the entry-to-stop distance).
- Reference 50% partial exit at 1R.
- Keep the original stop at 1R; do not automatically move it to breakeven.
- Spread, commission, slippage, gaps, contract size and account currency can change results.

## GUARDRAILS
- Maximum two setups/entries per India calendar day.
- Allowed window: 12:00–20:00 Asia/Kolkata.
- Avoid high-impact news from 15 minutes before through 15 minutes after. The current prototype has a **manual** blackout toggle; it has no live economic-calendar integration.
- Maximum planned risk: 1% of equity per setup. Position sizing depends on instrument/broker contract multiplier and account currency; verify it rather than copying backtest quantity into live trading.
- No setup when scope is FLAT, data is missing, or guardrails fail.

## Testing plan
1. Start with one liquid major FX pair, one data feed, H1 chart, H4 scope.
2. Compile indicator and strategy separately in TradingView Pine Editor.
3. Review historical candles including losing and sideways periods.
4. Set realistic costs and symbol-specific contract sizing in Strategy Tester.
5. Record sample period, trade count, expectancy, profit factor, max drawdown, costs and limitations.
6. Test an untouched out-of-sample period and then forward-observe without changing the rules.
7. Publish no performance claims until the evidence is reproducible.

Required disclaimer: Educational purposes only. Not a buy/sell recommendation. Not SEBI-registered investment advice. Past behaviour does not guarantee future results.
