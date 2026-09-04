# Strategy Factory v2 — Next D0 Production Materialization Contract

Date: 2026-09-04

## Purpose

This document records the production execution boundary for materializing the already-frozen next-D0 discovery corpus. It grants **data materialization only**. It does not grant performance evaluation, confirmation, Frozen OOS, SF4, Demo promotion, live execution or real execution authority.

## Frozen identities

- campaign: `sfv2-existing-data-low-turnover-v1`;
- design: `sfv2-next-existing-data-v1`;
- dataset-plan SHA-256: `c3ae7735f657d905c2931613062fa9091c72dd9458d7cdfae678a01bcea26171`;
- frozen catalog SHA-256: `0aa793ca70ba8719486ba6edae314c77803e1b87884665d17ec88019ec71654a`;
- catalog size: 128 candidates, 32 per frozen family;
- prior inspected candidate count: 406;
- cumulative search-history count if this D0 is evaluated: 534.

## Dataset boundary

- symbol: BTCUSDT;
- venue: Binance USD-M Futures;
- base interval: 1m;
- price bucket: 5.0;
- order-flow source: verified Binance public USD-M `aggTrades` archive;
- number of D0 windows: 10;
- first boundary: `2026-08-22T00:15:00Z`;
- last boundary: `2026-09-01T00:00:00Z`.

The first window deliberately begins at 00:15 because the causal order-flow feature requires one prior fully closed minute; the required 00:14 footprint remains outside M5 Frozen OOS. The final window ends exactly when the protected SF4 interval begins.

This corpus is discovery-only reused/inspected-era evidence and cannot be called fresh confirmation.

## Production execution boundary

PR #140 introduced a local-only root-side oneshot systemd materializer:

`eba-sfv2-next-d0-materialization.service`

Key invariants:

- at most one frozen window per invocation;
- research state lives under `/var/lib/eba-trader/research/...`, outside the Git checkout;
- service and deployment share `/run/lock/eba-trader-runtime-mutation.lock`;
- research cannot use the checkout while deployment mutates it, and deployment cannot mutate it while research holds the shared lock;
- service resources are bounded;
- there is no public/PWA start/stop/materialize endpoint;
- the frozen data-builder source identity is pinned across the receipt sequence;
- a status receipt is written only after a complete window build succeeds;
- the final bundle SHA is written only after all ten receipts are complete.

The production auto-update path may start the next-D0 service only after the first Strategy Factory v2 D0 is already terminal/complete and the next-D0 corpus is not complete. This start remains root-side and asynchronous to the web client.

## Per-window receipt requirements

Every terminal materialized window must bind at least:

- exact window identity/time range;
- exact feature row count;
- feature dataset SHA-256;
- deterministic workflow ID/manifest;
- candle acquisition/provenance identity;
- order-flow dataset/acquisition provenance and archive integrity/checksum evidence;
- required causal timestamp alignment;
- frozen builder source-code identity.

If any required identity or causal/provenance check fails, the window is not accepted as complete.

## Read-only production proof

PR #141 added a GitHub Actions production proof that reads only:

- `/api/app-info`;
- `/api/research/status`.

It checks exact production build identity, receipt phase/count and all downstream safety locks. It has no mutation authority.

PR #142 added sanitized read-only systemd state for `eba-sfv2-next-d0-materialization.service`. The purpose is to distinguish a missing first receipt from an explicit service failure or unloaded unit. It exposes only bounded service state such as load/active/sub-state, result, exit status and timestamps; it does not expose journal contents or systemd mutation actions.

## Immutable dataset receipt gate

Performance evaluation remains blocked until all ten windows are complete and independently validated. Then one immutable corpus receipt must bind:

- frozen dataset-plan SHA;
- frozen 128-candidate catalog SHA;
- all ten feature SHA-256 values;
- all ten workflow IDs;
- all ten row counts;
- candle/order-flow provenance for all ten windows;
- frozen builder source-code SHA/identity.

Only after this receipt is complete and frozen may a **separate explicit D0 evaluator authorization package** be created.

## Research locks

The following remain false/closed throughout materialization:

- `performanceEvaluationAllowed`;
- fresh-confirmation authority;
- verification authority;
- D1 opened;
- Frozen OOS opened;
- SF4 access;
- Demo promotion authority;
- live execution;
- real execution.

No profitability, expectancy, sample, cross-window or statistical threshold may be changed after observing results. Fees/slippage and causal execution remain mandatory.

## Interpretation labels

- Merged/tests-green materializer: **CODE READY**.
- Exact deployed build/read-only service proof: **PRODUCTION VERIFIED**.
- Ten complete validated data receipts: **EMPIRICALLY MATERIALIZED/VERIFIED DATASET**, not strategy verification.
- A D0 survivor: **DISCOVERY SURVIVOR**, not verified profitability.
- `VERIFIED PROFITABLE` remains unavailable until the full independent verification chain passes.
