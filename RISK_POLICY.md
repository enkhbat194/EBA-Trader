# EBA Trader Risk Policy

## Purpose

Risk control has higher authority than strategy selection, AI analysis and profit targets.

## Active rule split

EBA Trader has two distinct risk scopes:

1. **Historical Spot research** — the earlier conservative BTC/USDT Spot evidence pipeline.
2. **Fast Momentum paper simulation** — a separate futures-style simulation used to measure whether small-margin leveraged setups have positive net expectancy after fees/slippage.

These scopes must not be confused. Paper leverage permission does **not** authorize real leveraged orders.

## Hard runtime defaults

- Maximum simultaneously open Fast Momentum paper positions: **1** initially.
- Paper margin test baseline: **$10**.
- Paper leverage tiers: **5x / 10x / 20x** for normal evaluation.
- 50x / 100x: **aggressive-demo research only** until lower tiers have evidence.
- Real futures/leverage order submission: **disabled**.
- Martingale / loss-size multiplication: **prohibited**.
- Averaging down without an explicit validated strategy rule: **prohibited**.
- Every entry must have a defined stop/invalidation rule.
- Fees and slippage must be included in net P&L.
- Leveraged paper records must include liquidation-distance/risk metadata.

Historical Spot risk defaults (0.50% risk per trade, 2% daily loss, 8% drawdown) remain part of the preserved research/evidence track and are not silently reused as claims of optimality for Fast Momentum.

## Mandatory veto conditions

Any of the following produces `DENY` / `HALT` for a new entry:

- market data is stale,
- runtime/API health is degraded,
- persistent state cannot be read/written reliably,
- an existing position conflicts with requested exposure,
- strategy proposal lacks a valid stop/invalidation level,
- fees/slippage invalidate the expected edge,
- spread/volatility is outside the tested operating envelope,
- requested leverage exceeds the allowed mode/tier,
- mode is not explicitly allowed for the requested action.

## Leveraged paper accounting

For a paper position:

```text
notional      = margin * leverage
gross_pnl     = signed_price_return * notional
net_pnl       = gross_pnl - entry_fee - exit_fee - slippage_cost
```

The engine must record at least:

- margin,
- leverage,
- notional,
- side,
- entry,
- current/exit,
- TP,
- SL,
- fees,
- slippage,
- gross P&L,
- net P&L,
- liquidation-distance estimate,
- exit reason.

## AI authority

AI may research, critique or explain a setup. It cannot bypass a deterministic `DENY` / `HALT`, cannot change hard risk limits at runtime, and cannot directly submit exchange orders.

## Promotion to real capital

Real execution remains locked until all of the following are true:

- paper execution is persistent across process/server restart,
- server and PWA show the same authoritative position/history state,
- order sizing/fees/slippage/risk calculations are tested,
- forward paper evidence is acceptable,
- the exchange execution adapter is separately tested,
- project state explicitly records a promotion decision.

## API security

Future live API keys must use least privilege:

- read permission only as needed,
- trading permission only when a live gate is explicitly opened,
- withdrawals: **disabled**,
- IP allowlist: **required where supported**,
- keys/secrets: server environment or secret manager only, never Git.
