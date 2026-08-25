# EBA Trader — Session Handoff

_Last handoff prepared: 2026-08-26 (Asia/Ulaanbaatar)_

## What was completed

- Restored project state from repository continuity before work.
- PR #31 is merged at `5443f19e93a1d1cf7f305bb212d7e744c680bba4`: same-dataset candle-only/order-flow backtest adapters and ablation invariants.
- PR #32 is merged at `931b8a7dff68c659f2fa21d4fea33c87053c5022`: read-only Research / AI Lab PWA dashboard.
- Manual production proof established that Linode consumed `main` through `050cd9be203a09aca95a152d7102fa280c397ee7`, nginx/Let's Encrypt HTTPS was bootstrapped, and the public PWA opened from an external iPhone at `https://eba-trader-172-236-150-62.sslip.io/`.
- Home, Scan and Settings were observed showing server-backed Binance Demo / Fast Paper state.
- Clarified that Home `Current opportunity` was carry/arbitrage-only, not Fast Momentum signal count.
- PR #33 is merged at `2b62f056f438c38865694d2f0aa130480926e7b2`.
- PR #33 relabels Home metrics to `Carry opportunity` / `Carry expected net` and adds a read-only Fast Momentum heartbeat using `/api/runner/status`.
- Heartbeat shows LIVE/STALE/OFF, current decision, last server scan, next expected scan and interval; PWA cache is `eba-trader-ui-v14`, app release `0.12.1 / LINODE-M6`.
- PR #33 final head passed Continuity guard, Linode runtime checks and Linode production bundle before merge.

## Current project state

- GitHub `main` is the code/continuity source of truth; Linode is the sole active runtime target.
- M4 research platform is complete.
- M5 AI Strategy Factory is in progress.
- Historical USD-M aggregate-trade acquisition, repair, footprint windows, causal candle alignment and aligned feature-dataset materialization are implemented.
- Candle-only and candle+delta/CVD M4 adapters are merged and tested.
- Research / AI Lab and scanner heartbeat are merged and read-only.
- Real Binance order submission remains locked.
- Frozen OOS automation remains locked pending lifecycle-order reconciliation.

## Production proof status

Confirmed manually on 2026-08-26:

- latest-main lineage through `050cd9be...` was present on Linode;
- nginx/Certbot HTTPS bootstrap succeeded;
- external iPhone opened the public PWA;
- Home, Scan and Settings showed live server-backed state;
- Binance Demo connection and Fast Paper scanner operation were visible.

Still pending:

- full Chart / Positions / History / Research / trade-detail smoke pass;
- one active Fast Momentum paper position surviving service/server restart and then continuing through MARK/CLOSE;
- decision to persist/recover or explicitly retire the older carry paper engine.

## Important decisions

- Repository state is the cross-chat shared memory bridge; actual code/Git overrides stale chat memory.
- Footprint/order flow remains experimental and must beat candle-only controls under identical assumptions.
- Candle and order-flow ablation arms share dataset identity, EMA parameters, execution assumptions, fees and slippage.
- Gapped order-flow data fails closed.
- Development ranking has no OOS/execution promotion authority.
- Research / AI Lab and scanner heartbeat are read-only observability.

## Next exact task

1. Implement the deterministic M5 ablation orchestrator: paired `ema_feature_baseline_v1` vs `ema_orderflow_v1` experiments with identical dataset identity, EMA parameters, capital, fees, slippage and execution assumptions.
2. Add the real historical BTCUSDT USD-M development feature-dataset CLI/workflow.
3. Run controlled development ablations through the M4 queue/worker/evidence/gate path.
4. Compare/persist survivors for triage only; keep frozen OOS closed.
5. In parallel, finish the remaining production smoke and active-position restart/recovery proof.

## Notes for the next AI session

Start with `AGENTS.md`, then `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, and this file. Inspect recent Git history and relevant code before making changes. If text is stale, repair it from repository reality first.
