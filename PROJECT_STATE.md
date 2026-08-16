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
- Engine target: `nautilus_trader==1.230.0`
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
- [x] Free/local core validation completed on Python 3.13.5: **13 tests passed**
- [x] NautilusTrader stable release pinned to `1.230.0`
- [x] Official v1.230.0 Binance data-only example/API surface checked before integration
- [x] Deterministic `MarketDataHealth` freshness tracker added
- [x] Binance data-only probe added for `BTCUSDT.BINANCE`
- [x] `live_public` mode added: no Binance API key required
- [x] `demo` mode added: credentials accepted from environment variables only
- [x] Data-only node contains **no execution client / execution factory**
- [x] Quote, trade and 1-minute bar subscriptions configured
- [x] M1 runbook added at `docs/M1_BINANCE_DATA_PIPELINE.md`

## Infrastructure note

A GitHub Actions CI workflow was tested but GitHub did not allocate a runner because the account currently reports a billing/payment or spending-limit restriction. The workflow was removed to avoid repeated failed runs or unnecessary cost. Tests remain in the repository and free/local validation is the active bootstrap path.

## Current validation status

- Original deterministic core unit tests: **13/13 passed** on Python 3.13.5 in a local isolated validation copy.
- New M1 unit tests for data freshness and Binance probe configuration are committed but still need a full package test run after the trading dependency is installed.
- GitHub Actions: intentionally disabled until account billing/spending-limit status is resolved or a free runner path is chosen.
- Binance public REST reachability was independently confirmed on 2026-08-17, but the NautilusTrader WebSocket probe still needs runtime execution in an environment with outbound network access.
- Current ChatGPT container cannot perform external network/DNS access, so it cannot itself prove the WebSocket connection.

## In progress

- [ ] Execute `eba-binance-data` against Binance public Spot data.
- [ ] Capture first BTC/USDT quote/trade/bar evidence.
- [ ] Wire stale-data state into a hard Risk Engine veto.

## Next tasks — strict order

1. Run the committed data-only probe in a networked Python 3.12-3.14 environment.
2. Confirm `BTCUSDT.BINANCE` resolves and quote/trade/bar subscriptions stream correctly.
3. Feed `MarketDataHealth` into the Risk Engine so stale data always returns DENIED/NO_TRADE.
4. Add durable normalized market-data recording for research.
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

## Milestone status

### M0 — Safe research engine bootstrap

**Passed.**

Evidence:
- deterministic risk veto path exists,
- regime detector returns known enum states,
- `NO_TRADE` is first class,
- live execution is impossible by default configuration and risk policy,
- 13 unit tests passed in local validation.

### M1 — Binance data-only pipeline

**Implementation substantially complete; runtime validation pending.**

Implemented:
- pinned NautilusTrader dependency,
- public live and Demo data modes,
- environment-only Demo credential policy,
- BTC/USDT quote/trade/bar subscriptions,
- no execution client path,
- deterministic stale-data tracker,
- runbook and CLI entry point.

Remaining exit evidence:
- actual NautilusTrader WebSocket session receives/logs BTC/USDT events,
- stale-data tracker is connected to the Risk Engine hard-veto path.
