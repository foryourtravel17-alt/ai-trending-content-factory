# Bullseye Theory — Telegram-only Content Factory

This repository runs the Bullseye Theory social-content pipeline with free GitHub Actions workflows. Telegram is the only social publishing destination. Facebook and Instagram are intentionally disconnected: no Meta Graph API calls, Instagram credentials, Instagram publishing, Facebook publishing, or Instagram health checks are part of this automation.

The source repository remains private. No paid social scheduler, TradingView Pro plan, or paid image host is required.

## Publishing policy

**Every public market card and educational Reel requires an explicit owner approval in the private Telegram approval chat.** Automated formatting and safety checks do not count as owner approval.

1. GitHub Actions generates market cards or educational Reels.
2. Market cards are sent as private Telegram photo drafts with APPROVE / REJECT buttons.
3. Educational Reels are rendered, uploaded to the existing Supabase `REELS` media bucket, and sent to the owner's private Telegram approval chat.
4. The Telegram approval poller checks for callback decisions every five minutes.
5. Only the exact item with a persisted, authorized APPROVE decision can be sent to the `@bullseye_theory` Telegram channel.
6. The system records Telegram message IDs and blocks duplicates or ambiguous delivery outcomes.

Rejected, stale, unapproved, failed-safety, or ambiguous items are not automatically published. No workflow is allowed to bypass the Telegram owner approval step.

## Schedules (India time)

| Workflow | Schedule | Output |
|---|---|---|
| Autonomous Market Content Factory | Monday–Friday, 09:15, 11:15, 13:30, 15:45 | Market cards → private Telegram approval |
| Bullseye Daily Educational Reel Draft | Daily, 10:17, 14:17, 18:17 | Reel MP4 → private Telegram approval |
| Market Signal Approval Poller | Every 5 minutes | Process authorized Telegram APPROVE / REJECT callbacks |
| Weekly P&L and Telegram report | Friday, 22:00 | Private Telegram scenario report |
| Daily automation report / watchdogs | Existing configured schedules | Private Telegram status and failure notices |

Market workflow manual dispatch defaults to `dry_run=true`. A dry run generates and validates content but sends no approval request and makes no public post.

## Required GitHub Actions secrets

Open **Repository → Settings → Secrets and variables → Actions**.

Required:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID` — the owner's private Telegram chat for approvals and reports
- `TELEGRAM_APPROVER_USER_IDS` — owner Telegram numeric user ID, recommended for an explicit allowlist
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

Supabase is used only as durable media storage for educational Reel MP4s. The existing `REELS` bucket must stay public-read so Telegram can fetch the approved video URL; uploads use the service-role key inside GitHub Actions. Market-card photos are uploaded directly from the workflow runner to Telegram.

### Telegram setup

1. Start a private chat with the approval bot and send `/start`.
2. Add the same bot as an administrator to `@bullseye_theory` with permission to post messages.
3. Ensure `TELEGRAM_CHAT_ID` points to the owner's private approval chat (not the public channel).
4. Set `TELEGRAM_APPROVER_USER_IDS` to the numeric Telegram user ID allowed to approve/reject. Do not put bot tokens or secret values in chat or source code.

## Safe manual test

1. Open **Actions → Autonomous Market Content Factory → Run workflow**.
2. Keep `dry_run=true` for a no-publish generation test.
3. For an intentional approval-queue test, dispatch with `dry_run=false`. This sends draft cards to the private approval chat; it does not publish to the channel.
4. Review each draft and press APPROVE or REJECT. After APPROVE, the five-minute poller triggers Telegram channel delivery.
5. Never use a public test-post workflow as a substitute for the private approval flow.

Educational Reel drafts can also be run manually from **Actions → Bullseye Daily Educational Reel Draft**. A manual or scheduled draft still needs your Telegram approval before channel publishing.

## Data and safety notes

- Market analysis uses public hourly OHLC data and may skip stale, missing-volume, or neutral setups; it never invents a signal to fill a posting quota.
- Market cards are scenarios, not personalized investment advice or guaranteed outcomes.
- Educational content uses the existing deterministic topic/script pipeline and automated safety/format checks. The checks do not independently prove factual correctness; owner review remains required.
- Approved educational Reels have a 48-hour publishing window and a three-post daily cap.
- Telegram message IDs and state markers are persisted so successful or ambiguous sends are not duplicated.
- The project does not connect to a broker or execute trades.

## Repository architecture

- `agents/scout.py`, `agents/analyst.py`, `agents/charts.py`, `agents/card.py`, `agents/copy.py`, `agents/qa.py`: market research, card rendering, Telegram copy, and QA.
- `agents/publisher.py`: Telegram-only market draft/approval/channel delivery.
- `src/orchestrator.py`: scheduled market-content generation and approved Telegram publishing.
- `src/telegram_process.py`: authorized callback polling and durable approval-state updates.
- `src/telegram_reel_publish.py`: Telegram-only approved Reel delivery with media-integrity and duplicate checks.
- `scripts/publish_approved_educational_reels.py`: exact approved Reel IDs handed from the callback poller to the Telegram publisher.
- `scripts/upload_educational_reel.py`: uploads and verifies Reel MP4s in Supabase Storage.
- `docs/APPROVAL_MATRIX.md`: workflow-level publishing policy.

Instagram/Facebook-related GitHub secrets, if they already exist, are unused by this Telegram-only version. They can be deleted separately from GitHub Settings, but their presence does not enable any publishing integration.
