# EBA Trader — Project State

_Last updated: 2026-08-21 (Asia/Ulaanbaatar)_

This is the authoritative cross-chat continuation record.

## Mission

Build an autonomous research-first trading system that only promotes deterministic strategies after
reproducible edge evidence, keeps `NO_TRADE` first-class, and always lets deterministic risk controls
overrule any future AI/router decision.

## Hard constraints

- Repo: `enkhbat194/EBA-Trader`
- Current market focus: BTC/USDT Spot; derivatives data is research input only
- Python evidence target: 3.12
- Real-money orders, leverage, futures execution and short execution: disabled
- AI order submission / self-deployment: disabled
- 2021-01-01 through 2025-01-01 exclusive is development/research data
- 2024 is reused development data, not pristine OOS
- Frozen 2025 holdout: **`LOCKED_NOT_ACCESSED`**
- Do not rescue failed cycles with post-result parameter tuning

## Completed infrastructure

- M0 safe bootstrap, deterministic Risk Engine, LIVE locks
- M1 public Binance data pipeline and stale-data veto
- M2 historical downloader, integrity checks, causal next-open semantics, fees/slippage, benchmarks,
  robustness tooling, provenance binding, final-freeze/OOS safeguards
- known 2021/2023 Binance Spot source gaps explicitly allowlisted; unexpected gaps fail closed

## Closed strategy/search cycles

### Trend V1 — REJECTED

- return: -45.07%
- expectancy: -$1.34/trade
- PF: 0.770
- severe return: -85.74%
- neighborhood positive expectancy: 0%
- risk layer blocked

### Trend V2 — REJECTED

- return: -17.53%
- MDD: -22.90%
- 101 trades
- PF: 0.612
- expectancy: -$1.74/trade
- positive-expectancy neighborhood: 0/9
- rolling positive return/expectancy/PF>1: 11/30 each
- risk layer blocked

### V3 Bull Pullback Recovery — REJECTED

- final branch head before M5: `dfbddf944a462d499e4a9917ad842794c4319266`
- pytest: 157 PASS; Ruff PASS
- return: -13.73%
- MDD: -14.64%
- 79 trades
- PF: 0.612
- expectancy: -$1.74/trade
- neighborhood: 0/9
- rolling positive return/expectancy/PF>1: 4/30 each
- gates: 7 PASS / 14 FAIL / 13 BLOCKED
- risk layer blocked

### M5 Price/Volume Edge Discovery V1 — CLOSED / NO STABLE EDGE

Branch: `edge-discovery-engine`
Final implementation/result commit: `64cbcf27bca4534c1ecf4d173f20ac75f69203fd`

- pytest: 167 PASS; Ruff PASS
- frozen search: 24 candidates × 3 horizons = 72 tests
- `LONG_EDGE_CANDIDATE`: 0
- `NO_TRADE_VETO_CANDIDATE`: 0
- discovery-passing horizons: 0/72
- 2024 challenge-passing horizons: 0/72
- decision: `NO_STABLE_EDGE_FOUND`
- evidence SHA-256: `a535d7c79576d92e0979a18f52b718d62885097953f0883bc1ac9f5b74595279`
- record: `docs/M5_EDGE_DISCOVERY_RESULT_2026-08-21.md`

## M6 Derivatives Historical Data Audit — CLOSED / FULL CONTRACT FAIL

Branch: `m6-derivatives-data-audit`
Record: `docs/M6_DERIVATIVES_DATA_AUDIT_RESULT_2026-08-21.md`

M6 added no strategy. It audited whether materially new USD-M derivatives information was clean
enough for 2021–2024 research.

### Acquisition and result

- Direct `fapi.binance.com` from GitHub-hosted Azure returned HTTP 451; no proxy/bypass used.
- Completed audit used official `data.binance.vision` monthly USD-M archives.
- Every present ZIP was verified against Binance Vision `.CHECKSUM` before parsing.
- 48/48 monthly files existed for each audited family.
- 2025 remained `LOCKED_NOT_ACCESSED`.
- decision: **`M6_DERIVATIVES_DATA_AUDIT_FAIL`**

| Source | Rows | Coverage / cadence | Result |
|---|---:|---|---|
| Funding rate | 4,383 | median 8h cadence | PASS |
| Perpetual futures 15m | 140,256 | 100.000% | PASS |
| Premium-index 15m | 139,582 | 99.51945%, max gap 96h | FAIL |
| Index-price 15m | 139,103 | 99.17793%, max gap 48h | FAIL |
| Premium/futures/index intersection | 138,621 | 98.83427% | FAIL |

Frozen kline requirement was >=99.90% coverage and <=12h maximum missing run. The thresholds were not
relaxed after observing the result. Only funding and perpetual-futures activity were permitted into a
new search cycle; failed premium/index families stayed excluded.

## M7 Funding + Futures Activity Edge Discovery — CLOSED / NO STABLE EDGE

Branch: `m7-funding-futures-edge-discovery`
Result record: `docs/M7_FUNDING_FUTURES_EDGE_DISCOVERY_RESULT_2026-08-21.md`

M7 used only the M6-PASS derivatives families plus frozen Spot outcome data. The search was frozen
before results:

- 12 predeclared derivatives-specific candidates
- horizons: 4 / 16 / 48 15m bars
- 36 total discovery tests
- Base round-trip cost: 30 bps
- Severe round-trip cost: 70 bps
- same-direction unconditional Spot baseline uplift required: >=10 bps
- BH-FDR q <= 0.10 across all 36 tests
- cross-year economic/uplift stability required in 2021, 2022 and 2023
- 2024 used only as reused development challenge

Pre-evidence validation:

- deterministic tests: **191 passed**
- Ruff: **PASS**
- implementation-only fix commit: `67d10f26cfd4b5f7f8691c629a22d9328d21db57`

First complete frozen evidence:

- evidence workflow commit: `bbc6df7caf2bbf191710d3b975824e4d90980668`
- Actions run: `32424800002`
- decision: **`NO_STABLE_DERIVATIVES_EDGE_FOUND`**
- `LONG_EDGE_CANDIDATE`: **0**
- `NO_TRADE_VETO_CANDIDATE`: **0**
- `OBSERVATION_ONLY`: **12**
- discovery-passing candidate/horizons: **0/36**
- final discovery + challenge passing candidate/horizons: **0/36**
- evidence SHA-256: `0c341876395f573b6c82bb14a91763c2387b34a51d28066b30e773ceede20bf6`
- evidence artifact ID: `9427083252`
- 2025 OOS: **`LOCKED_NOT_ACCESSED`**

Key M7 diagnostics across 36 discovery tests:

- positive Base mean: 3/36
- positive Severe mean: 0/36
- positive Base median: 0/36
- >=10 bps baseline uplift: 12/36
- yearly stability gate: 0/36
- BH-FDR q <=0.10: 0/36

M7 is closed. The three positive-mean observations remain observations only and must not be promoted,
retuned or reversed into a strategy after the result.

## Next research decision

Do **not** create another price/volume/funding threshold search by minor parameter variation. M5 and M7
show that these predeclared families did not produce a cost-robust, temporally stable edge under the
current evidence standard.

Any next cycle must add materially new information or methodology and first prove historical data
provenance. Candidate research families include independently archived open interest, liquidation
history, order-book/microstructure history, cross-venue information, or macro/news state. No next
family may weaken prior gates merely to obtain a survivor.

Future AI Strategy Router remains later architecture: it may route only among deterministic strategies
that have already passed research and paper/shadow gates. The deterministic Risk Engine remains the
superior authority and `NO_TRADE` remains valid.

## Explicitly forbidden now

- opening/downloading/inspecting 2025 BTC holdout
- retuning V1/V2/V3/M5/M6/M7 after their results
- treating 2024 as pristine OOS
- using failed M6 premium/index families as if they passed
- promoting any M7 observation into a strategy without a new frozen contract
- real-money orders
- futures/leverage/short execution
- copy trading, martingale, averaging down
- AI-controlled order submission or strategy self-deployment
- API withdrawal permission
