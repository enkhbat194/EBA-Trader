# EBA Trader — Session Handoff

_Last handoff prepared: 2026-09-01 (Asia/Ulaanbaatar)_

## Exact continuation point

Repository: `enkhbat194/EBA-Trader`.

Actual GitHub head must always be queried at startup because documentation-only commits can advance `main`. Latest code-bearing research baseline reconciled here:

`81e30bda98ce1709277c0ccfee91be8977f52720` — PR #124.

PR #109, #110, #112, #115, #117, #119, #121, #122 and #124 are merged. The most recent integrity sequence is:

- PR #119: complete non-rejected D0 candidates require the full fixed finite selection metric schema on every stratum;
- PR #121: Factory-specific survivor-freeze completeness/diversity boundary;
- PR #122: survivor eligibility rebuilt from immutable campaign/candidate/trial-ledger evidence; full declared catalog must be terminal across the exact registered D0 strata;
- PR #124: the canonical `zero survivors is valid` rule is now executable and immutable, so the system never needs to manufacture a survivor merely to produce a non-empty result.

Exact-current-build D0 production proof for `81e30bda98ce1709277c0ccfee91be8977f52720` completed successfully in Actions run `33485440135`, verify job `99784309005`; exact-build wait and existing-only D0 inspection both succeeded.

The production 406-candidate × 12-strata campaign has **not** been executed. No survivor selection has been frozen. D1 remains sealed. No public/automatic campaign trigger was added.

## Work completed in the latest engineering run

1. Re-read current GitHub `main`, production evidence and every required canonical document before making changes.
2. Reconciled stale prose against merged PR #121/#122 and exact production proof rather than trusting the stale handoff.
3. Audited PR #122 at code level and confirmed survivor freeze is ledger-backed, full-catalog terminal, provenance-bound, cluster-diverse and downstream-authority false.
4. Found a real contract mismatch: canonical Factory v2 explicitly said `zero survivors is valid`, but `freeze_d0_pilot_survivors()` rejected an empty candidate set.
5. Implemented the minimum Factory-specific fix rather than broadening unrelated generic discovery semantics.
6. Added immutable empty-selection persistence only after the same registered-campaign, exact-strata, source/dataset identity and full-catalog terminality checks.
7. Added regression coverage proving an empty outcome is persisted with `DISCOVERY_ONLY` authority and D1/Frozen OOS/live false, and cannot later be rewritten as a non-empty survivor selection.
8. Initial PR #124 functional regression suite passed; CI found only Ruff import-order formatting. No gate was bypassed.
9. Fixed only the import order and reran exact-head CI.
10. Final PR #124 head `9812ed9ab60a39b14e1d0b81f0f333bfad3a8fb9` passed the four required PR checks: production bundle/validate, runtime checks, repository hygiene and continuity guard.
11. PR #124 was squash-merged with expected-head SHA guard to code-bearing main `81e30bda98ce1709277c0ccfee91be8977f52720`.
12. Exact merged-build D0 production proof run `33485440135`, verify job `99784309005`, completed successfully.
13. Re-audited the fix after merge: zero-survivor persistence still requires complete immutable D0 evidence and cannot grant D1/Frozen OOS/live authority.
14. Preserved the operator-only production campaign invocation boundary; no public workaround was introduced.
15. No SF4 replication data was inspected, evaluated or retuned.

## Exact completed D0 proof baseline

Build `81e30bda98ce1709277c0ccfee91be8977f52720`, Actions run `33485440135`, verify job `99784309005`:

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

This proof validates exact build + existing D0 source readiness only. It is not evidence that the 406×12 campaign ran and is not strategy-verification evidence.

## Strategy Factory v2 current state

- raw cap 500; exact pilot catalog 406; per-family cap 64; survivor cap 30;
- 8 existing causal strategy families;
- common causal evaluator with fees/slippage;
- immutable campaign/candidate/trial ledger;
- temporal-gap warmup protection and terminal-trial resume active;
- inspected reusable D0 remains discovery-only;
- deterministic behavioral dedup/clustering fixed at 0.90;
- incomplete/rejected/schema-invalid candidates cannot expose aggregate selection economics or enter behavioral eligibility;
- authorized survivor freeze is `freeze_d0_pilot_survivors()`;
- freeze-time evidence is rebuilt from immutable registered campaign + declared candidate + trial ledger;
- full declared catalog must be terminal across exact expected D0 strata before any survivor outcome is written;
- non-empty survivors must be complete, non-rejected, behaviorally eligible and one-per-cluster;
- empty survivor outcome is valid after the same completeness checks and is immutable;
- frozen selection keeps D1/Frozen OOS/live false;
- no empirical cluster/survivor counts exist until production campaign execution.

## Research status and hard locks

There is still **no verified profitable strategy**. SF1, SF2 and SF3 closed with zero promoted candidates. D0 ranking, clustering or survivor status is not verification.

SF4 keeps exact `s3_vsm_s150` and `s3_cex_s075` frozen for prospective replication on only new BTCUSDT USD-M data from `2026-09-01T00:00:00Z` through `2026-09-13T00:00:00Z`. Evaluation before `2026-09-13T00:00:00Z` remains fail-closed. SF3 evidence cannot be pooled. The conservative 48-test search budget remains carried forward.

Hard locks:

- Factory v2 D1 hidden confirmation: sealed.
- M5/D3 Frozen OOS: sealed/not opened.
- SF4 pre-unlock evaluation: prohibited.
- Real Binance execution: locked.
- Demo has no promotion authority.
- D0/reused data cannot be called fresh confirmation.
- Survivor freeze cannot transition durable StrategyLifecycle.

## Next exact tasks

1. When an authorized Linode shell path is available, invoke only `scripts/run_sfv2_d0_pilot_production_once.sh`; do not add an unauthenticated/public trigger.
2. Run/resume exact 406 candidates across all 12 D0 strata while the shared checkout lock is held.
3. Record empirical raw/unique-spec/family/eligible/cluster counts from immutable production campaign evidence.
4. Continue only under the existing D0 diversity/racing contract; no new family, threshold or ranking weight is authorized by this handoff.
5. Freeze at most 30 survivors only through the ledger-backed Factory guard after actual D0 evidence exists; zero survivors is valid.
6. Open D1 only through a separately authorized hidden-confirmation workflow after survivor freeze prerequisites pass.
7. Keep SF4 untouched until `2026-09-13T00:00:00Z`, and keep Frozen OOS/live locked.

## Startup rule

Read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, this file, `BACKTEST_PROTOCOL.md`, `docs/CONTINUITY_PROTOCOL.md` and `docs/STRATEGY_FACTORY_V2_DESIGN.md`; then query actual GitHub/production state before editing.