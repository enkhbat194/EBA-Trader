# M12 Cross-Asset ETH→BTC Edge Discovery — Final Result

Date: 2026-08-21
Branch: `m12-cross-asset-eth-btc-edge`
Authoritative source commit: `5a04bf92c0c12ac0c1afd324dc4eda928437be5f`

## Decision

**`NO_STABLE_CROSS_ASSET_EDGE_FOUND`**

The first complete M12 result was generated from the frozen predeclared search contract. No candidate,
threshold, direction, horizon, cost assumption, gate, data boundary, or FDR rule was changed after the
search space was frozen.

No M12 observation is eligible for strategy generation, risk sizing, short execution, AI signal use,
or live deployment.

## Validation before evidence

- Python target: 3.12
- Full deterministic pytest suite: **PASS**
- Ruff: **PASS**
- Frozen M12 policy verification: **PASS**
- tracked worktree before evidence: clean
- 2025 OOS: **`LOCKED_NOT_ACCESSED`**

The only pre-evidence implementation correction after the initial CI run was a test-file line-length
style fix. Frozen M12 research semantics were unchanged.

## Frozen inputs reproduced and verified

ETHUSDT USD-M perpetual 15m, qualified by M11:
`69855dcaf2f34c2a529ddb7f83964fa61b39ed0a27ae8796a6c0eaafd5b744f5`

BTCUSDT Spot research 2021-2023:
`253c6ae35856e58e35df17eaa71caeea5caaa3681c38dd7214a2872afccd8d63`

BTCUSDT Spot reused development challenge 2024:
`3a96b6b668cfacb0fefabb8665675d4ca589cc712b0681fb57e7a13356eda0f2`

The authoritative workflow independently re-created the M11 ETH dataset from official Binance Vision
monthly archives and required the exact frozen SHA before M12 forward-return computation.

M10 ETH Spot history remained excluded.

## Frozen search

- candidates: **8**
- horizons: **4 / 16 / 48** 15m bars
- discovery hypotheses: **24**
- Base round-trip screening cost: **30 bps**
- Severe round-trip screening cost: **70 bps**
- same-direction unconditional BTC baseline uplift required: **>= 10 bps**
- BH-FDR threshold: **q <= 0.10** across all 24 tests
- discovery: 2021-2023
- reused challenge: 2024

## Result summary

- `LONG_EDGE_CANDIDATE`: **0**
- `NO_TRADE_VETO_CANDIDATE`: **0**
- `OBSERVATION_ONLY`: **8**
- discovery-passing horizons: **0 / 24**
- final discovery + challenge passing horizons: **0 / 24**

This was not a low-sample failure. The frozen candidates generally produced hundreds to thousands of
discovery events. Nevertheless, **all 24 discovery candidate/horizon tests had negative mean Base-net
signed return**, and every discovery test had **BH-FDR q = 1.0**.

Representative discovery results:

| Candidate | Horizon | Events | Mean Base net | Mean Severe net | Median Base net | Baseline uplift | FDR q |
|---|---:|---:|---:|---:|---:|---:|---:|
| `eth_1h_up_1_5` | 4 | 1,854 | -0.3084% | -0.7084% | -0.3213% | -0.0124% | 1.0 |
| `eth_1h_up_1_5` | 48 | 1,843 | -0.3285% | -0.7285% | -0.3392% | -0.0730% | 1.0 |
| `eth_1h_down_1_5` | 48 | 1,758 | -0.3732% | -0.7732% | -0.5019% | -0.0286% | 1.0 |
| `eth_relative_1h_outperform_1` | 4 | 1,131 | -0.2940% | -0.6940% | -0.2994% | +0.0020% | 1.0 |
| `eth_flow_1h_up_buy_confirm` | 48 | 368 | -0.1985% | -0.5985% | -0.3831% | +0.0570% | 1.0 |
| `eth_flow_1h_down_sell_confirm` | 48 | 526 | -0.3000% | -0.7000% | -0.3249% | +0.0446% | 1.0 |

Some isolated reused-2024 challenge observations had positive Base-net mean at the 48-bar horizon, for
example `eth_1h_up_1_5` and `eth_flow_1h_up_buy_confirm`. They are **not promotable evidence** because
their corresponding 2021-2023 discovery tests failed, their Severe-net challenge means remained
negative, and post-result selection from the challenge period is forbidden.

## Evidence provenance

- GitHub Actions run: `32438774152`
- artifact ID: `9431703188`
- evidence file: `artifacts/m12_cross_asset_eth_btc_edge.json`
- evidence SHA-256: `d79c8549ed9731cce081dc2957ad9db2f9a709b76ce1e6aed525f81be1a859c4`
- uploaded artifact ZIP SHA-256: `dc2963a2774232612c59187e9de49a5d5dc246e0767bac29d543d908a473e8a6`

## Research consequence

M12 is retired as a frozen failed edge-discovery family. Do not rescue it by lowering ETH impulse
thresholds, changing directions, adding a post-result filter, selecting only the favorable 2024
48-bar observations, changing costs, or opening 2025.

Across M2-M12 the project has now tested several materially different deterministic families without a
promotable cost-robust BTC edge: trend/pullback strategy hypotheses, BTC price-volume states,
funding/futures states, BookDepth microstructure, and qualified ETH-perpetual cross-asset states.

The correct current engineering decision is therefore **research-only / NO_TRADE / live blocked**.
Do not continue creating arbitrary M13/M14 searches merely to obtain a positive backtest. A new
research cycle should be opened only when there is a materially new, independently justified data
source or market mechanism that can be predeclared before outcome inspection.

## Holdout and deployment status

- 2025 OOS: **`LOCKED_NOT_ACCESSED`**
- strategy generation from M12: **FORBIDDEN**
- risk sizing from M12: **FORBIDDEN**
- short execution: **NOT AUTHORIZED**
- AI module: **EXCLUDED**
- live execution: **FORBIDDEN**
