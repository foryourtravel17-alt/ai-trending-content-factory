# Educational Reel recovery — operator note

The Oct 23, 2026 Reel `draft_risk-per-trade_evening_20261023_134943` was rendered and uploaded to Supabase; the publish wrapper failed with a known `NameError` before platform outcomes were recorded. The next scheduled Reel run skipped the existing draft to avoid duplicate generation, so that failure was not recovered automatically.

The recovery utility is intentionally strict: it requires a fresh (<24h), previously automated-approved record, the known NameError, valid exact-media integrity metadata, an Instagram state of `ready_for_publish`, and no recorded/ambiguous platform outcomes. It reserves one attempt in `data/state.json` before calling the existing publisher and will never retry that ID a second time.

**Default behavior:** live recovery is disabled. Scheduled execution only runs if repository Actions variable `ENABLE_REEL_RECOVERY=true` is set. Manual dispatch requires setting `confirm_live_publish=true`. Both can post the existing approved Reel to Instagram and Telegram; do not enable them unless a live post is intended.

A no-op is safe and expected when there is no candidate. The current code does not recreate or regenerate media and does not bypass the existing safety/approval checks.
