# EBA Trader — Project State

_Last updated: 2026-08-17 (Asia/Ulaanbaatar)_

This is the authoritative cross-chat continuation record.

## Mission

Build a professional-grade autonomous trading system that validates strategies with evidence, refuses low-quality trades, enforces deterministic risk limits, and only later gains exchange execution after research/paper gates pass.

## Owner constraints

- The owner should not need to master a complex exchange UI.
- Complexity belongs in the engine; future UI stays minimal.
- Learn from historical bot failure modes instead of copying one retail strategy.
- Preserve all state/decisions in repo for cross-chat continuity.
- Bootstrap infrastructure budget is **$0 until edge evidence exists**.
- BestCode integration is deferred; V1 stays standalone.
- Replit is only a temporary network runtime, not the development center.

## Frozen V1

- Repo: `enkhbat194/EBA-Trader`
- Market: BTC/USDT Spot
- Primary exchange: Binance; backup target: OKX
- Engine: `nautilus_trader==1.230.0`
- Python: 3.12–3.14
- Runtime: standalone Linux/Python
- Paid 24/7 server: forbidden until edge evidence exists
- Timeframes: 5m execution / 15m signal / 1h regime target
- Strategies planned: Trend, Mean Reversion, Breakout, Momentum, NO_TRADE
- AI: research/analysis/critique only
- Risk authority: deterministic Risk Engine
- Real money / futures / leverage: disabled

## Completed

### M0 — Safe bootstrap

- [x] architecture / strategy / risk / backtest contracts
- [x] deterministic Risk Engine + position sizing
- [x] LIVE/MICRO_LIVE locked by default
- [x] baseline Regime Detector + first-class NO_TRADE
- [x] initial deterministic tests passed

### M1 — Binance data-only pipeline

- [x] NautilusTrader pinned and installed
- [x] public Binance data mode requiring no API key
- [x] no execution client in data path
- [x] quote/trade/bar subscriptions
- [x] stale-data hard veto
- [x] Replit Python 3.12.12 runtime validated
- [x] actual Binance BTC/USDT `QuoteTick` observed
- [x] actual Binance BTC/USDT `TradeTick` observed
- [x] M1 runtime connectivity **PASSED**

### M2A — Historical/backtest plumbing

- [x] Binance public REST historical downloader
- [x] timestamp / duplicate / OHLC / interval-gap integrity gates
- [x] exclusive end timestamps to prevent split-boundary leakage
- [x] Trend Following V1: long-only EMA 20/50 baseline
- [x] strict crossover semantics: no synthetic BUY merely because fast EMA is already above slow EMA at a window boundary
- [x] signal-at-close / execution-next-open
- [x] optional causal `trade_start_time_ms` gate: pre-start candles may warm indicators but cannot contribute trades/equity/benchmark/exposure
- [x] fee + slippage model
- [x] BTC buy-and-hold benchmark
- [x] total/annualized return, drawdown, expectancy, profit factor, avg win/loss, Sharpe, Sortino, exposure, costs
- [x] base/adverse/severe cost scenarios
- [x] earlier isolated M2 logic tests passed 10/10 before latest audit commits

### M2B — Robustness/evidence tooling

- [x] parameter neighborhood: fast EMA 15/20/25 × slow EMA 40/50/60
- [x] parameter-neighborhood stability report
- [x] neighborhood explicitly diagnostic-only for first cycle, not a tuning menu
- [x] rolling walk-forward: default 180d train / 30d test / 30d step
- [x] walk-forward parameter selection uses train data only
- [x] unseen test uses full causal train history as EMA warm-up context while all trading/performance starts at test boundary
- [x] causal regression test ensuring future test-tail changes cannot alter first-fold train selection
- [x] causal bull/bear/range historical regime diagnostics
- [x] trade PnL/win-rate/return breakdown by regime
- [x] fixed same-candle regime look-ahead bug: entry uses previous fully completed candle
- [x] regression test for same-open-timestamp leakage
- [x] `eba-validate-trend`
- [x] `eba-regime-report`
- [x] one-command `eba-development-study`
- [x] `eba-development-study` accepts no EMA override; first cycle is hard-locked to predeclared EMA 20/50
- [x] regression tests added for strict crossover, causal evaluation boundary and no development EMA override
- [x] methodology documented in `docs/M2B_ROBUSTNESS.md`

## Evidence-window policy

Development windows:
- research: `2021-01-01` → `2024-01-01` exclusive
- validation: `2024-01-01` → `2025-01-01` exclusive

Frozen holdout:
- OOS: `2025-01-01` → `2026-01-01` exclusive

Fresh future:
- 2026+ remains outside the first baseline cycle.

### Critical OOS lock

The old baseline design exposed 2025 together with development data. This was corrected before historical study execution.

- [x] `eba-baseline-study` opens research + validation only
- [x] 2025 OOS is not downloaded/exposed by preferred development study
- [x] development study fails closed if a 2025 OOS cache file already exists
- [x] development report records holdout cache absence
- [x] direct OOS use through baseline function is rejected
- [x] OOS cannot accept ad-hoc `--fast/--slow` overrides
- [x] `eba-freeze-oos-candidate` freezes only `development_report.frozen_baseline`
- [x] freeze file stores SHA-256 of the development evidence report
- [x] changing development evidence after freeze invalidates the freeze
- [x] frozen OOS requires separate `eba-oos-study --confirm-frozen`
- [x] OOS verifies frozen candidate still matches hashed development baseline
- [x] existing OOS report blocks rerun
- [x] retuning after OOS open is forbidden

## Preferred one-command development workflow

`eba-development-study` is the next real-data action.

It will:
1. verify no 2025 OOS cache exists;
2. download/cache only 2021–2024 development data;
3. run predeclared strict EMA 20/50 under base/adverse/severe costs;
4. run parameter-neighborhood fragility diagnostics on research data;
5. run causal walk-forward with train-history EMA warm-up and test-boundary trading gate;
6. run causal regime diagnostics on research and validation;
7. write `artifacts/m2_development_evidence.json`;
8. leave 2025 OOS `LOCKED_NOT_ACCESSED`.

## Current validation caveat

- M1 live public data is proven.
- Earlier isolated M2 logic tests passed.
- The newest strict-crossover/walk-forward/freeze/OOS-lock commits and their new tests have **not yet been executed as one complete suite in a synced Python environment**.
- No real historical BTC development evidence report has been generated yet.

## Next tasks — strict order

1. In one free networked runtime, sync/install latest repo and run full `pytest` once.
2. Run `eba-development-study` once; capture `artifacts/m2_development_evidence.json`.
3. Review research + validation evidence without touching 2025.
4. If EMA 20/50 is rejected, stop this cycle and create a new hypothesis without opening 2025.
5. If EMA 20/50 is retained, run `eba-freeze-oos-candidate` with no parameter arguments.
6. Then and only then run `eba-oos-study --confirm-frozen` once.
7. If OOS passes, move toward PAPER/SHADOW; if it fails, start a new research cycle without tuning against 2025.
8. Mean Reversion / Breakout / Momentum only after Trend baseline is understood.
9. Paid server only after forward evidence justifies it.
10. Futures/crowding/liquidation remains V2+.

## Explicitly forbidden now

- paid permanent VPS
- real-money orders
- futures / leverage
- copy trading
- martingale
- AI-controlled order submission
- strategy self-deployment
- API withdrawal permission
