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

### Acquisition

- Direct `fapi.binance.com` from GitHub-hosted Azure returned HTTP 451; no proxy/bypass used.
- Completed audit used official `data.binance.vision` monthly USD-M archives.
- Every present ZIP was verified against Binance Vision `.CHECKSUM` before parsing.
- 48/48 monthly files existed for each audited family.
- 2025 remained `LOCKED_NOT_ACCESSED`.

### Frozen result

Decision: **`M6_DERIVATIVES_DATA_AUDIT_FAIL`**

| Source | Rows | Coverage / cadence | Result |
|---|---:|---|---|
| Funding rate | 4,383 | median 8h cadence | PASS |
| Perpetual futures 15m | 140,256 | 100.000% | PASS |
| Premium-index 15m | 139,582 | 99.51945%, max gap 96h | FAIL |
| Index-price 15m | 139,103 | 99.17793%, max gap 48h | FAIL |
| Premium/futures/index intersection | 138,621 | 98.83427% | FAIL |

Frozen kline requirement was >=99.90% coverage and <=12h maximum missing run. The thresholds are not
relaxed after observing the result.

Dataset SHA-256:
- funding: `73b9decde0d54a0609d55ccfd49131a6e825416b595d728457bb01a968b55fd6`
- futures: `3c97c9b59ded32595f129a480a23e920823c0edbbf2e4f32c5d66e5020e35947`
- premium: `807eba68834c016e89358feb40ee3bd1457216fe6e3121e232c83af7e2bc7bfb`
- index: `76201859297ec3ff18aa9a507e78ced7dd17b114ff097b8fb1529047f3b39603`

Completed historical audit provenance:
- source commit: `8a8b5c7d83d6be4bac69c8aea82c123f670e6e0f`
- Actions run: `32422829081`
- evidence artifact ID: `9426328736`
- artifact ZIP SHA-256: `d241e991131a7e0d32dc514cc88aa63aabd943d7f2d79e79cc2add0887bb1a4d`

### What M6 taught us

The four-source contract is rejected and cannot be rescued by weakening gates. However, funding and
perpetual-futures 15m price/activity independently passed their predeclared data-quality gates before
any forward-return edge search. Therefore they may be used in a **new separately frozen research
cycle**. Failed premium/index families are excluded from that next cycle.

Open-interest REST history and Binance REST basis remain excluded from long-horizon research because
their documented retention is too short. A future archival source would require a separate audit.

## Next cycle — M7 Funding + Futures Activity Edge Discovery

Strict order:

1. Branch from the closed M6 state; do not modify the M6 result.
2. Use only M6-PASS derivatives families: funding and perpetual futures 15m activity.
3. Existing validated Spot data may be used only for causal spot-return outcome measurement or an
   explicitly predeclared perpetual-versus-Spot derived feature; known Spot source gaps remain hard
   resets.
4. Predeclare a small, derivatives-specific candidate search before examining forward-return results.
5. Apply transaction-cost stress, cross-year/temporal stability and multiple-testing correction.
6. Treat 2021–2024 entirely as development; 2025 stays locked.
7. If no edge survives, close M7 without rescue tuning.
8. Only a surviving robust edge may lead to a separately frozen strategy contract.
9. Future AI Strategy Router may choose only among deterministic strategies that have already passed
   research/paper gates; deterministic Risk Engine remains superior authority.

## Explicitly forbidden now

- opening/downloading/inspecting 2025 BTC holdout
- retuning V1/V2/V3/M5/M6 after their result
- treating 2024 as pristine OOS
- using failed M6 premium/index families in M7
- real-money orders
- futures/leverage/short execution
- copy trading, martingale, averaging down
- AI-controlled order submission or strategy self-deployment
- API withdrawal permission
