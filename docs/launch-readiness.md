# Launch readiness: evidence before claims

## Non-negotiable release rule

Do not describe Bullseye Theory as launch-ready until a real payment has been completed and the resulting paid access has been verified end-to-end. A green CI run, a working login, or an admin-granted test entitlement is not proof of the payment-to-access path.

## Required end-to-end proof

- [ ] A real checkout/payment is completed through the intended production payment provider.
- [ ] The payment is verified server-side against the provider's trusted result (never solely from a browser redirect or client-submitted status).
- [ ] The correct user receives the intended course entitlement only after verified payment.
- [ ] Paid lesson HTML and media are not retrievable without entitlement; test direct URLs, not only browser redirects.
- [ ] Premium Telegram access is issued only after verified payment, and revocation/expiry is tested.
- [ ] Duplicate callbacks, retries, failed payments, refunds, and replay attempts do not grant extra or unauthorized access.
- [ ] Evidence, timestamps, and test account are recorded without storing payment secrets or access tokens in logs.

## Meta / Instagram constraint

Do not request or rotate Meta/Facebook/Instagram credentials as a default troubleshooting step. Treat Graph API code=100, subcode=33 as a permissions/configuration investigation unless new evidence proves a credential is invalid. Keep publishing changes separate from payment/access readiness.

## Automation repository checks

The deployment_readiness.yml and market_content_tests.yml workflows are expected to provide CI evidence for public-repository code changes. A passing workflow validates only the checks it actually runs; it does not establish payment-provider integration or secure paid-content delivery by itself.

## Current blockers to clear before a launch claim

- Verify the lesson_progress primary/unique key, RLS policies, and lesson progress upsert against the live schema.
- Audit SECURITY DEFINER functions and pin safe search_path values with fully qualified references.
- Confirm certificate eligibility requires completion of the actual published lesson set and required quiz conditions.
- Protect lesson HTML and media server-side; client-side redirects are not access control.
- Complete a real payment → server-side verification → course entitlement → protected content → premium Telegram invite/revocation test.

Never store service-role keys, bot tokens, payment secrets, or Meta access tokens in the repository or documentation.
