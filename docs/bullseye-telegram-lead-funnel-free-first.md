# Bullseye Theory: Free-First Reel-to-Telegram Lead Funnel

Status: draft strategy and copy only. Nothing in this document authorizes publishing, sending Telegram messages, changing credentials, enabling paid services, or deploying.

## Goal
Turn original educational short-form content into Telegram community joins and qualified enquiries for the ₹999 Bullseye Theory course. Lead with education, not income promises or signals.

## Funnel
1. Publish only after owner approval: one original educational Reel with a clear hook, 3–4 teaching beats, one takeaway, and readable risk disclaimer.
2. CTA: invite viewers to join the existing public Telegram channel @bullseye_theory for free educational notes and lesson previews.
3. Telegram pinned post: explain what members receive, state that content is educational and not financial advice, and offer a voluntary course-details request.
4. Course enquiry: record only information the user voluntarily sends. Do not collect PAN, Aadhaar, bank details, passwords, or wallet seed phrases.
5. Course offer: ₹999 only if price and course access are confirmed; explain exact inclusions and refund/access terms before payment. No fabricated testimonials, profit claims, scarcity, or guaranteed outcomes.
6. Measure weekly: Reel views, profile visits, Telegram joins, course-detail requests, and paid conversions. Never infer conversions from views.

## CTA copy (draft; approval required)
"Want the concept notes and more risk-aware trading education? Join the free Bullseye Theory Telegram community: @bullseye_theory. Educational content only—not financial advice. Trading involves risk."

## Pinned Telegram welcome copy (draft; approval required)
"Welcome to Bullseye Theory — Filter the Noise. Read the Structure. Hit the Bullseye.

Here you'll find beginner-friendly explanations of market structure, liquidity, indicators, risk management, and trading psychology. We don't promise profits or provide guaranteed signals. Charts are illustrative unless explicitly labelled with a source and timestamp.

Start with the free lesson/notes. If you'd like the ₹999 course syllabus and access details, message: COURSE DETAILS. Please don't send sensitive identity or banking information here.

Educational purposes only; not financial advice. Trading involves risk."

## Seven original Reel concepts
1. Liquidity: why thin liquidity can amplify price impact. Hook: "Price can move fast without a big order—here's why." Explain liquidity and slippage; don't frame liquidity pools as guaranteed targets.
2. EMA 20 vs EMA 50: faster vs slower response, lag, and sideways-market whipsaws. No buy/sell signal.
3. Market structure: distinguish swing highs/lows from a single candle; use an illustrative chart.
4. Support/resistance: zones, not exact magic lines; explain false breaks.
5. RSI: momentum context, not automatic overbought/oversold reversals.
6. Risk per trade: position size depends on stop distance and risk budget; include a simple hypothetical example clearly labelled educational.
7. Trading psychology: predefine invalidation and avoid revenge trading; no outcome promises.

## Script and storyboard quality gate
- First 1–2 seconds: specific curiosity hook, no misleading guarantee.
- One concept per Reel; spoken script is original, not copied from a reference.
- 4–7 visual beats; phone-readable overlays, short sentences, high contrast, captions.
- Illustrative charts only unless sourced live data is deliberately verified and timestamped.
- End with one CTA, not a pile of hashtags.
- Keep "Educational only. Not financial advice. Illustrative chart—not a live signal. Trading involves risk." legible.
- Check rendered MP4, audio, spelling, scene order, duration, and disclaimer before approval.
- Never publish automatically. Keep Instagram/Telegram posting behind owner approval.

## Free-first production stack
- Existing Python/Pillow + FFmpeg renderer and GitHub Actions for deterministic rendering.
- Repository-local TTS fallback (eSpeak NG where available); verify pronunciation and audio quality.
- Use original vector/illustrative chart scenes before external generative video tools.
- Prefer free tiers only; check quotas and license/usage restrictions before use. No paid APIs, subscriptions, or usage-based credits without separate explicit approval.
- Reference research should record source URL, date checked, observed hook/pacing/visual format, and the original adaptation. Do not download/repost another creator's video or copy scripts verbatim.

## Telegram bot safety checklist
- Confirm the bot's configured chat/channel is the intended Bullseye destination without printing token values.
- Test a harmless draft/approval message first.
- Verify APPROVE and REJECT callback handlers update the queue/state correctly.
- Verify approval does not itself publish to Instagram unless a separate explicit approval and configured workflow require it.
- Never expose bot tokens in logs, screenshots, source files, or messages.

## Lead tracking fields
Date; content ID; topic; Reel URL (after approved publication); Telegram joins (aggregate); course-details requests; paid conversions (verified only); notes. Avoid storing unnecessary personal data.

## First draft script: Liquidity (about 25–30 seconds)
Hook: "Price can move fast without a huge order. Here's one reason."
Beat 1: "Liquidity describes how easily an asset can be bought or sold without moving its price too much."
Beat 2: "When available orders are thinner, even ordinary trades can have a larger price impact."
Beat 3: "That can increase slippage, especially around fast news or low-volume periods."
Takeaway: "Liquidity is market context—not a magic signal that predicts the next move."
CTA: "Join Bullseye Theory on Telegram for free, risk-aware trading education."
Disclaimer: "Educational only. Not financial advice. Illustrative chart—not a live signal. Trading involves risk."

## First draft script: EMA 20 vs EMA 50 (about 25–30 seconds)
Hook: "Why can two moving averages disagree?"
Beat 1: "An EMA gives more weight to recent prices, but it still reacts after price has moved."
Beat 2: "A 20-period EMA usually responds faster than a 50-period EMA."
Beat 3: "In a sideways market, they can cross repeatedly and create misleading impressions."
Takeaway: "A crossover is context, not a guaranteed entry. Study structure and risk."
CTA and disclaimer as above.

## Release checklist
- [ ] Generated MP4 exists and is downloadable.
- [ ] Human inspected video/audio on a phone.
- [ ] Hook, scene copy, chart labels, and disclaimer are readable.
- [ ] No unverified current price, trade signal, return claim, or copied material.
- [ ] Owner explicitly approved the exact final asset and destination.
- [ ] Telegram bot callback behavior was verified.
- [ ] Lead tracking does not expose secrets or collect sensitive personal data.
