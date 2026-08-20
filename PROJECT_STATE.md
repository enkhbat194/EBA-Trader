# EBA Trader — Project State

_Last updated: 2026-08-21 (Asia/Ulaanbaatar)_

This is the authoritative cross-chat continuation record.

## Mission

Build a professional-grade autonomous trading system that validates market edges and strategies with
evidence, refuses low-quality trades, enforces deterministic risk limits, and only later gains
exchange execution after research/paper gates pass.

## Owner / infrastructure constraints

- The owner should not need to master a complex exchange UI.
- Complexity belongs in the engine; future UI stays minimal.
- Preserve state and decisions in the repo for cross-chat continuity.
- Bootstrap infrastructure budget is **$0 until edge evidence exists**.
- Replit is only a temporary runtime, not the development center.
- Deterministic risk authority always outranks strategy or future AI recommendations.

## Core system constraints

- Repo: `enkhbat194/EBA-Trader`
- Current research market: BTC/USDT Spot
- Primary exchange/data source: Binance; backup target: OKX
- Engine dependency: `nautilus_trader==1.230.0`
- Supported Python: 3.12–3.14; evidence validation target: Python 3.12
- `NO_TRADE` is a valid first-class outcome
- Real-money orders, futures and leverage: disabled
- AI cannot override deterministic risk controls

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
- [x] seven reproducible 2021/2023 Binance source gaps are explicitly allowlisted

## Evidence-window policy

Development discovery/research:
- `2021-01-01` → `2024-01-01` exclusive

Fixed reused development challenge:
- `2024-01-01` → `2025-01-01` exclusive
- This is **not pristine OOS** after V1/V2/V3 development.

Frozen holdout:
- `2025-01-01` → `2026-01-01` exclusive
- Status: **`LOCKED_NOT_ACCESSED`**

Forward future:
- 2026+ is reserved for evidence collected forward from a later PAPER/SHADOW freeze timestamp.

## Strategy evidence history

### Trend V1 — REJECTED

- Decision: `REJECT_DEVELOPMENT_CYCLE`
- Validation return: **-45.07%**
- Expectancy: **-$1.34/trade**
- Profit factor: **0.770**
- Severe-cost return: **-85.74%**
- Neighborhood positive expectancy: **0%**
- Risk layer: blocked
- Record: `docs/M2_TREND_V1_DEVELOPMENT_RESULT_2026-08-20.md`

### Trend V2 — REJECTED

- Decision: `REJECT_TREND_V2_SIGNAL_CYCLE`
- Validation return: **-17.53%**
- Maximum drawdown: **-22.90%**
- Closed trades: **101**
- Profit factor: **0.612**
- Expectancy: **-$1.74/trade**
- Positive-expectancy neighborhood variants: **0/9**
- Rolling positive-return / positive-expectancy / PF>1 folds: **11/30** each
- Risk layer: blocked
- Record: `docs/M3_TREND_V2_DEVELOPMENT_RESULT_2026-08-20.md`

### V3 Bull Pullback Recovery — REJECTED

Final pushed implementation branch head before M5:
`dfbddf944a462d499e4a9917ad842794c4319266`

- Decision: `REJECT_V3_SIGNAL_CYCLE`
- Full pytest before evidence: **157 passed**
- Ruff: **passed**
- Validation return: **-13.73%**
- Maximum drawdown: **-14.64%**
- Closed trades: **79**
- Profit factor: **0.612**
- Expectancy: **-$1.74/trade**
- Positive-expectancy neighborhood variants: **0/9**
- Rolling folds with trades: **21/30**
- Rolling positive-return / positive-expectancy / PF>1 folds: **4/30** each
- Gates: **7 PASS / 14 FAIL / 13 BLOCKED**
- Risk-sized layer: blocked, not run
- Record: `docs/M4_V3_DEVELOPMENT_RESULT_2026-08-21.md`

V1, V2, and V3 are retired for promotion. Do not rescue them with post-result parameter retuning.

## M5 — Edge Discovery Engine

Feature branch: `edge-discovery-engine`

Status: **PRICE/VOLUME V1 SEARCH SPACE FROZEN + IMPLEMENTATION IN PROGRESS**

M5 changes the research method:

`predeclare market events -> measure forward returns -> control costs/multiple testing -> require
cross-year stability -> fixed 2024 challenge -> only then consider a new strategy hypothesis`

M5 Price/Volume V1 frozen design:

- discovery uses 2021–2023 only;
- 2024 is a fixed reused development challenge;
- 2025 remains locked;
- 24 predeclared event candidates;
- 3 causal forward horizons: 4 / 16 / 48 15m bars;
- 72 total discovery hypothesis tests;
- signal at completed 15m close, hypothetical measurement starts at next 15m open;
- source-gap-reset ATR/VWAP/volume features;
- event cooldown: 4 bars;
- Base research friction: 30 bps round trip;
- Severe research friction: 70 bps round trip;
- yearly stability required in 2021, 2022, 2023;
- daily aggregation used before significance screening;
- Benjamini-Hochberg FDR correction across all 72 discovery tests, q <= 0.10;
- positive-direction survivors classify as `LONG_EDGE_CANDIDATE`;
- negative-direction survivors classify as `NO_TRADE_VETO_CANDIDATE` only, never short authority;
- no candidate can auto-generate or deploy V4.

Completed on the M5 branch:

- [x] `docs/M5_EDGE_DISCOVERY_PROTOCOL.md`
- [x] `docs/M5_EDGE_DISCOVERY_FREEZE.json`
- [x] `src/eba_trader/edge_discovery_policy.py`
- [x] `src/eba_trader/edge_discovery.py`
- [x] policy and causal/statistical unit tests
- [x] `eba-edge-discovery` CLI entry
- [x] Windows and Bash one-command runners
- [x] GitHub Actions Python 3.12 pytest/Ruff workflow
- [x] M5 worklog

## M5 next tasks — strict order

1. Run full repository pytest on Python 3.12.
2. Run Ruff on the same commit.
3. Fix implementation defects only; do not change the frozen 24 candidates, thresholds or gates.
4. Commit a green implementation.
5. On a clean tracked tree run `scripts/run_edge_discovery.ps1` on Windows.
6. The runner may read only the frozen 2021–2024 development datasets.
7. Preserve the first complete JSON result; the runner refuses to overwrite it.
8. If nothing survives, record `NO_STABLE_EDGE_FOUND`; do not invent a rescue filter.
9. If candidates survive, audit them before writing any V4 strategy contract.
10. Do not open 2025.

## Later research, not in Price/Volume V1

Funding/basis can be added only as a separately versioned edge-discovery family with explicit
historical-data provenance. Open-interest, liquidation, order-book, news/macro and AI inputs remain
later scope and must not contaminate the frozen M5 Price/Volume V1 run.

## Explicitly forbidden now

- opening or downloading the 2025 BTC holdout
- changing the M5 frozen search after seeing its first complete result
- using 2024 as if it were pristine OOS
- automatically turning an observed sign reversal into a new candidate
- paid permanent VPS
- real-money orders
- futures / leverage / short execution
- copy trading
- martingale / averaging down
- AI-controlled order submission
- strategy self-deployment
- API withdrawal permission
