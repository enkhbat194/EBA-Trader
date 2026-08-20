# M6 Derivatives Data Audit Worklog — 2026-08-21

Branch: `m6-derivatives-data-audit`

## Goal

Determine whether materially new Binance USDⓈ-M derivatives information is reproducibly available
for the full 2021–2024 development window before defining any new edge search or strategy.

## Frozen audit contract

- Protocol: `docs/M6_DERIVATIVES_DATA_AUDIT_PROTOCOL.md`
- Protocol SHA-256: `e5ef3f512c815138d2d25e72c25dd9f946a51039190ec6d0aacc05a8f15bb785`
- Audit window: 2021-01-01 → 2025-01-01 exclusive
- 2025 OOS: `LOCKED_NOT_ACCESSED`
- Strategy generation: forbidden
- AI: excluded
- Live/futures execution: forbidden

## Core historical sources

1. funding-rate history — `/fapi/v1/fundingRate`
2. premium-index 15m klines — `/fapi/v1/premiumIndexKlines`
3. perpetual futures 15m klines — `/fapi/v1/klines`
4. index-price 15m klines — `/fapi/v1/indexPriceKlines`

The perpetual kline dataset preserves futures volume, quote volume, trade count, and taker-buy
base/quote volume for later activity-feature research if the audit passes.

## Retention-blocked Binance REST sources

- historical open-interest statistics — `/futures/data/openInterestHist`: current Binance docs limit
  availability to the latest 1 month.
- basis — `/futures/data/basis`: current Binance docs limit availability to the latest 30 days.

These are not silently substituted into 2021–2024 research. A later archival source would require a
separate provenance audit.

## Implemented

- frozen protocol and manifest
- protocol hash verification
- hard M6 development-window guard before network access
- funding-history pagination/download/cache
- premium-index 15m pagination/download/cache
- perpetual futures 15m pagination/download/cache
- index-price 15m pagination/download/cache
- cache SHA-256 recording
- funding cadence/range/value audit
- independent kline timestamp/OHLC/coverage/gap audits
- futures activity-field validation
- cross-source timestamp intersection audit
- synthetic perpetual/index basis calculation
- final decision: `ELIGIBLE_FOR_M6_EDGE_DESIGN` or `M6_DERIVATIVES_DATA_AUDIT_FAIL`
- Python unit tests
- Windows/Bash one-command runners
- GitHub Actions Python 3.12 pytest/Ruff validation
- CLI: `eba-m6-data-audit`

## Runtime rule

CI validates code only and does not perform the multi-year Binance download. The historical audit is
run locally on the clean M6 branch so the downloaded datasets remain in ignored `data/cache/m6/` and
the report remains in ignored `artifacts/`.

## Next strict step

1. Obtain green pytest + Ruff on the exact branch head.
2. Fix implementation defects only; do not relax the frozen audit thresholds after seeing data.
3. Run `scripts/run_m6_derivatives_audit.ps1` on the clean Windows worktree.
4. Inspect the generated data-audit report.
5. Only if decision is `ELIGIBLE_FOR_M6_EDGE_DESIGN`, write and freeze a separate derivatives-informed
   edge-discovery contract.
6. Never access 2025 automatically.
