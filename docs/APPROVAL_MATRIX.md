# Approval Matrix

| Workflow file | Trigger | Can publish publicly without owner approval? |
|---|---|---|
| automation_failure_watchdog.yml | Schedule; workflow completion | No — alerting only. |
| daily_automation_report.yml | Daily schedule; manual dispatch | No — private report only. |
| deployment_readiness.yml | Push; manual dispatch | No — readiness checks only. |
| educational_reel_draft.yml | Three daily schedules; manual dispatch | No — Reels require explicit Telegram owner approval before Telegram channel publishing. |
| market_approval_poll.yml | Every 5 minutes; push; market workflow completion; manual dispatch | No — public publishing through this poller requires an existing owner approval state. |
| market_content.yml | Four weekday schedules; manual dispatch | No — market scenarios go to private Telegram for owner approval; only an explicit approval button can publish to the Telegram channel. Manual dispatch defaults to dry-run. |
| market_content_tests.yml | Pull request/push/manual CI trigger | No — tests only. |
| market_publish_retry.yml | Manual dispatch with exact RETRY confirmation | No new approval — retries one previously approved Telegram post after freshness/duplicate preflight. |
| market_stall_watchdog.yml | Weekday schedule | No — stalled-run alert only. |
| premium_daily_autopublish.yml | Daily schedule; manual dispatch with publish_now=true | No public post — explicit private-channel exception auto-sends an evergreen lesson to the configured Premium Telegram destination. |
| premium_telegram_education.yml | Manual dispatch | No — preview and optional read-only destination check. |
| ritu-daily.yml | Daily schedule; manual dispatch | No — generates and commits a content queue; no public publishing step in this workflow. |
| telegram-approval-recovery.yml | Manual dispatch; one-time push on workflow addition | No — sends only pending private educational Reel approval requests; it never publishes. |
| telegram_approval.yml | Manual dispatch | No — informational only. |
| test_telegram_channel.yml | Manual dispatch with confirm_test_post=true | No — public test post is blocked unless the owner explicitly confirms the fixed video in the dispatch form. |
| weekly_report.yml | Weekly schedule; manual dispatch | No — reporting only. |
