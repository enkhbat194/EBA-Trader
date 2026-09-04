# EBA Trader — Project State

_Last reconciled: 2026-09-04 (Asia/Ulaanbaatar)_

Actual merged code, exact-build production evidence and the latest explicit decision/config documents override stale prose. Query GitHub/production before editing.

## Current goal

Build a research-first autonomous trading system that discovers repeatable net edges while keeping broad discovery, hidden confirmation, robustness, Frozen OOS and execution as separate authorities. Real-money execution remains locked.

The first Strategy Factory v2 D0 campaign and its production failure postmortem are now complete. The active focus is **Package 2: implement a smaller, lower-turnover, genuinely new next-campaign design without reusing failed-family parameter neighborhoods**.

## Canonical repository/runtime state

- Repository: `enkhbat194/EBA-Trader`.
- Production URL: `https://eba-trader-172-236-150-62.sslip.io`.
- Exact build that production-verified the Package 1 postmortem: `b822a9815f8f5cc42c674f849e5626d8b7022602`.
- Postmortem production proof: workflow `Strategy Factory v2 D0 failure postmortem proof`, run `33823539570`, job `100871190923`, conclusion `success`.
- Factory v2 D1 hidden confirmation: **SEALED**.
- M5/D3 Frozen OOS: **SEALED / NOT OPENED**.
- Real-money execution: **LOCKED**.

## First Strategy Factory v2 D0 — immutable result

Campaign: `sfv2-discovery-pilot-v1`.
Authority: `DISCOVERY_ONLY`.

- candidates: 406;
- families: 8;
- D0 strata: 12;
- terminal trials: 4,872 / 4,872;
- complete candidates: 406;
- rejected candidates: 254;
- behaviorally eligible candidates: 152;
- behavioral clusters: 127;
- frozen survivors: **0**;
- D1 opened: false;
- Frozen OOS opened: false;
- live/real execution allowed: false.

The zero-survivor selection is immutable. The unused 94 slots below the old 500 cap are not a quota or post-hoc retuning budget.

## Package 1 production postmortem — complete

Canonical result: `docs/SFV2_D0_FAILURE_POSTMORTEM_2026-09-04.md`.

The postmortem read the existing immutable 4,872-trial ledger only; it did not rerun or rewrite D0.

Global evidence:

- 152 / 152 complete non-rejected candidates had non-positive net return;
- 152 / 152 had non-positive expectancy;
- 152 / 152 had non-positive benchmark-relative return;
- 107 were `cost_sensitive_proxy` diagnostics;
- 254 were rejected/incomplete;
- family diagnosis: 6 `COST_SENSITIVE_PROXY`, 2 `INACTIVE_OR_REJECTED`;
- fixed round-trip friction: 11 bps;
- global one-bar pre-entry move: +0.09237 bps mean across 33,444 matched trades, so one-bar delay is not a global explanation.

Mechanism-specific findings:

- `atr_trailing_v1`: active but negative; ~+5.26 bps average next-open chase.
- `donchian_breakout_v1`: active but negative; ~+7.63 bps average next-open chase.
- `mean_reversion_z_v1`: negative despite ~-5.79 bps favorable pre-entry movement; timing alone cannot rescue it.
- `orderflow_delta_impulse_v1`: 20,227 trades across complete candidates; structural turnover/cost failure, not delay failure.
- `rolling_flow_trend_v1`: partial inactivity plus negative economics; delay small.
- `compression_expansion_v1` and `volume_shock_momentum_v1`: primarily inactive/rejected under frozen rules.
- `vwap_reversion_flow_v1`: mostly inactive and the two complete candidates remained negative.

`cost_sensitive_proxy` adds recorded cost attribution back to net return as a diagnostic only. It is not a zero-cost counterfactual simulation and is not profitability evidence.

There is still **no verified profitable strategy**.

## Package 2 — next-campaign design

Canonical design: `docs/SFV2_NEXT_CAMPAIGN_DESIGN_2026-09-04.md`.
Config: `config/sfv2_next_campaign_design_v1.json`.
Validator: `src/eba_trader/strategy_factory_v2_next_design.py`.

Design ID: `sfv2-next-existing-data-v1`.
Reserved future campaign ID: `sfv2-existing-data-low-turnover-v1`.
Authority: `DESIGN_ONLY`.
Evaluation enabled: false.

Preliminary hard caps:

- raw candidates: 128;
- candidates per family: 32;
- survivors: 12;
- prior inspected candidates retained in search history: 406.

Four frozen mechanism slots:

1. `mtf_trend_pullback_v1` — slower directional regime + pullback entry;
2. `breakout_retest_entry_v1` — causal break then retest rather than immediate breakout chase;
3. `path_efficiency_persistence_v1` — direction relative to path/noise efficiency;
4. `low_turnover_flow_persistence_v1` — sustained executed-flow state with cooldown/minimum hold.

These are design slots, not evaluated strategies. Exact engine definitions, dataset window and deterministic candidate specifications still must be frozen before any performance inspection.

## Data-plane audit

Historical causal planes currently supported for this design:

- Binance USD-M candles / price / volume;
- executed aggregate-trade order flow;
- footprint-derived executed-flow features.

Present runtime/prototype capability does not equal a historical research corpus:

- `m18_fee_aware.py` has current spot/futures book + commission/carry snapshot logic, but no approved historical basis/funding/order-book dataset.
- `momentum_engine.py` is a 1m/5m paper-only engineering prototype and explicitly not a validated edge.

The current next-campaign design therefore marks historical funding, open interest, basis and resting-order-book planes unavailable. Those require a separate acquisition/provenance package before they can enter a later campaign.

## Package 2 implementation gates

Before any next-campaign D0 evaluation:

1. implement the four causal family engines/adapters;
2. implement causal 5m/15m/60m aggregation from fully closed 1m data;
3. implement explicit signal/order availability and causal retest/limit fill semantics where used;
4. inventory all inspected/protected time ranges and freeze a permissible slower-horizon D0 dataset contract;
5. freeze a deterministic <=128 candidate catalog and seed;
6. prove no-lookahead, cooldown/turnover and search-accounting invariants in tests;
7. merge exact-head CI green;
8. only then consider a separate explicit D0 evaluation authorization.

## SF4 prospective replication

Exact hypotheses remain frozen:

- `s3_vsm_s150`;
- `s3_cex_s075`.

Prospective interval: `2026-09-01T00:00:00Z` through `2026-09-13T00:00:00Z`.

Evaluation remains fail-closed before `2026-09-13T00:00:00Z`. Parameters cannot be retuned and SF3 evidence cannot be pooled. Package 2 cannot inspect SF4 prospective evidence.

## Validation

- First D0 campaign exact production proof succeeded with all 4,872 trials terminal and 0 survivors.
- Package 1 postmortem production proof run `33823539570` succeeded on exact build `b822a9815f8f5cc42c674f849e5626d8b7022602`.
- PR #134 passed full regression, Ruff, shell/deployment contract, runtime, continuity and hygiene before merge.
- Package 2 design has no evaluation authority and its validator fails closed if search-history, unavailable-data, SF4/D1/OOS or execution locks are weakened.

## Safety invariants

- Discovery ranking and diagnostic proxies are not promotion authority.
- Reused/inspected D0 cannot become fresh confirmation evidence.
- Full search history, including the prior 406 candidates, remains accounted for.
- No failed family may be rescued by lowering gates or padding neighboring parameters after seeing results.
- Robustness precedes Frozen OOS.
- Demo is execution-plumbing evidence only.
- Deterministic risk keeps veto authority.
- Spot and USD-M futures data are never silently mixed.
- SF4 prospective evidence remains protected by its time gate.
- Real Binance execution remains disabled.

## Next exact tasks

1. Merge the Package 1 closeout + Package 2 design package after exact-head CI is green.
2. Implement the four design-only family engines and causal multi-timeframe aggregation.
3. Inventory historical dataset usage/protected ranges before freezing the next D0 window.
4. Freeze exact <=128 deterministic catalog only after engine/data contracts are ready.
5. Do not run performance evaluation until a separate authorization exists.

## Continuity protocol

New sessions read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, `SESSION_HANDOFF.md`, `BACKTEST_PROTOCOL.md`, `docs/CONTINUITY_PROTOCOL.md`, `docs/STRATEGY_FACTORY_V2_DESIGN.md`, `docs/SFV2_D0_PRODUCTION_RESULT_2026-09-03.md`, `docs/SFV2_D0_FAILURE_POSTMORTEM_2026-09-04.md` and `docs/SFV2_NEXT_CAMPAIGN_DESIGN_2026-09-04.md`, then query actual GitHub/production state before editing.
