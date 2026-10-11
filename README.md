# AI Trading Content Factory — Bullseye Theory

A free-tier-first GitHub Actions content factory for Bullseye Theory. The original educational Reel pipeline remains in place; the market-analysis pipeline is an additive workflow under `agents/` and `src/orchestrator.py`.

> **Risk note:** This system publishes rule-based educational market scenarios, not personalized investment advice. Technical levels can fail. Yahoo Finance data can be delayed, incomplete, or corrected. Never treat an automated setup as a guaranteed outcome or as an instruction to place a trade.

## Existing system (preserved)

- `src/main.py`: deterministic educational topic/script pipeline with an optional OpenAI-compatible LLM.
- `src/reel_generator.py`: creates approved short-form Reels.
- `src/telegram_send.py` and `src/telegram_process.py`: Telegram approval queue and callback processing.
- `src/instagram_publish.py`: existing Reel publisher through Meta Graph API and Supabase.
- Existing workflows continue to run independently: `pipeline.yml`, `generate_approved_reel.yml`, `instagram_publish.yml`, token health, failure watchdog, daily report, and Ritu workflow.

The legacy workflow uses Python 3.12 and the market workflow uses Python 3.11. Both use `config/env.py` to resolve supported Instagram credential aliases. If `HUMAN_APPROVAL` is unset or ambiguous, approval is required.

## New market-content factory

### Agents

1. `agents/scout.py` downloads hourly OHLC data with yfinance for Gold, BTC, ETH, EUR/USD, Nasdaq 100, SPY, Nifty 50, Bank Nifty, Reliance, HDFC Bank, TCS, Infosys, and SBI. It calculates EMA20/EMA50, RSI(14), MACD, ATR(14), session VWAP where volume exists, and recent swing support/resistance.
2. `agents/charts.py` renders dark candlestick charts with EMA overlays, RSI, and volume to `output/<slug>.png`.
3. `agents/card.py` creates a branded 1080×1080 signal-scenario card at `output/<slug>_card.png`.
4. `agents/analyst.py` uses an optional OpenAI-compatible LLM (Venice by default) and deterministic fallback copy.
5. `agents/copy.py` creates Telegram HTML and Instagram captions. Global instruments use English; Indian instruments use natural Roman-script Hinglish. Captions include a short hook and educational disclaimer.
6. `agents/qa.py` checks level ordering, positive finite values, R:R to TP2 of at least 1.5, and duplicate IDs using `data/state.json`.
7. `agents/publisher.py` posts cards to Telegram and Instagram, verifies a public image URL, and records platform-specific status to avoid resending successful posts.

`src/orchestrator.py` coordinates the chain. A symbol that fails does not prevent the other symbols from being processed. Each run selects up to three strongest non-neutral scenarios per region; it does not invent signals when no setup passes.

### Workflow schedule

`.github/workflows/market_content.yml` runs on weekdays at:

- 09:15 IST (03:45 UTC)
- 11:15 IST (05:45 UTC)
- 13:30 IST (08:00 UTC)
- 15:45 IST (10:15 UTC)

The workflow first generates and commits PNGs/state, then publishes. That order allows Instagram to fetch a public image URL. GitHub Pages is preferred when configured; raw GitHub is a fallback for public repositories. It also supports manual dispatch with `dry_run=true`.

**Public image hosting:** this repository is public. The market publisher checks candidate image URLs with HTTP HEAD and fails closed if the card is not reachable. `IMAGE_BASE_URL` should point to the public GitHub Pages `/output` path or another public HTTPS image host. Confirm the exact generated card URL is reachable before enabling public publishing.

`.github/workflows/market_approval_poll.yml` checks Telegram approval buttons every 30 minutes. If `HUMAN_APPROVAL=true`, market drafts go to the Telegram chat with **APPROVE & PUBLISH** and **REJECT** buttons. The existing Telegram callback processor handles both legacy Reel approvals and new market approvals. Both callback workflows share a concurrency group so they do not poll Telegram updates at the same time.

`.github/workflows/weekly_report.yml` sends a Friday Telegram report. It estimates hypothetical signal outcomes from post-signal hourly OHLC (conservatively counting same-candle stop/target ambiguity as a stop) and fetches Instagram Insights when permissions allow. This is not actual broker P&L; the report clearly labels it as scenario analysis. `.github/workflows/market_stall_watchdog.yml` checks weekday evening for a recent successful market-content run and sends an alert only if the scheduled factory appears stalled. The failure watchdog also monitors the new market workflows.

## Setup checklist

### 1. Add GitHub Actions secrets

Open **Repository → Settings → Secrets and variables → Actions → New repository secret**.

Required for Telegram:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID` — your private Telegram chat ID for drafts/reports

Required for Instagram publishing:
- `IG_USER_ID` — optional canonical Instagram professional account ID; aliases are supported below
- `IG_ACCESS_TOKEN` — optional canonical token; aliases are supported below

Optional/compatibility:
- `LLM_API_KEY` — Venice/OpenAI-compatible API key; deterministic fallback works without it
- `LLM_BASE`, `LLM_MODEL` — optional LLM endpoint/model settings; these are non-secret configuration and are best stored as Variables, but the workflow also accepts them as Secrets
- `GH_USER`, `GH_REPO` — public GitHub username and repository name (these are public metadata; repository Variables are also supported by the approval workflow)
- `META_SYSTEM_USER_TOKEN`, `INSTAGRAM_USER_ID`, `INSTAGRAM_ACCESS_TOKEN` — supported credential aliases for both pipelines; the alias layer resolves `IG_USER_ID` before `INSTAGRAM_USER_ID`, and `IG_ACCESS_TOKEN` before `META_SYSTEM_USER_TOKEN` before `INSTAGRAM_ACCESS_TOKEN`
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` — required by the existing Reel publishing workflow, not the new market-card publisher
- `META_APP_ID`, `META_APP_SECRET` — only needed locally by the token refresh helper; never commit them

Recommended repository **Variables** (Settings → Secrets and variables → Actions → Variables):
- `HUMAN_APPROVAL` = `true` (recommended and fail-closed default). Public publishing requires an explicit callback bound to the exact content/signal ID and version/hash. Set `false` only for an intentional, explicitly configured automation mode after testing
- `LLM_ENABLED` = `true` to use the configured LLM; fallback copy works if unavailable
- `LLM_BASE` = `https://api.venice.ai/api/v1` (or your OpenAI-compatible base URL)
- `LLM_MODEL` = your selected model, default `llama-3.3-70b`
- `IMAGE_BASE_URL` = optional public base URL ending in `/output`, e.g. `https://USERNAME.github.io/REPOSITORY/output`
- `META_GRAPH_API_VERSION` = optional; default `v23.0`

The workflow accepts `GH_USER` and `GH_REPO` as secrets. They are not sensitive, so Variables are preferable when configuring them for the market approval workflow. Do not put any access token, app secret, or API key in Variables or source code.

### 2. Create the Telegram bot and channel access

1. In Telegram, open **@BotFather**, send `/newbot`, and follow the prompts.
2. Copy the bot token into `TELEGRAM_BOT_TOKEN`; never share it publicly.
3. Create or open the Bullseye Theory channel (`@bullseye_theory`) and add the bot as an administrator with permission to post.
4. Start a private chat with your bot and send `/start`.
5. Obtain your private chat ID using the bot's `getUpdates` response or a trusted Telegram ID helper, then set `TELEGRAM_CHAT_ID`. The bot must be able to message you before draft delivery works.
6. For full auto, set `HUMAN_APPROVAL=false`. For a review gate, set it to `true`; approve/reject buttons are polled every 30 minutes.

### 3. Set up Instagram Graph API

1. Use an Instagram **Professional** account (Business or Creator) linked to a Facebook Page.
2. Create/configure a Meta developer app and grant the app/user access to the Page and linked Instagram account.
3. Ensure the required Instagram content publishing and account/Page permissions are approved for the app. Generate a token for the correct account and confirm it can publish image media.
4. Set `IG_USER_ID` and `IG_ACCESS_TOKEN` in GitHub Secrets. Do not use a short-lived token for unattended publishing.
5. Make sure the Instagram account is not restricted and that the image URL is publicly accessible over HTTPS. Publishing an image uses Graph API `/{ig-user-id}/media` followed by `/{ig-user-id}/media_publish`.

#### Refresh the long-lived token

On a private local machine, install Python dependencies and authenticate GitHub CLI (`gh auth login`). Set `META_APP_ID`, `META_APP_SECRET`, and the current `IG_ACCESS_TOKEN` in your local environment, then run:

```bash
python scripts/refresh_ig_token.py
```

By default, the script exchanges the token and updates the repository secret `IG_ACCESS_TOKEN` through GitHub CLI without printing the value. If you need to copy the token manually, run `python scripts/refresh_ig_token.py --print-token` only in a private terminal and paste it into GitHub Secrets. **Never run the print option in GitHub Actions logs or commit the token.** Token exchange may fail if the original token/app permissions are invalid; inspect the Meta error and regenerate the credential if necessary.

### 4. Enable GitHub Pages for public card URLs

1. Open **Repository → Settings → Pages**.
2. Choose **Deploy from a branch**, select branch `main` and folder `/(root)`, then save.
3. Wait until GitHub reports that the site is published. The images are committed under `output/`, so a card is served at `https://USERNAME.github.io/REPOSITORY/output/<slug>_card.png`.
4. Optionally set the `IMAGE_BASE_URL` repository Variable to `https://USERNAME.github.io/REPOSITORY/output`.
5. Keep the repository public if using public Pages or the raw-GitHub fallback. Only generated market cards/charts and state are committed; never add credentials or private account data to generated output.

### 5. First run and verification

1. Confirm the secrets/variables above are configured.
2. Open **Actions → Autonomous Market Content Factory → Run workflow**.
3. Select `dry_run=true` first. It should generate charts, cards, copy, and QA/state records but must not post to Telegram or Instagram.
4. Review the Action log and committed image output. Then run with `dry_run=false` to enable publishing.
5. Watch **Actions** for per-symbol warnings and platform status. A weak/neutral setup is skipped. If Yahoo Finance has no valid candles or every symbol fails, inspect the logs; the system does not fabricate a signal. Stale hourly data is rejected after 20 hours for non-crypto instruments and 36 hours for crypto. Missing publishing credentials now fail the publish step rather than silently claiming success.
6. Run the QA unit tests locally or in CI with `python -m unittest discover -s tests`.

## Environment and dependencies

Python 3.11 for the new market workflow. Requirements include yfinance, pandas, NumPy, mplfinance, Pillow, requests, and the existing PyYAML dependency. Secrets are read from environment variables only.

Useful environment flags:
- `DRY_RUN=1`: render and validate without posting.
- `HUMAN_APPROVAL=true`: send draft to Telegram DM; button approval is required before public posting.
- `LLM_ENABLED=true`: use the configured LLM when `LLM_API_KEY` is available.
- `GENERATE_ONLY=true`: generate and save images/state before the publish phase.
- `PUBLISH_ONLY=true`: publish prepared, committed records.
- `LOG_LEVEL=INFO`: readable per-symbol and per-platform logs.

## Current limitations

- yfinance is a convenient public data source, not an exchange-grade feed; some tickers may be delayed, have missing volume, or temporarily fail.
- The rule-based EMA/RSI/MACD screen is intentionally simple and is not evidence of profitability.
- The weekly report estimates hypothetical R outcomes from public OHLC and labels them as non-executed scenario analysis. It does not represent broker P&L or guarantee that a trade was filled. Instagram engagement requires Insights API permissions; if unavailable, the report says so.
- This project does not connect to a broker and does not execute trades.
