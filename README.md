# AI Trading Content Factory — Bullseye Theory

A free-tier-first GitHub Actions content factory for Bullseye Theory. Educational Reels use the approval-gated `educational_reel_draft.yml` workflow; the market-analysis pipeline runs under `agents/` and `src/orchestrator.py`.

> **Risk note:** This system publishes rule-based educational market scenarios, not personalized investment advice. Technical levels can fail. Yahoo Finance data can be delayed, incomplete, or corrected. Never treat an automated setup as a guaranteed outcome or as an instruction to place a trade.

## Existing system (preserved)

- `src/main.py`: deterministic educational topic/script pipeline with an optional OpenAI-compatible LLM.
- `src/telegram_send.py` and `src/telegram_process.py`: Telegram approval queue and callback processing.
- The retired manual `pipeline.yml` and its legacy `generate_approved_reel.yml` / `instagram_publish.yml` publishing chain are unsupported and have been removed; use `educational_reel_draft.yml` for educational Reels. See [the workflow approval matrix](docs/APPROVAL_MATRIX.md).

The scheduled daily educational Reel workflow runs a Python 3.12/FFmpeg pipeline and creates draft-only Reels. The owner must approve the exact Reel in Telegram before the approval poller can publish it; automated safety screening is not owner approval.

`.github/workflows/educational_reel_draft.yml` generates three curated evergreen educational Reel drafts per day at 10:17 AM, 2:17 PM, and 6:17 PM India time. It renders one MP4 per slot, uploads and verifies the exact object in Supabase, registers the draft as pending human review, and sends a private Telegram approval request. It does not publish publicly. The approval poller publishes only after the owner approves the exact draft; automated safety screening is not approval. Approved drafts have a 48-hour publishing window, and one private Telegram notice lists drafts that expired in the last 24 hours. Scheduled runs pass the intended slot explicitly so delayed GitHub cron starts cannot mislabel a slot.

Market cards auto-publish on schedule by design; educational Reels require owner approval.

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

The workflow first generates and commits PNGs/state, then publishes. That order allows Instagram to fetch a public image URL. GitHub Pages is preferred when configured; raw GitHub is a fallback for public repositories. Manual dispatch defaults to `dry_run=true` so the first manual run is safe; set it to `false` only after reviewing generated output and confirming credentials and hosting.

**Important hosting and visibility note:** this repository is currently **public** (verified on GitHub). Instagram needs a publicly reachable HTTPS image URL; the publisher checks URL reachability and fails rather than posting a broken image. Keep secrets and private account data out of source, commits, generated output, and logs. GitHub Pages or `IMAGE_BASE_URL` can serve generated cards. Do not change repository visibility as part of this workflow without first reviewing the image-hosting impact.

`.github/workflows/market_approval_poll.yml` is the single Telegram callback consumer for approval-gated market records and educational Reels. Market-card publication remains a separate automated-QA path configured with `HUMAN_APPROVAL=false`; that is an explicit automated-policy exception and is documented in [the approval matrix](docs/APPROVAL_MATRIX.md).

`.github/workflows/weekly_report.yml` sends a Friday Telegram report. It estimates hypothetical signal outcomes from post-signal hourly OHLC (conservatively counting same-candle stop/target ambiguity as a stop) and fetches Instagram Insights when permissions allow. This is not actual broker P&L; the report clearly labels it as scenario analysis. `.github/workflows/market_stall_watchdog.yml` checks weekday evening for a recent successful market-content run and sends an alert only if the scheduled factory appears stalled. The failure watchdog also monitors the new market workflows.

`.github/workflows/ads_preflight_report.yml` runs every Monday at 10:00 IST and can also be run manually. It reviews up to 12 recent published Instagram posts, reads available Insights, and sends a private Telegram preflight note. This is **read-only**: it never creates, activates, edits, or budgets ads. With fewer than three posts with readable reach/engagement metrics, it labels the data early and does not recommend a boost. It requires `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and either `IG_ACCESS_TOKEN` or `META_SYSTEM_USER_TOKEN`.

## Setup checklist

### 1. Add GitHub Actions secrets

Open **Repository → Settings → Secrets and variables → Actions → New repository secret**.

Required for Telegram:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID` — your private Telegram chat ID for drafts/reports

Required for Instagram publishing:
- `IG_USER_ID` — Instagram professional account ID
- `IG_ACCESS_TOKEN` — valid long-lived token with content-publishing permission

Optional/compatibility:
- `LLM_API_KEY` — Venice/OpenAI-compatible API key; deterministic fallback works without it
- `LLM_BASE`, `LLM_MODEL` — optional LLM endpoint/model settings; these are non-secret configuration and are best stored as Variables, but the workflow also accepts them as Secrets
- `GH_USER`, `GH_REPO` — public GitHub username and repository name (these are public metadata; repository Variables are also supported by the approval workflow)
- `META_SYSTEM_USER_TOKEN`, `INSTAGRAM_USER_ID` — compatibility names for the existing legacy publisher
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` — required by the existing Reel publishing workflow, not the new market-card publisher
- `META_APP_ID`, `META_APP_SECRET` — only needed locally by the token refresh helper; never commit them

Recommended repository **Variables** (Settings → Secrets and variables → Actions → Variables):
- Market publishing sets `HUMAN_APPROVAL=false` in the workflow so eligible new market scenarios publish automatically after quality and freshness checks.
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
6. Scheduled market scenarios use the documented automated-QA policy. Educational Reel drafts do **not** publish automatically: review the exact MP4, caption, and hashtags in your private Telegram chat, then press the approval button. The separate Premium Telegram lesson workflow is an explicit private-channel exception and requires `PREMIUM_TELEGRAM_CHAT_ID`.

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
3. The manual workflow defaults to `dry_run=true`. It should generate charts, cards, copy, and QA/state records but must not post to Telegram or Instagram.
4. Review the Action log and generated output after the dry run. Scheduled runs publish automatically; for manual dispatch, set `dry_run=false` only when you intentionally want to send content live. Instagram/Telegram credentials, public image hosting, and Meta permissions must be configured first.
5. Watch **Actions** for per-symbol warnings and platform status. A weak/neutral setup is skipped. If Yahoo Finance has no valid candles or every symbol fails, inspect the logs; the system does not fabricate a signal. Stale hourly data is rejected after 20 hours for non-crypto instruments and 36 hours for crypto. Missing publishing credentials now fail the publish step rather than silently claiming success.
6. Run the QA unit tests locally or in CI with `python -m unittest discover -s tests`.

## Organic-to-paid preflight review (read-only)

`.github/workflows/ads_preflight_report.yml` runs each Monday at 10:00 IST and can also be dispatched manually. It reads recent published Instagram content records, requests available media Insights, and sends a private Telegram report ranking posts by a transparent weighted-engagement-per-reach heuristic (likes + 2×comments + 3×saves + 3×shares, divided by reach). This is only an organic-engagement signal, not evidence of leads, sales, or return on ad spend.

The report does not call advertising write APIs, create/edit/enable campaigns, change budgets, or spend money. It does not commit private performance metrics into this public repository. If Insights are unavailable or reach is missing, it deliberately makes no winner recommendation.

Before any paid campaign can be launched, the owner must confirm the exact Meta ad account, course/lead destination, tracking event, objective, audience, campaign dates, and daily/total spending limit, then provide explicit final approval. Do not claim guaranteed trading results or fabricate testimonials, social proof, or performance statistics.

## Environment and dependencies

Python 3.11 for the new market workflow. Requirements include yfinance, pandas, NumPy, mplfinance, Pillow, requests, and the existing PyYAML dependency. Secrets are read from environment variables only.

Useful environment flags:
- `DRY_RUN=1`: render and validate without posting.
- `HUMAN_APPROVAL=true`: send draft to Telegram DM; button approval is required before public posting.
- `AUTO_PUBLISH_ENABLED=false`: keep the legacy manual pipeline draft-only.
- Approved educational Reels expire after 48 hours; the poller sends one private notice per expired draft.
- `LLM_ENABLED=true`: use the configured LLM when `LLM_API_KEY` is available.
- `GENERATE_ONLY=true`: generate and save images/state before the publish phase.
- `PUBLISH_ONLY=true`: publish prepared, committed records.
- `LOG_LEVEL=INFO`: readable per-symbol and per-platform logs.

## Workflow approval policy

See [docs/APPROVAL_MATRIX.md](docs/APPROVAL_MATRIX.md) for every GitHub Actions workflow, its trigger, and whether it can publish without owner approval.

The Premium Telegram lesson workflow is an explicit exception to the owner-approval rule: it automatically posts evergreen lessons only to the configured private Premium Telegram destination at 10:00 AM IST. It requires `TELEGRAM_BOT_TOKEN` and `PREMIUM_TELEGRAM_CHAT_ID`; the destination ID must be checked manually in GitHub Actions Secrets. If the secret is missing or wrong, the workflow fails closed before sending. The connector cannot create or inspect secret values, and secret values must never be pasted into chat.

## Current limitations

- yfinance is a convenient public data source, not an exchange-grade feed; some tickers may be delayed, have missing volume, or temporarily fail.
- The rule-based EMA/RSI/MACD screen is intentionally simple and is not evidence of profitability.
- The weekly report estimates hypothetical R outcomes from public OHLC and labels them as non-executed scenario analysis. It does not represent broker P&L or guarantee that a trade was filled. Instagram engagement requires Insights API permissions; if unavailable, the report says so.
- This project does not connect to a broker and does not execute trades.
