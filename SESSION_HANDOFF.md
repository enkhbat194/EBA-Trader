# EBA Trader — Session Handoff

_Last handoff prepared: 2026-08-26 (Asia/Ulaanbaatar)_

## What was completed

- Restored project state from the repository continuity system before coding.
- Completed PR #31 and merged it to `main` at `5443f19e93a1d1cf7f305bb212d7e744c680bba4`.
- PR #31 added causal feature-dataset materialization plus `ema_feature_baseline_v1` and `ema_orderflow_v1` allowlisted M4 backtest adapters.
- The two ablation arms consume the exact same aligned feature dataset and share EMA exits, next-bar execution, fees and slippage.
- Tests prove a permissive order-flow gate reproduces the candle-only metrics and negative delta/CVD gates suppress otherwise valid entries.
- Fixed pre-existing annualized-return overflow on very short/high-return synthetic windows and made non-finite evidence metrics JSON-safe.
- Completed PR #32 and squash-merged it to `main` at `931b8a7dff68c659f2fa21d4fea33c87053c5022`.
- Added read-only `/api/research/status`, backed by repository continuity plus optional read-only M4 research SQLite counts.
- Added a seventh PWA `Research` tab showing M5 focus/progress, data-plane readiness, ablation adapters/features, experiment/lifecycle counts and explicit safety locks.
- Bumped PWA cache to `eba-trader-ui-v13` and added backend/UI contract tests.
- PR #32 final head passed full regression, Ruff, shell/deployment, Linode runtime and Continuity guard checks before merge.

## Current project state

- GitHub `main` remains the code and continuity source of truth.
- Linode remains the sole active backend/runtime target.
- M4 research platform is complete.
- M5 AI Strategy Factory is in progress.
- Historical Binance USD-M aggregate-trade acquisition, gap repair, footprint windows, causal candle alignment and aligned feature-dataset materialization are implemented.
- Candle-only and candle+delta/CVD ablation adapters are merged and tested.
- Research / AI Lab is merged and read-only; it has no lifecycle, risk, OOS-unlock or execution authority.
- Real Binance order submission remains locked.
- Frozen OOS automation remains locked pending lifecycle-order reconciliation.

## Problems / blockers

### Lifecycle order

`src/eba_trader/lifecycle.py` currently enforces:

`GENERATED -> BACKTESTED -> OOS_VERIFIED -> ROBUSTNESS_VERIFIED -> ...`

Desired methodology conceptually wants robustness before frozen OOS. Do not bypass the code. Resolve with an explicit lifecycle migration and tests before automated OOS orchestration.

### External production proof

Still not proven by repository CI:

- latest `main` actually consumed by Linode;
- external-phone HTTPS availability;
- real service/server restart recovery of an active Fast Momentum paper position through later MARK/CLOSE;
- final disposition of the older carry paper engine.

## Important decisions made

- Repository state is the cross-chat shared memory bridge.
- Actual code/config/tests + Git history override stale chat memory.
- M5 uses constrained strategy DSL/schema rather than arbitrary generated Python.
- Footprint/order flow remains an experimentally validated feature family, not assumed edge.
- Gapped historical order-flow data fails closed.
- Candle-only and order-flow ablation arms must share dataset/execution/cost assumptions.
- Cheap screening/ranking has no OOS/execution promotion authority.
- Research / AI Lab is read-only observability and may show an absent local research DB without fabricating experiment counts.

## Next exact task

1. Implement a deterministic ablation orchestrator that emits paired candle-only vs candle+delta/CVD experiments with identical dataset identity, EMA parameters, fees and slippage.
2. Add a CLI/workflow to materialize a real historical BTCUSDT USD-M development feature dataset from candle CSV + verified order-flow/acquisition manifests.
3. Run controlled development ablations through the M4 worker/evidence/gate path.
4. Surface real experiment counts/results automatically in Research / AI Lab when a research DB is present on the runtime used for research.
5. Keep frozen OOS and real execution locked.
6. In parallel, complete the external Linode HTTPS + restart/recovery proof.

## Notes for the next AI session

Start with `AGENTS.md`, then `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, and this file. Inspect recent Git history and the actual modules relevant to the next task before coding. If any text here is stale, repair it from repository reality first.
