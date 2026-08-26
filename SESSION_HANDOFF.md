# EBA Trader — Session Handoff

_Last handoff prepared: 2026-08-26 (Asia/Ulaanbaatar)_

## What was completed

- Restored project state from repository continuity before work.
- PR #33 merged at `2b62f056f438c38865694d2f0aa130480926e7b2`: carry labels + Fast Momentum heartbeat.
- PR #34 merged at `ee5fd3f16ed5ad88ca928ced0efdb5790cbf568d`: deterministic one-control-to-many-treatment M5 order-flow ablation orchestration.
- PR #35 merged at `178611f535e95d61747a726b73cf7346f94358e4`: venue-matched USD-M candle + order-flow feature-dataset workflow and `eba-build-orderflow-features` CLI.
- Current production screenshots additionally prove persisted Fast Paper History and trade-detail/chart rendering from server truth.
- PR #36 implements one-time Binance Demo API credential persistence:
  - validates Demo key/secret before persistence;
  - encrypts at rest with Fernet authenticated encryption;
  - separates master key under `/etc/eba-trader` from ciphertext under `/var/lib/eba-trader/credentials`;
  - uses private file permissions and atomic writes;
  - provisions the master key on fresh install and existing Linode auto-update without implicit rotation;
  - never returns the saved secret to the browser;
  - never uses browser localStorage/sessionStorage for secrets;
  - supports masked status, automatic saved-key reconnect, explicit Replace and Delete;
  - rejects live/non-Binance credential storage;
  - preserves public-data Fast Paper when no account key is stored.
- PR #36 release target: `0.12.2 / LINODE-M7`, PWA cache `eba-trader-ui-v15`.
- PR #36 full regression, Ruff, Linode runtime, production bundle and continuity checks passed on the core head. Final continuity head still requires the same final gate before merge.

## Current project state

- GitHub `main` is the code/continuity source of truth; Linode is the sole active runtime target.
- M4 research platform is complete; M5 AI Strategy Factory is in progress.
- Historical USD-M acquisition/repair, causal feature materialization, allowlisted adapters, deterministic ablation orchestration and real feature-dataset workflow are implemented/merged through PR #35.
- PR #36 encrypted Demo credential persistence is pending final CI/merge.
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
- after PR #36 deploys, one real encrypted credential save followed by no-paste auto-connect;
- one active Fast Momentum paper position surviving service/server restart and later MARK/CLOSE;
- persist/recover or explicitly retire the older carry paper engine.

## Next exact task

1. Revalidate and squash-merge PR #36.
2. Implement a deterministic real-ablation CLI/workflow that takes the PR #35 feature `dataset_ref`, creates the PR #34 baseline/treatment batch in the M4 store/queue, and emits machine-readable batch/experiment IDs.
3. Run `eba-build-orderflow-features` on Linode for a real BTCUSDT USD-M development window outside frozen OOS.
4. Run the ablation experiments through M4 queue/worker/evidence/gates.
5. Compare/persist survivors for triage only; keep frozen OOS and live execution closed.
6. Verify the one-time encrypted Demo credential UX and remaining production smoke/restart proof in parallel.

## Notes for the next AI session

Read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, and this file before coding. Actual code/Git overrides stale text. Never request that the user paste an API secret into chat; credential entry belongs in the PWA only.
