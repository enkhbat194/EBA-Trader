# EBA Trader — Session Handoff

_Last handoff prepared: 2026-08-30 (Asia/Ulaanbaatar)_

## Exact continuation point

Repository: `enkhbat194/EBA-Trader`

Canonical production `main`:

`0f6d0c1d7c74f8a42ae16921d24dfe446d805380`

Current working branch:

`sf1-closeout-sf2-preregistration`

Production exact-build proof for `0f6d0c1d...`: **SUCCESS**.

## What was completed

- SF1 was production-run at the full preregistered 48/48 candidate budget and closed with zero verified candidates.
- The final 12 SF1 slots were genuinely independent long/short raw footprint-Delta signal generators rather than EMA gates.
- Production exact-build evidence kept Frozen OOS closed and real execution locked.
- The stale repository continuity state was reconciled to the SF1 closeout.
- A new SF2 fresh-development protocol was preregistered before any fresh SF2 window was materialized or evaluated.

## What is proven

### Binance USD-M Futures Demo execution plumbing

- real Demo BTCUSDT BUY/SELL round trip previously passed;
- terminal proof is preserved;
- one-shot probe is disabled;
- pre/post position was flat;
- real money was not used;
- real execution remains locked.

This proves execution plumbing only, not strategy profitability.

### M5 / `absorption_020`

- structurally an EMA-crossover entry filter rather than an independent absorption strategy;
- only 4 development trades;
- negative expectancy;
- center not profitable;
- sample insufficient;
- robustness not verified.

Do not promote it and do not open M5 Frozen OOS.

### SF1 independent-family search

SF1 is now fully consumed and closed:

- 12 ATR candidates;
- 12 Donchian breakout candidates;
- 12 z-score mean-reversion candidates;
- 12 independent raw footprint-delta impulse candidates;
- total 48/48 candidates;
- 12 original development windows;
- 4 bps fees;
- 1.5 bps slippage;
- causal next-open execution;
- Bonferroni search budget 48.

Exact production result on `0f6d0c1d...`:

- `validationState=NO_VERIFIED_CANDIDATE`;
- `verifiedCandidateCount=0`;
- `topVerifiedCandidate=null`;
- Frozen OOS closed;
- live/real execution locked.

Top development-ranked candidate `mr_48z15x00`:

- 10/12 baseline-beating windows;
- 30 trades;
- mean return about `-0.0965%`;
- mean expectancy about `-1.17`;
- adjusted p-value about `0.246`.

It is rejected because the fixed quality gate requires positive mean return, positive expectancy and adjusted p <= 0.05 in addition to activity/cross-window requirements.

The 12 direct raw-delta impulse candidates also failed despite adequate activity: all beat baseline in 0/12 windows, all had negative mean return/expectancy and adjusted p-value 1.0.

## Fixed quality gate — never weaken silently

A candidate may enter robustness only when all are true:

1. mean return > 0;
2. mean expectancy > 0;
3. total trades >= 30;
4. baseline beaten in >=9/12 development windows;
5. Bonferroni-adjusted p-value <= 0.05.

Then robustness remains mandatory before any Frozen-OOS consideration.

## Scientific decision after SF1

Do not add more candidate thresholds to SF1 and do not keep tuning on the same 12 windows. SF1 consumed its full preregistered 48-candidate budget; repeated adaptive use of the same development evidence would create data snooping / overfitting.

SF2 therefore uses new development windows that were not used by SF1. Candidate definitions, execution assumptions and the data-window schedule are preregistered before any SF2 evaluation output is observed.

## Current branch work — SF2 preregistration

Files added/updated:

- `config/sf2_research_protocol_v1.json`
- `src/eba_trader/sf2_protocol.py`
- `tests/test_sf2_protocol.py`
- `PROJECT_STATE.md`
- `TODO.md`
- `SESSION_HANDOFF.md`

SF2 locked design:

- 24 active candidates;
- statistical correction budget remains 48;
- 12 new 4-hour development windows;
- no overlap with the original SF1 corpus;
- 2026-08-01 original smoke day excluded;
- all new windows remain inside M5 development `2026-07-01 -> 2026-08-15`;
- M5 Frozen OOS `2026-08-15 -> 2026-08-22` remains sealed;
- fees 4 bps;
- slippage 1.5 bps;
- one-bar signal-to-execution delay;
- minimum hold 2 bars;
- maximum hold 12 bars;
- quality gate unchanged.

Preregistered families, six candidates each:

1. `divergence_reversal_v1`;
2. `absorption_reversal_v1`;
3. `stacked_delta_continuation_v1`;
4. `flow_price_continuation_v1`.

The protocol loader fails closed if an SF1 development window is reused, the original smoke day is reused, execution assumptions change, the multiple-testing budget is lowered, or the quality gate is weakened.

## Next exact task

1. Inspect PR #91 for `sf1-closeout-sf2-preregistration`.
2. Run exact-head full regression, Ruff, runtime, continuity and production-bundle checks.
3. Fix every failure; do not merge red CI.
4. Merge only when all checks are green.
5. Verify exact merged build on Linode and confirm SF1 remains `NO_VERIFIED_CANDIDATE`, Frozen OOS closed and real execution locked.
6. Implement all four SF2 families without materializing or evaluating the fresh SF2 windows.
7. Add causality, no-lookahead, fee/slippage, long/short and holding-period tests.
8. Freeze implementation/configuration with green CI.
9. Only then materialize the preregistered fresh SF2 corpus from Binance USD-M archives.
10. Run all 24 candidates across all 12 fresh windows with the conservative 48-hypothesis Bonferroni correction.
11. Reject every candidate that misses any fixed quality criterion.
12. Do not open M5 Frozen OOS and do not enable real-money execution unless the required later gates actually pass.

## Hard locks

- Legacy 2025 Frozen OOS remains locked.
- M5 Frozen OOS (`2026-08-15 -> 2026-08-22` UTC) remains sealed/not opened.
- Real Binance execution remains locked.
- Demo execution has no strategy-promotion authority.
- Development/ranking results have no promotion authority.
- Repeated analysis of already-inspected development data cannot be relabelled as fresh verification.

## Startup rule

Read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, this file and `docs/CONTINUITY_PROTOCOL.md`; then query actual GitHub and production proof state before editing.
