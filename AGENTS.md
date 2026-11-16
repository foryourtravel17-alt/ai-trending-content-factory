# Bullseye Theory — AI Project Source of Truth

## Brand and content safety
- Brand: Bullseye Theory.
- Positioning: serious trading education; never present the product as easy money, guaranteed profits, or personalized financial advice.
- Voice: professional, institutional, confident, educational, disciplined.
- Core philosophy: LEARN | TRADE | GROW.
- Educational content only. No guaranteed outcomes or certainty about market direction.
- Include clear educational disclaimers in published content.
- Do not present illustrative charts as live signals.

## Social automation policy — Telegram only
- Telegram is the only social publishing destination.
- Facebook and Instagram are disconnected. Do not call Meta Graph API, use Instagram/Facebook credentials, or create FB/IG publisher steps.
- Market cards and educational Reels always require a persisted owner APPROVE decision from the authorized private Telegram chat before public channel publishing.
- Automated safety/format checks are not owner approval.
- Rejected, stale, unapproved, or ambiguous Telegram deliveries must never be automatically republished.
- Market card images are uploaded directly to Telegram from the Actions runner.
- Educational Reel MP4s are durably stored in the existing Supabase `REELS` bucket, verified by SHA-256/size/duration, then sent to Telegram after approval.
- Never expose bot tokens, Supabase service-role keys, or other secrets in source files or logs.

## Current automation architecture
1. Generate weekday market scenarios and cards.
2. Render daily educational Reel drafts.
3. Run automated QA, freshness, duplicate, format, and media-integrity checks.
4. Send exact draft assets to the private Telegram approval chat.
5. Poll Telegram callbacks every five minutes.
6. Publish only the exact approved asset to `@bullseye_theory`.
7. Persist Telegram message IDs and state for duplicate-safe retries.
8. Send private Telegram weekly/daily reports and failure alerts.

## Automation invariants
- Never regenerate an already-generated approved Reel.
- Never publish failed safety, stale, unapproved, or mismatched media.
- Never publish an item whose approval is not authorized and persisted.
- Block automatic retry when Telegram's send result is ambiguous.
- Prefer idempotent steps and explicit state flags.
- A safe no-op workflow should finish successfully.
- Keep manual dispatches in dry-run by default.

## Infrastructure
- GitHub Actions is the workflow runner and source of truth.
- Supabase `REELS` is durable MP4 media storage only; it is not a social publishing destination.
- Telegram bot is the sole publishing integration.
- The project does not connect to a broker or execute trades.

## Market-content extension
- Market analysis code lives in `agents/` and `src/orchestrator.py`.
- Market workflow uses public OHLC data and transparent EMA/RSI/MACD/ATR rules.
- Stale candles are deliberately rejected: 20 hours for non-crypto instruments and 36 hours for crypto.
- A no-signal run is valid; do not fabricate market setups.
- Market cards are approved privately, then published to Telegram.

## Local workflow and verification
- Run `python -m unittest discover -s tests -v`.
- Validate YAML syntax for all `.github/workflows/*.yml`.
- Use only synthetic or mocked credentials in CI.
- Do not deploy or publish content as part of unit tests.
