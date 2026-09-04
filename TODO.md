# EBA Trader — TODO

Actual merged code, exact production evidence and latest explicit frozen decisions override stale prose. Query `main`, recent/open PRs and production workflows before continuing.

## DONE — Strategy Factory v2 first D0 campaign

Campaign `sfv2-discovery-pilot-v1`:

- [x] Freeze 406-candidate / 8-family catalog.
- [x] Evaluate 406 × 12 = 4,872 trials.
- [x] Reach 4,872 / 4,872 terminal trials.
- [x] Freeze survivor selection at **0 survivors**.
- [x] Keep D1/Frozen OOS/Demo promotion/live/real execution closed.
- [x] Complete immutable failure postmortem without rerunning or rewriting D0.
- [x] Preserve the zero-survivor result without lowering any gate.

There is still **no verified profitable strategy**.

## DONE — next-campaign design, engines and freezes

Campaign `sfv2-existing-data-low-turnover-v1`; design `sfv2-next-existing-data-v1`.

- [x] Audit current historical causal planes.
- [x] Keep funding/OI/basis/resting-book history outside this campaign until separately acquired/provenanced.
- [x] Freeze four new mechanism families: `mtf_trend_pullback_v1`, `breakout_retest_entry_v1`, `path_efficiency_persistence_v1`, `low_turnover_flow_persistence_v1`.
- [x] Implement all four causal family engines/adapters.
- [x] Implement causal closed-1m -> 5m/15m/60m aggregation.
- [x] Implement breakout-retest causal fill rules and low-turnover minimum-hold/cooldown behavior.
- [x] Inventory inspected/protected historical ranges.
- [x] Freeze next-D0 dataset plan outside M5 Frozen OOS and SF4.
- [x] Freeze exact deterministic 128-candidate catalog: 32/family.
- [x] Preserve 406 prior inspected candidates in search history; cumulative count becomes 534 if evaluated.
- [x] Freeze catalog SHA-256 `0aa793ca70ba8719486ba6edae314c77803e1b87884665d17ec88019ec71654a` before performance inspection.
- [x] Add no-lookahead/aggregation/retest/turnover/search-accounting regression coverage.
- [x] Keep performance evaluation disabled through all design/catalog/data-plan freezes.

## DONE — production next-D0 materialization plumbing

PR #140:

- [x] Add local-only `eba-sfv2-next-d0-materialization.service`.
- [x] Materialize at most one frozen window per invocation.
- [x] Use Binance USD-M verified public `aggTrades` archive.
- [x] Bind frozen dataset-plan/catalog identities.
- [x] Write per-window exact row count, feature SHA-256, workflow ID and provenance receipts.
- [x] Pin frozen builder source identity across the sequence.
- [x] Use shared `/run/lock/eba-trader-runtime-mutation.lock` so deploy/research cannot interleave checkout use.
- [x] Keep production research state outside the Git checkout.
- [x] Keep public/PWA mutation authority absent.
- [x] Keep performance/D1/Frozen-OOS/SF4/live/real authority closed.

PR #141/#142:

- [x] Add read-only exact-production next-D0 progress proof.
- [x] Add sanitized read-only systemd service state to distinguish running/failed/unloaded from receipt status.
- [x] Do not expose journal secrets or any start/stop/mutation action through the PWA/API proof surface.
- [x] Public production smoke run `33889836392` verified exact current main `be778b2b760402aa2d9df9a00841731708f1b77e` deployed and healthy at the public surface.

## NOW — empirically complete and freeze the 10-window D0 corpus

Frozen data plan:

- plan SHA-256 `c3ae7735f657d905c2931613062fa9091c72dd9458d7cdfae678a01bcea26171`;
- BTCUSDT Binance USD-M Futures;
- 1m base interval;
- 10 windows from `2026-08-22T00:15:00Z` through exactly `2026-09-01T00:00:00Z`;
- authority `D0_DATA_MATERIALIZATION_ONLY` / `D0_DISCOVERY_ONLY_NOT_CONFIRMATION`.

- [ ] Obtain terminal dedicated next-D0 proof for exact current main and inspect sanitized materializer service state.
- [ ] Materialize and validate next-d0-01.
- [ ] Materialize and validate next-d0-02.
- [ ] Materialize and validate next-d0-03.
- [ ] Materialize and validate next-d0-04.
- [ ] Materialize and validate next-d0-05.
- [ ] Materialize and validate next-d0-06.
- [ ] Materialize and validate next-d0-07.
- [ ] Materialize and validate next-d0-08.
- [ ] Materialize and validate next-d0-09.
- [ ] Materialize and validate next-d0-10.
- [ ] Confirm each window's exact row count, feature SHA-256, workflow manifest, candle provenance, order-flow provenance/checksum and causal timestamp validity.
- [ ] Freeze one immutable complete dataset receipt containing plan SHA, catalog SHA, 10 feature SHA values, 10 workflow IDs, row counts, provenance and frozen source-code SHA.

## BLOCKED — do not bypass

- [ ] 128-candidate performance evaluation is blocked until every frozen next-D0 dataset receipt is complete and one immutable corpus receipt is frozen.
- [ ] Factory D1 is blocked until a future D0 freezes a non-empty survivor set.
- [ ] M5/D3 Frozen OOS remains sealed until strict prerequisites pass.
- [ ] SF4 evaluation before `2026-09-13T00:00:00Z` is intentionally fail-closed.
- [ ] Real-money Binance orders remain intentionally locked.

## NEXT — explicit D0 evaluation authorization

Only after immutable dataset-receipt freeze:

- [ ] Freeze D0 selection rules before any performance inspection if not already frozen.
- [ ] Create a separate explicit evaluator/runner authorization package for the frozen 128 candidates and frozen 10-window corpus.
- [ ] Keep fees/slippage and all profitability/expectancy/sample/statistical gates unchanged.
- [ ] Evaluate all 128 frozen candidates.
- [ ] Freeze D0 survivor selection deterministically.
- [ ] Treat D0 survivor status as discovery only, never VERIFIED profitability.
- [ ] Accept survivor count 0 without adding neighboring candidates or weakening thresholds.

## ACTIVE — SF4 prospective replication

- [x] Frozen hypotheses preregistered independently from Factory D0.
- [x] Protected interval `2026-09-01T00:00:00Z -> 2026-09-13T00:00:00Z`.
- [x] Evaluation fail-closed before `2026-09-13T00:00:00Z`.
- [x] Retuning prohibited before evaluation.
- [x] SF3/SF4 evidence pooling prohibited.
- [ ] After unlock, evaluate only the exact frozen SF4 replication hypotheses under their preregistered contract.

## FUTURE — genuinely new data-plane research

Do not retrofit these post-hoc into the frozen 128-candidate campaign.

- [ ] Historical Binance funding-rate acquisition with exact availability timestamps and integrity hashes.
- [ ] Historical open-interest acquisition/alignment if venue history is defensible.
- [ ] Historical futures basis/premium plane.
- [ ] Historical resting-order-book plane only if sequence/integrity reconstruction is defensible.
- [ ] Predeclare any multi-symbol universe before cross-symbol performance ranking.

## FIXED RESEARCH-INTEGRITY RULES — DO NOT LOWER

- [x] causal/no-lookahead execution;
- [x] fees/slippage included;
- [x] dataset/source provenance and immutable evidence;
- [x] development/discovery/confirmation/OOS separation;
- [x] robustness before Frozen OOS;
- [x] profitability/expectancy/sample/cross-window/statistical gates preserved;
- [x] post-hoc tuning and multiple-testing protection;
- [x] reused data cannot be relabelled fresh;
- [x] discovery ranking/survivor status has no promotion authority;
- [x] zero survivors is acceptable;
- [x] deterministic risk veto remains independent of AI;
- [x] real-money execution stays locked.

## Handoff rule

At meaningful session end, record exact commits, CI/production proof, risks and next action. Never convert code readiness, execution plumbing, a discovery leaderboard, reused evidence or a D0 survivor into a verified-profitability claim.
