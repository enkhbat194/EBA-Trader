# EBA Trader — Session Handoff

_Last handoff prepared: 2026-09-01 (Asia/Ulaanbaatar)_

## Exact continuation point

Repository: `enkhbat194/EBA-Trader`

Engine baseline before this documentation reconciliation:

`0f3ee0745b643abeda3fb9c796f7d6c1a219f6a8`

PR #109 and PR #110 are merged. PR #109 added the deterministic resume-safe D0 pilot campaign runner; PR #110 hardened source provenance so production derives the source SHA from the actual clean checkout rather than trusting operator text.

Exact production build `9b2d31efd00981282acc405b944d0b913960fca1` passed D0 existing-source proof after #109. The next production proof must confirm the latest provenance-hardened build before any campaign execution.

## What was completed

1. Reconciled stale canonical docs against actual merged code and exact production evidence.
2. Confirmed production D0 source is available, valid and inspected reusable discovery evidence only.
3. Merged PR #109 after exact-head full regression, Ruff, runtime, production-bundle, hygiene and continuity checks passed.
4. Confirmed `9b2d31ef...` reached production and retained the exact D0 hashes/12-stratum safety contract.
5. Audited #109 and found a provenance defect: operator-supplied `--source-code-sha` could falsely label the immutable campaign source.
6. Merged PR #110 after green exact-head checks; campaign production wrapper now derives actual clean Git SHA and rejects dirty/mismatched source checkouts.
7. Identified the remaining production execution-safety blocker: the Linode five-minute auto-updater can mutate the checkout while a long D0 campaign process is active unless execution and update are coordinated.

## Exact D0 proof

On production build `9b2d31efd00981282acc405b944d0b913960fca1`:

- source kind: `INSPECTED_M5_DEVELOPMENT_CORPUS`;
- materialization ID: `m5corpusmat_25007f47e456b5f2d42ef16b`;
- policy ID: `m5policy_3b90b051bd27eeab0e79be74`;
- corpus ID: `m5corpus_28c69171b3657be02bffd556`;
- declaration SHA-256: `88365779d6821c1fb30372148bbcedbfadf11471843f57722723286a43cbc77c`;
- dataset SHA-256: `aa13bcfc111c00f6da19621353a3ca8044f58eca1ab95e837d9490a205aa72eb`;
- candle SHA-256: `6368c9f41ff635d2474860a8d4579fc00e57488871020a9df38222f32d9f4744`;
- order-flow SHA-256: `3398d17c48dd282c86a13a3ccf9daafcd2784e1e64732bb52c29b9b294e82da3`;
- row count: 2,880;
- windows/strata: 12 / 12;
- authority: `DISCOVERY_ONLY`;
- provenance: `INSPECTED_REUSABLE_DISCOVERY_DATA`;
- fresh confirmation evidence: false;
- verification authority: false;
- D1/Frozen OOS/live: closed/closed/locked.

## Strategy Factory v2 state

- raw cap 500; exact pilot catalog 406; per-family cap 64; survivor cap 30;
- 8 existing causal strategy families;
- common causal evaluator and fees/slippage semantics;
- immutable campaign/candidate/trial ledger;
- resume reuses terminal trials without re-evaluation;
- temporal-gap warmup protection is active;
- production D0 data source is proven;
- all-strata campaign orchestration is merged;
- actual clean-checkout source provenance binding is merged;
- D1 remains sealed and no survivor freeze has occurred.

## Research status and hard locks

There is still no verified profitable strategy. SF1, SF2 and SF3 closed with zero promoted candidates. D0 discovery ranking is not verification.

SF4 keeps exact `s3_vsm_s150` and `s3_cex_s075` parameters frozen for prospective replication using only `2026-09-01T00:00:00Z` through `2026-09-13T00:00:00Z`. Evaluation before the declared end time is fail-closed. SF3 evidence cannot be pooled into the replication result.

Hard locks:

- M5 Frozen OOS remains sealed/not opened.
- Factory v2 D1 hidden confirmation remains sealed.
- SF4 cannot be evaluated before `2026-09-13T00:00:00Z`.
- Real Binance execution remains locked.
- Demo execution has no strategy-promotion authority.
- D0/development ranking has no promotion authority.
- Reused/inspected D0 data cannot be called fresh confirmation evidence.
- A discovery survivor is not a verified strategy and cannot transition durable StrategyLifecycle.

## Next exact task

1. Confirm exact production proof for the latest merged source-provenance hardening.
2. Design the minimum production-safe campaign execution path: pin one exact clean build and prevent `eba-auto-update` from changing the checkout while campaign execution is active. Do not add a public unauthenticated trigger.
3. Prove the concurrency/update guard with tests before starting 406×12 D0 execution.
4. Run/resume the exact pilot only after that proof; never rank incomplete candidates.
5. Then aggregate selection-only metrics and behavioral fingerprints, deduplicate behavior, and continue only under the existing D0 diversity/racing contract.
6. Keep D1, Frozen OOS, SF4 pre-unlock evaluation and real-money execution closed.

## Startup rule

Read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, this file, `BACKTEST_PROTOCOL.md`, `docs/CONTINUITY_PROTOCOL.md` and `docs/STRATEGY_FACTORY_V2_DESIGN.md`; then query actual GitHub/production proof before editing.
