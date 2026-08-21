# EBA Trader — Project State

_Last updated: 2026-08-21 (Asia/Ulaanbaatar)_

This is the authoritative cross-chat continuation record.

## Mission

Build an autonomous research-first trading system that only promotes deterministic strategies after
reproducible edge evidence, keeps `NO_TRADE` first-class, and always lets deterministic risk controls
overrule any future AI/router decision.

## Hard constraints

- Repo: `enkhbat194/EBA-Trader`
- Current execution focus: BTC/USDT Spot; derivatives/microstructure data is research input only
- Python evidence target: 3.12
- Real-money orders, leverage, futures execution and short execution: disabled
- AI order submission / self-deployment: disabled
- 2021-01-01 through 2025-01-01 exclusive is development/research data
- 2024 is reused development data, not pristine OOS
- Frozen 2025 holdout: **`LOCKED_NOT_ACCESSED`**
- Do not rescue failed cycles with post-result parameter or gate tuning

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

- direct `fapi.binance.com` from GitHub-hosted Azure returned HTTP 451; no proxy/bypass used
- completed audit used official `data.binance.vision` monthly USD-M archives
- every present ZIP was verified against Binance Vision `.CHECKSUM`
- 48/48 monthly files existed for each audited family
- decision: **`M6_DERIVATIVES_DATA_AUDIT_FAIL`**

| Source | Rows | Coverage / cadence | Result |
|---|---:|---|---|
| Funding rate | 4,383 | median 8h cadence | PASS |
| Perpetual futures 15m | 140,256 | 100.000% | PASS |
| Premium-index 15m | 139,582 | 99.51945%, max gap 96h | FAIL |
| Index-price 15m | 139,103 | 99.17793%, max gap 48h | FAIL |
| Premium/futures/index intersection | 138,621 | 98.83427% | FAIL |

Only funding and perpetual-futures activity were permitted into M7. Failed premium/index families
remain excluded.

## M7 Funding + Futures Activity Edge Discovery — CLOSED / NO STABLE EDGE

Branch: `m7-funding-futures-edge-discovery`
Result record: `docs/M7_FUNDING_FUTURES_EDGE_DISCOVERY_RESULT_2026-08-21.md`

- frozen search: 12 candidates × 3 horizons = 36 tests
- Base round-trip cost: 30 bps
- Severe round-trip cost: 70 bps
- same-direction unconditional Spot baseline uplift required: >=10 bps
- BH-FDR q <=0.10
- deterministic tests: 191 PASS; Ruff PASS
- authoritative Actions run: `32424800002`
- decision: **`NO_STABLE_DERIVATIVES_EDGE_FOUND`**
- `LONG_EDGE_CANDIDATE`: 0
- `NO_TRADE_VETO_CANDIDATE`: 0
- discovery-passing horizons: 0/36
- evidence SHA-256: `0c341876395f573b6c82bb14a91763c2387b34a51d28066b30e773ceede20bf6`

## M8 Alternative Derivatives Historical Data Audit — CLOSED / FAIL WITH ONE PARTIAL SOURCE

Branch: `m8-alt-derivatives-data-audit`
Result record: `docs/M8_ALT_DERIVATIVES_DATA_AUDIT_RESULT_2026-08-21.md`
Authoritative complete Actions run: `32433740347`
Authoritative source commit: `02889240376c915a330492bc0ceaca49ace8952c`
Evidence artifact ID: `9430097001`
Evidence JSON SHA-256: `1bcfd0f44917d608b0d0c413d22aa7ce851e55ee4d54b1b81f87f588682a887f`

M8 computed **no forward returns, PnL or strategy evidence**. It audited materially new positioning,
cross-venue and microstructure sources only.

### Primary results

| Source | Evidence | Result |
|---|---|---|
| Binance USD-M metrics 5m | 1461/1461 checksum-verified files, 420,167 rows, 99.8574% coverage | **FAIL** |
| Bybit 1h kline | official public V5 request returned HTTP 403 on GitHub runner | **ERROR / unqualified** |
| Bybit 1h open interest | HTTP 403 on GitHub runner | **ERROR / unqualified** |
| Bybit 1h account ratio | HTTP 403 on GitHub runner | **ERROR / unqualified** |
| Bybit funding | HTTP 403 on GitHub runner | **ERROR / unqualified** |
| Cross-exchange hourly alignment | no qualified Bybit rows; 0/35,064 aligned | **FAIL** |

Binance metrics failed despite adequate overall coverage because the frozen contract also requires no
conflicting duplicate timestamps, strict five-minute alignment, and every frozen metric value finite
and strictly positive. Evidence contained `2` conflicting duplicate timestamps, alignment violations,
and malformed/non-positive metric evidence. Frozen thresholds were not weakened.

The Bybit result is an execution-provenance access error, not proof that Bybit's history itself is bad.
Those datasets remain unqualified because M8 did not reproduce them in the authoritative environment.

### Secondary results

**Binance bookDepth 2023-2024: `PARTIAL_WINDOW_ELIGIBLE`**

- expected daily files: 731
- checksum-verified existing files: 728
- daily coverage: 99.589603%
- parsed rows: 20,685,850
- parse-error files: 0
- invalid rows: 0
- <=120s positive snapshot-gap ratio: 99.998066%

This is explicitly **not** full 2021-2024 evidence. It may only be used under a new, separately frozen
short-window research protocol that declares 2023-2024 before any forward-return computation.

**Binance liquidationSnapshot: `EXCLUDED_INCOMPLETE_HISTORY`**

- expected daily files: 1461
- existing official archive files: 0
- coverage: 0%

M8 final decision: **`M8_ALT_DERIVATIVES_DATA_AUDIT_FAIL`**.
2025 remained **`LOCKED_NOT_ACCESSED`**.

## Next research decision

Do not create another minor price/volume/funding/positioning threshold search. M5/M7 found no stable
edge, and M8 rejected its full-window positioning contract.

The one newly qualified information family is Binance `bookDepth`, but only for the fixed 2023-2024
partial window. The next legitimate research cycle, if pursued, should therefore be a **separate
microstructure/book-depth edge-discovery protocol** that is frozen before computing any forward
returns. It must explicitly use the shorter 2023-2024 development window and use rolling/temporal
validation appropriate to that reduced history. It must not silently promote bookDepth to 2021-2024.

A separate future transport/provenance audit may also test whether official Bybit public history can be
reproduced outside the GitHub-hosted environment; that is not a rescue of M8 and cannot alter the M8
result.

Future AI Strategy Router remains later architecture: it may route only among deterministic strategies
that have already passed research and paper/shadow gates. The deterministic Risk Engine remains the
superior authority and `NO_TRADE` remains valid.

## Explicitly forbidden now

- opening/downloading/inspecting 2025 BTC holdout
- retuning V1/V2/V3/M5/M6/M7/M8 after their results
- treating 2024 as pristine OOS
- using failed M6 premium/index families as if they passed
- promoting M7 observations into a strategy without a new frozen contract
- treating M8 bookDepth as full 2021-2024 evidence
- repairing/imputing rejected Binance metrics values to rescue M8
- treating Bybit HTTP 403 as a Bybit data-quality PASS or FAIL
- real-money orders
- futures/leverage/short execution
- copy trading, martingale, averaging down
- AI-controlled order submission or strategy self-deployment
- API withdrawal permission
