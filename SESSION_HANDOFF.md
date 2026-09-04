# EBA Trader — Session Handoff

_Last handoff prepared: 2026-09-04 (Asia/Ulaanbaatar)_

## Exact continuation point

Repository: `enkhbat194/EBA-Trader`.

Always query actual GitHub `main`, open PRs and production workflows before editing because the hourly automation may advance state between sessions.

The exact production build that verified the completed first Strategy Factory v2 D0 failure postmortem is:

`b822a9815f8f5cc42c674f849e5626d8b7022602`

Production postmortem proof:

- workflow: `Strategy Factory v2 D0 failure postmortem proof`;
- Actions run: `33823539570`;
- proof job: `100871190923`;
- conclusion: `success`;
- completed approximately `2026-09-04T01:02:54Z`.

## Immutable first D0 result

Campaign: `sfv2-discovery-pilot-v1`.

- authority: `DISCOVERY_ONLY`;
- candidates: 406;
- families: 8;
- strata: 12;
- terminal trials: 4,872 / 4,872;
- complete candidates: 406;
- rejected candidates: 254;
- behaviorally eligible candidates: 152;
- behavioral clusters: 127;
- frozen survivor count: **0**;
- D1 opened: false;
- Frozen OOS opened: false;
- live execution allowed: false;
- real execution allowed: false.

This zero-survivor result is immutable. Do not fill the old unused 94 slots, weaken thresholds or reinterpret a diagnostic proxy as a winner.

## Package 1 postmortem result

Canonical document: `docs/SFV2_D0_FAILURE_POSTMORTEM_2026-09-04.md`.

The production postmortem is read-only and used the exact closed ledger. It did not rerun the campaign.

Global failure flags:

- non-positive net return: 152 / 152 complete non-rejected candidates;
- non-positive expectancy: 152 / 152;
- non-positive benchmark-relative return: 152 / 152;
- cost-sensitive diagnostic proxy: 107;
- rejected/incomplete candidates: 254.

Family diagnoses:

- 6 × `COST_SENSITIVE_PROXY`;
- 2 × `INACTIVE_OR_REJECTED`.

Important family findings:

- ATR trailing: ~+5.26 bps mean pre-entry chase; active but negative.
- Donchian breakout: ~+7.63 bps mean pre-entry chase; active but negative.
- Mean reversion: ~-5.79 bps favorable pre-entry move but still negative, so timing is not the main failure.
- Order-flow delta impulse: 20,227 trades across complete candidates; turnover/cost is structural.
- Rolling flow trend: partial inactivity + negative economics; delay small.
- Compression-expansion and volume-shock: primarily inactive/rejected under frozen rules.
- VWAP reversion flow: only 2 complete candidates, both negative.

Across all matched trades the mean one-bar pre-entry move was only +0.09237 bps, so delay is not a global campaign explanation.

`cost_sensitive_proxy` is only an attribution diagnostic. It is not a zero-fee/slippage rerun and does not establish gross or net profitable edge.

There is still **no verified profitable strategy**.

## Package 2 design — frozen as DESIGN_ONLY

Canonical design document: `docs/SFV2_NEXT_CAMPAIGN_DESIGN_2026-09-04.md`.
Config: `config/sfv2_next_campaign_design_v1.json`.
Validator: `src/eba_trader/strategy_factory_v2_next_design.py`.

Design ID: `sfv2-next-existing-data-v1`.
Reserved campaign ID: `sfv2-existing-data-low-turnover-v1`.

Preliminary caps:

- raw candidates: 128;
- per family: 32;
- survivors: 12;
- prior inspected candidates retained in search history: 406.

Four mechanism slots:

1. `mtf_trend_pullback_v1`;
2. `breakout_retest_entry_v1`;
3. `path_efficiency_persistence_v1`;
4. `low_turnover_flow_persistence_v1`.

The design explicitly excludes neighboring parameter extensions of all eight failed first-pilot families.

## Data/engine audit

Historical causal planes already supported:

- Binance USD-M candle/price/volume;
- executed aggregate-trade order flow;
- footprint-derived executed-flow features.

Not currently approved as historical Strategy Factory planes:

- funding history;
- open-interest history;
- basis/premium history;
- resting order-book history.

`m18_fee_aware.py` has point-in-time spot/futures book + commission/carry estimates but is not a historical research corpus.

`momentum_engine.py` is a 1m/5m paper-only engineering prototype and is not verified profitability evidence or an approved next-campaign family by itself.

## Current Package 2 implementation gates

No performance evaluation is authorized yet. Before the reserved campaign can run:

1. implement the four causal family engines/adapters;
2. implement closed 1m -> causal 5m/15m/60m aggregation;
3. implement explicit family-specific order availability and causal retest/limit fill semantics where used;
4. inventory every inspected/protected historical time range;
5. freeze an exact slower-horizon D0 dataset/window contract with no SF4/Frozen-OOS leakage;
6. freeze exact deterministic <=128 catalog + seed;
7. add no-lookahead, fill, cooldown/turnover and search-accounting tests;
8. merge exact-head CI green;
9. only then consider a separate explicit D0 evaluation authorization.

## SF4 remains independent and time-gated

Exact frozen hypotheses:

- `s3_vsm_s150`;
- `s3_cex_s075`.

Prospective interval:

`2026-09-01T00:00:00Z` through `2026-09-13T00:00:00Z`.

Do not inspect/evaluate/retune SF4 before `2026-09-13T00:00:00Z`. SF3 evidence cannot be pooled into SF4 qualification. The conservative 48-test search burden remains carried forward.

## Hard locks

- verified profitable strategy: none;
- next-campaign design authority: DESIGN_ONLY;
- next D0 evaluation: not authorized;
- Factory D1: sealed;
- M5/D3 Frozen OOS: sealed;
- SF4 pre-unlock evaluation: prohibited;
- Demo promotion authority: false;
- real Binance execution: locked;
- deterministic risk keeps veto authority.

## What was completed

- PR #133 closed the first D0 zero-survivor campaign and continuity state.
- PR #134 added the read-only family/cost/delay/regime failure decomposition and production proof.
- Production postmortem proof run `33823539570` succeeded on exact build `b822a9815f8f5cc42c674f849e5626d8b7022602`.
- Package 1 is empirically closed with no winner.
- Package 2 data/engine audit and DESIGN_ONLY next-campaign boundary were created with smaller 128/32/12 caps and four lower-turnover mechanism slots.
- A fail-closed config validator and tests prevent the design package from silently opening evaluation, unavailable data planes, SF4, D1, Frozen OOS or execution authority.

## Next exact task

After the Package 1 closeout + Package 2 design PR is exact-head CI green and merged, implement the four next-campaign causal family engines and multi-timeframe aggregation **without running performance evaluation**. In parallel, inventory historical data usage so the slower-horizon D0 window can be frozen without touching SF4 or Frozen OOS.

## Immediate continuation tasks

1. Query actual main/open PR state before doing anything else.
2. Merge the current closeout/design package only after exact-head CI is green.
3. Implement `mtf_trend_pullback_v1`, `breakout_retest_entry_v1`, `path_efficiency_persistence_v1`, and `low_turnover_flow_persistence_v1` as causal adapters.
4. Add causal 5m/15m/60m aggregation and family-specific order/fill availability rules.
5. Inventory all inspected/protected research windows before freezing the next D0 dataset.
6. Keep evaluation disabled until exact dataset + exact catalog freezes are separately merged and authorized.
7. Keep SF4/D1/Frozen OOS/live/real locks unchanged.

## Startup rule

Read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, this file, `BACKTEST_PROTOCOL.md`, `docs/CONTINUITY_PROTOCOL.md`, `docs/STRATEGY_FACTORY_V2_DESIGN.md`, `docs/SFV2_D0_PRODUCTION_RESULT_2026-09-03.md`, `docs/SFV2_D0_FAILURE_POSTMORTEM_2026-09-04.md` and `docs/SFV2_NEXT_CAMPAIGN_DESIGN_2026-09-04.md`; then query actual GitHub/production state before editing.
