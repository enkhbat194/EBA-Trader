# Strategy Factory v2 — first executable pilot family catalog

Date: 2026-09-01

## Decision

Use eight already-implemented causal strategy families for the first D0 discovery pilot. Do not
invent additional families merely to hit the 500-candidate hard cap.

The declared plan is **406 raw candidates maximum** across eight distinct mechanisms. The remaining
94 slots are intentionally unspent headroom. The pilot may stop earlier when behavioral novelty
collapses, economics are invalid, or compute budget is exhausted.

## Families

1. `atr_trailing_v1` — volatility-scaled trend persistence — 30 declared variants.
2. `donchian_breakout_v1` — channel breakout / faster channel exit — 16 variants.
3. `mean_reversion_z_v1` — downside z-score reversion — 64 sampled variants.
4. `orderflow_delta_impulse_v1` — executed-flow impulse — 40 variants.
5. `rolling_flow_trend_v1` — price trend plus persistent executed-flow confirmation — 64 variants.
6. `volume_shock_momentum_v1` — abnormal executed-volume continuation — 64 variants.
7. `vwap_reversion_flow_v1` — price/VWAP dislocation with flow reversal — 64 variants.
8. `compression_expansion_v1` — volatility compression followed by directional expansion — 64 variants.

All family parameter spaces are bounded and deterministic. The catalog maps each family to an
existing EBA causal backtest engine. No unrestricted AI-generated Python, Bayesian optimization or
genetic programming is enabled.

## Candidate accounting

- hard global raw-candidate cap remains 500;
- hard per-family cap remains 64;
- catalog declaration is 406, not 500;
- deterministic quasi-random sampling is used where the declared space is larger than the sample
  allocation;
- small complete spaces are enumerated deterministically through the existing sampler fallback;
- exact candidate IDs replay from the campaign seed and family definition;
- all performance-inspected candidates still count in the immutable discovery ledger.

## Authority

This catalog has `DISCOVERY_ONLY` purpose. A high-ranked D0 candidate remains unverified. Behavioral
novelty cannot rescue negative economics. Frozen OOS, Demo promotion, live execution and real-money
execution remain outside Strategy Factory v2 authority.

The separate SF4 prospective replication of `s3_vsm_s150` and `s3_cex_s075` continues independently
and is not part of this 406-candidate D0 search budget.
