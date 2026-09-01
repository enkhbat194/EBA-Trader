# EBA Trader — TODO

Actual merged code, exact production evidence and latest explicit decisions override stale prose. Query `main`, open PRs and workflows before continuing. Latest code-bearing research baseline reconciled here: `48bdb0fa95cb6b1ae6a32e3ff6c9cf519fba68c3` (PR #127).

## DONE — repository/runtime and research foundation

- [x] Canonical GitHub `main` + Linode production path.
- [x] Keep real-money execution locked and deterministic risk veto authoritative.
- [x] Seal Frozen OOS from discovery/development authority.
- [x] Close SF1/SF2/SF3 with zero verified/promoted candidates without weakening gates.

## DONE — Strategy Factory v2 foundation

- [x] Separate broad discovery from strict verification authority.
- [x] Hard-cap raw candidates at 500, per-family candidates at 64, survivors at 30.
- [x] Register 8 executable causal families with exact deterministic 406-candidate pilot catalog.
- [x] Common causal D0 evaluator with fees/slippage.
- [x] Immutable campaign/candidate/trial accounting and behavioral fingerprints.
- [x] D0/D1/D2/D3 evidence zoning; D1/Frozen OOS remain closed.
- [x] Bind D0 only to inspected reusable M5 development corpus.
- [x] Prevent temporal-gap warmup leakage and reuse terminal trials on resume.
- [x] Production D0 source proved: 2,880 rows, 12 strata, `DISCOVERY_ONLY`, inspected reusable evidence.
- [x] PR #109: resume-safe all-strata D0 orchestration.
- [x] PR #110: clean-checkout source provenance.
- [x] PR #112: shared checkout `flock` for updater/operator D0 wrapper.
- [x] PR #115: behavioral cluster accounting and separate raw/spec/family/eligible/cluster counts.
- [x] PR #117: no partial/rejected aggregate selection economics.
- [x] PR #119: full finite D0 selection-metric schema required per complete stratum.
- [x] PR #121: Factory-specific survivor-freeze completeness/diversity boundary.
- [x] PR #122: rebuild survivor eligibility from immutable campaign/candidate/trial ledger; require terminal full-catalog D0 coverage.
- [x] PR #124: allow an immutable zero-survivor negative outcome after the same full-catalog prerequisite; forbid later rewrite into a winner.
- [x] PR #127 / issue #126: freeze exact `stratum_id -> materialized dataset_sha256` in campaign registration and require every candidate/stratum D0 trial to match it before either non-empty or zero-survivor freeze.
- [x] Keep campaign invocation non-public and non-automatic.

## EXACT D0 EVIDENCE

Latest exact production D0 source proof: merged PR #127 build `48bdb0fa95cb6b1ae6a32e3ff6c9cf519fba68c3`, Actions run `33498788797`, verify job `99827022315`, completed successfully.

- [x] exact-build wait succeeded;
- [x] existing-only D0 inspection succeeded;
- [x] declaration SHA `88365779d6821c1fb30372148bbcedbfadf11471843f57722723286a43cbc77c`;
- [x] dataset SHA `aa13bcfc111c00f6da19621353a3ca8044f58eca1ab95e837d9490a205aa72eb`;
- [x] candle SHA `6368c9f41ff635d2474860a8d4579fc00e57488871020a9df38222f32d9f4744`;
- [x] order-flow SHA `3398d17c48dd282c86a13a3ccf9daafcd2784e1e64732bb52c29b9b294e82da3`;
- [x] rows 2,880; windows/strata 12/12;
- [x] authority `DISCOVERY_ONLY`; provenance `INSPECTED_REUSABLE_DISCOVERY_DATA`;
- [x] fresh-confirmation evidence false; verification authority false;
- [x] D1/Frozen OOS/live closed/closed/locked.

This is source/readiness evidence only. The 406×12 campaign has not run.

## ACTIVE — SF4 prospective replication

- [x] Exact `s3_vsm_s150` and `s3_cex_s075` frozen without retuning.
- [x] New BTCUSDT USD-M interval preregistered: `2026-09-01T00:00:00Z` through `2026-09-13T00:00:00Z`.
- [x] SF3 pooling prohibited.
- [x] Conservative 48-test search budget carried forward.
- [x] Evaluation locked before `2026-09-13T00:00:00Z`.
- [ ] After unlock, evaluate only the frozen hypotheses on new data under the preregistered contract.

## DONE — pre-D1 survivor-freeze integrity

- [x] Factory freeze reconstructs evidence from immutable ledger state.
- [x] Full declared catalog must be terminal across exact registered D0 strata.
- [x] Campaign registration freezes the exact materialized dataset SHA for every declared D0 stratum before trial execution.
- [x] Freeze rejects missing, duplicate, unexpected-stratum or SHA-mismatched low-fidelity candidate/stratum trial provenance.
- [x] Non-empty survivors must be complete, non-rejected, behaviorally eligible and cluster-diverse.
- [x] Frozen selection binds source SHA, parent D0 declaration/dataset, exact stratum dataset SHAs, expected strata and fixed 0.90 threshold.
- [x] Empty survivor set is valid only after the same completeness and exact-stratum-provenance checks and is persisted immutably as a negative discovery outcome.
- [x] Existing empty outcome cannot later be rewritten to a non-empty winner under the same campaign.
- [x] Survivor freeze keeps D1, Frozen OOS and live authority false.

## NOW — D0 invocation

- [ ] When an authorized Linode shell path is available, invoke only `scripts/run_sfv2_d0_pilot_production_once.sh`.
- [ ] Do not add an unauthenticated public trigger to bypass shell-access limitations.
- [ ] Keep execution `DISCOVERY_ONLY`; no lifecycle/D1/Frozen-OOS/demo/live authority.

## NEXT — bounded D0 pilot

- [ ] Run/resume exact 406 candidates across all 12 declared D0 strata while checkout lock is held.
- [ ] Account for every performance-inspected candidate in immutable trial ledger.
- [ ] Record empirical raw/unique-spec/family/eligible/cluster counts after campaign execution.
- [ ] Apply higher-fidelity D0 racing only under the existing diversity/search contract.
- [ ] Nominate at most 30 discovery survivors; zero is valid.
- [ ] Freeze survivor outcome only through `freeze_d0_pilot_survivors()` after actual D0 evidence exists.

## THEN — hidden confirmation and strict verification

- [ ] Open D1 only through a separately authorized hidden-confirmation workflow after survivor freeze prerequisites pass.
- [ ] Account for broad-search/multiple-testing history.
- [ ] No post-hoc retuning of failed D1 survivors.
- [ ] D2 robustness only after confirmation survives.
- [ ] Robustness before D3 Frozen OOS.
- [ ] Forward paper and Binance Demo remain later execution stages, not verification authority.
- [ ] Real execution remains separately locked.

## FIXED RESEARCH-INTEGRITY RULES — DO NOT LOWER

- [x] causal/no-lookahead execution;
- [x] fees/slippage included;
- [x] dataset/source provenance and immutable evidence;
- [x] development/confirmation/OOS separation;
- [x] robustness before Frozen OOS;
- [x] profitability/expectancy/sample/cross-window/statistical gates preserved;
- [x] post-hoc-tuning and multiple-testing protection;
- [x] reused data cannot be relabelled fresh;
- [x] discovery ranking/survivor status has no promotion authority;
- [x] zero survivors remains acceptable;
- [x] deterministic risk veto remains independent of AI;
- [x] real-money execution stays locked.

## BLOCKED / GATED

- [ ] Production 406-candidate D0 invocation — connected project tools still do not expose an authorized Linode operator shell action; do not weaken access controls to work around this.
- [ ] Factory survivor freeze — mechanism is ready, but there is no production D0 campaign result yet.
- [ ] Factory D1 — separately gated; no authorization exists.
- [ ] SF4 evaluation before `2026-09-13T00:00:00Z` — intentionally fail-closed.
- [ ] M5 Frozen OOS — sealed until strict prerequisites pass.
- [ ] Real-money Binance orders — intentionally locked.

## Handoff rule

At meaningful session end, record exact commits, CI/production proof, risks and next action. Never convert execution plumbing, a discovery leaderboard, reused D0 evidence, a survivor, or a zero-survivor infrastructure outcome into a profitability/live-readiness claim.