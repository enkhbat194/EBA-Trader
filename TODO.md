# EBA Trader — TODO

Actual merged code, exact production evidence and latest explicit decisions override stale prose. Query `main`, open PRs and workflows before continuing.

## DONE — repository/runtime and research foundation

- [x] Canonical GitHub `main` + Linode production path.
- [x] Keep real-money execution locked and deterministic risk veto authoritative.
- [x] Seal Frozen OOS from discovery/development authority.
- [x] Close SF1/SF2/SF3 with zero verified/promoted candidates without weakening gates.

## DONE — Strategy Factory v2 foundation

- [x] Separate broad discovery from strict verification authority.
- [x] Hard-cap pilot raw candidates at 500, per-family candidates at 64 and survivors at 30.
- [x] Register 8 executable causal families with deterministic 406-candidate pilot catalog.
- [x] Common causal D0 evaluator with fees/slippage.
- [x] Immutable campaign/candidate/trial accounting and behavioral fingerprints.
- [x] D0/D1/D2/D3 evidence zoning; D1/Frozen OOS remain closed.
- [x] Bind D0 only to inspected reusable M5 development corpus.
- [x] Prevent temporal-gap warmup leakage and safely resume terminal trials.
- [x] Preserve a non-public invocation boundary; no PWA/HTTP research mutation endpoint.
- [x] Factory survivor freeze reconstructs exact registered candidate/stratum/dataset evidence.
- [x] Empty survivor set is a valid immutable negative outcome only after full-catalog terminal proof.

## DONE — Strategy Factory v2 D0 production campaign

Single-use request: `sfv2-d0-prod-20260901-v1`.

- [x] Fix the production trigger path without adding public mutation authority.
- [x] PR #132 removed the incorrect executable-bit gate on the bash-invoked D0 runner.
- [x] Exact production build/source SHA: `bdb84a4a926dac53d13116364e8315e98b35e6e1`.
- [x] Official production campaign proof: Actions run `33674168891`, run #3, `success`.
- [x] Evaluate all 406 candidates over all 12 frozen D0 strata.
- [x] Require all 4,872 candidate/stratum trials terminal before selection freeze.
- [x] Terminal trials: 4,872 / 4,872.
- [x] Complete candidates: 406.
- [x] Rejected candidates: 254.
- [x] Behaviorally eligible candidates: 152.
- [x] Behavioral clusters: 127.
- [x] Freeze deterministic D0 survivor selection.
- [x] Frozen survivor count: **0**.
- [x] Keep D1 closed because no candidate survived D0.
- [x] Keep Frozen OOS/live/real execution closed/locked.
- [x] Record closeout in `docs/SFV2_D0_PRODUCTION_RESULT_2026-09-03.md`.

The zero-survivor result is a valid negative discovery outcome. It must not be converted into a winner by lowering thresholds or rewriting the immutable selection.

## NOW — Strategy Factory next-search design

The first 406-candidate pilot failed on net economics, not merely on candidate count. The catalog intentionally used 406 of the 500 hard cap; the unused numeric headroom is not a quota.

- [ ] Produce a D0 postmortem that separates family/mechanism failure, activity, cost/turnover and behavioral diversity.
- [ ] Audit existing data planes and causal backtest engines before proposing new families.
- [ ] Prefer genuinely new mechanisms, data planes and/or execution horizons; do not pad the search with neighboring parameters from the failed eight families.
- [ ] Carry the 406 already inspected candidates forward in the broad-search/multiple-testing history.
- [ ] Keep any reused D0 evidence explicitly `DISCOVERY_ONLY` / contaminated for confirmation purposes.

## NEXT — versioned Factory campaign

- [ ] Version any next Factory campaign under a new campaign ID and deterministic seed/catalog.
- [ ] Predeclare its raw-candidate/search budget before performance evaluation.
- [ ] Freeze any future non-empty survivor set before D1 data can be opened.
- [ ] If a future campaign again yields zero survivors, accept the negative result rather than weakening gates.
- [ ] Design/version D1 hidden confirmation only for a future non-empty frozen survivor set.

## ACTIVE — SF4 prospective replication

- [x] Exact `s3_vsm_s150` and `s3_cex_s075` frozen without retuning.
- [x] New BTCUSDT USD-M interval preregistered: `2026-09-01T00:00:00Z` through `2026-09-13T00:00:00Z`.
- [x] SF3 pooling prohibited.
- [x] Conservative 48-test search budget carried forward.
- [x] Evaluation locked before `2026-09-13T00:00:00Z`.
- [ ] After unlock, evaluate only the frozen hypotheses on new data under the preregistered contract.

## GATED — hidden confirmation and strict verification

Current Factory D1 is not merely waiting for code: it is **not applicable to the closed D0 pilot because survivor count is zero**.

- [ ] Open D1 only through a separately authorized hidden-confirmation workflow.
- [ ] Require a dataset never consumed by discovery for D1 authority.
- [ ] Account for the full broad-search/multiple-testing history.
- [ ] Do not post-hoc retune failed D1 candidates.
- [ ] D2 robustness only after hidden confirmation survives.
- [ ] Robustness before D3 Frozen OOS.
- [ ] Forward paper and Binance Demo remain later execution stages, not verification authority.
- [ ] Real execution remains separately locked.

## FIXED RESEARCH-INTEGRITY RULES — DO NOT LOWER

- [x] causal/no-lookahead execution;
- [x] fees/slippage included;
- [x] dataset/source provenance and immutable evidence;
- [x] development/discovery/confirmation/OOS separation;
- [x] robustness before Frozen OOS;
- [x] profitability/expectancy/sample/cross-window/statistical gates preserved;
- [x] post-hoc-tuning and multiple-testing protection;
- [x] reused data cannot be relabelled fresh;
- [x] discovery ranking/survivor status has no promotion authority;
- [x] zero survivors remains acceptable;
- [x] deterministic risk veto remains independent of AI;
- [x] real-money execution stays locked.

## BLOCKED / TIME-GATED

- [ ] SF4 evaluation before `2026-09-13T00:00:00Z` — intentionally fail-closed.
- [ ] Factory D1 — no current survivor exists; a future campaign must first freeze a non-empty survivor set.
- [ ] M5/D3 Frozen OOS — sealed until strict prerequisites pass.
- [ ] Real-money Binance orders — intentionally locked.

## Handoff rule

At meaningful session end, record exact commits, CI/production proof, risks and next action. Never convert execution plumbing, a discovery leaderboard, reused D0 evidence, a survivor, or a zero-survivor infrastructure outcome into a profitability/live-readiness claim.
