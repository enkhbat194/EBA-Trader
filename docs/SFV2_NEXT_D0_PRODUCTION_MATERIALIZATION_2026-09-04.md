# Strategy Factory v2 — Next D0 Production Materialization Contract

Date: 2026-09-04; operational state reconciled 2026-09-05.

## Purpose

This document records the production execution boundary for materializing the already-frozen next-D0 discovery corpus. It grants **data materialization only**. It does not grant performance evaluation, confirmation, Frozen OOS, SF4, Demo promotion, live execution or real execution authority.

## Frozen identities

- campaign: `sfv2-existing-data-low-turnover-v1`;
- design: `sfv2-next-existing-data-v1`;
- dataset-plan SHA-256: `c3ae7735f657d905c2931613062fa9091c72dd9458d7cdfae678a01bcea26171`;
- frozen catalog SHA-256: `0aa793ca70ba8719486ba6edae314c77803e1b87884665d17ec88019ec71654a`;
- catalog size: 128 candidates, 32 per family;
- prior inspected candidate count: 406;
- cumulative search-history count if evaluated: 534.

## Dataset boundary

- symbol: BTCUSDT;
- venue: Binance USD-M Futures;
- base interval: 1m;
- price bucket: 5.0;
- order-flow source: verified Binance public USD-M `aggTrades` archive;
- D0 windows: 10;
- first boundary: `2026-08-22T00:15:00Z`;
- last boundary: `2026-09-01T00:00:00Z`.

The first window begins at 00:15 because the causal order-flow feature requires one prior fully closed minute; required 00:14 remains outside M5 Frozen OOS. The final window ends exactly at SF4 start. This corpus is discovery-only and cannot be called fresh confirmation.

## Production execution boundary

`eba-sfv2-next-d0-materialization.service` is a local/root-side oneshot service.

Invariants:

- at most one frozen window per invocation;
- research state under `/var/lib/eba-trader/research/...`, outside Git checkout;
- service and deployment share `/run/lock/eba-trader-runtime-mutation.lock`;
- service resources are bounded;
- no public/PWA start/stop/materialize endpoint;
- data-builder source identity is pinned across the receipt sequence;
- a status receipt is written only after a complete window succeeds;
- final bundle SHA is written only after all ten receipts complete.

## Per-window receipt requirements

Every accepted window must bind:

- exact window/time range;
- exact feature row count;
- feature dataset SHA-256;
- deterministic workflow ID/manifest;
- candle acquisition/provenance;
- order-flow dataset/acquisition provenance and archive integrity/checksum evidence;
- causal timestamp alignment;
- frozen builder source identity.

If any required identity, causality or provenance check fails, the window is not complete.

## Confirmed preflight failure and PR #144 repair

Initial production telemetry proved the service was terminally failed:

- `activeState=failed`;
- `result=exit-code`;
- `execMainStatus=1`;
- start and exit both `2026-09-05 09:22:57 UTC`.

Root cause was deterministic: the source-contract hash referenced nonexistent `src/eba_trader/footprint.py`. The wrapper computed this identity before archive/network work, so `sha256_file()` failed immediately under `set -e`.

PR #144 repaired the path to actual `footprint_dataset.py` and completed the builder identity with direct feature-generation dependencies that had been omitted: core orderflow, alignment, divergence and response logic. Regression coverage now rejects duplicate/obsolete paths and requires every pinned path to exist.

No next-D0 status/receipt existed before this repair. Therefore the corrected complete source identity was established before any immutable first-window receipt could pin it.

After the first successful receipt exists, the frozen builder/source-contract files must not change between windows. A mismatch must fail closed. Unrelated documentation/UI work does not change the corpus identity.

## Read-only production proof and CI semantics

PR #141 added a read-only GitHub Actions proof that reads only `/api/app-info` and `/api/research/status`. PR #142 added sanitized systemd state so receipt absence can be distinguished from running/failed/unloaded service state without granting mutation authority.

PR #146 separates CI authority correctly:

- `main` and manual strict production proof remain fail-closed and authoritative;
- pull-request base-observation is non-authoritative and may report transport/TLS/network unreachability as a diagnostic instead of failing an unrelated docs/UI PR;
- workflow concurrency is isolated per PR/ref so one PR cannot cancel another PR or the main proof.

A PR transport timeout is not production-health evidence and is never converted into a success claim. Exact main strict proof remains required for production verification.

## PWA read-only progress surface

PR #147 added a Research / AI Lab next-D0 card that displays:

- completed/expected receipt count and percentage;
- service state;
- phase;
- next window when available;
- frozen source identity when a first receipt exists;
- `Performance evaluation: LOCKED`;
- `Fresh confirmation: NO · DISCOVERY ONLY`.

The PWA only reads `/api/research/status`. It has no materialization mutation endpoint. Even a future 10/10 state is explicitly not a verified profitable strategy.

## Current exact production checkpoint

Current main: `c8befb7799abbffc740399a941632fcdc0adb273`.

- Linode production bundle run `33966683041`: `success`.
- Strict next-D0 production proof run `33966683013`, job `101307967313`: `success`.
- Proof timestamp: `2026-09-05T12:41:42Z`.
- exact build reached production: yes;
- `productionHealthy=true`;
- next-D0 receipt/status: unavailable;
- completed windows: **0 / 10**;
- `datasetBundleSha256`: null;
- `sourceCodeSha`: null;
- service: loaded / `activating`;
- `result=success`;
- `execMainStatus=0`;
- service start: `2026-09-05 12:41:29 UTC`.

This proves the current materialization code/deployment and service start path are healthy at the strict checkpoint. It does **not** prove next-d0-01 completed.

## Immutable corpus receipt gate

Performance evaluation remains blocked until all ten windows are complete and validated. Then one immutable corpus receipt must bind:

- frozen dataset-plan SHA;
- frozen 128-candidate catalog SHA;
- all ten feature SHA-256 values;
- all ten workflow IDs;
- all ten row counts;
- candle/order-flow provenance for all ten windows;
- frozen builder source identity.

Only after this receipt is complete and frozen may a **separate explicit D0 evaluator authorization package** be created. D0 selection rules must be frozen before any performance inspection.

## Future research separation

Professional-strategy hypotheses, historical funding/OI/basis, multi-symbol research, a regime engine and any defensible L2/order-book plane belong to a later versioned campaign. They cannot be retrofitted into this frozen 128-candidate campaign after performance is observed.

## Research locks

Throughout materialization the following remain false/closed:

- `performanceEvaluationAllowed`;
- fresh-confirmation authority;
- verification authority;
- D1 opened;
- Frozen OOS opened;
- SF4 access before its time gate;
- Demo promotion authority;
- live execution;
- real execution.

No profitability, expectancy, sample, cross-window or statistical threshold may be changed after observing results. Fees/slippage and causal execution remain mandatory.

## Interpretation labels

- merged/tests-green materializer: **CODE READY**;
- exact deployed build + healthy strict production proof: **PRODUCTION VERIFIED**;
- current service start path: **EMPIRICALLY STARTED**;
- ten complete validated data receipts: **EMPIRICALLY MATERIALIZED/VERIFIED DATASET**, not strategy verification;
- D0 survivor: **DISCOVERY SURVIVOR**, not verified profitability;
- **VERIFIED PROFITABLE** remains unavailable until the full independent verification chain passes.
