# EBA Trader — Project State

_Last reconciled: 2026-09-03 (Asia/Ulaanbaatar)_

Actual merged code, exact-build production evidence and the latest explicit decision documents override stale prose. Query GitHub before editing.

## Current goal

Build a research-first autonomous trading system that discovers genuinely repeatable edges efficiently while preserving strict statistical integrity. Broad discovery and strict verification remain separate authorities. Real-money execution remains locked.

The immediate research focus has moved from executing the first Strategy Factory v2 D0 pilot to **closing out its zero-survivor result and designing the next versioned search campaign around genuinely new mechanisms/data/horizons rather than more parameter variants of failed families**.

## Canonical repository/runtime state

- Repository: `enkhbat194/EBA-Trader`.
- Production URL: `https://eba-trader-172-236-150-62.sslip.io`.
- Exact D0 completion build/source SHA: `bdb84a4a926dac53d13116364e8315e98b35e6e1`.
- Official D0 production proof: GitHub Actions run `33674168891` (`Strategy Factory v2 D0 production campaign proof`, run #3), conclusion `success`.
- PR #132 fixed the production start blocker by removing an incorrect executable-bit requirement from a runner that systemd invokes via `/bin/bash`.
- M5/D3 Frozen OOS remains **SEALED / NOT OPENED**.
- Factory v2 D1 hidden confirmation remains **SEALED**.
- Real-money execution remains **LOCKED**.

## Strategy Factory v2 D0 — immutable completed result

Campaign: `sfv2-discovery-pilot-v1`.

Authority: `DISCOVERY_ONLY`.

Exact empirical result:

- candidates: 406;
- independent pilot families: 8;
- D0 strata: 12;
- expected candidate/stratum trials: 4,872;
- terminal candidate/stratum trials: 4,872;
- complete candidates: 406;
- rejected candidates: 254;
- behaviorally eligible candidates: 152;
- behavioral clusters: 127;
- frozen D0 survivors: **0**;
- D1 opened: false;
- Frozen OOS opened: false;
- live execution allowed: false;
- real execution allowed: false.

The zero-survivor selection was permitted by the rule frozen before production results were observed and is now an immutable negative discovery outcome.

The highest-ranked sanitized discovery candidate, `dc_41ef5a002157b82e92bd8df9` (`mean_reversion_z_v1`), still had negative mean total return, negative expectancy and negative benchmark-relative return. No D0 candidate met the predeclared positive economics + activity rule.

Full closeout: `docs/SFV2_D0_PRODUCTION_RESULT_2026-09-03.md`.

## What the D0 result means

The first pilot did not fail because all candidates collapsed into one duplicate behavior: 152 candidates were behaviorally eligible and formed 127 clusters. The decisive failure was **net economics after the fixed evaluator/cost assumptions**.

The pilot catalog intentionally contained 406 candidates even though 500 is the hard upper cap. The remaining numerical headroom is not a quota and must not be filled post-hoc with neighboring parameter variants merely because survivor count was zero.

There is still **no verified profitable strategy**.

## Next Strategy Factory search rules

Any further Strategy Factory search is a new versioned campaign decision, not an extension/rewrite of `sfv2-discovery-pilot-v1`.

Required before evaluation:

1. audit the failed eight-family catalog by mechanism, activity, turnover/cost and data plane;
2. prefer genuinely new mechanisms, data planes and/or execution horizons;
3. freeze a deterministic candidate catalog and search budget before observing the new campaign results;
4. carry all 406 already inspected candidates in the broad-search/multiple-testing history;
5. keep reused D0 data explicitly contaminated/reusable discovery evidence only;
6. do not open D1 unless a future campaign freezes a non-empty survivor set;
7. never lower profitability, expectancy, sample-size, statistical, causal, cost or robustness gates to force a survivor.

## Existing D1 safety groundwork

`HiddenConfirmationFreezeStore` already provides a sealed one-way D0-survivor freeze boundary:

- survivor selection must exist first;
- candidate identities/spec/source SHA are frozen;
- discovery dataset hashes are recorded;
- a D1 dataset hash already consumed by D0 is rejected;
- the freeze remains `SEALED` and does not itself open D1;
- Frozen OOS authority remains false.

This mechanism is not activated for the completed D0 pilot because its survivor count is zero.

## SF4 prospective replication

The exact `s3_vsm_s150` and `s3_cex_s075` hypotheses remain frozen. Replication uses only new BTCUSDT USD-M data from `2026-09-01T00:00:00Z` through `2026-09-13T00:00:00Z`.

Evaluation remains fail-closed before `2026-09-13T00:00:00Z`; parameters may not be retuned and SF3 evidence may not be pooled into SF4 qualification. The conservative 48-test search budget remains carried forward.

The Strategy Factory D0 closeout must not inspect or evaluate SF4 data.

## Safety invariants

- Development/discovery ranking is not promotion authority.
- A discovery survivor would still not be verified; zero survivors is valid.
- Reused/adaptively inspected data cannot be relabelled fresh evidence.
- Full search/multiple-testing history must remain accounted for.
- Robustness precedes Frozen OOS.
- Frozen OOS cannot be opened by discovery workflows.
- Demo is execution plumbing evidence, not verification.
- Deterministic risk retains veto authority.
- Spot and USD-M futures data are never silently mixed.
- Real Binance execution remains disabled.

## Next exact tasks

1. Merge the D0 closeout/continuity package after CI is green.
2. Build a family-level D0 postmortem from immutable discovery evidence without touching D1/SF4.
3. Audit the currently available causal data planes/backtest engines and identify genuinely new search mechanisms.
4. Write a new versioned Strategy Factory campaign proposal with explicit candidate budget, deterministic generation, data authority and multiple-testing accounting before running it.
5. Keep SF4 untouched until `2026-09-13T00:00:00Z`.
6. Keep D1, Frozen OOS and real-money execution locked unless their strict prerequisites are actually satisfied.

## Continuity protocol

New sessions read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, `SESSION_HANDOFF.md`, `BACKTEST_PROTOCOL.md`, `docs/STRATEGY_FACTORY_V2_DESIGN.md`, `docs/SFV2_D0_PRODUCTION_AUTHORIZATION_2026-09-01.md` and `docs/SFV2_D0_PRODUCTION_RESULT_2026-09-03.md`, then query actual GitHub/production state before editing.
