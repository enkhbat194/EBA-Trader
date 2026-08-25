# M4 — Backtest Adapter, Worker and Evidence Flow

## Purpose

This slice connects the durable experiment queue to an existing research backtester without
allowing arbitrary strategy code to execute. It also makes every successful run traceable to
its immutable strategy specification, dataset bytes and source revision.

## Initial adapter allowlist

The first registered adapter is:

```text
ema_trend_v1
```

It wraps the existing `run_trend_backtest()` implementation. Unknown adapters fail closed.
Unknown specification fields and unknown experiment parameters also fail closed.

The adapter accepts an immutable strategy specification with these top-level fields:

```json
{
  "adapter": "ema_trend_v1",
  "fixed": {},
  "dataset": {
    "symbol": "BTCUSDT",
    "interval": "15m",
    "start_ms": 0,
    "end_ms": 0
  }
}
```

`fixed` values cannot be overridden by experiment parameters. This prevents a queued run from
silently changing fields that the strategy version declared immutable.

## Dataset gate

Before running the backtest the adapter:

1. loads the CSV through the existing validated candle loader;
2. validates exact interval-window coverage;
3. rejects duplicate or malformed candles through existing history validation;
4. blocks the frozen first-cycle BTCUSDT OOS window by default.

The generic worker has no flag that opens frozen OOS. A later OOS orchestrator must use a
separately authorized path after development freeze/gates.

## Evidence manifest

Every successful worker run creates a content-addressed evidence manifest with schema:

```text
eba-research-evidence-v1
```

The manifest records at least:

- experiment ID;
- strategy ID and immutable version;
- strategy specification SHA-256;
- experiment parameters and their SHA-256;
- resolved backtest configuration;
- dataset reference, byte size and SHA-256;
- exact dataset window metadata;
- adapter name/version;
- Git commit/source provenance;
- SHA-256 hashes of the numerical research source files;
- required backtest metrics.

The evidence ID is derived from the canonical manifest bytes. Evidence files are stored under
an experiment-specific directory and are not overwritten. A separate `evidence_records`
SQLite table indexes the artifact and its hashes.

Different source commits can therefore produce different evidence records even for the same
logical experiment identity; prior evidence remains intact.

## Queue worker flow

```text
claim queued experiment
        |
        v
load immutable strategy version
        |
        v
resolve allowlisted adapter + dataset
        |
        v
validate data / holdout boundary
        |
        v
run existing backtester
        |
        v
build + persist evidence manifest
        |
        v
mark queue PASSED with evidence:<id>
```

Configuration errors and unsupported adapters are terminal failures. Missing datasets and
unexpected infrastructure failures are retryable while the queue attempt budget remains.

## CLI

The package exposes:

```text
eba-research-worker
```

It can process one or more queued jobs with a configured research database, dataset root,
evidence directory, worker ID and optional stage filter. Dataset references are resolved under
the configured root; references that escape that root are rejected.

## Safety boundary

- No exchange order API is reachable from these modules.
- The runtime `TradeLedger` is not used.
- A successful backtest only marks its experiment `PASSED`; it does not promote the strategy.
- Strategy lifecycle promotion still requires separate gate logic and evidence checks.
- Frozen OOS remains closed in the generic worker.
- Real-money execution remains locked.

## Next slice

1. Automated development screening gates over persisted metrics/evidence.
2. Gate orchestration that promotes only sequential lifecycle states.
3. Cost-scenario and robustness experiment fan-out.
4. Separately authorized frozen OOS orchestration after strategy freeze.
