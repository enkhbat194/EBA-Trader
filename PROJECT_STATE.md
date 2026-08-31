# EBA Trader — Project State

_Last reconciled: 2026-08-31 (Asia/Ulaanbaatar)_

Actual GitHub code, workflow state and Linode production proof override stale prose.

## Current goal

Build a verified automated trading research pipeline without weakening the quality bar. Candidate discovery remains development-only until a strategy passes profitability, activity, cross-window, multiple-testing and robustness gates. Real-money execution stays locked.

## Canonical repository/runtime state

- Repository: `enkhbat194/EBA-Trader`
- Production URL: `https://eba-trader-172-236-150-62.sslip.io`
- Canonical production `main`: `28c6d12f378433395118b024a0a4132c6d4edf5d`
- Exact-build Linode external production proof for `28c6d12...`: **PASS**.
- Public production smoke for `28c6d12...`: **PASS**.
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
- structurally an EMA-crossover entry filter, not an independent absorption signal generator.

### SF1 independent-family search — CLOSED

SF1 consumed its complete preregistered 48-candidate budget across 12 development windows with 4 bps fees, 1.5 bps adverse slippage and causal next-open execution.

Production result:

- `validationState=NO_VERIFIED_CANDIDATE`;
- `verifiedCandidateCount=0`;
- `topVerifiedCandidate=null`;
- Frozen OOS remained closed;
- live execution remained locked.

Top development-ranked `mr_48z15x00` was rejected despite 10/12 baseline-beating windows and 30 trades because mean return was approximately `-0.0965%`, mean expectancy approximately `-1.17`, and Bonferroni-adjusted p approximately `0.246`.

The 12 direct raw-delta candidates also failed economically: all beat baseline in `0/12` windows and had negative return/expectancy.

SF1 must not be extended with post-hoc threshold tuning on the same evidence.

## SF2 preregistration and signal implementation — FROZEN

SF2 protocol is merged and fixed in `config/sf2_research_protocol_v1.json`:

- phase `sf2_fresh_development_v1`;
- 24 active candidates in four independent families, six each;
- 12 fresh non-overlapping four-hour development windows;
- no SF1 window reuse;
- the previously inspected 2026-08-01 smoke day excluded;
- all windows remain inside M5 development `2026-07-01 -> 2026-08-15`;
- Bonferroni correction budget remains 48;
- exact sign-flip permutations: 4096;
- fees 4 bps;
- adverse slippage 1.5 bps;
- one-bar signal-to-execution delay;
- minimum hold 2 bars;
- maximum hold 12 bars.

SF2 direct-signal implementation merged at production `28c6d12...` and passed regression/runtime/public/external production proof. Families:

1. `divergence_reversal_v1`;
2. `absorption_reversal_v1`;
3. `stacked_delta_continuation_v1`;
4. `flow_price_continuation_v1`.

The implementation uses causally available closed order-flow/price information and next-open execution. It has no Frozen-OOS, promotion or live authority.

## Validation status

Current working branch: `sf2-fresh-corpus-evaluation-pipeline`.

This branch adds the machinery required to consume the preregistered fresh SF2 evidence without reusing SF1 infrastructure incorrectly:

- `sf2_development.py`: 24 × 12 evaluator, fixed EMA 12/26 comparison baseline, aggregate metrics, exact 4096 sign-flip null test and Bonferroni(48) validation;
- `sf2_runtime.py`: resumable/custom-corpus Binance USD-M archive materialization, immutable development/validation evidence and reusable terminal status;
- `sf2_dashboard.py`: sanitized read-only public summary with no path/credential leakage;
- maintenance integration: SF2 runs as an independent development stage, not as a child of legacy `absorption_020` robustness;
- tests cover significance, unsafe-report rejection, runtime evidence reuse, safe failure behavior, dashboard sanitization and maintenance independence.

Fresh SF2 production evidence has **not yet been claimed or inspected** in this branch state. The code must pass exact-head CI, merge, deploy, and then the production maintenance runtime may materialize/evaluate the preregistered windows.

## Fixed quality gate — DO NOT LOWER

An SF2 development candidate may become **robustness-eligible only** if all are true:

1. mean return > 0;
2. mean expectancy > 0;
3. total trades >= 30;
4. baseline beaten in at least 9 of 12 development windows;
5. mean return delta versus baseline > 0;
6. Bonferroni-adjusted exact sign-flip p-value <= 0.05.

The 48-hypothesis correction budget remains in force even though SF2 has 24 active candidates. Passing this gate still does **not** open Frozen OOS. A candidate-specific robustness stage must pass next.

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
- Reused/adaptively inspected data cannot be relabelled as fresh verification.

## Next exact task

1. Finish exact-head CI for `sf2-fresh-corpus-evaluation-pipeline`.
2. Fix every failure; merge only with full regression, Ruff, runtime, continuity, repository hygiene and deployment-contract checks green.
3. Verify exact merged `main` on Linode.
4. Allow the versioned maintenance service to materialize the 12 preregistered SF2 windows from Binance USD-M archives and run all 24 candidates.
5. Read the sanitized production `sf2` summary from `/api/research/status`.
6. If `verifiedCandidateCount=0`, close SF2 without promotion and do not touch Frozen OOS.
7. If a candidate is robustness-eligible, build and pass a candidate-appropriate fixed robustness suite before any Frozen-OOS consideration.
8. Do not enable real-money execution.

## Continuity protocol

New sessions read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, `SESSION_HANDOFF.md`, and `docs/CONTINUITY_PROTOCOL.md`, then query actual GitHub/production state before editing.
