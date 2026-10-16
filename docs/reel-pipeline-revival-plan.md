# Bullseye Theory — Reel Pipeline Revival Plan

Status: planning/specification only. This document does not authorize publishing, deployment, paid services, or merging PR #2.

## Goal
Revive the existing Reel pipeline without replacing it. Improve the quality and reliability of educational trading Reels: hooks, accurate scripts, storyboard frames, original chart visuals, indicators/market-structure annotations, captions, QA, and approval-gated publishing.

## Hard constraints
- ₹0 incremental spend. No paid API, credits, subscriptions, hosting, storage, or ad spend.
- Preserve the legacy path: `src/main.py -> src/reel_generator.py -> src/instagram_publish.py`.
- Do not publish live or enable unattended publishing. Do not merge PR #2. Do not change IMAGE_BASE_URL, hosting, or public visibility.
- Dry-run first; explicit human approval before every publish.
- Never fabricate live prices, market events, indicators, results, backtests, entries, exits, SL/TP, or performance claims.
- Do not expose credentials. Do not copy competitor content or copyrighted chart/video assets.

## Proposed pipeline
1. **Topic selection** — choose from a maintained educational topic bank: market structure, HH/HL and LH/LL, BOS/CHoCH, liquidity concepts, indicator interpretation, risk sizing, R:R, psychology, and worked wins/losses. Mark examples as illustrative unless a verified data source is available.
2. **Research/fact sheet** — generate claims separately from the script. Every market-specific claim must have a source and timestamp; without verified sources, produce evergreen education only.
3. **Hook variants** — generate 3 hooks and score them for clarity, specificity, truthful promise, and relevance. Ban guaranteed-profit language, fake urgency, and misleading signal claims.
4. **Script** — produce a 20–35 second script with timecodes, on-screen text, voiceover, chart action, and a concise educational disclaimer when needed.
5. **Storyboard** — produce a scene table: seconds, purpose, background, chart/indicator overlay, exact text, voiceover, transition, and asset path. Keep a consistent 9:16 Bullseye palette (deep navy, neon lime signal highlights, restrained gold).
6. **Chart/visual generation** — prefer deterministic original SVG/Canvas/Pillow-style chart illustrations or supplied/licensed assets. Label synthetic examples as illustrative. Indicator calculations must use defined formulas and input data; never draw a visual that implies a real signal from invented data.
7. **Render** — create a vertical video with readable safe-zone text, captions, scene pacing, controlled transitions, consistent audio levels, and a thumbnail. Reuse installed/free local tooling; if required dependency or tool is missing, fail clearly rather than pretending an MP4 exists.
8. **Automated QA** — verify files exist and are non-empty, expected aspect ratio/duration, all scenes have assets, no unresolved placeholders, caption/script alignment, prohibited claims, stale data, source presence for live claims, and no duplicate recent topic/content hash.
9. **Human review** — save to a review queue with MP4, thumbnail, script, sources, and QA report. State is `pending_approval` by default.
10. **Publish** — only after a human explicitly approves that exact asset/caption. Dry-run must be a true no-op: no API publish call, no scheduled post, and no externally visible side effect. Persist idempotency keys and record provider response.

## Quality gates (block generation or publishing)
- Invalid/missing topic, source, script, storyboard, render, thumbnail, or QA report.
- Live market claim without verifiable source + timestamp.
- Fabricated trade levels, performance, win rate, or price.
- Stale research where a live/current claim is used.
- Paid-only asset, watermark, unresolved template placeholder, or missing commercial-use permission.
- Content over configured freshness window; duplicate or near-duplicate output.
- Approval missing, revoked, or not bound to the exact final media hash and caption.
- `dry_run=true` must never call publishing APIs.

## Minimal output contract
For each run, create a unique run directory containing:
- `topic.json`: topic, audience, educational objective, data mode (`evergreen` or `verified_live`), sources/timestamps if applicable.
- `script.md`: hook variants, selected hook, timed voiceover and on-screen text.
- `storyboard.json`: ordered scenes with duration, visuals, overlays, asset paths, transition, and narration.
- `assets/`: original chart illustrations, background/thumbnail, subtitle file, final video.
- `qa.json`: deterministic checks, blocked/warning reasons, asset hashes.
- `approval.json`: pending/approved/rejected, reviewer, approved media hash, approved caption, timestamp.
- `publish_result.json`: only written after an approved publish attempt; never fabricated during dry-run.

## Acceptance tests before considering the pipeline revived
1. Offline/dry-run builds one complete educational Reel package from a fixture topic.
2. Repeated run does not create duplicate publish actions or silently overwrite reviewed media.
3. Missing source for a live claim blocks output; evergreen educational content can proceed.
4. Missing storyboard asset or render failure blocks approval.
5. Paid-only asset or watermark detection produces a block/warning and never auto-publishes.
6. Approval for an old media hash cannot authorize a newly rendered file.
7. `dry_run=true` has zero publish/schedule API calls.
8. Stale/unreviewed/duplicate content is rejected.
9. No secrets appear in artifacts or logs.
10. Legacy Reel entry point remains usable and tests cover its end-to-end dry-run behavior.

## Implementation order
A. Inspect current branch, entry points, dependencies, configuration, and tests before editing.
B. Reproduce the current failure in a no-side-effect run and record exact logs.
C. Fix the earliest failing stage with a small commit and regression test.
D. Add structured script/storyboard/asset contracts while preserving the legacy entry point.
E. Add deterministic chart/storyboard rendering using already-installed free dependencies only.
F. Run offline fixtures and inspect generated frames/video manually.
G. Verify approval + dry-run safeguards and CI. Keep all output as drafts.
H. Request explicit user approval before any merge, deployment, new hosting, or live publishing.

## Honest status
This document is a plan, not proof that the existing pipeline works. No live publishing, payment, paid tool, deployment, or merge is authorized by this document.