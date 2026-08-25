# EBA Trader — Session Handoff

_Last handoff prepared: 2026-08-26 (Asia/Ulaanbaatar)_

## What was completed

- Restored project state from repository continuity before work.
- PR #33 merged at `2b62f056f438c38865694d2f0aa130480926e7b2`: Home carry metrics are explicit and Fast Momentum now has read-only LIVE/STALE/OFF heartbeat, decision, last scan, next expected scan and interval.
- Manual production proof remains recorded: Linode consumed `main` through `050cd9be...`, nginx/Let's Encrypt HTTPS was bootstrapped, and the PWA opened externally on iPhone at `https://eba-trader-172-236-150-62.sslip.io/`.
- Implemented PR #34 deterministic M5 order-flow ablation orchestration in `src/eba_trader/m5_ablation.py`.
- The orchestrator registers immutable candle-control and order-flow-treatment strategy specs with identical dataset, EMA, capital, fee, slippage and trade-start assumptions.
- It emits one deduplicated baseline plus up to 64 deterministic delta/CVD treatment variants, maps every treatment to the control, rejects duplicate/empty/non-finite gates and is invariant to input gate ordering.
- The stage is fixed to `m5_orderflow_ablation_dev`; there is no OOS switch or lifecycle-promotion authority.
- Added tests for deterministic replay/idempotency, shared assumptions, gate-order invariance, dataset/cost identity changes, bounded fan-out and fail-closed validation.
- PR #34 core implementation head passed Continuity guard, Linode runtime checks and Linode production bundle. Continuity-updated final head requires revalidation before merge.

## Current project state

- GitHub `main` is the source of truth; Linode is the sole active runtime target.
- M4 research platform is complete; M5 AI Strategy Factory is in progress.
- Acquisition, gap repair, causal alignment, feature-dataset materialization and allowlisted candle/order-flow adapters are merged.
- Deterministic ablation orchestration is implemented in PR #34 pending final CI/merge.
- Research / AI Lab and scanner heartbeat are read-only.
- Real execution and automated frozen OOS remain locked.

## Production proof still pending

- Full Chart / Positions / History / Research / trade-detail smoke pass.
- One active Fast Momentum paper position surviving service/server restart and later MARK/CLOSE.
- Persist/recover or explicitly retire the older carry paper engine.

## Next exact task

1. Revalidate and merge PR #34.
2. Add a CLI/workflow to materialize a real BTCUSDT USD-M development feature dataset from candle CSV + verified order-flow/acquisition manifests.
3. Run the deterministic ablation batch through M4 queue/worker/evidence/gates.
4. Compare/persist survivors for triage only; keep frozen OOS closed.
5. Continue remaining production smoke/restart proof in parallel.

## Notes for the next AI session

Read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, and this file before coding. Actual code/Git overrides stale text.
