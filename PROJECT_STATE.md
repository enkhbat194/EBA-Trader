# EBA Trader — Project State

_Last reconciled: 2026-09-01 (Asia/Ulaanbaatar)_

Actual merged code, exact-build production evidence and latest explicit decision documents override stale prose. Documentation commits may advance `main`; query GitHub for the live head before editing. The latest code-bearing research baseline reconciled here is `3d30199b3d4d59269e093b5cfebbce267c70afb9` (PR #122).

## Current goal

Build a research-first automated trading system that can discover repeatable trading edges efficiently without weakening statistical or verification integrity. Broad discovery and strict verification remain separate authorities. Real-money execution remains locked.

## Canonical repository/runtime state

- Repository: `enkhbat194/EBA-Trader`
- Production URL: `https://eba-trader-172-236-150-62.sslip.io`
- Latest code-bearing research baseline: `3d30199b3d4d59269e093b5cfebbce267c70afb9` (PR #122).
- PR #109 merged resume-safe Strategy Factory v2 D0 pilot campaign orchestration.
- PR #110 merged clean-checkout source-provenance binding.
- PR #112 merged the shared production-checkout concurrency guard between the five-minute updater and operator-only D0 wrapper.
- PR #115 merged discovery-only behavioral cluster accounting with separate raw/spec/family/eligible/cluster counts and fail-closed representative drift checks.
- PR #117 prevented incomplete/rejected candidates from exposing partial aggregate D0 selection economics.
- PR #119 requires the full fixed finite selection-metric schema on every terminal non-rejected D0 stratum before aggregate metrics or behavioral eligibility are exposed.
- PR #121 added a Factory-specific survivor-freeze completeness/diversity boundary while keeping D1/Frozen OOS/live closed.
- PR #122 strengthened that boundary so survivor eligibility is rebuilt from immutable registered campaign + declared candidate + trial-ledger evidence at freeze time rather than trusting a caller-supplied report object. The full declared catalog must be terminal across the exact registered D0 strata before any survivor selection can be written.
- Exact-current-build D0 production proof for `3d30199b3d4d59269e093b5cfebbce267c70afb9` completed successfully in Actions run `33484772388`, verify job `99782195060`; exact-build wait and existing-only D0 source inspection both succeeded.
- No public or automatic campaign trigger was introduced.
- The 406-candidate × 12-strata campaign has **not** been executed in production yet.
- No survivor selection has been frozen and no empirical survivor/cluster result exists yet.
- Fast Momentum remains a paper/runtime test-bed, not a verified profitable strategy.
- Binance USD-M Futures Demo execution plumbing is execution proof only.
- M5 Frozen OOS (`2026-08-15 -> 2026-08-22` UTC): **SEALED / NOT OPENED**.
- Real-money execution: **LOCKED**.

## Validation status

There is still **no verified profitable strategy**. SF1, SF2 and SF3 closed with zero promoted candidates. SF4 is prospective replication only. Strategy Factory v2 is discovery-only. Demo, development ranking and D0 survivor status have no verification authority.

### SF4 prospective replication

PR #99 froze exact `s3_vsm_s150` and `s3_cex_s075` hypotheses. Replication uses only new BTCUSDT USD-M data from `2026-09-01T00:00:00Z` through `2026-09-13T00:00:00Z`. Evaluation is fail-closed before `2026-09-13T00:00:00Z`. SF3 evidence cannot be pooled into the replication result and parameters cannot be retuned. The contract still carries the conservative 48-test search budget and retains all execution/safety locks.

### Strategy Factory v2 merged state

- `DISCOVERY_ONLY` authority;
- raw-candidate hard cap 500, per-family cap 64, survivor cap 30;
- 8 executable causal families with an exact deterministic 406-candidate pilot catalog;
- immutable campaign/candidate/trial ledger;
- deterministic candidate/spec identity;
- common causal D0 evaluator with fees/slippage;
- D0 discovery / D1 hidden confirmation / D2 robustness / D3 Frozen OOS zoning;
- immutable D0 manifest with candle/order-flow/composite content hashes;
- explicit `INSPECTED_REUSABLE_DISCOVERY_DATA` provenance;
- 12 declared temporal strata bound to the already-inspected default M5 development corpus;
- D0 warmup cannot bridge independently sampled temporal windows;
- compute-budget resume reuses immutable terminal trials without re-evaluation;
- existing-only D0 loader cannot fetch, rebuild or extend missing evidence;
- campaign definition binds D0 declaration/dataset hashes, catalog seed/count, warmup, behavioral threshold and exact source checkout;
- production source attribution comes from the actual clean checkout;
- production D0 wrapper holds the shared checkout lock for the full invocation;
- aggregate selection metrics exist only for complete, non-rejected candidates;
- every complete, non-rejected stratum must provide the fixed finite selection metric schema before aggregate ranking/behavioral eligibility exists;
- incomplete/rejected candidates retain immutable trial accounting but expose no aggregate selection economics;
- deterministic behavioral similarity/deduplication with fixed pilot threshold 0.90;
- incomplete/rejected candidates excluded from behavioral clusters;
- cluster representative identity cross-checked against the existing low-fidelity representative selector and fails closed on drift;
- authorized Factory survivor freeze uses `freeze_d0_pilot_survivors()` and reconstructs the report/accounting from immutable ledger evidence;
- survivor freeze cross-checks immutable source SHA, D0 declaration SHA, D0 dataset SHA, fixed 0.90 threshold, planned catalog count and exact expected strata;
- the full declared catalog must have terminal D0 coverage before a survivor selection can be written;
- selected survivors must be complete, non-rejected, behaviorally eligible and diversity-safe; no two selected candidates may come from the same behavioral cluster;
- the frozen selection record explicitly keeps D1/Frozen OOS/live authority false.

The generic `DiscoveryTrialLedger.freeze_survivor_selection()` remains a generic primitive; it is not the authorized Strategy Factory v2 freeze path. Factory v2 must use the campaign-specific ledger-backed guard above.

## Exact production D0 evidence

Latest completed exact production D0 proof is build `3d30199b3d4d59269e093b5cfebbce267c70afb9`, GitHub Actions run `33484772388`, verify job `99782195060`. The exact-build wait and existing-only D0 safety/readiness inspection both completed successfully.

The canonical existing D0 source remains:

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

Actual campaign invocation remains operator-only; the currently connected project tools do not provide an authorized Linode shell action. Do not add an unauthenticated public trigger as an access workaround.

## Verification quality gate — DO NOT LOWER

Historical SF2/SF3 minimum reference gates remain:

1. mean return > 0;
2. mean expectancy > 0;
3. total trades >= 30;
4. baseline beaten in at least 9 of 12 declared windows;
5. positive mean return delta versus baseline;
6. corrected significance threshold satisfied.

Factory v2 D0 metrics are selection-only and do not satisfy these gates. A later confirmation protocol must account for broad-search history and use evidence that was not adaptively inspected as D0.

## Safety invariants

- Discovery ranking has no promotion authority.
- A discovery survivor is not verified.
- Frozen OOS cannot be opened by discovery workflows.
- Reused/adaptively inspected data cannot be relabelled fresh evidence.
- Full candidate/search history must be accounted for when evaluating selection bias.
- Raw candidate, unique specification, behavioral cluster and independent-family counts remain distinct concepts.
- Incomplete/rejected or selection-schema-invalid D0 candidates cannot expose aggregate selection economics or enter behavioral eligibility.
- Strategy Factory survivor freeze must reconstruct eligibility from immutable campaign/candidate/trial evidence and require terminal full-catalog D0 coverage.
- Survivor freeze itself does not authorize D1.
- Demo execution proof has no strategy-verification authority.
- Spot and USD-M futures data are never silently mixed.
- Executed footprint and resting order-book liquidity remain separate data planes.
- Gapped/tampered/missing-version research evidence fails closed.
- Real-money Binance execution remains disabled.

## Next exact tasks

1. When an authorized Linode shell path is available, invoke only `scripts/run_sfv2_d0_pilot_production_once.sh`; do not add an unauthenticated public trigger merely to bypass access limitations.
2. Run/resume the exact 406-candidate catalog across all 12 D0 strata while keeping the checkout fixed.
3. Record actual raw/unique/family/eligible/cluster counts from campaign evidence; do not confuse mechanism availability with empirical results.
4. Continue higher-fidelity D0 racing only under the predeclared diversity/search contract; D0 remains selection-only.
5. Freeze at most 30 survivors only through the ledger-backed Factory-specific guard after actual D0 evidence exists; zero survivors is valid. D1 still requires separate authorization.
6. Open D1 only through a separately authorized hidden-confirmation workflow after survivor freeze prerequisites pass.
7. Keep SF4 untouched until `2026-09-13T00:00:00Z`.
8. Keep Frozen OOS and real-money execution locked.

## Continuity protocol

New sessions read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, `SESSION_HANDOFF.md`, `BACKTEST_PROTOCOL.md` and `docs/STRATEGY_FACTORY_V2_DESIGN.md`, then query actual GitHub/production state before editing.
