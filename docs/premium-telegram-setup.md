# Bullseye Theory Premium Telegram education pipeline

## Current safety status

The GitHub Actions workflow `Bullseye Premium Telegram Education Preview` is manual-only and preview-only. It makes no Telegram network requests and cannot publish. This prevents accidental posts while the Premium channel destination is being identified.

The Python publisher is safe by default. It will only attempt a Telegram send when both `DRY_RUN=false` and `PREMIUM_TELEGRAM_AUTOPUBLISH=true`. Do not enable that gate until the destination is confirmed and a test is deliberately authorized.

## Find the Premium channel username or chat ID

1. Open the Telegram channel itself.
2. Tap/click the channel name at the top to open its info page.
3. If it is public, look for `t.me/<username>` or the `@username` field under channel type / links. The username is the part after `t.me/`, usually beginning with `@` when written in Telegram.
4. If it is private, it may not have a public username. Do not post an invite link publicly. For a private channel, add the bot as an administrator with permission to post messages, then use a known numeric channel chat ID from a safe bot/admin diagnostic or Telegram update. Do not paste bot tokens into chat.
5. The previously mentioned `@bullseye_theory` is used by an existing test workflow for a public channel and is not proof that this is the Premium channel. Do not assume they are the same.

## GitHub configuration

Repository: `https://github.com/foryourtravel17-alt/ai-trending-content-factory`

Settings location: **Settings → Secrets and variables → Actions**.

When the destination is confirmed and you intentionally enable publishing:

- `TELEGRAM_BOT_TOKEN` — Secret. Existing project secret; Python reads `os.getenv("TELEGRAM_BOT_TOKEN")`. Never print or share its value.
- `PREMIUM_TELEGRAM_CHAT_ID` — Secret. Add the Premium channel's exact `@public_username` or numeric chat ID. Python reads `os.getenv("PREMIUM_TELEGRAM_CHAT_ID")`.
- `PREMIUM_TELEGRAM_AUTOPUBLISH` — Repository variable, not secret. Keep unset or `false` until publishing is intentionally enabled. The publisher checks this gate in addition to `DRY_RUN=false`.

The preview workflow does not read these secrets or variables and cannot publish. Do not change the preview workflow to include a schedule until the channel, bot admin rights, test result, and desired cadence are confirmed.

## Run the preview

1. Open the repository's **Actions** tab.
2. Select **Bullseye Premium Telegram Education Preview**.
3. Click **Run workflow**, select branch `feat/premium-telegram-pipeline`, choose a lesson index, and run it.
4. Open the run and inspect the `Generate educational lesson preview` log. It should show the full lesson and `DRY RUN: no Telegram API request made.`

Lesson indexes: `0` Market Structure; `1` Risk Management; `2` Trading Psychology.

## Troubleshooting

- `CONFIG ERROR: TELEGRAM_BOT_TOKEN and PREMIUM_TELEGRAM_CHAT_ID are required.` — check the two secret names, not their values. Do not share token contents.
- Telegram HTTP `400` — inspect the response body for `chat not found`, `bot is not a member`, or `not enough rights`; verify the destination and bot administrator/posting permission.
- Telegram HTTP `401` — token is invalid/revoked; create a replacement through BotFather and update the GitHub secret without sharing it.
- `403` — bot may be blocked or lack permission; add it to the correct channel and grant posting rights.
- Network/DNS error — rerun after GitHub-hosted runner connectivity recovers; do not loosen authentication or paste secrets into logs.

Fallback: keep using the manual preview workflow; it has no external side effects. This first iteration deliberately sends educational lessons only, not unverified live prices, charts, or trade signals.
