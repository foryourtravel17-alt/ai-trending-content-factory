# Approval Matrix

| Workflow file | Trigger | Can publish publicly without owner approval? |
|---|---|---|
| ads_preflight_report.yml | Weekly schedule; manual dispatch | No — read-only preflight report. |
| automation_failure_watchdog.yml | Schedule; workflow completion | No — alerting only. |
| daily_automation_report.yml | Daily schedule; manual dispatch | No — private report only. |
| deployment_readiness.yml | Push; manual dispatch | No — readiness checks only. |
| educational_reel_draft.yml | Three daily schedules; manual dispatch | No — drafts require explicit Telegram owner approval. |
| educational_reel_recovery.yml | Manual dispatch with explicit live-publish confirmation | No new approval — only a previously approved Reel can be retried. |
| instagram_publish_recovery.yml | Successful workflow completion | No new approval — retries only a previously approved post after guarded reservation. |
| instagram_credential_diagnostic.yml | Manual dispatch | No — read-only credential and Page-link diagnostic. |
| instagram_token_health.yml | Schedule; push; manual dispatch | No — credential diagnostics only. |
| market_approval_poll.yml | Every 5 minutes; push; market workflow completion; manual dispatch | No — public publishing through this poller requires an existing owner approval state. |
| market_content.yml | Weekday schedule; manual dispatch | No — scheduled market scenarios require an authorized owner approval in private Telegram before public posting; manual dispatch defaults to dry-run. |
| market_content_tests.yml | Pull request/push/manual CI trigger | No — tests only. |
| market_publish_retry.yml | Manual dispatch with exact RETRY confirmation | No new approval — retries one signal only after the approval/freshness/duplicate preflight. |
| market_stall_watchdog.yml | Weekday schedule | No — stalled-run alert only. |
| premium_daily_autopublish.yml | Daily schedule; manual dispatch with publish_now=true | No public post — explicit private-channel exception auto-sends an evergreen lesson to the configured Premium Telegram destination. |
| premium_telegram_education.yml | Manual dispatch | No — preview and optional read-only destination check. |
| ritu-daily.yml | Daily schedule; manual dispatch | No — generates and commits a content queue; no public publishing step in this workflow. |
| telegram_approval.yml | Manual dispatch | No — informational only. |
| test_telegram_channel.yml | Manual dispatch with confirm_test_post=true | No — public test post is blocked unless the owner explicitly confirms the fixed video in the dispatch form. |
| weekly_report.yml | Weekly schedule; manual dispatch | No — reporting only. |
