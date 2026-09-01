# EBA Trader — Session Handoff

_Last handoff prepared: 2026-09-01 (Asia/Ulaanbaatar)_

## Exact continuation point

Repository: `enkhbat194/EBA-Trader`.

Actual GitHub head must always be queried at startup because documentation-only commits can advance `main`. Latest code-bearing research baseline reconciled here:

`48bdb0fa95cb6b1ae6a32e3ff6c9cf519fba68c3` — PR #127.

PR #109, #110, #112, #115, #117, #119, #121, #122, #124 and #127 are merged. The most recent integrity sequence is:

- PR #119: complete non-rejected D0 candidates require the full fixed finite selection metric schema on every stratum;
- PR #121: Factory-specific survivor-freeze completeness/diversity boundary;
- PR #122: survivor eligibility rebuilt from immutable campaign/candidate/trial-ledger evidence; full declared catalog must be terminal across the exact registered D0 strata;
- PR #124: the canonical `zero survivors is valid` rule is executable and immutable;
- PR #127: closes issue #126 by freezing an exact `stratum_id -> materialized dataset_sha256` mapping in the immutable campaign registration and validating every low-fidelity candidate/stratum trial against that mapping before either non-empty or zero-survivor freeze.

Exact-current-build D0 production proof for `48bdb0fa95cb6b1ae6a32e3ff6c9cf519fba68c3` completed successfully in Actions run `33498788797`, verify job `99827022315`; exact-build wait and existing-only D0 inspection both succeeded.

The production 406-candidate × 12-strata campaign has **not** been executed. No survivor selection has been frozen. D1 remains sealed. No public/automatic campaign trigger was added.

## What was completed in the latest engineering run

1. Re-read current GitHub `main`, production evidence and every required canonical document before making changes.
2. Confirmed current main and production evidence still had D1/Frozen OOS/live closed and the production 406×12 campaign unrun.
3. Revalidated issue #126 as a real freeze-boundary provenance defect: a correct `d0-low-v1:<stratum>` fidelity label did not prove the trial used the exact materialized dataset for that stratum.
4. Implemented the minimum fix in `strategy_factory_v2_campaign.py`: materialize strata before immutable campaign registration and bind exact per-stratum dataset SHAs.
5. Added freeze-time ledger reconstruction requiring the full candidate × registered-stratum trial matrix, with fail-closed rejection for missing, duplicate, unexpected-stratum or dataset-SHA-mismatched low-fidelity evidence.
6. Bound the same exact stratum-SHA map into both non-empty and zero-survivor frozen definitions.
7. Added regression coverage for successful exact provenance and for wrong-SHA rejection on both non-empty and zero-survivor paths.
8. Initial functional regression suite passed; CI exposed only Ruff line-length failures. Those formatting-only failures were fixed without changing research logic.
9. Final PR #127 head `3ffe788f8930e075a3073d9195cf1ea265ecf323` passed the four required PR workflows: runtime checks, production bundle/full regression + Ruff, repository hygiene and continuity guard.
10. PR #127 was squash-merged with an exact expected-head SHA guard to code-bearing main `48bdb0fa95cb6b1ae6a32e3ff6c9cf519fba68c3`; issue #126 closed as completed.
11. Exact merged-build D0 production proof run `33498788797`, verify job `99827022315`, completed successfully.
12. No SF4 replication data was inspected, evaluated or retuned.
13. No candidate family, catalog size, 500 cap, 0.90 behavioral threshold, selection economics, D1 policy, Frozen OOS policy or live-execution authority changed.

## Exact completed D0 proof baseline

Build `48bdb0fa95cb6b1ae6a32e3ff6c9cf519fba68c3`, Actions run `33498788797`, verify job `99827022315`:

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
- campaign registration freezes exact materialized dataset SHA per declared D0 stratum;
- full declared catalog must be terminal across exact expected D0 strata and every low-fidelity candidate/stratum trial must match its registered stratum dataset SHA before any survivor outcome is written;
- missing/duplicate/unexpected/SHA-mismatched low-fidelity trial provenance fails closed;
- non-empty survivors must be complete, non-rejected, behaviorally eligible and one-per-cluster;
- empty survivor outcome is valid only after the same completeness and exact-stratum-provenance checks and is immutable;
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