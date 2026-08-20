# EBA Trader — Project State

_Last updated: 2026-08-20 (Asia/Ulaanbaatar)_

This is the authoritative cross-chat continuation record.

## Mission

Build a professional-grade autonomous trading system that validates strategies with evidence, refuses low-quality trades, enforces deterministic risk limits, and only later gains exchange execution after research/paper gates pass.

## Owner constraints

- The owner should not need to master a complex exchange UI.
- Complexity belongs in the engine; future UI stays minimal.
- Learn from historical bot failure modes instead of copying one retail strategy.
- Preserve state and decisions in the repo for cross-chat continuity.
- Bootstrap infrastructure budget is **$0 until edge evidence exists**.
- Replit is only a temporary runtime, not the development center.

## Core system constraints

- Repo: `enkhbat194/EBA-Trader`
- Market under current research: BTC/USDT Spot
- Primary exchange/data source: Binance; backup target: OKX
- Engine dependency: `nautilus_trader==1.230.0`
- Supported Python: 3.12–3.14; evidence validation target: Python 3.12
- Risk authority: deterministic Risk Engine
- `NO_TRADE` is a valid first-class outcome
- Real-money orders, futures and leverage: disabled
- AI/news/funding/basis inputs: later overlay only after a deterministic baseline earns evidence

## Completed infrastructure

### M0 — Safe bootstrap

- [x] architecture / strategy / risk / backtest contracts
- [x] deterministic Risk Engine + position sizing
- [x] LIVE/MICRO_LIVE locked by default
- [x] baseline regime / `NO_TRADE` architecture

### M1 — Binance data-only pipeline

- [x] public Binance data mode requiring no API key
- [x] no execution client in data path
- [x] quote/trade/bar subscriptions
- [x] stale-data hard veto
- [x] actual Binance BTC/USDT QuoteTick and TradeTick observed
- [x] M1 runtime connectivity passed

### M2 — Historical evidence and OOS safeguards

- [x] Binance public historical downloader
- [x] timestamp / duplicate / OHLC / interval-gap validation
- [x] causal signal-at-close / execution-next-open semantics
- [x] fee + slippage cost model
- [x] BTC buy-and-hold benchmark
- [x] return, drawdown, expectancy, profit factor, Sharpe, Sortino, exposure and cost metrics
- [x] base/adverse/severe cost scenarios
- [x] parameter-neighborhood and rolling temporal stability tooling
- [x] risk-sized execution gate
- [x] clean Git provenance binding
- [x] final-freeze and one-shot OOS safeguards
- [x] generic downloader blocks BTCUSDT 2025 overlap before network access
- [x] seven reproducible 2021/2023 Binance source gaps are explicitly documented/allowlisted; every other unexpected gap remains a hard failure

## Evidence-window policy

Development only:
- Research: `2021-01-01` → `2024-01-01` exclusive
- Validation: `2024-01-01` → `2025-01-01` exclusive

Frozen holdout:
- OOS: `2025-01-01` → `2026-01-01` exclusive
- Status: **`LOCKED_NOT_ACCESSED`**

Forward future:
- 2026+ is reserved for evidence collected forward from a later PAPER/SHADOW freeze timestamp; it cannot be relabeled pristine historical OOS.

## Strategy evidence history

### Trend V1 — REJECTED

Real development evidence was run on 2026-08-20.

- Decision: `REJECT_DEVELOPMENT_CYCLE`
- Validation return: **-45.07%**
- Expectancy: **-$1.34/trade**
- Profit factor: **0.770**
- Severe-cost return: **-85.74%**
- Neighborhood positive expectancy: **0%**
- Risk layer: blocked, not run
- 2025 OOS: `LOCKED_NOT_ACCESSED`
- Record: `docs/M2_TREND_V1_DEVELOPMENT_RESULT_2026-08-20.md`

### Trend V2 — REJECTED

Frozen regime-filtered volatility-aware breakout cycle was implemented and tested on 2021–2024 development data.

- Result commit: `0c108182eb778688570950ee92e0c13d1a16d4e7`
- Decision: `REJECT_TREND_V2_SIGNAL_CYCLE`
- Validation return: **-17.53%**
- Maximum drawdown: **-22.90%**
- Closed trades: **101**
- Profit factor: **0.612**
- Expectancy: **-$1.74/trade**
- 9 parameter-neighborhood variants with positive expectancy: **0/9**
- Rolling positive-return / positive-expectancy / PF>1 folds: **11/30 (36.67%)** each
- Signal gates: 9 PASS / 14 FAIL
- Risk gates: 13 BLOCKED, not run
- 2025 OOS: `LOCKED_NOT_ACCESSED`
- Record: `docs/M3_TREND_V2_DEVELOPMENT_RESULT_2026-08-20.md`

Trend V1 and Trend V2 are retired for promotion. Do not rescue them by post-result parameter retuning.

## M4 — V3 Bull Pullback Recovery

Feature branch: `v3-bull-pullback-recovery`

Status: **FROZEN + IMPLEMENTED, RUNTIME VALIDATION PENDING**

V3 is materially different from V1/V2:

`4h bull regime -> bounded 15m pullback below prior 24h rolling VWAP -> recovery confirmation -> next 15m open entry`

Frozen baseline includes:
- 4h EMA50/EMA200 bull regime with rising EMA200
- 15m ATR14
- prior 96-bar rolling VWAP and median volume
- 0.75–2.25 ATR pullback envelope
- 3-bar local-high recovery confirmation
- source-gap recovery veto
- swing-low + 0.25 ATR stop buffer
- stop-distance acceptance 0.75–3.0 ATR
- fixed 2R target
- 24-bar time exit
- 0.35% planned risk/trade in risk-sized layer
- 50% notional cap
- 1.5% UTC daily realized-loss entry halt
- 8% mark-to-market drawdown halt

Completed on the V3 branch:
- [x] hypothesis contract frozen by SHA-256
- [x] 34 predeclared pass/fail gates
- [x] policy/constants module
- [x] causal 4h resampling / ATR / VWAP / volume / recovery engine
- [x] next-open execution, stop/target, time/regime exit logic
- [x] source-gap fail-closed behavior for armed and pending setups
- [x] signal/allocation and risk-sized execution paths
- [x] 9-variant robustness neighborhood
- [x] rolling 180d-context / 30d-test temporal stability
- [x] regime-only recovery control
- [x] V3 evidence/verdict report generator
- [x] `eba-v3-development` command
- [x] Windows and Bash one-command development runners
- [x] GitHub Actions Python 3.12 pytest/Ruff workflow

Important: the latest complete branch has **not yet been proven green by a full runtime pytest/Ruff execution after the final bundled edits**. No V3 historical evidence result is claimed yet.

## V3 next tasks — strict order

1. Run full repository pytest on the latest V3 branch with Python 3.12.
2. Run Ruff on the same commit.
3. Fix only implementation defects; frozen V3 parameters/gates must not change.
4. On a clean tracked tree, run `scripts/run_v3_development.ps1` on Windows or `scripts/run_v3_development.sh` on Bash/Linux.
5. That runner may use only the frozen 2021–2024 datasets and must verify their hashes.
6. If any signal gate 1–21 fails: reject V3 and leave risk gates 22–34 blocked.
7. Run the risk-sized layer only if every signal gate passes.
8. Even if all 34 development gates pass, do **not** open 2025 automatically; first perform a separate final-freeze review.

## Explicitly forbidden now

- opening or downloading the 2025 BTC holdout
- changing V3 parameters after seeing V3 development evidence
- paid permanent VPS
- real-money orders
- futures / leverage
- copy trading
- martingale / averaging down
- AI-controlled order submission
- strategy self-deployment
- API withdrawal permission
