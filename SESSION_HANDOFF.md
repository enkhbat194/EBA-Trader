# EBA Trader — Session Handoff

_Last handoff prepared: 2026-09-03 (Asia/Ulaanbaatar)_

## Exact continuation point

Repository: `enkhbat194/EBA-Trader`.

Always query actual GitHub `main`, production workflows and open PRs before editing.

Exact code/build that completed the first Strategy Factory v2 D0 production campaign:

`bdb84a4a926dac53d13116364e8315e98b35e6e1`

Official campaign proof:

- workflow: `Strategy Factory v2 D0 production campaign proof`;
- Actions run: `33674168891` (run #3);
- conclusion: `success`;
- completed at approximately `2026-09-02T19:46:40Z`.

PR #132 fixed the final production trigger blocker: `auto_update_entrypoint.sh` incorrectly required executable permission on `run_sfv2_d0_authorized_production.sh`, while the systemd unit invokes that tracked 100644 shell file explicitly through `/bin/bash`. PR #132 changed the start guard from executable-file to regular-file existence and added regression coverage. No research thresholds or authority boundaries changed.

## Immutable D0 result

Campaign: `sfv2-discovery-pilot-v1`.

- authority: `DISCOVERY_ONLY`;
- exact candidates: 406;
- pilot families: 8;
- D0 strata: 12;
- expected trials: 4,872;
- terminal trials: 4,872;
- complete candidates: 406;
- rejected candidates: 254;
- behaviorally eligible candidates: 152;
- behavioral clusters: 127;
- frozen survivor count: **0**;
- survivor candidate IDs: empty;
- D1 opened: false;
- Frozen OOS opened: false;
- live execution allowed: false;
- real execution allowed: false.

The zero-survivor outcome is valid and immutable. It must not be rewritten, bypassed or converted into a winner by lowering the preregistered rule.

Production proof also showed the highest-ranked sanitized candidate was still economically negative:

`dc_41ef5a002157b82e92bd8df9` / `mean_reversion_z_v1`

- mean total return: `-0.000596638634337889`;
- mean expectancy: `-2.5838131662228028`;
- total trades: 23;
- mean benchmark-relative return: `-0.001547214383630785`;
- eligible for D0 survivor: false.

Result document: `docs/SFV2_D0_PRODUCTION_RESULT_2026-09-03.md`.

## Interpretation

The pilot did not merely collapse into duplicate behavior: 152 behaviorally eligible candidates formed 127 clusters. The decisive failure was economic. No candidate satisfied the fixed positive net-return, positive expectancy, positive benchmark-relative-return and minimum-activity rule.

The catalog deliberately used 406 candidates under a 500 hard cap. The unused numerical headroom is not a quota. Do not add 94 neighboring parameter variants just to reach 500.

There is still **no verified profitable strategy**.

## Strategy Factory next step

Do not open D1 for the completed pilot because there is no survivor to confirm.

The next useful work is a new versioned search decision:

1. produce family-level postmortem from immutable D0 evidence;
2. audit available causal data planes and backtest engines;
3. prioritize genuinely new mechanisms, richer data planes and/or different execution horizons instead of post-hoc retuning the failed eight families;
4. freeze a new deterministic candidate catalog and search budget before running it;
5. preserve the 406 inspected candidates in broad-search/multiple-testing accounting;
6. keep reused D0 explicitly discovery-only/contaminated;
7. if a future campaign freezes non-empty survivors, only then use the sealed D1 confirmation boundary.

`src/eba_trader/strategy_confirmation_freeze_v2.py` already contains the relevant D1 safety groundwork: survivor selection is required before freeze, discovery dataset hashes are captured, a reused D0 dataset hash is rejected for D1, and the stored freeze remains sealed without itself opening D1.

## SF4 remains independent and time-gated

Exact frozen hypotheses:

- `s3_vsm_s150`;
- `s3_cex_s075`.

Prospective replication interval:

`2026-09-01T00:00:00Z` through `2026-09-13T00:00:00Z`.

Do not inspect/evaluate/retune SF4 before the unlock. SF3 evidence cannot be pooled into SF4 qualification. The conservative 48-test search budget remains carried forward.

## Hard locks

- verified profitable strategy: none;
- Factory D1: sealed/not applicable to the zero-survivor pilot;
- M5/D3 Frozen OOS: sealed;
- SF4 pre-unlock evaluation: prohibited;
- real Binance execution: locked;
- Demo has no promotion authority;
- reused D0 cannot become fresh confirmation evidence;
- deterministic risk keeps veto authority.

## What was completed

- The first Strategy Factory v2 D0 production campaign completed on exact build `bdb84a4a926dac53d13116364e8315e98b35e6e1`.
- All 4,872 candidate/stratum trials are terminal.
- The immutable D0 survivor selection froze with zero survivors.
- D1, Frozen OOS, Demo promotion, live execution and real execution remain closed/locked.
- The closeout package records the negative result without changing research thresholds or authorities.

## Next exact task

Merge the D0 closeout package after exact-head CI is green, then build a read-only family-level failure decomposition from immutable D0 evidence covering activity, gross/net economics, fees/slippage, execution-delay sensitivity, regime behavior, turnover/cost and sparse-vs-bad classification. Do not rerun or rewrite the closed D0 campaign and do not touch D1, SF4 prospective data or Frozen OOS.

## Immediate continuation tasks

1. Query actual `main` and the D0 closeout PR state.
2. Merge the closeout/continuity package only after CI is green.
3. Build a read-only family-level D0 postmortem from the immutable ledger; do not rerun/alter the closed campaign.
4. Audit data/engine coverage and draft the next campaign proposal before implementing/running new candidates.
5. Keep D1/SF4/Frozen OOS/live locks unchanged.

## Startup rule

Read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, this file, `BACKTEST_PROTOCOL.md`, `docs/CONTINUITY_PROTOCOL.md`, `docs/STRATEGY_FACTORY_V2_DESIGN.md`, `docs/SFV2_D0_PRODUCTION_AUTHORIZATION_2026-09-01.md` and `docs/SFV2_D0_PRODUCTION_RESULT_2026-09-03.md`; then query actual GitHub/production state before editing.
