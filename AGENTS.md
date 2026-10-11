# Bullseye Theory — AI Project Source of Truth

## Brand
- Brand: Bullseye Theory
- Positioning: serious trading education; never present the product as easy money, guaranteed profits, signal selling, or personalized financial advice.
- Voice: professional, institutional, confident, educational, disciplined.
- Primary language: English.
- Core philosophy: "TRADING IS NOT FOR THOSE WHO DON'T HAVE PATIENCE. LEARN | TRADE | EARN"

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
2. Educational script + safety check.
3. Telegram approval request with APPROVE / REJECT buttons.
4. Approved content generates exactly one Reel through the generator.
5. Reel is uploaded to Supabase.
6. Instagram publishing runs only for approved content.
7. Telegram channel mirrors the published Reel when publishing succeeds.

## Automation invariants
- Never regenerate an already-generated approved Reel.
- Never publish rejected or unapproved content.
- Never hard-code secrets or tokens.
- Prefer idempotent steps and explicit state flags.
- A no-op workflow should finish successfully rather than fail.
- Human approval remains the gate before public publishing.

## Current known infrastructure
- GitHub repository is the source of truth for the content factory.
- Replit hosts the separate D3 project.
- Supabase REELS bucket provides public media URLs for Instagram/Telegram delivery.


## Autonomous market-content extension

- New market-analysis code lives in `agents/` and `src/orchestrator.py`; it is additive and must not replace the legacy Reel pipeline.
- The market workflow uses Python 3.11, yfinance OHLC, transparent EMA/RSI/MACD/ATR rules, image cards, and `data/state.json` for deduplication.
- Market cards are educational scenarios, not personalized trade advice. Never imply a guaranteed result or count targets as hits without an explicitly recorded outcome.
- `HUMAN_APPROVAL=false` is the requested default for the new market workflow; `true` sends a private Telegram draft and requires an explicit approve/reject callback. This toggle does not remove the existing approval gate for legacy Reels.
- Commit generated images before publishing so public image URLs can be fetched by Instagram. Prefer GitHub Pages; verify reachability and use the public raw-GitHub URL as a fallback.
- Run the market pipeline's synthetic dry-run tests and never use live publishing credentials in a test job.
