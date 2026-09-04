# EBA Trader — Session Handoff

_Last handoff prepared: 2026-09-04 (Asia/Ulaanbaatar)_

## Startup rule

Repository: `enkhbat194/EBA-Trader`.

Before editing, query current `main`, recent/open PRs, exact production workflows and the continuity docs. Merged code + exact production evidence + latest explicit frozen decisions override stale prose.

## Current main checkpoint

PR #142 merged at:

`be778b2b760402aa2d9df9a00841731708f1b77e`

Recent sequence:

- #140 — production local-only next-D0 materializer + shared checkout lock;
- #141 — read-only next-D0 production progress proof;
- #142 — sanitized read-only systemd telemetry for the materializer service.

PR #142 changed observability only. It did not alter the frozen dataset plan, catalog, builder contract, evaluation gates, D1/OOS/SF4 locks or execution authority.

## Immutable first Strategy Factory v2 D0 result

Campaign `sfv2-discovery-pilot-v1`:

- 406 candidates / 8 families;
- 12 strata;
- 4,872 / 4,872 terminal trials;
- 406 complete;
- 254 rejected;
- 152 behaviorally eligible;
- 127 behavioral clusters;
- frozen survivors: **0**.

D1 did not open. Frozen OOS did not open. No winner was manufactured by threshold changes.

Canonical postmortem: `docs/SFV2_D0_FAILURE_POSTMORTEM_2026-09-04.md`.
The main takeaway is that the first factory was parameter-centric and heavily exposed to 1m friction/turnover; the next campaign therefore expands mechanism/horizon diversity, not neighboring parameter count.

## Frozen next campaign

Campaign: `sfv2-existing-data-low-turnover-v1`.
Design: `sfv2-next-existing-data-v1`.

Implemented causal families:

1. `mtf_trend_pullback_v1`;
2. `breakout_retest_entry_v1`;
3. `path_efficiency_persistence_v1`;
4. `low_turnover_flow_persistence_v1`.

Causal 1m -> 5m/15m/60m aggregation is implemented. Breakout requires a later fully closed retest rather than breakout-bar fill. Flow persistence uses minimum hold/cooldown to limit turnover structurally.

Frozen catalog:

- 32 candidates/family;
- 128 total;
- prior inspected count 406;
- cumulative search-history count on evaluation 534;
- SHA-256 `0aa793ca70ba8719486ba6edae314c77803e1b87884665d17ec88019ec71654a`;
- authority `CATALOG_FREEZE_ONLY`.

No performance was inspected during catalog freeze.

## Frozen next-D0 data plan

Authority: `D0_DATA_MATERIALIZATION_ONLY` and `D0_DISCOVERY_ONLY_NOT_CONFIRMATION`.

- BTCUSDT Binance USD-M Futures;
- 1m base interval;
- verified public Binance `aggTrades` archive;
- price bucket 5.0;
- plan SHA-256 `c3ae7735f657d905c2931613062fa9091c72dd9458d7cdfae678a01bcea26171`;
- 10 windows from `2026-08-22T00:15:00Z` to exactly `2026-09-01T00:00:00Z`.

Protected ranges remain sealed:

- 2025 first-cycle Frozen OOS;
- M5 Frozen OOS `2026-08-15T00:00:00Z -> 2026-08-22T00:00:00Z`;
- SF4 prospective `2026-09-01T00:00:00Z -> 2026-09-13T00:00:00Z`.

The first window intentionally starts at 00:15 so its prior required closed-minute footprint is 00:14 and does not enter M5 Frozen OOS. The last window ends exactly at SF4 start.

## Production materializer contract

PR #140 provides `eba-sfv2-next-d0-materialization.service`:

- local/root-side only; no public mutation endpoint;
- exactly one window per invocation;
- shared `/run/lock/eba-trader-runtime-mutation.lock` with deployment;
- bounded CPU/memory/time;
- research writes stay under `/var/lib/eba-trader/research/...`;
- source identity for the frozen builder contract is pinned across receipts;
- status is written only after a complete window succeeds;
- final dataset bundle SHA appears only after all 10 windows complete.

Each receipt binds exact feature SHA-256, row count, workflow ID, candle provenance, order-flow provenance/acquisition and source-code identity.

PR #141 proves progress read-only through production HTTP. PR #142 additionally exposes sanitized systemd state so missing status can be classified as service running/failed/unloaded without granting mutation authority.

## Last empirical production evidence

Public production smoke run `33889836392` verified exact build `be778b2b760402aa2d9df9a00841731708f1b77e` deployed on production and reported healthy chart/demo-vault/positions/research public surfaces.

The dedicated next-D0 proof run `33889836345` remains the authority for the materializer service and receipt sequence. At this handoff checkpoint it has not yet produced a terminal result, so no next-D0 window is marked complete from deployment alone.

Before #142, exact production build `1403b4ff0562f0b33a6892a6de848e2c9515d9f5` exposed `status_unavailable`, 0/10 receipts. Because status is created only after a whole window finishes, that old evidence did not distinguish a running first build from service failure.

Current classification:

- next-D0 materializer: **CODE READY**;
- exact current main deployment: **PRODUCTION VERIFIED**;
- all 10 D0 datasets: **NOT YET VERIFIED COMPLETE**;
- 128-candidate performance evaluation: **NOT AUTHORIZED**;
- verified profitable strategy: **NONE**.

## What was completed

- Audited actual GitHub current state instead of trusting the stale prompt SHA.
- Confirmed PRs #140 and #141 had already advanced beyond the supplied handoff.
- Verified the production materializer/shared checkout lock/read-only proof contracts.
- Added PR #142 sanitized service telemetry without modifying frozen builder/catalog/data-plan identities.
- Passed #142 exact-head CI and merged it to main `be778b2b760402aa2d9df9a00841731708f1b77e`.
- Public smoke run `33889836392` verified that exact main deployed successfully.
- Reconciled `PROJECT_STATE.md`, `SESSION_HANDOFF.md`, `TODO.md` and added `docs/SFV2_NEXT_D0_PRODUCTION_MATERIALIZATION_2026-09-04.md` on PR #143.
- No performance result was inspected; no threshold or scientific gate was changed.

## Next exact task

1. Read terminal dedicated production proof run `33889836345` and inspect `serviceState`, receipt availability, completed-window count, next window, bundle/source identities and all safety flags.
2. If service failed, repair only the operational cause while preserving frozen builder/catalog/data-plan identities and all downstream locks.
3. If the service is running or receipts have advanced, continue the existing one-window materialization path until 10/10 validated receipts exist.
4. Freeze one immutable complete dataset receipt containing dataset-plan SHA, catalog SHA, all ten feature SHA values, workflow IDs, row counts, provenance and frozen source-code identity.
5. Only after that freeze may a separate 128-candidate D0 evaluator authorization package be created.

## Exact continuation sequence

- Do not infer a completed window from a deployed build.
- Do not inspect strategy performance before dataset receipt freeze and explicit evaluator authorization.
- Freeze D0 selection rules before any performance results if not already frozen.
- Evaluate exactly the frozen 128 candidates only after authorization.
- Treat D0 survivors as discovery only; zero survivors remains acceptable.

## SF4 track remains independent

Do not inspect or evaluate protected SF4 performance before `2026-09-13T00:00:00Z`. Do not retune the frozen replication hypotheses and do not pool SF3 evidence into SF4 qualification.

## Hard locks

- profitability/expectancy/sample/statistical gates: unchanged;
- fees/slippage: mandatory;
- no-lookahead/causal execution: mandatory;
- inspected data cannot become fresh confirmation;
- D1: sealed until a frozen non-empty survivor set exists;
- Frozen OOS: sealed;
- Demo: execution plumbing only;
- real Binance execution: locked;
- deterministic risk: veto authority.

## Files to read on continuation

`AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, this file, `BACKTEST_PROTOCOL.md`, `STRATEGY_SPEC.md`, `docs/SFV2_NEXT_D0_PRODUCTION_MATERIALIZATION_2026-09-04.md`, the current SFv2 design/result documents, then actual GitHub/production state.
