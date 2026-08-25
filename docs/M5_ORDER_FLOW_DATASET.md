# M5 Historical Order-Flow Dataset

This batch converts Binance aggregate-trade records into deterministic, provenance-friendly research datasets and closed footprint windows.

## Binance aggregate-trade semantics

The parser uses the Binance aggregate-trade fields:

- `a` — aggregate trade ID;
- `p` — executed price;
- `q` — executed quantity;
- `T` — trade timestamp in milliseconds;
- `m` — buyer is maker.

Aggressor classification is therefore:

- `m = false` -> buyer was taker -> aggressive BUY;
- `m = true` -> buyer was maker -> seller was taker -> aggressive SELL.

This is executed-trade flow, not resting order-book depth and not proof of a hidden institutional order.

## Normalization and integrity

Records are ordered by aggregate trade ID. The normalizer rejects:

- duplicate IDs;
- conflicting duplicate IDs;
- timestamps that move backward after trade-ID ordering;
- malformed event fields.

Missing IDs are counted as `sequence_gap_count`. A cache may be written with gaps so acquisition defects can be inspected, but `require_research_ready()` rejects any dataset with gaps. Research must repair/re-download the range instead of silently backtesting incomplete order flow.

An empty dataset is also rejected for research.

## Content addressing and provenance

The normalized records are canonical JSONL. Their SHA-256 hash participates in the deterministic dataset ID. The manifest records:

- symbol and source;
- record count;
- first/last aggregate trade ID;
- start/end timestamp;
- sequence-gap count;
- records SHA-256;
- immutable records path.

`require_research_ready()` re-hashes the records file before research, so tampered or corrupted caches fail closed.

## Footprint windows

`FootprintDatasetBuilder` materializes fixed-width, closed windows. Events use `[start, end)` semantics: an event exactly at the boundary belongs to the next window. Empty windows are retained as neutral rows instead of disappearing.

Rows currently expose:

- buy volume;
- sell volume;
- delta;
- delta ratio;
- total volume;
- trade count;
- POC price bucket;
- cumulative delta.

The requested time range must align exactly to the configured window width.

## Anti-leakage rule

A completed footprint row can only be used at or after its `end_ms`. A strategy that wants an in-progress footprint must use a separate explicitly causal streaming feature contract; completed-window values must never be injected before close time.

## Next batch

1. Add an acquisition/client layer that pages historical Binance aggregate trades into this cache without sequence gaps.
2. Join closed footprint windows to candle datasets by timestamp with explicit availability time.
3. Add an allowlisted order-flow backtest adapter.
4. Run controlled candle-only vs candle+order-flow ablation experiments through the M4 gates.

Frozen OOS and all exchange execution remain locked.
