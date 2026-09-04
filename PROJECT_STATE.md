# EBA Trader — Project State

_Last reconciled: 2026-09-04 (Asia/Ulaanbaatar)_

Actual merged code, exact-build production evidence and the latest explicit frozen decisions override stale prose. Query GitHub and production before editing.

## Current goal

Find genuinely repeatable net trading edge with deterministic, causal, cost-aware verification. Do not manufacture winners by weakening gates. Real-money execution remains locked.

## Canonical repository state

- Repository: `enkhbat194/EBA-Trader`.
- Linode/PWA: `https://eba-trader-172-236-150-62.sslip.io`.
- Current main after PR #142: `be778b2b760402aa2d9df9a00841731708f1b77e`.
- PR #140 merged the production next-D0 materializer.
- PR #141 merged the read-only next-D0 production progress proof.
- PR #142 merged sanitized read-only systemd telemetry for the next-D0 service; no mutation authority was added.
- Factory D1: **SEALED**.
- Frozen OOS: **SEALED**.
- Real-money execution: **LOCKED**.

## First Strategy Factory v2 D0 — immutable closed result

Campaign: `sfv2-discovery-pilot-v1` (`DISCOVERY_ONLY`).

- 406 candidates / 8 mechanism families;
- 12 D0 strata;
- 4,872 / 4,872 terminal trials;
- 406 complete candidates;
- 254 rejected candidates;
- 152 behaviorally eligible candidates;
- 127 behavioral clusters;
- frozen survivors: **0**.

The zero-survivor result is immutable. D1 did not open and no threshold was weakened.

Canonical postmortem: `docs/SFV2_D0_FAILURE_POSTMORTEM_2026-09-04.md`.
The postmortem concluded that the first factory was too parameter-centric, with strong 1m friction/turnover exposure; the next campaign therefore increases mechanism/horizon diversity rather than merely adding neighboring parameters.

There is still **no verified profitable strategy**.

## Next campaign — design, engines and catalog are frozen

Campaign: `sfv2-existing-data-low-turnover-v1`.
Design: `sfv2-next-existing-data-v1`.

Four implemented causal families:

1. `mtf_trend_pullback_v1`;
2. `breakout_retest_entry_v1`;
3. `path_efficiency_persistence_v1`;
4. `low_turnover_flow_persistence_v1`.

Causal multi-timeframe support is implemented from closed 1m data to 5m/15m/60m. Breakout-retetst cannot fill on the breakout bar; flow persistence structurally limits turnover with minimum-hold/cooldown rules.

Frozen catalog:

- 32 candidates per family;
- 128 total candidates;
- prior inspected search history: 406;
- cumulative search-history candidate count if this D0 is evaluated: 534;
- catalog SHA-256: `0aa793ca70ba8719486ba6edae314c77803e1b87884665d17ec88019ec71654a`;
- catalog authority: `CATALOG_FREEZE_ONLY`.

No performance was inspected during catalog freeze.

## Historical/protected data boundary

Protected evidence remains inaccessible to next-D0 discovery:

- 2025 first-cycle Frozen OOS;
- M5 Frozen OOS: `2026-08-15T00:00:00Z -> 2026-08-22T00:00:00Z`;
- SF4 prospective interval: `2026-09-01T00:00:00Z -> 2026-09-13T00:00:00Z`.

Previously inspected development data is not fresh confirmation evidence.

## Frozen next-D0 dataset plan

Authority: `D0_DATA_MATERIALIZATION_ONLY` / `D0_DISCOVERY_ONLY_NOT_CONFIRMATION`.

- Symbol/venue: BTCUSDT Binance USD-M Futures.
- Base interval: 1m.
- Order-flow source: Binance verified public `aggTrades` archive.
- Price bucket: 5.0.
- Dataset-plan SHA-256: `c3ae7735f657d905c2931613062fa9091c72dd9458d7cdfae678a01bcea26171`.
- 10 windows cover `2026-08-22T00:15:00Z` through exactly `2026-09-01T00:00:00Z`.
- The first window starts at 00:15 so its required prior closed-minute footprint is 00:14 and does not enter M5 Frozen OOS.
- The final window stops exactly at SF4 start and cannot consume SF4 data.

All 10 feature datasets must be materialized and verified before any performance evaluator is authorized.

## Production materialization architecture

PR #140 provides a local-only, one-window-per-invocation production materializer:

- systemd service: `eba-sfv2-next-d0-materialization.service`;
- production research root: `/var/lib/eba-trader/research/...`;
- shared checkout lock: `/run/lock/eba-trader-runtime-mutation.lock`;
- deploy and research cannot mutate/use the checkout concurrently;
- bounded service resources;
- no public HTTP/PWA mutation endpoint;
- source-code identity for the frozen builder contract is pinned across all receipts;
- status/receipts are written only after a full window successfully completes;
- final bundle SHA exists only after all 10 windows complete.

Every completed window receipt binds workflow ID, exact feature SHA-256, row count, candle provenance, order-flow acquisition/provenance and source-code identity.

PR #141 provides a read-only GitHub production proof. PR #142 adds sanitized read-only systemd state so `status_unavailable` can be distinguished from a running/failed/unloaded service without exposing mutation authority.

## Current empirical production state

Before PR #142, exact production build `1403b4ff0562f0b33a6892a6de848e2c9515d9f5` was production-verified, but the next-D0 endpoint still reported `status_unavailable` and exposed 0/10 completed receipts. Because status is written only after a full window completes, that evidence did **not** establish whether the first window was running or whether the service had failed.

PR #142 is merged. Its exact-main production proof must be treated as the next authority for the operational state; do not infer materialization completion from merged code alone.

Classification at this checkpoint:

- materializer code: **CODE READY**;
- previous exact production build: **PRODUCTION VERIFIED**;
- 10-window next-D0 corpus: **NOT YET VERIFIED COMPLETE**;
- strategy evaluation: **NOT OPENED**;
- verified profitable strategy: **NONE**.

## Required next sequence

1. Obtain exact production proof for current main and read sanitized service/materialization state.
2. If service failed, diagnose/fix only the operational cause; do not open evaluation or weaken the frozen research contract.
3. Continue one-window-at-a-time materialization until all 10 receipts are present and validated.
4. Freeze one immutable dataset receipt containing dataset-plan SHA, frozen catalog SHA, all 10 feature SHA-256 values, workflow IDs, row counts, provenance and source-code SHA.
5. Only after that receipt is complete/frozen may a separate explicit 128-candidate D0 evaluator authorization package be created.
6. Freeze D0 selection rules before seeing performance if they are not already frozen.
7. Evaluate the 128 frozen candidates on the frozen 10-window D0 corpus.
8. D0 survivors are discovery only; survivor count 0 remains acceptable.

## SF4 independent prospective track

Frozen replication hypotheses remain independent of Factory D0. The protected interval is `2026-09-01T00:00:00Z -> 2026-09-13T00:00:00Z`; evaluation is prohibited before `2026-09-13T00:00:00Z`. Do not inspect SF4 performance, retune parameters or pool SF3 evidence into SF4 qualification before the time gate.

## Non-negotiable research locks

- profitability/expectancy/sample/statistical gates are not lowered;
- fees and slippage remain included;
- causality/no-lookahead is mandatory;
- inspected data is never relabelled fresh;
- Demo is execution plumbing, not verification;
- discovery ranking is not promotion authority;
- D1 remains closed until a frozen non-empty survivor set exists;
- Frozen OOS remains sealed until prerequisites pass;
- deterministic risk keeps veto authority;
- real execution remains locked.

## Continuity protocol

New sessions read `AGENTS.md`, this file, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, `SESSION_HANDOFF.md`, `BACKTEST_PROTOCOL.md`, `STRATEGY_SPEC.md` and the current SFv2 design/result documents, then query actual GitHub/production state before editing.
