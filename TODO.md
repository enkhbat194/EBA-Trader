# EBA Trader — TODO

Actual merged code, exact production evidence and latest explicit decisions override stale prose. Query `main`, open PRs and workflows before continuing.

## DONE — repository/runtime and research foundation

- [x] Canonical GitHub `main` + Linode production path.
- [x] Keep real-money execution locked and deterministic risk veto authoritative.
- [x] Seal Frozen OOS from discovery/development authority.
- [x] Close SF1/SF2/SF3 with zero verified/promoted candidates without weakening gates.
- [x] Strategy Factory v2 discovery/verification authority separation, immutable ledger and behavioral dedup.
- [x] D0/D1/D2/D3 evidence zoning with D1/Frozen OOS closed by default.

## DONE — Strategy Factory v2 first D0 campaign

Campaign: `sfv2-discovery-pilot-v1`.

- [x] Freeze deterministic 406-candidate / 8-family catalog under the 500 hard cap.
- [x] Bind D0 to inspected reusable M5 development evidence with causal warmup and content identity.
- [x] Evaluate 406 × 12 = 4,872 candidate/stratum trials.
- [x] Terminal trials: 4,872 / 4,872.
- [x] Complete candidates: 406.
- [x] Rejected candidates: 254.
- [x] Behaviorally eligible candidates: 152.
- [x] Behavioral clusters: 127.
- [x] Freeze D0 survivor selection with **0 survivors**.
- [x] Keep D1, Frozen OOS, Demo promotion, live and real execution closed/locked.
- [x] Record production result in `docs/SFV2_D0_PRODUCTION_RESULT_2026-09-03.md`.

## DONE — Package 1: immutable D0 failure postmortem

Production analysis build: `b822a9815f8f5cc42c674f849e5626d8b7022602`.

Production proof: `Strategy Factory v2 D0 failure postmortem proof`, run `33823539570`, job `100871190923`, `success`.

- [x] Read the closed 4,872-trial ledger without rerunning or rewriting D0.
- [x] Separate family activity, economics, turnover/cost and execution-delay diagnostics.
- [x] Confirm all 152 complete non-rejected candidates have non-positive net return, expectancy and benchmark-relative return.
- [x] Record 107 cost-sensitive diagnostic proxies without treating them as counterfactual winners.
- [x] Diagnose 6 families as `COST_SENSITIVE_PROXY` and 2 as `INACTIVE_OR_REJECTED`.
- [x] Identify ATR (~+5.26 bps) and Donchian (~+7.63 bps) next-open chase headwinds.
- [x] Identify order-flow delta impulse as a structural turnover/cost failure (20,227 trades across complete candidates).
- [x] Confirm mean reversion remains negative despite favorable pre-entry movement.
- [x] Preserve compression-expansion/volume-shock negative/inactive result without loosening thresholds.
- [x] Record canonical postmortem in `docs/SFV2_D0_FAILURE_POSTMORTEM_2026-09-04.md`.

There is still **no verified profitable strategy**.

## NOW — Package 2: next-campaign design and implementation gate

Design ID: `sfv2-next-existing-data-v1`.
Reserved future campaign ID: `sfv2-existing-data-low-turnover-v1`.
Authority: `DESIGN_ONLY`.

- [x] Audit current historical causal planes: USD-M candles/volume + executed orderflow/footprint.
- [x] Record historical funding/OI/basis/resting-book planes as unavailable until a separate causal acquisition package exists.
- [x] Reduce preliminary search budget to max **128 raw / 32 per family / 12 survivors** instead of scaling blindly toward 500.
- [x] Preserve all prior 406 inspected candidates in broad-search/multiple-testing history.
- [x] Freeze four mechanism slots: multi-timeframe trend pullback, breakout retest entry, path-efficiency persistence and low-turnover flow persistence.
- [x] Prohibit post-hoc neighboring variants of the eight failed first-pilot families.
- [x] Add fail-closed design validator; the design cannot authorize evaluation, D1, Frozen OOS, SF4 access or execution.
- [ ] Implement the four causal family engines/adapters.
- [ ] Implement causal 5m/15m/60m aggregation from closed 1m data.
- [ ] Implement family-specific order-availability/fill rules, including causal retest/limit semantics where used.
- [ ] Inventory every previously inspected/protected historical range and freeze a permissible slower-horizon D0 dataset contract.
- [ ] Freeze the exact deterministic <=128 candidate catalog and seed before performance evaluation.
- [ ] Add no-lookahead, fill-availability, cooldown/turnover and search-accounting regression tests.
- [ ] Only after all of the above are merged and green, consider a separate explicit D0 evaluation authorization.

Canonical design: `docs/SFV2_NEXT_CAMPAIGN_DESIGN_2026-09-04.md`.
Config: `config/sfv2_next_campaign_design_v1.json`.

## NEXT — genuinely new data-plane research

Do not mix this into the current design until acquisition/provenance is implemented.

- [ ] Historical Binance funding-rate acquisition with exact availability timestamps and integrity hashes.
- [ ] Historical open-interest acquisition/alignment if the venue/API history supports the required range and granularity.
- [ ] Historical futures basis/premium research plane.
- [ ] Historical resting-order-book plane only if sequence/integrity reconstruction is defensible.
- [ ] Predeclared multi-symbol universe before any cross-symbol performance ranking.
- [ ] Version a separate campaign for genuinely new data-plane mechanisms; do not retrofit them post-hoc into the current 128-cap design.

## ACTIVE — SF4 prospective replication

- [x] Exact `s3_vsm_s150` and `s3_cex_s075` frozen without retuning.
- [x] New BTCUSDT USD-M interval preregistered: `2026-09-01T00:00:00Z` through `2026-09-13T00:00:00Z`.
- [x] SF3 pooling prohibited.
- [x] Conservative 48-test search budget carried forward.
- [x] Evaluation locked before `2026-09-13T00:00:00Z`.
- [ ] After unlock, evaluate only the exact frozen hypotheses under the preregistered SF4 contract.

## GATED — hidden confirmation and strict verification

- [ ] Factory D1 remains sealed until a future campaign freezes a non-empty survivor set.
- [ ] D1 must use data never consumed by discovery.
- [ ] Full search/multiple-testing history must remain accounted for.
- [ ] D2 robustness only after hidden confirmation survives.
- [ ] Robustness before D3 Frozen OOS.
- [ ] Forward paper and Binance Demo remain execution stages, not verification authority.
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
- [ ] Next Factory D0 evaluation — blocked until dataset window + exact catalog are frozen and separately authorized.
- [ ] Factory D1 — no current survivor exists.
- [ ] M5/D3 Frozen OOS — sealed until strict prerequisites pass.
- [ ] Real-money Binance orders — intentionally locked.

## Handoff rule

At meaningful session end, record exact commits, CI/production proof, risks and next action. Never convert execution plumbing, a discovery leaderboard, a cost-recovery proxy, reused D0 evidence or a survivor into a profitability/live-readiness claim.
