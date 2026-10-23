# Approval Matrix

| Workflow file | Trigger | Can publish publicly without owner approval? |
|---|---|---|
| ads_preflight_report.yml | Weekly schedule; manual dispatch | No — read-only preflight report. |
| automation_failure_watchdog.yml | Schedule; workflow completion | No — alerting only. |
| daily_automation_report.yml | Daily schedule; manual dispatch | No — private report only. |
| deployment_readiness.yml | Push; manual dispatch | No — readiness checks only. |
| educational_reel_draft.yml | Three daily schedules; manual dispatch | No — drafts require explicit Telegram owner approval. |
| educational_reel_recovery.yml | Manual dispatch with explicit live-publish confirmation | No new approval — only a previously approved Reel can be retried. |
| generate_approved_reel.yml | Manual dispatch; successful legacy pipeline completion | Conditional — accepts legacy automated-policy records without human approval; manual-review records are ineligible. |
| instagram_publish.yml | Manual dispatch; successful Reel-generation completion | Conditional — publishes only records accepted by persisted policy checks; manual dispatch is a live action. |
| instagram_publish_recovery.yml | Successful workflow completion | No new approval — retries only a previously approved post after guarded reservation. |
| instagram_token_health.yml | Schedule; push; manual dispatch | No — credential diagnostics only. |
| market_approval_poll.yml | Every 5 minutes; push; market workflow completion; manual dispatch | No — public publishing through this poller requires an existing owner approval state. |
| market_content.yml | Weekday schedule; manual dispatch | Yes for scheduled runs — market scenarios use automated QA and HUMAN_APPROVAL=false; manual dispatch defaults to dry-run. |
| market_content_tests.yml | Pull request/push/manual CI trigger | No — tests only. |
| market_publish_retry.yml | Manual dispatch with exact RETRY confirmation | No new approval — retries one signal only after the approval/freshness/duplicate preflight. |
| market_stall_watchdog.yml | Weekday schedule | No — stalled-run alert only. |
| pipeline.yml | Manual dispatch | No — draft-only; AUTO_PUBLISH_ENABLED=false. |
| premium_daily_autopublish.yml | Daily schedule; manual dispatch with publish_now=true | Yes, explicit exception — sends an evergreen lesson only to the configured private Premium Telegram destination. |
| premium_telegram_education.yml | Manual dispatch | No — preview and optional read-only destination check. |
| ritu-daily.yml | Scheduled workflow | Separate Ritu content workflow; check its own publishing guard before use, outside the Bullseye approval pipeline. |
| telegram_approval.yml | Manual dispatch | No — informational only. |
| test_telegram_channel.yml | Manual dispatch | No public content publishing — destination test only. |
| weekly_report.yml | Weekly schedule; manual dispatch | No — reporting only. |
