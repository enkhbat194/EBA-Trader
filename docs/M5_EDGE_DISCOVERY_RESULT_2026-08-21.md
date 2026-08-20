# M5 Edge Discovery Price/Volume V1 — Final Development Result

Date: 2026-08-21
Branch: `edge-discovery-engine`
Implementation/result commit: `64cbcf27bca4534c1ecf4d173f20ac75f69203fd`

## Decision

`NO_STABLE_EDGE_FOUND`

The frozen M5 Price/Volume V1 search completed exactly once after implementation-only fixes. The frozen candidate set, thresholds, horizons, gates, costs, FDR threshold, data boundaries, and 2025 holdout lock were not changed after the search space was frozen.

## Verification

- Full pytest: **167 passed**
- Ruff: **PASS**
- Tracked worktree after run: **clean**
- First complete M5 report was preserved and not overwritten
- 2025 OOS: **`LOCKED_NOT_ACCESSED`**

## Search result

- Predeclared candidates: **24**
- Forward horizons per candidate: **3** (`4 / 16 / 48` 15m bars)
- Total discovery hypotheses: **72**
- `LONG_EDGE_CANDIDATE`: **0**
- `NO_TRADE_VETO_CANDIDATE`: **0**
- `OBSERVATION_ONLY`: **24**
- Discovery-passing horizons: **0 / 72**
- 2024 challenge-passing horizons: **0 / 72**

No M5 Price/Volume V1 candidate earned promotion to a strategy hypothesis.

## Evidence provenance

Local evidence path:
`artifacts/m5_edge_discovery_price_volume_v1.json`

Evidence SHA-256:
`a535d7c79576d92e0979a18f52b718d62885097953f0883bc1ac9f5b74595279`

## Research consequence

M5 is retired as a frozen search cycle. Do not rescue it by changing thresholds, adding post-result filters, reversing failed signals, or rerunning the same frozen search under altered rules.

The next research family must add materially new information rather than more price/volume threshold tuning. Candidate next inputs are derivatives market-state variables with separately audited historical provenance, such as BTCUSDT USDⓈ-M perpetual funding rate and premium/basis information. Open interest is not admitted until long-horizon historical provenance is separately demonstrated.

2025 remains untouched and cannot be used to rescue or select the next research family.
