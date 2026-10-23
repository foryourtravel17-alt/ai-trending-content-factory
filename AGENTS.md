# Bullseye Theory — AI Project Source of Truth

## Brand
- Brand: Bullseye Theory
- Positioning: serious trading education; never present the product as easy money, guaranteed profits, signal selling, or personalized financial advice.
- Voice: professional, institutional, confident, educational, disciplined.
- Primary language: English.
- Core philosophy: "LEARN | TRADE | GROW"

## Visual system
- Background: Dark Obsidian Navy.
- Signal accent: Neon Lime only for genuine signal / emphasis states.
- Accent: Metallic Gold.
- Text: Off-white.
- Visual direction: terminal HUD, optical focal brackets, structural drafting / modular grid, premium institutional trading environment.
- Avoid bull/bear/rocket clichés.
- Charts used for educational illustration must be clearly non-live and not presented as trade signals.

## Content safety
- Educational content only.
- No guaranteed outcomes.
- No personalized buy/sell/entry/exit instructions.
- No claims of certain profits or certainty about market direction.
- Include a clear educational disclaimer in published content.

## Current automation architecture
1. Daily topic generation.
2. Educational script + automated safety/format gate.
3. Render exactly one Reel for each scheduled slot.
4. Upload the exact MP4 to Supabase and verify its URL, hash, size, and duration.
5. Publish eligible educational content to Instagram and mirror it to the Telegram channel after the automated policy gate.
6. Persist platform IDs and status for duplicate-safe retries.

## Automation invariants
- Never regenerate an already-generated approved Reel.
- Never publish content that failed automated safety, freshness, media-integrity, duplicate, or technical eligibility checks.
- Never hard-code secrets or tokens.
- Prefer idempotent steps and explicit state flags.
- A no-op workflow should finish successfully rather than fail.
- New scheduled educational Reels and market scenarios use an explicit automated-policy gate; legacy callback handling remains only for older pending records.

## Current known infrastructure
- GitHub repository is the source of truth for the content factory.
- Replit hosts the separate D3 project.
- Supabase REELS bucket provides public media URLs for Instagram/Telegram delivery.


## Autonomous market-content extension

- New market-analysis code lives in `agents/` and `src/orchestrator.py`; it is additive and must not replace the legacy Reel pipeline.
- The market workflow uses Python 3.11, yfinance OHLC, transparent EMA/RSI/MACD/ATR rules, image cards, and `data/state.json` for deduplication.
- Market cards are educational scenarios, not personalized trade advice. Never imply a guaranteed result or count targets as hits without an explicitly recorded outcome.
- `HUMAN_APPROVAL=false` is the default for the market workflow so eligible market cards publish automatically after QA, freshness checks, public-image verification, and deduplication.
- Daily educational Reels use an automated safety/format policy rather than Telegram approval. The recorded `automated_passed` state means automated screening passed; it is not independent fact verification. Keep topics curated and evergreen, avoid live-market claims/personalized advice, and retain freshness, media integrity, daily-cap, duplicate, and ambiguous-outcome guards.
- Commit generated images before publishing so public image URLs can be fetched by Instagram. Prefer GitHub Pages; verify reachability and use the public raw-GitHub URL as a fallback.
- Run the market pipeline's synthetic dry-run tests and never use live publishing credentials in a test job.


- The failure watchdog covers the market-content, approval, test, weekly-report, and schedule-watchdog workflows. The weekday schedule watchdog checks for a recent successful market-content run and sends a Telegram alert only when it detects a stall.
- Missing Telegram or Instagram credentials must fail publishing loudly; do not report success when both channels were skipped.
- Stale OHLC candles are rejected before publishing: 20 hours for non-crypto instruments and 36 hours for crypto.
