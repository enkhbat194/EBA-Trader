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

## Frozen V1 decisions

- Repository: `enkhbat194/EBA-Trader`
- Market: BTC/USDT
- Product: Spot
- Primary exchange target: Binance
- Backup exchange target: OKX
- Existing KuCoin account: not the V1 backend
- Engine target: NautilusTrader stable release
- Python: 3.12+
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

## In progress

- [ ] Python project scaffold
- [ ] Domain models
- [ ] Deterministic Risk Engine V1
- [ ] Regime Detector baseline
- [ ] Unit tests
- [ ] NautilusTrader/Binance Demo integration spike

## Next tasks — strict order

1. Build pure-Python domain core and tests.
2. Implement position-sizing and risk veto rules.
3. Implement baseline market-regime classifier without AI.
4. Add deterministic strategy proposal interface and `NO_TRADE` path.
5. Add NautilusTrader stable dependency and Binance Demo market-data adapter.
6. Record live public BTC/USDT data without placing orders.
7. Build historical-data ingestion and benchmark harness.
8. Implement first Trend Following baseline.
9. Run bias/cost-aware backtests.
10. Only after evidence: add other strategies and paper execution.

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

Exit criteria:
- package installs cleanly,
- unit tests pass,
- risk engine denies invalid proposals,
- regime detector returns known enum states,
- live execution is impossible by configuration/default code path,
- next milestone state is recorded here.
