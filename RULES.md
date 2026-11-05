# Bullseye Levels — deterministic rule specification

Version: 1.0.0  
Status: implementation contract  
Purpose: educational supply/demand zones and confirmed breakout scenarios. This is not an execution system or investment advice.

## 1. Supported market data

- Only the exact chart intervals **15m** and **1h** are supported. All other intervals must return an unsupported-timeframe/no-trade state and must not emit a signal.
- Candles are chronological, oldest first, and contain finite `high`, `low`, `close`, and `volume` values. Each candle represents a completed exchange interval.
- ATR is Wilder's ATR(14), calculated from true range. Volume SMA is the simple moving average of the current and preceding 19 completed candle volumes. A missing indicator value prevents a signal.
- All comparisons and calculations use IEEE-754 numbers without display rounding. Round only when formatting labels/messages.

## 2. Confirmed swing pivots

For a candidate candle at index `i`, with left strength `L=3` and right strength `R=3`:

- A swing high exists only when its high is **strictly greater** than the high of every candle in `[i-L, i-1]` and `[i+1, i+R]`.
- A swing low exists only when its low is **strictly less** than the low of every candle in those ranges.
- Candidates without all L left candles and R right candles are ignored.
- The pivot becomes known only after candle `i+R` closes. Its source price and source index remain those of candle `i`; no earlier bar may use it.
- Equal highs/lows do not form pivots. A candle may independently qualify as a high and a low only if both strict conditions hold.

## 3. ATR-scaled zone clustering

- Cluster supply (swing-high) pivots separately from demand (swing-low) pivots; never mix the two types.
- Each pivot uses the ATR(14) value at its source candle. A pivot with missing, non-finite, or non-positive ATR is excluded from clustering.
- Process pivots in ascending source-index order. The first unassigned pivot seeds a cluster. A later unassigned pivot joins that cluster when its absolute price distance from the seed price is less than or equal to `k × min(seed ATR, candidate ATR)`, where `k=0.25`. Membership is measured against the fixed seed, not a moving average; this prevents transitive chain-merging.
- A pivot joins at most one cluster. If it qualifies for multiple existing seeds, it joins the qualifying cluster with the smallest absolute distance; ties go to the earlier seed.
- Zone bottom is the minimum member pivot price; zone top is the maximum member pivot price. The zone centre is the arithmetic mean of member pivot prices.
- A cluster is a valid zone only with at least **2 distinct pivot touches**. Clusters with fewer touches are discarded.
- Zone ID is deterministic: `<type>-<seed pivot source index>`. Strength score is the integer touch count; it is descriptive, not a probability.

## 4. Breakout qualification

Evaluate only a completed candle, only on 15m or 1h, and only against a valid zone:

- LONG: `close > zone.top + 0.10 × ATR(14)`.
- SHORT: `close < zone.bottom - 0.10 × ATR(14)`.
- In either direction, volume must be strictly greater than `SMA(volume, 20) × 1.5`.
- Equality at either price threshold or volume threshold is not a breakout.
- If both directions were somehow eligible due to malformed/inverted zone data, reject the zone; valid zones must satisfy `bottom <= top`.
- Missing/non-finite ATR or volume SMA, non-positive ATR, or invalid candle/zone values produce no signal.
- A candle may qualify against more than one zone; each zone is evaluated independently.

## 5. Entry, stop, target, and risk/reward

- Entry is the breakout candle close.
- LONG stop loss: `zone.bottom - 0.20 × ATR(14)`.
- SHORT stop loss: `zone.top + 0.20 × ATR(14)`.
- Risk is the absolute distance between entry and stop. Non-positive or non-finite risk rejects the signal.
- LONG target: `entry + 2 × risk`.
- SHORT target: `entry - 2 × risk`.
- Reward/risk is exactly 2.0 before display formatting.

## 6. Per-zone cooldown

- A zone may emit at most one signal in any 12-bar interval.
- After a signal on bar `s`, signals for that same zone are suppressed for bars `s+1` through `s+11`; the zone may signal again on bar `s+12`.
- Cooldown is independent for each zone ID. A new zone ID has no prior cooldown.
- Only accepted/emitted signals update the last-signal bar for that zone.

## 7. Non-repainting and alert contract

- A pivot is unavailable until its three right-hand candles have closed.
- Breakout, volume, ATR, zone, and cooldown decisions use completed candles only.
- Web polling may display the last completed candle's result; an in-progress exchange candle must never generate or alter a signal.
- Pine must gate signal generation and `alert()` with `barstate.isconfirmed`; alerts use `alert.freq_once_per_bar_close`.
- A signal is immutable after its source candle closes. Later data may create new pivots/zones but must not retroactively create an earlier signal.
- When no valid, non-cooled-down setup exists, the API/UI state is explicitly `NO_TRADE`.

## 8. Cross-implementation parity

- This document is the single rule source for the Node.js and Pine implementations.
- Both implementations must use the same strict pivot comparisons, ATR-at-pivot clustering rule, seed-anchored clustering, zone boundaries, thresholds, strict volume test, stop/target equations, and cooldown boundary.
- Supported timeframe identifiers are `15m` and `1h`; API adapters must normalize exchange interval strings to these identifiers before evaluation.
- Tests use fixed candles and exact expected numeric outputs. Any intentional rule change requires updating this document and both implementations together.
