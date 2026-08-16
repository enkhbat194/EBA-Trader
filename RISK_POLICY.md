# EBA Trader Risk Policy

## Purpose

Risk control has higher authority than strategy selection, AI analysis and profit targets.

## V1 hard defaults

These are conservative research defaults, not claims of optimality. They may only be changed after evidence from backtest, paper and shadow stages.

- Maximum risk per trade: **0.50% of account equity**
- Maximum daily realized loss: **2.00% of start-of-day equity**
- Maximum strategy/account drawdown: **8.00%**
- Maximum simultaneously open positions: **1**
- Futures/leverage: **disabled**
- Short selling: **disabled in BTC/USDT spot V1**
- Martingale / loss-size multiplication: **prohibited**
- Averaging down without an explicit validated strategy rule: **prohibited**

## Mandatory veto conditions

Any of the following produces `DENY` / `HALT`:

- market data is stale,
- exchange/account state cannot be reconciled,
- daily-loss limit is reached,
- maximum drawdown is reached,
- position size exceeds calculated risk budget,
- strategy proposal lacks a valid stop/invalidation level,
- estimated fees/slippage invalidate positive expectancy,
- volatility is outside the validated operating envelope,
- execution/API health is degraded,
- mode is not explicitly allowed for the requested action.

## Position sizing

V1 uses risk-based position sizing:

```text
risk_budget = equity * risk_per_trade
unit_risk   = abs(entry_price - stop_price)
raw_size    = risk_budget / unit_risk
```

The final quantity must also obey exchange minimums, available cash, fees and configured exposure caps.

## AI authority

AI may recommend `BUY`, `SELL`, `WAIT` or `NO_TRADE`, but the Risk Engine can only return:

- `ALLOW`
- `DENY`
- `HALT`

AI cannot override `DENY` or `HALT`.

## Promotion to real capital

Micro-live is forbidden until all conditions in `BACKTEST_PROTOCOL.md` are satisfied and the project state explicitly records approval.

## API security

Future live API keys must use least privilege:

- read: enabled only as needed,
- spot trading: enabled only for the bot subaccount,
- withdrawals: **disabled**,
- IP allowlist: **required where supported**,
- keys/secrets: environment or secret manager only, never Git.
