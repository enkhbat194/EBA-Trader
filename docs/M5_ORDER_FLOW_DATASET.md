# M5 Historical Order-Flow Dataset

This M5 data plane converts Binance aggregate-trade records into deterministic, provenance-friendly research datasets and closed footprint windows. PR #30 extends the original cache with venue-aware acquisition, missing-ID repair, request provenance and causal candle alignment.

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

## Venue boundary

Order-flow data is venue-specific. The acquisition layer supports:

- Binance Spot aggregate trades;
- Binance USD-M Futures aggregate trades.

USD-M Futures is the default for the current BTCUSDT perpetual research target. Spot is an explicit alternate dataset and must not be silently mixed with futures flow in one experiment.

## Deterministic acquisition

`orderflow_acquisition.py` starts each requested `[start_ms, end_ms)` range with a time-bounded bootstrap request, then continues by aggregate-trade ID (`fromId = last_id + 1`). The normalized stored dataset is still content-addressed by its executed-event contents.

Acquisition provenance is persisted separately and records:

- exact endpoint / venue;
- requested start/end range;
- request mode (`time_bootstrap`, `from_id`, or `repair_from_id`);
- request parameters;
- response counts;
- first/last returned aggregate-trade IDs and timestamps;
- a deterministic SHA-256 over the request provenance;
- the resulting content-addressed dataset ID.

The CLI is `eba-download-orderflow`. It applies the existing first-cycle frozen-OOS holdout guard before acquisition. Downloading order-flow data is not an OOS-unlock mechanism.

## Normalization and integrity

Records are ordered by aggregate trade ID. The normalizer rejects:

- duplicate IDs;
- conflicting duplicate IDs;
- timestamps that move backward after trade-ID ordering;
- malformed event fields.

Missing IDs are counted as `sequence_gap_count`. `find_missing_id_ranges()` exposes the exact inclusive ID ranges and `repair_missing_id_ranges()` re-requests those ranges by `fromId`.

A repair attempt is not assumed successful. If any gap remains, `require_research_ready()` continues to reject the dataset. Research must never silently backtest incomplete order flow.

An empty dataset is also rejected for research.

## Content addressing and provenance

The normalized records are canonical JSONL. Their SHA-256 hash participates in the deterministic dataset ID. The dataset manifest records:

- symbol and source;
- record count;
- first/last aggregate trade ID;
- start/end timestamp;
- sequence-gap count;
- records SHA-256;
- immutable records path.

`require_research_ready()` re-hashes the records file before research, so tampered or corrupted caches fail closed.

The acquisition manifest complements rather than replaces this manifest: dataset identity describes *what data was stored*; acquisition provenance describes *how that range was requested and repaired*.

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

## Causal candle alignment

`align_closed_footprints_to_candles()` uses explicit availability time.

For a candle opening at `t`, the eligible footprint is the already closed window `[t-step, t)`. Its `end_ms` equals the candle `open_time_ms`, so it is known at the decision boundary.

The still-forming footprint `[t, t+step)` is never attached to that same candle. This prevents the candle-vs-order-flow ablation from gaining future-event leakage.

By default, missing prior footprint rows fail closed rather than silently dropping or imputing the candle.

## Next batch

1. Add an allowlisted M4 order-flow backtest adapter that consumes only approved, causally aligned footprint features.
2. Define candle-only and candle+delta/CVD strategy variants with identical execution/cost assumptions.
3. Run development ablations under the same fee, slippage and gate policy.
4. Preserve evidence/ranking for comparison, but keep survivor ranking as triage rather than lifecycle authority.
5. Keep frozen OOS closed until lifecycle ordering is explicitly reconciled.

All exchange order submission remains locked.
