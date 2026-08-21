# M18 — Fee-Aware Execution Economics Protocol

Status: **ENGINEERING_VALIDATION / NO LIVE EXECUTION**

## Purpose

M18 does not rescue or retune the rejected M17 historical cash-and-carry result. Its purpose is to build the deterministic execution-economics layer needed before any future paper/shadow or live arbitrage work.

The engine answers one narrow question from a current market snapshot:

> After account-specific Binance commissions, current executable order-book depth, a reserved exit-slippage allowance, and a fixed safety buffer, is the currently visible quarterly futures premium large enough to be worth recording as a paper candidate?

The only outputs are `NO_TRADE` or `PAPER_CANDIDATE`. `PAPER_CANDIDATE` is **not** authorization to submit orders.

## Official Binance inputs

M18 uses only read-only/public endpoints:

- Spot account commission: signed `GET /api/v3/account/commission` for `BTCUSDT`.
- USDⓈ-M Futures user commission: signed `GET /fapi/v1/commissionRate` for the selected quarterly symbol.
- Spot order book: public `GET /api/v3/depth`.
- USDⓈ-M Futures order book: public `GET /fapi/v1/depth`.
- USDⓈ-M exchange information: public `GET /fapi/v1/exchangeInfo` to discover the nearest active `BTCUSDT_YYMMDD` delivery contract when a symbol is not explicitly supplied.

The signed commission endpoints require an API key and signature, but M18 never calls an order-placement, cancellation, transfer, withdrawal, or leverage-changing endpoint.

## Fee treatment

Spot fees are derived from the account-specific commission payload. For each side and liquidity role, M18 includes:

1. standard role commission (`maker` or `taker`),
2. standard side commission (`buyer` or `seller`),
3. special role + side commission,
4. tax role + side commission.

When Binance reports the BNB commission discount as enabled for both the account and symbol, the reported discount multiplier is applied only to the standard commission component. Special and tax commission are not discounted by M18.

USDⓈ-M Futures fees use the account-specific maker/taker commission returned for the selected delivery symbol. The first M18 screening path uses taker fees on both legs so simultaneous hedging is not credited with an unearned maker fill.

## Executable prices

For a requested BTC quantity:

- Spot entry buys BTC through the current ask book and computes actual depth-weighted VWAP.
- Delivery-futures entry shorts the same BTC quantity through the current bid book and computes actual depth-weighted VWAP.
- If either side cannot fill the requested quantity from the supplied depth, the decision is `NO_TRADE`.
- Quotes older than the policy freshness limit are `NO_TRADE`.

M18 never evaluates a headline best bid/ask when the requested size spans multiple levels.

## Screening economics

For equal BTC quantity `q`:

- spot entry notional = `q * spot_entry_vwap`
- futures entry notional = `q * futures_entry_vwap`
- fully funded capital denominator = spot entry notional + futures entry notional
- gross convergence value = `q * (futures_entry_vwap - spot_entry_vwap)`

The screening estimate then subtracts:

- actual account-specific taker fees for both entry legs,
- a reserve for both exit-leg fees using the same current account rates,
- a fixed exit-slippage reserve per exit leg,
- a fixed additional safety buffer on fully funded capital.

This is deliberately a screening estimate, not a guarantee of expiry settlement P&L. It does not model a settlement price or assume an order can be filled in the future at today’s price.

## Frozen engineering defaults

- depth limit: 100 levels
- maximum quote age: 1,500 ms
- requested BTC quantity default: 0.001 BTC
- exit-slippage reserve: 2.0 bps per exit leg
- additional safety buffer: 5.0 bps of fully funded capital
- minimum screening net edge for `PAPER_CANDIDATE`: 5.0 bps of fully funded capital
- entry mode: taker/taker only
- live execution: forbidden
- AI signal authority: forbidden

These defaults are engineering safety defaults, not an M17 historical search grid. A later research cycle must separately freeze any profitability hypothesis before historical outcomes are computed.

## Deterministic vetoes

M18 returns `NO_TRADE` when any of the following is true:

- missing or invalid commission payload,
- stale Spot or Futures book,
- insufficient Spot or Futures depth,
- non-positive visible futures premium after depth-weighted execution,
- invalid quantity or prices,
- screening net edge below the frozen minimum.

The existing deterministic Risk Engine remains superior to any future execution/router layer. M18 does not weaken the existing live-execution lock.

## Research boundary

M18 does **not**:

- rerun M17 with cheaper costs,
- inspect 2024 challenge outcomes that M17 blocked,
- inspect 2025,
- change M17 entry offsets,
- introduce a basis threshold into M17,
- assume maker fills after seeing results,
- place real orders.

2025 remains `LOCKED_NOT_ACCESSED`.

## Promotion path

1. Validate deterministic fee parsing, signing, depth VWAP, and veto behavior in CI.
2. Run read-only account-specific snapshots with no trading permissions required by this code path.
3. Record paper/shadow opportunities and realized hypothetical convergence separately.
4. Only if a materially justified research hypothesis exists, freeze a new profitability protocol before testing it.
5. Live execution remains blocked until a separately validated edge, pair-execution safety layer, reconciliation, kill switch, and deterministic Risk Engine integration all pass.
