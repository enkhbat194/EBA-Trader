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

Development/research only:
- `2021-01-01` → `2025-01-01` exclusive
- 2021–2024 has now been reused across multiple development cycles and must not be described as pristine OOS.
- New research must use temporal/rolling stability inside this development window rather than pretending 2024 is untouched validation.

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

## M5 — Price/Volume Edge Discovery V1 — CLOSED / NO STABLE EDGE

Feature branch: `edge-discovery-engine`

Final implementation/result commit:
`64cbcf27bca4534c1ecf4d173f20ac75f69203fd`

Decision: **`NO_STABLE_EDGE_FOUND`**

M5 changed the research method from strategy-first to edge-first:

`predeclare market events -> measure forward returns -> control costs/multiple testing -> require
cross-year stability -> development challenge -> only then consider a strategy hypothesis`

Frozen M5 search:

- 24 predeclared price/volume event candidates
- 3 causal forward horizons: 4 / 16 / 48 15m bars
- 72 total discovery hypothesis tests
- Base research friction: 30 bps round trip
- Severe research friction: 70 bps round trip
- yearly stability required in 2021, 2022, 2023
- daily aggregation before significance screening
- Benjamini-Hochberg FDR correction across all 72 tests, q <= 0.10
- no candidate could auto-generate or deploy a strategy

Final M5 result:

- Full pytest: **167 passed**
- Ruff: **PASS**
- `LONG_EDGE_CANDIDATE`: **0**
- `NO_TRADE_VETO_CANDIDATE`: **0**
- `OBSERVATION_ONLY`: **24**
- Discovery-passing horizons: **0/72**
- 2024 challenge-passing horizons: **0/72**
- 2025 OOS: **`LOCKED_NOT_ACCESSED`**
- Evidence SHA-256: `a535d7c79576d92e0979a18f52b718d62885097953f0883bc1ac9f5b74595279`
- Record: `docs/M5_EDGE_DISCOVERY_RESULT_2026-08-21.md`

M5 is retired as a frozen search cycle. Do not rescue it by changing thresholds, adding post-result filters, reversing failed signs, or rerunning it under altered rules.

## M6 — Derivatives Information Edge Discovery — NEXT

M6 must add materially new information rather than more price/volume threshold tuning.

Primary candidate inputs for provenance audit:

- Binance BTCUSDT USDⓈ-M perpetual funding-rate history
- Binance BTCUSDT USDⓈ-M premium-index klines
- BTCUSDT perpetual-versus-spot basis derived only if both source series have complete, auditable timestamps
- futures activity/volume features only if historical coverage and fields are reproducible

Open interest is excluded from M6 until long-horizon historical provenance is independently demonstrated. News, macro, liquidation feeds, order-book history, and AI remain later research families.

### M6 strict order

1. Create a separately versioned derivatives-data audit branch from the closed M5 state.
2. Implement public-data download/cache code with the existing 2025 holdout guard applied before any network request.
3. Audit exact 2021–2024 coverage, timestamps, duplicates, gaps, source semantics, and reproducibility for each proposed derivatives series.
4. Record dataset hashes and reject any source that cannot provide reproducible historical coverage.
5. Do **not** freeze an edge search space until the data audit is complete.
6. After the audit, predeclare a small derivatives-informed search space and temporal validation protocol before examining candidate forward-return results.
7. Use 2021–2024 only as development data with rolling/walk-forward stability; do not relabel 2024 pristine OOS.
8. Keep 2025 `LOCKED_NOT_ACCESSED` throughout M6 development.
9. If M6 finds no stable edge, stop that family without rescue tuning.
10. AI strategy routing remains future architecture only after multiple deterministic strategies/edges earn evidence.

## Explicitly forbidden now

- opening or downloading the 2025 BTC holdout
- changing or rerunning M5 to rescue failed candidates
- using 2024 as if it were pristine OOS
- paid permanent VPS
- real-money orders
- futures / leverage / short execution
- copy trading
- martingale / averaging down
- AI-controlled order submission
- strategy self-deployment
- API withdrawal permission
