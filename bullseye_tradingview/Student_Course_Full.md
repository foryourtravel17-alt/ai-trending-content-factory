# Bullseye Theory — Student Course (Draft v0.2)

**Positioning:** Learn | Trade | Grow  
**Level:** Beginner to intermediate  
**Format:** Written lessons + recorded lessons to be produced separately + chart exercises  
**Important:** This is educational material, not a trade signal, personalized investment advice, or a promise of profit. The indicator is a rule-based study prototype and must be compiled and tested before distribution.

## Lesson 1 — Learn to Read a Chart

### Goal
Understand what a chart actually records before adding indicators.

A chart shows how an instrument's quoted price changed over time. Every candle represents one time interval. The candle's **open** is the first recorded price in that interval; **high** is the highest; **low** is the lowest; **close** is the last recorded price. A green candle commonly means its close is above its open; red commonly means the opposite, although colors can be changed.

The chart timeframe controls the length of one candle. An H1 candle covers one hour, H4 covers four hours, and Daily covers one trading day. A candle's color does not predict what the next candle must do. Gaps, spread, session hours and differences between data feeds can change how a chart looks.

Bullseye uses two views: a higher-timeframe view for broad direction and a chart-timeframe view for a pullback and trigger. The higher timeframe is context, not certainty.

### Example
Imagine a fictional EUR/USD H1 candle opens at 1.1000, reaches 1.1020, drops to 1.0990 and closes at 1.1010. The body spans 1.1000–1.1010 and the wicks show prices outside the body. This single candle alone cannot tell you whether the market will rise next.

### Practice
Pick one liquid instrument on a historical chart. Write down its name, data feed, timeframe and five consecutive candles' OHLC values. Do not place an order.

### Check yourself
1. What does a candle's close represent? **Answer:** The last recorded price for that candle's interval.
2. Does a bullish candle guarantee that the next candle rises? **Answer:** No.
3. Why record the data feed? **Answer:** Feeds can have different quotes and candle shapes.

## Lesson 2 — Market Structure and Neutral Conditions

### Goal
Describe direction without forcing every chart into “bullish” or “bearish.”

An uptrend is often described by a sequence of higher highs and higher lows. A downtrend often has lower highs and lower lows. A range has price moving between areas without a clear sequence. Real charts can be messy: one swing may not confirm a trend, and structure can transition from trending to ranging.

Bullseye has a deliberate third state: **FLAT**. If the Scope test does not show a clear direction, the system should not invent one. Skipping an unclear situation is part of a defined process, not a missed opportunity.

A structure label should be based on a repeatable definition. Do not move swing points after seeing what happens next simply to make the chart appear correct.

### Example
A chart makes two higher highs, then breaks down and falls below the last higher low. That should prompt a fresh analysis; it is not proof that a new downtrend is fully established. Wait for the next confirmed sequence.

### Practice
On a historical chart, label ten swing highs/lows. Mark the sections you would call uptrend, downtrend and range. Ask another person to repeat the task with the same rules and compare disagreements.

### Check yourself
1. What is a valid outcome when direction is unclear? **Answer:** FLAT / no setup.
2. Why should you avoid relabeling past swings to fit a story? **Answer:** It introduces hindsight bias.
3. Is a range a failure of the process? **Answer:** No; it is a market condition.

## Lesson 3 — SCOPE: Direction Before a Setup

### Goal
Apply the first Bullseye pillar consistently.

For FX and crypto, the prototype defaults to the **previous completed H4 candle**. For stocks, choose Daily (1D). The indicator compares EMA 50 and EMA 200 calculated on that higher timeframe. EMA 50 above EMA 200 is labeled BULL; EMA 50 below EMA 200 is labeled BEAR; equal or unresolved values produce FLAT.

An exponential moving average (EMA) smooths recent prices, giving more weight to newer prices. It is still based on past data and can lag or whipsaw in a range. It describes a condition; it does not forecast with certainty.

Bullseye uses the last completed higher-timeframe candle instead of relying on an unfinished H4/Daily candle. That choice reduces a common source of repainting, although it does not make every possible script/data behavior immune to change.

### Example
Suppose H4 EMA 50 is above H4 EMA 200. The Scope is BULL for this rule set. A bearish candle pattern is not a reason to reverse the Scope; it may simply be ignored by this system.

### Practice
Record five historical H1 chart dates with H4 Scope: BULL, BEAR or FLAT. Write the actual EMA condition beside each label.

### Check yourself
1. Which EMAs define Scope? **Answer:** EMA 50 and EMA 200 on the selected higher timeframe.
2. What do you do with FLAT? **Answer:** No setup.
3. Does BULL Scope guarantee rising prices? **Answer:** No; moving averages lag and conditions change.

## Lesson 4 — Trend Filters Can Fail

### Goal
Recognize the limitations of a simple direction filter.

A moving-average relationship can remain bullish while price falls, because averages respond to past movement. During a range, averages can repeatedly cross or switch order. A filter can reduce some countertrend setups while still allowing losing setups.

Different instruments have different liquidity, trading hours, spreads and contract specifications. A condition that looks clean on one feed may look different on another. Backtest settings and chart screenshots must therefore identify the symbol, feed, timeframe and sample dates.

Do not “fix” every loss by adding another indicator. Extra filters can overfit a historical sample—making the rules look good on past data but less useful later.

### Example
During a sideways month, EMA 50 and EMA 200 may stay close together. Several small moves can make the filter switch back and forth. Bullseye's FLAT state means there is no valid setup until the defined Scope rule gives a direction again.

### Practice
Find three historical situations where an EMA filter lagged a reversal or whipsawed in a range. Record how the rule behaves; do not edit the rule during the same test.

### Check yourself
1. Why can moving averages lag? **Answer:** They summarize historical prices.
2. What is overfitting? **Answer:** Tuning rules to past data in a way that does not generalize.
3. Should each loss immediately trigger a rule change? **Answer:** No; test changes separately on new data.

## Lesson 5 — TARGET: Wait for the Pullback Zone

### Goal
Learn the second Bullseye pillar: define the area where price must return.

The prototype uses the chart-timeframe EMA 21 and ATR(14). It draws a blue band from EMA 21 − 0.5 × ATR(14) to EMA 21 + 0.5 × ATR(14). ATR is an average true-range measure used to describe recent movement; it does not identify direction.

The band expands when measured volatility rises and contracts when it falls. It is a zone, not a magical support/resistance level. Bullseye looks for price to revisit the zone instead of chasing a price that has already moved far away.

### Example
If EMA 21 is 1.1000 and ATR is 0.0020, half the ATR is 0.0010. The illustrative zone is 1.0990–1.1010. These are made-up numbers to explain the calculation, not a live quote or a trade instruction.

### Practice
Calculate a hypothetical zone with EMA 21 = 100 and ATR = 4. Record the upper and lower edges. Then find historical chart examples of a zone touch followed by continuation and a touch followed by failure.

### Check yourself
1. What creates the band? **Answer:** EMA 21 plus/minus 0.5 ATR(14).
2. Does touching the band alone trigger a setup? **Answer:** No; Scope and Trigger are also required.
3. Why not chase price far from the band? **Answer:** It would violate the predefined location rule.

## Lesson 6 — Candle Trigger Basics

### Goal
Identify the two candle-pattern types used by the prototype.

An engulfing candle has a body that covers the prior candle's body in the opposite direction, according to the script's specific comparisons. The prototype requires the current candle's body to be at least 55% of the candle's high–low range. These exact definitions matter: people sometimes use the term “engulfing” for slightly different patterns.

A pin/rejection candle has a dominant wick relative to its body and closes in the direction of the rejection. The prototype uses a configurable wick/body ratio. The code's specific rules define what qualifies; do not change visual interpretation halfway through a test.

Candle patterns are descriptions of past price action. They do not reveal the future, guarantee large orders, or prove that a level will hold.

### Example
A candle pokes below a zone and closes strongly higher. That may look like rejection, but Bullseye's exact bullish trigger also requires the correct Scope, a zone intersection and a close beyond the far edge. The pattern in isolation is insufficient.

### Practice
Collect five historical engulfing-looking candles and five rejection-looking candles. Apply the code's exact body/wick definitions, including examples that fail the threshold.

### Check yourself
1. What is the minimum engulfing body percentage? **Answer:** 55% of that candle's full high–low range.
2. Does any pin bar qualify? **Answer:** No; it must meet the configured wick/body and other trigger tests.
3. Why use fixed definitions? **Answer:** To reduce subjective chart selection and hindsight.

## Lesson 7 — TRIGGER: Confirmation, Not Prediction

### Goal
Combine Scope, Target and Trigger into one defined condition.

A bullish candidate requires BULL Scope, a candle that intersects the pullback zone, a qualifying bullish engulfing or rejection pattern, and a **confirmed candle close above the upper edge of the zone**. A bearish candidate mirrors those conditions in BEAR Scope and closes below the lower edge of the zone. The script waits for a confirmed chart candle rather than acting on a candle that is still forming.

A valid rule can still lose. A later candle may reverse, a stop may be hit, and a chart pattern may fail. Bullseye labels a rule condition—not a guaranteed entry or a prediction.

### Example
Price is in a bullish Scope and returns to the blue band. If a green-looking candle closes inside the band, the defined bullish Trigger has not completed. If the candle forms the required pattern and closes above the upper band edge, the chart may show a candidate—provided Guardrails also pass.

### Practice
Use at least twenty historical zone interactions. For each, record: Scope, zone touch, pattern test, closing position, Guardrails and final candidate yes/no. Include every case rather than selecting only attractive examples.

### Check yourself
1. Why wait for candle close? **Answer:** A live candle can change before it is confirmed.
2. Can a Trigger override FLAT Scope? **Answer:** No.
3. Is a chart label an order? **Answer:** No; the indicator does not submit orders.

## Lesson 8 — SHIELD: Risk Boundary and Position Size

### Goal
Understand planned risk before thinking about reward.

Bullseye's stop reference is 1.5 × ATR(14) beyond the pullback-zone edge: below the lower edge for a bullish candidate and above the upper edge for a bearish candidate. This provides a reproducible reference distance for historical study. It is not a broker stop order, and the indicator does not know the actual account balance, spread, margin or contract specifications.

The proposed rulebook caps planned risk at 1% of account equity per setup. To convert that into quantity, a trader needs the actual entry-to-stop distance, tick/pip value, contract multiplier, account currency and costs. Those values vary by instrument and broker, especially across stocks, FX, futures and crypto. The backtest quantity is a research approximation—not a lot size you should copy into a live account.

Stops can slip or gap; the loss can exceed the planned amount. Never interpret “1% planned risk” as a loss guarantee.

### Example
On a hypothetical account of ₹10,000, 1% corresponds to ₹100 of planned risk. That simple arithmetic is not enough to choose a lot size: you still need the exact instrument's point/pip value and broker rules. Do not enter a real trade based on this example.

### Practice
Take one historical candidate and list all sizing inputs required by your chosen broker. If one is unknown, mark the calculation incomplete instead of guessing.

### Check yourself
1. What is the stop reference rule? **Answer:** 1.5 ATR beyond the relevant zone edge.
2. Does 1% risk guarantee a maximum loss of exactly 1%? **Answer:** No; gaps, slippage and costs can make losses larger.
3. Can you reuse FX quantity on a stock or crypto contract? **Answer:** No, not without verifying contract rules.

## Lesson 9 — BULLSEYE: 1R Partial and 2R Target

### Goal
Understand the planned exit framework without treating R as a profit promise.

R is a unit defined by the initial entry-to-stop reference distance. If the distance is ₹2 per unit, a 1R move is ₹2 in the favorable direction and a 2R move is ₹4, before costs. Bullseye's first version references a 50% partial exit at 1R and the remaining 50% at 2R. The original stop remains in place at 1R; this rule set does not automatically move it to break-even.

A 2R target does not say how often the setup wins. Performance depends on the full sample, win rate, losses, spread, commissions, slippage and execution model. Backtests can also misrepresent order fills around gaps or when both stop and target sit inside the same candle.

### Example
Suppose the hypothetical entry-to-stop distance is 5 points. 1R = 5 points, 2R = 10 points. The planned exit reference is half the position at +5 points and the remainder at +10 points. This arithmetic says nothing about whether price will reach either level.

### Practice
Calculate 1R and 2R for ten made-up stop distances. Then explain what happens if the original stop is hit before 1R.

### Check yourself
1. What does R represent? **Answer:** The initial risk distance for that setup.
2. What is the planned partial? **Answer:** 50% at 1R.
3. Does a 2R plan prove positive expectancy? **Answer:** No; the results must be tested across a meaningful sample and include costs.

## Lesson 10 — Backtesting Without Self-Deception

### Goal
Use historical tests to find flaws, not to promise profits.

The Strategy Tester simulates a rule on historical chart data according to its fill model and settings. Results may change with symbol/feed, date range, timeframe, commission, spread, slippage and contract-size settings. An overly perfect backtest may indicate that the sample is too narrow, the rules were tuned to the data, costs were omitted, or an assumption cannot happen in a real account.

Freeze the rules before testing. Record all qualifying setups, including losses, sideways periods and boring periods. Split data into a development period and a later out-of-sample period that was not used to tune the script. Forward observation on a paper/demo process can find errors, but it still does not guarantee future results.

Important measures include trade count, net expectancy after costs, profit factor, maximum drawdown, average win/loss, time in market and the date range. A large percentage return with too few trades or unrealistic costs is not strong proof.

### Practice
Create a test log with: symbol/feed, timeframe, start/end dates, rule version, costs, trade count, wins, losses, net result, max drawdown and known limitations. Keep the first rule version frozen.

### Check yourself
1. What is out-of-sample testing? **Answer:** Testing on a period not used to design/tune the rules.
2. Why include costs? **Answer:** Real trades incur spread, commission and slippage.
3. Can a historical test guarantee future results? **Answer:** No.

## Lesson 11 — Discipline, News and the Journal

### Goal
Use the routine consistently and know when not to act.

The current Bullseye guardrails define a maximum of two setups per India calendar day and an allowed session from 12:00 to 20:00 Asia/Kolkata. The current prototype's high-impact news blackout is **manual**: it does not fetch or verify a live economic calendar. The rule calls for avoiding the 15 minutes before and after the relevant high-impact event. Calendar event times can be revised; confirm the time and time zone on a trustworthy source.

A journal should record the process, not just the result: date, symbol/feed, timeframe, five pillars, screenshot, entry/stop/target references, costs, outcome, rule adherence and notes. A winning result from a rule violation is still a process error; a losing result from correct execution is still worth reviewing.

Never revenge trade, increase size to recover losses or market a historical screenshot as a live signal. Waiting and recording “no setup” are valid outcomes.

### Practice
Fill out five sample journal rows. One row must be FLAT/no setup. One row must show a setup blocked by news or the daily cap.

### Check yourself
1. What is the daily cap? **Answer:** Two setups in the current rule set.
2. Is the news filter automated? **Answer:** No; a manual toggle is used.
3. What is the goal of a journal? **Answer:** Review consistency, errors, risk and evidence—not predict the next price move.

---

## Final learner checklist
- I can identify chart timeframe, OHLC and spread.
- I can label Scope as BULL, BEAR or FLAT with the defined EMA rule.
- I can calculate the pullback zone from EMA 21 and ATR(14).
- I can apply the exact candle-pattern and close conditions.
- I can explain the stop reference, 1R partial and 2R target.
- I can name the two-setup cap, India session window and manual news toggle.
- I understand that a chart marker is not an order, and a backtest is not a guarantee.
- I do not trade a live account based on this prototype.

**Required disclaimer:** Educational purposes only. Not a buy/sell recommendation or personalized investment advice. Bullseye Theory does not promise profits. Trading involves risk; past behaviour does not guarantee future results.
