# EBA Trader — Project State

_Last reconciled: 2026-09-01 (Asia/Ulaanbaatar)_

Actual merged code, exact-build production evidence and latest explicit decision documents override stale prose. Query GitHub for the live head before editing. The latest code-bearing research baseline reconciled here is `48bdb0fa95cb6b1ae6a32e3ff6c9cf519fba68c3` (PR #127).

## Current goal

Build a research-first autonomous trading system that discovers genuinely repeatable edges efficiently while minimizing data-mining bias and preserving strict statistical/research integrity. Broad discovery and strict verification are separate authorities. Real-money execution remains locked.

## Canonical repository/runtime state

- Repository: `enkhbat194/EBA-Trader`.
- Production URL: `https://eba-trader-172-236-150-62.sslip.io`.
- Latest code-bearing research baseline: `48bdb0fa95cb6b1ae6a32e3ff6c9cf519fba68c3` (PR #127).
- Strategy Factory v2 remains the existing 8-family / deterministic 406-candidate pilot under a 500 raw-candidate hard cap and 30 survivor cap.
- PR #109 added resume-safe all-strata D0 campaign orchestration.
- PR #110 bound campaign source provenance to the actual clean checkout.
- PR #112 added the shared checkout lock between auto-update and the operator-only D0 wrapper.
- PR #115 added discovery-only behavioral cluster accounting.
- PR #117 suppressed partial/rejected aggregate D0 selection economics.
- PR #119 fails closed on missing/non-finite D0 selection metrics.
- PR #121 added the Factory-specific survivor-freeze completeness/diversity boundary.
- PR #122 rebuilt survivor eligibility from immutable registered campaign/candidate/trial-ledger evidence and requires terminal full-catalog D0 coverage before selection write.
- PR #124 makes the already-declared `zero survivors is valid` rule executable after the same full-catalog terminal checks.
- PR #127 closes issue #126 by binding every declared D0 stratum to its exact materialized dataset SHA in the immutable campaign definition, checking candidate/stratum trial SHAs from the ledger at survivor-freeze time, and carrying the same mapping into non-empty and zero-survivor frozen outcomes.
- No public or automatic production campaign trigger was added.
- The production 406-candidate × 12-strata campaign has **not** been executed yet.
- No empirical survivor/cluster result exists yet and no survivor selection has been frozen.
- M5 Frozen OOS remains **SEALED / NOT OPENED**.
- Factory v2 D1 hidden confirmation remains sealed.
- Real-money execution remains **LOCKED**.

## Exact production D0 evidence

Latest completed exact production D0 proof before PR #127 is build `81e30bda98ce1709277c0ccfee91be8977f52720`, GitHub Actions run `33485440135`, verify job `99784309005`. The exact-build wait and existing-only D0 source inspection both completed successfully.

A new exact-build D0 proof for merged PR #127 build `48bdb0fa95cb6b1ae6a32e3ff6c9cf519fba68c3` is running as Actions run `33498788797`, verify job `99827022315`. Until that run succeeds, the prior completed proof remains the latest completed production D0 evidence.

Canonical existing D0 source:

- source kind: `INSPECTED_M5_DEVELOPMENT_CORPUS`;
- materialization ID: `m5corpusmat_25007f47e456b5f2d42ef16b`;
- policy ID: `m5policy_3b90b051bd27eeab0e79be74`;
- corpus ID: `m5corpus_28c69171b3657be02bffd556`;
- declaration SHA-256: `88365779d6821c1fb30372148bbcedbfadf11471843f57722723286a43cbc77c`;
- dataset SHA-256: `aa13bcfc111c00f6da19621353a3ca8044f58eca1ab95e837d9490a205aa72eb`;
- candle SHA-256: `6368c9f41ff635d2474860a8d4579fc00e57488871020a9df38222f32d9f4744`;
- order-flow SHA-256: `3398d17c48dd282c86a13a3ccf9daafcd2784e1e64732bb52c29b9b294e82da3`;
- rows: 2,880;
- windows/strata: 12 / 12;
- authority: `DISCOVERY_ONLY`;
- provenance: `INSPECTED_REUSABLE_DISCOVERY_DATA`;
- fresh confirmation evidence: false;
- verification authority: false;
- D1 opened: false;
- Frozen OOS opened: false;
- live execution allowed: false.

This proof validates the existing D0 source and exact production build. It is **not** evidence that the 406×12 campaign has run and is not profitability/verification evidence.

## SF4 prospective replication

The exact `s3_vsm_s150` and `s3_cex_s075` hypotheses remain frozen. Replication uses only new BTCUSDT USD-M data from `2026-09-01T00:00:00Z` through `2026-09-13T00:00:00Z`. Evaluation remains fail-closed before `2026-09-13T00:00:00Z`; parameters may not be retuned and SF3 evidence may not be pooled into SF4 qualification. The conservative 48-test search budget remains carried forward.

No SF4 replication data was inspected or evaluated during the PR #127 work.

## Strategy Factory v2 state

- `DISCOVERY_ONLY` authority.
- 8 existing causal strategy families; exact deterministic pilot catalog: 406 candidates.
- Hard caps: 500 raw candidates, 64 per family, 30 survivors.
- Common causal evaluator includes fees/slippage.
- D0/D1/D2/D3 evidence zoning remains enforced.
- D0 is inspected/reusable discovery evidence only; it cannot become fresh confirmation.
- Immutable campaign/candidate/trial accounting and source/dataset provenance are active.
- D0 temporal-gap warmup protection and terminal-trial resume are active.
- Behavioral dedup/clustering uses the existing fixed 0.90 threshold.
- Incomplete/rejected/schema-invalid candidates cannot expose aggregate selection economics or enter behavioral eligibility.
- Authorized Factory survivor freeze is `freeze_d0_pilot_survivors()`; the generic ledger freeze is not the sanctioned Factory path.
- Freeze-time eligibility is reconstructed from immutable ledger evidence; caller-supplied report/accounting is not trusted.
- Campaign registration now freezes an exact `stratum_id -> materialized dataset_sha256` mapping before trial execution.
- The full declared candidate catalog must be terminal over the exact registered D0 strata, and every low-fidelity candidate/stratum trial must match the registered stratum dataset SHA before any survivor outcome is frozen.
- Missing, duplicate, unexpected-stratum or dataset-SHA-mismatched D0 trial provenance fails closed.
- Non-empty selections must be complete, non-rejected, behaviorally eligible and one-per-behavioral-cluster.
- An empty selection is a valid immutable negative discovery outcome after the same full-catalog and exact-stratum-provenance prerequisite. It cannot later be changed into a non-empty selection under the same campaign.
- Survivor freeze itself leaves D1, Frozen OOS and live authority false.

## Validation status

There is still **no verified profitable strategy**. SF1, SF2 and SF3 closed with zero promoted candidates. SF4 is prospective replication only. Factory v2 D0 ranking, clustering, survivor selection or a zero-survivor outcome has discovery authority only.

Historical SF2/SF3 strict reference gates remain unchanged: positive mean return and expectancy, at least 30 trades, cross-window performance, positive baseline delta and corrected significance. Factory D0 does not satisfy those gates and no gate was lowered in PR #127.

## Safety invariants

- Development/discovery ranking is not promotion authority.
- A discovery survivor is not verified; zero survivors is valid.
- Reused/adaptively inspected data cannot be relabelled fresh evidence.
- Full search/multiple-testing history must remain accounted for.
- Robustness precedes Frozen OOS.
- Frozen OOS cannot be opened by discovery workflows.
- Demo is execution plumbing evidence, not verification.
- Deterministic risk retains veto authority.
- Spot and USD-M futures data are never silently mixed.
- Real Binance execution remains disabled.

## Next exact tasks

1. Require the merged PR #127 exact-production D0 proof to succeed before production campaign invocation.
2. When an authorized Linode operator shell path is available, invoke only `scripts/run_sfv2_d0_pilot_production_once.sh`; do not add an unauthenticated/public trigger as an access workaround.
3. Run/resume the exact 406 candidates across all 12 D0 strata while the shared checkout lock is held.
4. Record actual raw/unique-spec/family/eligible/cluster counts from immutable production campaign evidence.
5. Continue higher-fidelity D0 racing only under the existing predeclared diversity/search contract; no new family, threshold or ranking weight is authorized by this reconciliation.
6. Freeze at most 30 survivors only through the ledger-backed Factory guard after actual D0 evidence exists; zero survivors is valid.
7. Open D1 only through a separately authorized hidden-confirmation workflow after survivor freeze prerequisites pass.
8. Keep SF4 untouched until `2026-09-13T00:00:00Z`.
9. Keep Frozen OOS and real-money execution locked.

## Continuity protocol

New sessions read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, `SESSION_HANDOFF.md`, `BACKTEST_PROTOCOL.md` and `docs/STRATEGY_FACTORY_V2_DESIGN.md`, then query actual GitHub/production state before editing.