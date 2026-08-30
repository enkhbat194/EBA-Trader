# EBA Trader — Project State

_Last reconciled: 2026-08-30 (Asia/Ulaanbaatar)_

Actual GitHub code, workflow state and Linode production proof override stale prose.

## Current goal

Build a verified automated trading research pipeline without weakening the quality bar. Candidate discovery stays development-only until a strategy passes profitability, activity, cross-window, multiple-testing and robustness gates. Real-money execution stays locked.

## Canonical repository/runtime state

- Repository: `enkhbat194/EBA-Trader`
- Production URL: `https://eba-trader-172-236-150-62.sslip.io`
- Canonical production `main`: `0f6d0c1d7c74f8a42ae16921d24dfe446d805380`
- Exact-build Linode production proof for `0f6d0c1d...`: **PASS**.
- Fast Momentum remains the sole active production paper scanner.
- Binance USD-M Futures Demo execution plumbing: **REAL DEMO ROUND-TRIP VERIFIED**.
- M5 Frozen OOS (`2026-08-15 -> 2026-08-22` UTC): **SEALED / NOT OPENED**.
- Legacy 2025 Frozen OOS: **LOCKED**.
- Real-money execution: **LOCKED**.

## M5 / SF1 research status

### Historical M5 candidate

`absorption_020` is closed without promotion:

- only 4 development trades;
- negative expectancy;
- `centerProfitable=false`;
- `sampleSufficient=false`;
- `robustnessVerified=false`;
- structurally it is an EMA-crossover entry filter, not an independent absorption signal generator.

### SF1 independent-family search — CLOSED

SF1 used the complete preregistered multiple-testing budget:

- 12 ATR trailing-stop candidates;
- 12 Donchian breakout candidates;
- 12 z-score mean-reversion candidates;
- 12 independent raw footprint-delta impulse candidates;
- total: **48/48 candidates**;
- development windows: **12**;
- fees: **4 bps**;
- adverse slippage: **1.5 bps**;
- causal next-open execution;
- Bonferroni budget: **48**.

Production result on exact build `0f6d0c1d...`:

- `validationState=NO_VERIFIED_CANDIDATE`;
- `verifiedCandidateCount=0`;
- `topVerifiedCandidate=null`;
- Frozen OOS remained closed;
- live execution remained locked.

The top development-ranked candidate was `mr_48z15x00`:

- baseline-beating windows: `10/12`;
- total trades: `30`;
- mean return: approximately `-0.0965%`;
- mean expectancy: approximately `-1.17`;
- Bonferroni-adjusted p-value: approximately `0.246`.

It therefore fails the unchanged quality gate and is rejected.

The new independent order-flow delta family had adequate sample size but poor economics:

- all 12 candidates beat the baseline in `0/12` windows;
- all had negative mean return and negative mean expectancy;
- adjusted p-values were `1.0`;
- this is a performance failure, not an inactivity failure.

## Validation status

- SF1 production evaluation completed on all 48 preregistered candidates.
- No strategy is development-verified or robustness-eligible.
- SF1 evidence is closed and must not be extended with post-hoc threshold tuning.
- SF2 protocol validation is required to fail closed on reused SF1 evidence, smoke-day reuse, lowered statistical budget or weakened quality criteria.

## Quality gate — DO NOT LOWER

A development candidate may enter robustness only if all are true:

1. mean return > 0;
2. mean expectancy > 0;
3. total trades >= 30;
4. baseline beaten in at least 9 of 12 development windows;
5. Bonferroni-adjusted p-value <= 0.05.

Passing development still does **not** open Frozen OOS. Robustness must then pass center profitability, sample sufficiency, cost stress, parameter-neighborhood stability and other locked checks.

## Scientific closeout decision

SF1 has consumed its full 48-candidate preregistered search budget. Do not add more SF1 thresholds or retune the same 12 development windows. Doing so would create adaptive data snooping / overfitting.

The next research phase is SF2 and must use **fresh development evidence not used by SF1**. Candidate definitions and the data windows must be preregistered before any SF2 evaluation result is inspected.

## SF2 preregistration — IN PROGRESS

Branch: `sf1-closeout-sf2-preregistration`

Protocol file:

- `config/sf2_research_protocol_v1.json`

Locked SF2 design:

- source phase: `sf1_independent_families_v1`;
- active candidates: **24**;
- statistical correction budget remains **48** (conservative; it is not reduced to 24);
- fresh development windows: **12 × 4 hours**;
- none overlap the SF1 12-window corpus;
- the previously inspected 2026-08-01 smoke day is excluded;
- every window is inside the sealed M5 development range `2026-07-01 -> 2026-08-15`;
- M5 Frozen OOS `2026-08-15 -> 2026-08-22` remains unreachable by normal SF2 development;
- fee/slippage and the quality gate remain unchanged.

Preregistered SF2 families, six candidates each:

1. `divergence_reversal_v1` — independent price/Delta divergence reversal entries;
2. `absorption_reversal_v1` — direct executed-flow absorption-proxy reversal entries;
3. `stacked_delta_continuation_v1` — stacked imbalance + Delta confirmation;
4. `flow_price_continuation_v1` — executed-flow and already-closed price-response continuation.

SF2 adds fixed anti-churn holding rules (`minimum_hold_bars=2`, `max_hold_bars=12`) because SF1 raw-delta impulse overtraded and lost to poor expectancy/costs. These rules are preregistered before fresh SF2 data is inspected.

## Safety invariants

- Frozen OOS cannot be opened by normal development workflows.
- M5 Frozen OOS stays sealed until a candidate passes strict development + robustness gates.
- Real Binance execution remains disabled.
- Demo execution proof has no strategy-promotion authority.
- Development rankings have no promotion authority.
- Runtime persistence and research persistence remain separate.
- Spot and USD-M futures data are never silently mixed.
- Executed footprint and resting LOB/order-book liquidity remain separate data planes.
- Gapped/tampered/missing-version research data fails closed.
- Reusing already-inspected development evidence must be labelled adaptive/exploratory; it cannot masquerade as fresh verification.

## Next exact task

1. Finish CI for `sf1-closeout-sf2-preregistration`.
2. Merge only with full regression/runtime/continuity checks green.
3. Verify exact production build while confirming SF1 remains `NO_VERIFIED_CANDIDATE` and all locks remain closed.
4. Implement the four SF2 signal families **without materializing or evaluating the fresh SF2 windows yet**.
5. Add causality, fee/slippage, holding-period, long/short and no-lookahead regression tests.
6. Only after candidate implementation is frozen and CI-green, materialize the preregistered fresh SF2 corpus from the Binance USD-M archive.
7. Run the 24 candidates across the 12 fresh windows using the unchanged 48-hypothesis Bonferroni correction.
8. Reject every candidate that misses any quality-gate condition; do not open M5 Frozen OOS and do not enable real-money execution.

## Continuity protocol

New sessions read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, `SESSION_HANDOFF.md`, and `docs/CONTINUITY_PROTOCOL.md`, then query actual GitHub/production state before editing.
