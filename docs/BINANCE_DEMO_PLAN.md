# M1 — Binance Demo Data Pipeline

## Goal

Connect EBA Trader to Binance Demo for BTC/USDT **market data only**. No execution client is allowed in M1.

## Dependency baseline

- Python: 3.12-3.14
- NautilusTrader: `1.230.0` stable
- Product: Binance Spot
- Instrument target: `BTCUSDT.BINANCE`
- Environment: Binance `DEMO`

## Safety rule

M1 must configure only a NautilusTrader Binance **data client**. It must not configure or register a Binance execution client/factory.

This means the M1 node can observe data but has no exchange order-submission gateway.

## Credentials

Use environment variables only:

```text
BINANCE_DEMO_API_KEY
BINANCE_DEMO_API_SECRET
```

Never paste credentials into source files, GitHub issues, commits or chat.

## Implementation steps

1. Validate installation of the pinned NautilusTrader stable wheel.
2. Create a Binance Demo data-client config for Spot.
3. Add a data-only Actor for `BTCUSDT.BINANCE`.
4. Subscribe to trade ticks first.
5. Add quote/order-book data only after the basic stream is stable.
6. Record timestamps and data freshness.
7. Feed stale/disconnect state into EBA Trader's deterministic safety layer.
8. Log data locally; do not submit orders.

## M1 acceptance criteria

- Node starts using Binance Demo endpoints.
- BTC/USDT trade ticks are observed.
- Incoming timestamps are logged.
- Disconnect/stale conditions are detectable.
- No execution client exists in configuration.
- No order-submission code path exists.
- Secrets remain outside Git.

## M2 preview

After M1 passes, build historical-data ingestion and a benchmark/backtest harness. Strategy development starts only after data integrity is verified.
