# EBA Trader — TODO

This list is ordered by current priority. Actual GitHub/runtime state overrides stale prose; every session must query `main`, open PRs and workflows before continuing.

## NOW — Production truth / operator safety

- [x] Fix false `Server scanner: UNREACHABLE` incident reported from production iPhone UI.
- [x] Define missing `mt5PositionMarkup` and `paperPositionMarkup` helpers before `trade_detail.js` loads.
- [x] Make Fast Momentum heartbeat (`fastThreadAlive`, `fastRunning`, `lastFastScanAtMs`) authoritative for Settings scanner health.
- [x] Reserve `UNREACHABLE` for actual `/api/runner/status` fetch/API failure; renderer exceptions become `UI sync warning` instead.
- [x] Harden service-worker/static asset revalidation to reduce stale/mixed JavaScript after deploys.
- [x] Add regression coverage for renderer definition/load order, scanner error classification and PWA cache revalidation.
- [x] Merge PR #65 as `b1afa22fcfa459d2a8a3789291b74a0566041545`.
- [x] External exact-build production proof run `33111336161` PASS.
- [x] Public smoke run `33111336195` attempt 2 PASS after a transient deploy-time `/api/chart` 502 on attempt 1.

## COMPLETE — M5 isolated order-flow candidate cycle

- [x] Delta/CVD candidate tested; best Delta `0.2` still negative.
- [x] Stacked/diagonal imbalance tested; improved baseline but did not beat Delta.
- [x] Absorption/exhaustion tested; absorption remained negative, exhaustion produced zero trades.
- [x] Price/Delta divergence tested; all three thresholds produced the same losing trade.
- [x] Close the old `2026-08-01T00:00Z -> 04:00Z` single-window tuning cycle without an edge/promotion claim.

## COMPLETE — M5 chronological study policy

- [x] Seal development range `2026-07-01 -> 2026-08-15` UTC.
- [x] Seal separate M5 Frozen OOS `2026-08-15 -> 2026-08-22` UTC.
- [x] Keep legacy 2025 Frozen OOS independent and locked.
- [x] Pre-register 12 fresh non-overlapping four-hour development windows.
- [x] Exclude the already-inspected `2026-08-01 00:00Z -> 04:00Z` window from the fresh corpus.
- [x] Block normal M5 development acquisition from sealed M5 OOS before network access.
- [x] Merge PR #63.

## NOW — Resume existing PR #64, do not restart

PR #64 `M5: materialize resumable development corpus` already has implementation on branch `m5-development-corpus-materializer`.

- [ ] Query actual latest `main`, PR #64 head and workflows.
- [ ] Compare PR #64 existing diff against latest main (now includes scanner hotfix/continuity changes).
- [ ] Bring PR #64 branch forward without recreating or dropping its existing materializer work.
- [ ] Validate deterministic 12-window materialization identity.
- [ ] Validate immutable per-window checkpoints and final manifest.
- [ ] Validate interrupted-run resume behavior.
- [ ] Validate completed replay performs no unnecessary acquisition/build work.
- [ ] Validate workflow policy/phase/domain/range/order-flow source and feature CSV SHA-256 provenance.
- [ ] Keep archive order flow as the reproducible historical default unless existing PR evidence requires otherwise.
- [ ] Run full regression + Ruff + shell/deployment + Linode runtime + continuity checks.
- [ ] Fix every CI failure; require exact PR-head green workflows before merge.
- [ ] Merge PR #64.
- [ ] Deploy exact main to Linode.
- [ ] Materialize **only** the 12 pre-registered development windows.
- [ ] Verify 12/12 window evidence/hashes/provenance and resumable replay.
- [ ] Do not acquire/open the M5 Frozen OOS.

## NEXT — Multi-window Strategy Factory evaluation

- [ ] Build deterministic multi-window evaluator/aggregator over the materialized development corpus.
- [ ] Compare strategies across all registered development windows, not one cherry-picked sample.
- [ ] Require minimum activity/trade-count rules so zero-trade arms cannot rank as winners.
- [ ] Aggregate return, expectancy, drawdown, costs, exposure, trade count and consistency across windows.
- [ ] Add candidate-family/parameter provenance and immutable ranking evidence.
- [ ] Strengthen exact/near-duplicate filtering as hypothesis volume increases.
- [ ] Route survivors into existing M4 screening/robustness contracts.
- [ ] Require robustness before any Frozen-OOS consideration.

## LATER

- [ ] Build Verified Strategy Knowledge Base from full-path survivors.
- [ ] Build forward-paper strategy factory.
- [ ] Build Binance Demo execution laboratory.
- [ ] Add separate sequence-validated LOB/order-book data plane if research evidence warrants it.
- [ ] Build Market Brain/regime selector after enough independently verified strategies exist.
- [ ] Add strategy selector, portfolio selector, outcome attribution and drift monitoring.
- [ ] Define explicit shadow -> micro-live -> live gates only after required evidence exists.

## BLOCKED / GATED

- [ ] M5 Frozen OOS access.
  - Sealed and intentionally unavailable to normal development workflows.
  - Lifecycle v2 requires robustness-before-OOS and immutable passing evidence.

- [ ] Real-money Binance orders.
  - Intentionally locked pending demo/shadow/micro-live evidence chain.

- [ ] Resting LOB/order-book strategy claims.
  - Require a separate approved snapshot/diff reconstruction and sequence-integrity contract.
  - Do not infer resting/hidden liquidity from executed-trade footprint features.

## CONTINUOUS-WORK HANDOFF RULE

Before coding, read the canonical continuity files, query actual GitHub state, compare any active branch/PR to main, and resume existing work rather than duplicating it. At meaningful session end, record exact commits, PR/CI/production proof, unresolved risks and the next exact action.
