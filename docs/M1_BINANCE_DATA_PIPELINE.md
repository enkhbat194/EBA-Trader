# M1 — Binance Data-Only Pipeline

## Goal

Receive BTC/USDT Spot market data through NautilusTrader without enabling any order-execution client.

Pinned integration target: `nautilus_trader==1.230.0`.

## Safety invariant

M1 must never register a Binance execution client or execution-client factory. The node is market-data only.

## Modes

### `live_public` — default

Uses Binance production public Spot market data. No API key is required.

```bash
export EBA_BINANCE_DATA_ENV=live_public
python -m pip install -e '.[trading,dev]'
eba-binance-data
```

Expected subscriptions for `BTCUSDT.BINANCE`:

- instrument definition,
- quote ticks,
- trade ticks,
- 1-minute external bars.

Stop with Ctrl+C.

### `demo`

Uses Binance Demo endpoints and virtual infrastructure. Demo credentials must come from environment variables only.

```bash
export EBA_BINANCE_DATA_ENV=demo
export BINANCE_DEMO_API_KEY='...'
export BINANCE_DEMO_API_SECRET='...'
eba-binance-data
```

Never commit either credential.

## Why public data comes first

The first integration question is whether our data path is correct and stable, not whether orders can be sent. Public Spot data can be streamed without credentials in NautilusTrader 1.230.0, allowing us to verify symbol mapping, subscriptions and connection behavior before account access exists.

## Health policy

`MarketDataHealth` is a deterministic, exchange-independent freshness tracker.

Default design threshold: a continuously subscribed BTC tick feed older than 15 seconds is considered stale. A stale feed must later become a hard veto in the Risk Engine before any executable order path is introduced.

## M1 acceptance evidence

Before marking M1 complete, capture:

1. exact NautilusTrader version,
2. node startup log,
3. resolved `BTCUSDT.BINANCE` instrument,
4. received quote/trade/bar events,
5. clean shutdown,
6. simulated stale-data test,
7. proof that no execution client is configured.

## Not part of M1

- placing orders,
- account balance access,
- Futures,
- leverage,
- funding or liquidation streams,
- AI trade decisions,
- strategy profitability testing.
