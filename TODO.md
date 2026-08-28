# EBA Trader — TODO

Actual GitHub/runtime state overrides stale prose. Query `main`, open PRs and workflows before continuing.

## DONE — Repository hygiene

- [x] Reduce stale branch sprawl without deleting unique history.
- [x] Add automatic merged/archived branch pruning.
- [x] Preserve old unique experiment history under `archive/legacy-experiments-20260828`.
- [x] Add repository-hygiene CI for runtime DB/log/cache/artifact/raw-data/secret-like files.
- [x] Harden `.gitignore`, `AGENTS.md`, PR checklist and repository-hygiene documentation.
- [x] Merge PR #67 and PR #68.
- [x] Final branch list: `main`, active PR #64 branch, one history-only archive branch.
- [x] Exact current main production/public/external checks PASS.

## DONE — Production operator safety

- [x] Fix false red `Server scanner: UNREACHABLE` caused by missing UI renderer and incorrect error classification.
- [x] Make Fast Momentum heartbeat authoritative for scanner health.
- [x] Keep UI render errors separate from server reachability.
- [x] Production-verify the scanner-status hotfix.

## DONE — M5 study setup

- [x] Close Delta/stacked/absorption-exhaustion/price-delta-divergence single-window cycle without edge promotion.
- [x] Stop tuning new indicators on the already-inspected four-hour sample.
- [x] Seal chronological development and separate M5 Frozen OOS ranges.
- [x] Pre-register 12 fresh non-overlapping development windows.
- [x] Block normal development acquisition from sealed M5 Frozen OOS.

## NOW — Resume existing PR #64; do not restart

PR #64 `M5: materialize resumable development corpus` already contains the next implementation on `m5-development-corpus-materializer`.

- [ ] Compare PR #64 head `39cd2b6d...` against current `main` `52356778...`.
- [ ] Bring the existing branch forward without recreating/dropping its materializer implementation.
- [ ] Revalidate deterministic 12-window materialization identity.
- [ ] Revalidate immutable per-window checkpoints and final manifest.
- [ ] Revalidate interrupted-run resume and completed replay behavior.
- [ ] Revalidate policy/domain/range/source/hash provenance and fail-closed tamper behavior.
- [ ] Run exact-head full regression, Ruff, deployment/runtime, continuity and repository-hygiene CI.
- [ ] Fix every failure and merge PR #64 only when all required checks are green.
- [ ] Deploy exact merged main to Linode.
- [ ] Materialize **only** the 12 pre-registered development windows.
- [ ] Verify 12/12 hashes/provenance/sequence integrity and replay safety.
- [ ] Do not acquire/open M5 Frozen OOS.

## NEXT — Multi-window Strategy Factory evaluation

- [ ] Build deterministic multi-window evaluator/aggregator.
- [ ] Compare candidate strategies across all registered development windows.
- [ ] Require minimum activity/trade-count rules so zero-trade arms cannot rank as winners.
- [ ] Aggregate return, expectancy, drawdown, costs, exposure, trade count and consistency.
- [ ] Persist candidate/parameter provenance and immutable ranking evidence.
- [ ] Strengthen exact/near-duplicate filtering as hypothesis volume grows.
- [ ] Route survivors through existing M4 screening and robustness contracts.
- [ ] Require robustness before any Frozen-OOS consideration.

## LATER

- [ ] Verified Strategy Knowledge Base.
- [ ] Forward-paper strategy factory.
- [ ] Binance Demo execution laboratory.
- [ ] Separate sequence-validated LOB/order-book data plane if research evidence warrants it.
- [ ] Market Brain/regime selector after enough independently verified strategies exist.
- [ ] Strategy/portfolio selector, outcome attribution and drift monitoring.
- [ ] Explicit shadow -> micro-live -> live promotion gates only after required evidence exists.

## BLOCKED / GATED

- [ ] M5 Frozen OOS access — sealed; robustness-before-OOS required.
- [ ] Real-money Binance orders — intentionally locked.
- [ ] Resting LOB/order-book claims — require separate reconstruction/integrity contract.

## Handoff rule

Resume existing valid branch/PR work instead of rebuilding it. At meaningful session end, record exact commits, CI/production proof, risks and the next exact action.
