# EBA Trader — Project State

_Last updated: 2026-08-17 (Asia/Ulaanbaatar)_

This file is the authoritative cross-chat continuation record. Update it whenever architecture, scope, progress, blockers or next tasks change.

## Mission

Create an autonomous professional-grade trading system that can analyze markets, choose among validated strategies, refuse low-quality trades, enforce hard risk limits and eventually execute through exchange APIs after evidence-based validation.

## User constraints / product intent

- The owner does not want to manually master a complex exchange UI before the system becomes useful.
- Front-end UI should remain simple; complexity belongs in the engine.
- The system should learn from historical bot/trading-system failure modes rather than copy a single retail bot strategy.
- The owner wants a real trading engine, not a decorative AI signal generator.
- Cross-chat continuity is mandatory; repo state must preserve decisions and next work.
- Avoid unnecessary paid infrastructure during bootstrap.

## Frozen V1 decisions

- Repository: `enkhbat194/EBA-Trader`
- Market: BTC/USDT
- Product: Spot
- Primary exchange target: Binance
- Backup exchange target: OKX
- Existing KuCoin account: not the V1 backend
- Engine target: NautilusTrader stable release
- Python: 3.12-3.14 compatibility target
- Timeframes: 5m execution, 15m signal, 1h regime
- Strategies: Trend Following, Mean Reversion, Breakout, Momentum, NO_TRADE
- AI role: research / analysis / critique only
- Risk authority: deterministic Risk Engine
- Live funds: disabled during bootstrap/research
- Futures/leverage: out of scope for V1

## Completed

- [x] Repository created as private
- [x] README initialized
- [x] Architecture documented
- [x] Risk policy documented
- [x] Strategy contract documented
- [x] Backtest/validation protocol documented
- [x] Secret-safe `.gitignore` added
- [x] Python project scaffold added
- [x] Core domain enums/models added
- [x] Trade-proposal invariants added
- [x] Deterministic Risk Engine V1 added
- [x] Position sizing and hard veto rules added
- [x] Live / micro-live mode locked by default
- [x] Baseline deterministic Regime Detector added
- [x] Strategy protocol and first-class `NO_TRADE` strategy added
- [x] Unit tests added for domain, risk, regime and config locks
- [x] Demo-only environment template added

## Infrastructure note

A GitHub Actions CI workflow was tested but GitHub did not allocate a runner because the account currently reports a billing/payment or spending-limit restriction. The workflow was removed to avoid repeated failed runs or unnecessary cost. Tests remain in the repository and free/local validation is the active bootstrap path.

## In progress

- [ ] Local/free validation of the scaffold
- [ ] NautilusTrader stable dependency validation
- [ ] Binance Demo market-data integration spike

## Next tasks — strict order

1. Validate the pure-Python core and test suite outside paid GitHub Actions.
2. Add/lock a tested NautilusTrader stable release.
3. Build Binance Demo **data-only** connectivity first.
4. Record BTC/USDT demo/live-public market data without placing orders.
5. Build historical-data ingestion and benchmark harness.
6. Implement first Trend Following baseline.
7. Run bias/cost-aware backtests.
8. Add Mean Reversion, Breakout and Momentum one at a time only after baselines exist.
9. Add paper execution after research metrics are credible.
10. Futures/crowding/liquidation work remains V2+.

## Explicitly not allowed yet

- real-money order placement,
- futures,
- leverage,
- copy trading,
- martingale,
- AI-controlled order submission,
- strategy self-deployment,
- API withdrawal permission.

## Current milestone

**M0: Safe research engine bootstrap**

Completed design/code criteria:
- deterministic risk veto path exists,
- regime detector returns known enum states,
- `NO_TRADE` is first class,
- live execution is impossible by default configuration and risk policy,
- unit tests are present.

Remaining M0 exit criteria:
- run the test suite successfully in a free/local environment,
- validate package installation,
- lock the next milestone dependency path,
- then advance to **M1: Binance Demo data pipeline**.
