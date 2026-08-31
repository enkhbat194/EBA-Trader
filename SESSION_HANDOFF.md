# EBA Trader — Session Handoff

_Last handoff prepared: 2026-09-01 (Asia/Ulaanbaatar)_

## Exact continuation point

Repository: `enkhbat194/EBA-Trader`

Canonical `main` at this handoff base:

`f9161ab091093d69f725b6b96ab6018443aaa6da`

Main commit:

`Strategy Factory v2: register executable pilot family catalog (#100)`

Exact-main proof:

- Linode runtime checks: **SUCCESS**;
- Linode production bundle: **SUCCESS**;
- continuity guard: **SUCCESS**;
- repository hygiene: **SUCCESS**.

No open pull requests existed before this reconciliation branch was created.

## Research status

### SF1 / SF2 / SF3

All three phases are closed with `NO_VERIFIED_CANDIDATE`. No candidate was promoted. Frozen OOS was
not opened.

SF3's two most informative clues remain non-verified:

- `s3_vsm_s150`: 10/12 baseline wins but negative mean return/expectancy and only 11 trades;
- `s3_cex_s075`: positive economics and adjusted p `0.046875`, but only 4 trades.

The 30-trade and other fixed gates were not lowered.

### SF4 prospective replication

PR #99 merged as `755bf719587c274570bf5c7258aaff74eb94d693`.

Two exact frozen hypotheses are being carried forward:

- `s3_vsm_s150` -> `s4_vsm_s150_replication`;
- `s3_cex_s075` -> `s4_cex_s075_replication`.

Prospective data window: `2026-09-01T00:00:00Z` through `2026-09-13T00:00:00Z`.
Evaluation is fail-closed before `2026-09-13T00:00:00Z`.

SF3 evidence cannot be pooled into the replication result. Parameters cannot be retuned. The
conservative prior search budget of 48 remains carried forward. Passing replication would only
justify a separately preregistered robustness phase.

## Strategy Factory v2 state

The discovery-only foundation is merged. PR #100 added the first executable family catalog and was
merged to `f9161ab...` with exact-head checks green.

Foundation includes:

- `DISCOVERY_ONLY` authority;
- 500 hard raw-candidate cap;
- 64 per-family cap;
- 30 survivor cap;
- deterministic candidate/spec identity;
- immutable campaign/candidate/trial ledger;
- dataset SHA and source-code SHA accounting;
- behavioral fingerprint/similarity/deduplication;
- behavioral cluster reporting;
- bounded family registry and deterministic quasi-random sampling;
- in-process batch evaluation and compute-budget stopping;
- immutable survivor freeze;
- D0/D1/D2/D3 data-zone separation;
- no lifecycle promotion, Frozen OOS, Demo-promotion or real-execution authority.

First executable pilot catalog:

1. ATR trailing — 30 variants;
2. Donchian breakout — 16;
3. z-score mean reversion — 64;
4. order-flow delta impulse — 40;
5. rolling flow trend — 64;
6. volume-shock momentum — 64;
7. VWAP reversion + flow — 64;
8. compression/expansion — 64.

Total declared raw candidate slots: **406**, deliberately below the 500 maximum.

## Current highest-priority implementation task

Build the common D0 discovery evaluator/adaptor layer.

Required behavior:

1. Map each of the 8 catalog families to its already-existing causal backtest engine; do not fork
   strategy semantics.
2. Normalize selection-only metrics such as net return, expectancy, trade count, drawdown, cost,
   benchmark delta, exposure and turnover where available.
3. Create actual `BehavioralFingerprint` output from candidate behavior.
4. Apply static/sanity rejection before performance ranking.
5. Run through `run_discovery_batch` so every inspected candidate is declared and immutable in the
   trial ledger with dataset SHA, source-code SHA, fidelity and compute accounting.
6. Add tests proving rejected/evaluated results remain immutable and raw/unique/cluster/family
   counts stay distinct.
7. Do not open D1 or Frozen OOS as part of this work.

After this layer is merged, declare/materialize D0 and run the bounded 406-candidate pilot. The
pilot may stop early for compute or novelty collapse. Zero survivors is valid.

## Hard locks

- M5 Frozen OOS (`2026-08-15 -> 2026-08-22` UTC) remains sealed/not opened.
- SF4 cannot be evaluated before its preregistered end time.
- Real Binance execution remains locked.
- Demo execution has no strategy-promotion authority.
- Development/discovery ranking has no promotion authority.
- Reused/inspected data cannot be called fresh confirmation evidence.
- A discovery survivor is not a verified strategy and cannot transition durable StrategyLifecycle.

## Startup rule

Read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`,
this file, `BACKTEST_PROTOCOL.md`, `docs/CONTINUITY_PROTOCOL.md` and
`docs/STRATEGY_FACTORY_V2_DESIGN.md`; then query actual GitHub/production proof before editing.
