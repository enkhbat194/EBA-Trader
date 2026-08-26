# EBA Trader — Session Handoff

_Last handoff prepared: 2026-08-26 (Asia/Ulaanbaatar)_

## What was completed

- Restored project state from repository continuity before work.
- PR #33 is merged at `2b62f056f438c38865694d2f0aa130480926e7b2`: Home carry metrics are explicit and Fast Momentum has read-only LIVE/STALE/OFF heartbeat, decision, last scan, next expected scan and interval.
- PR #34 is merged at `ee5fd3f16ed5ad88ca928ced0efdb5790cbf568d`: deterministic one-control-to-many-treatment M5 order-flow ablation orchestration.
- PR #35 implements venue-aware Binance candle acquisition plus the real USD-M M5 feature-dataset workflow.
- The new pipeline acquires exact USD-M futures candles, acquires/repairs USD-M `aggTrades`, verifies immutable manifests/hashes, aligns prior-closed footprint features causally, writes the feature CSV and returns an M4-safe `dataset_ref`.
- Added `eba-build-orderflow-features` as the one-command development dataset builder.
- PR #35 prevents silent Spot-candle + futures-order-flow contamination.
- Frozen first-cycle OOS remains blocked by the existing holdout guard; there is no execution or lifecycle-promotion authority in this workflow.
- PR #35 full regression passed. Two Ruff-only findings (unused import and import order) were fixed; the subsequent head passed Ruff, Linode runtime checks, Linode production bundle and Continuity guard before the latest continuity updates.
- User-provided production screenshots now additionally prove History and Fast Paper trade-detail/chart rendering from persisted server truth.

## Current project state

- GitHub `main` is the code/continuity source of truth; Linode is the sole active runtime target.
- M4 research platform is complete; M5 AI Strategy Factory is in progress.
- Order-flow acquisition, repair, causal alignment, feature adapters and deterministic ablation orchestration are implemented.
- PR #35 is pending final continuity-head CI/merge.
- Research / AI Lab and scanner heartbeat are read-only.
- Real Binance order submission remains locked.
- Automated frozen OOS remains locked pending lifecycle-order reconciliation.

## Production proof status

Confirmed on 2026-08-26:

- public HTTPS PWA opened on iPhone;
- Home / Scan / Settings showed server-backed state;
- History showed persisted Fast Paper trades and exit reasons;
- Fast Paper trade detail showed execution facts, strategy evidence and chart data.

Still pending:

- standalone Chart / Positions / Research smoke;
- one active Fast Momentum paper position surviving service/server restart and later MARK/CLOSE;
- persist/recover or explicitly retire the older carry paper engine.

## New user requirement — persistent Demo credentials

The Binance Demo modal currently requires re-entering API key/secret. Implement a server-side credential vault after PR #35 is merged:

- user enters Demo key + secret once in the app;
- backend stores encrypted-at-rest credentials outside Git and outside browser persistent storage;
- browser never receives the secret back;
- status endpoint returns only saved/connected/masked metadata;
- explicit Replace and Delete credential actions;
- no withdrawal permission requirement and no real-money key path;
- service/server restarts must preserve the saved Demo credential.

## Next exact task

1. Revalidate and squash-merge PR #35.
2. Implement encrypted server-side one-time Binance Demo credential persistence with tests and phone-first UI status/replace/delete flow.
3. Run `eba-build-orderflow-features` on Linode for a real BTCUSDT USD-M development window outside frozen OOS.
4. Emit the #34 deterministic ablation batch and run it through M4 queue/worker/evidence/gates.
5. Compare/persist survivors for triage only; keep frozen OOS and live execution closed.
6. Continue remaining production smoke/restart proof in parallel.

## Notes for the next AI session

Read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, and this file before coding. Actual code/Git overrides stale text.
