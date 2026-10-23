# Bullseye Theory — Owner Launch Checklist

## Status legend
- **Automated:** code/docs/tests are in the repository.
- **Needs TradingView:** only the authenticated owner can see Pine Editor compilation and submit final publication.
- **Not enabled:** no broker orders; the educational Reel recovery workflow remains disabled unless explicitly opted in.

## Phase A — code and education
- [x] Write an original indicator prototype following the five pillars.
- [x] Write a separate backtest strategy harness.
- [x] Add rulebook, full 11-lesson course draft, Telegram posts, Reel hooks, client templates and landing-page HTML.
- [x] Add basic static tests for rule consistency.
- [ ] Compile both Pine files in TradingView; this is a manual, account-side action.
- [ ] Backtest with realistic symbol-specific fees and contract details; share screenshots for review.
- [ ] Review the indicator output with a competent independent trader; do not treat AI as a substitute for validation.

## Phase B — platform and offer
- [ ] Decide whether the first public script is free/open-source. Source will be visible on that route.
- [ ] If planning paid invite-only access or bundling script access with a paid course, confirm TradingView's Marketplace route before Nov 1, 2026. Official announcement: https://www.tradingview.com/blog/en/commercial-scripts-move-to-marketplace-61291/
- [ ] Approve pricing and deliverables. ₹599 founding cohort / ₹999 standard are draft ideas only.
- [ ] Write clear access duration, support scope, refund/cancellation rules.
- [ ] Insert verified UPI/payment and delivery details. Never request OTP, UPI PIN or trading-account password.
- [ ] Replace all placeholders in landing-page.html; test on phone.

## Phase C — publishing
- [ ] Compile, visually inspect historical charts and backtest results.
- [ ] Verify captions, disclaimer, logo/brand assets, course link and Telegram channel.
- [ ] You manually press TradingView's final Publish button; I cannot truthfully report publication without that platform confirmation.
- [ ] A code merge does not mean a script is published or that an Instagram post went live.

## What the words mean
- **Pine Script:** TradingView's scripting language.
- **Indicator:** draws calculated information on a chart.
- **Strategy / backtest:** simulates rule-based orders on past chart data.
- **R:** entry-to-stop reference distance.
- **Repainting:** a result changes after it first appears; using confirmed candle values helps reduce common causes.
- **GitHub Actions:** scheduled automation that runs code/tests without you opening a laptop.
- **PR (pull request):** a reviewable change to the repository; not the same thing as publishing the TradingView script.

## Final safety rule
No live account orders, guaranteed-profit language, or unverified performance claims. Treat the indicator as a test prototype until external compile/test evidence exists.
