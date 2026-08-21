# M13 ML Edge Engine — First Complete Frozen Result

Decision: `NO_STABLE_ML_EDGE_FOUND`

M13 tested whether a small deterministic supervised-ML search could turn the already-qualified BTC/ETH/futures/funding development inputs into a stable BTCUSDT Spot long / NO_TRADE edge after costs. It did not earn promotion.

## Authoritative evidence

- GitHub Actions run: `32446152844`
- Artifact: `9434173433`
- Evidence SHA-256: `84f39d0619ef96f668df34ca178680a3d84bb2f1f227dfab7c16cdb0910d5859`
- Artifact ZIP SHA-256: `d47080628c92de1548caee6bd9a5ba429a3e120dbd5845559cd5241dea2058a7`
- Evidence branch/head: `m13-ml-edge-engine` / `18a0d9d632531d679aa95d8c04e9ce77d17dbfe3`
- scikit-learn: `1.7.2`
- Full pytest: PASS (266 tests)
- Ruff: PASS
- Frozen contract verification: PASS
- 2025 OOS: `LOCKED_NOT_ACCESSED`

## Frozen search

- 19 causal features
- model families: logistic regression and histogram gradient boosting
- probability gates: 0.60 and 0.65
- horizons: 4, 16, 48 bars
- total configurations: 12
- walk-forward discovery predictions:
  - train 2021 → predict 2022
  - train 2021–2022 → predict 2023
- 2024 challenge was allowed only for discovery-passing configurations
- Base round-trip cost: 30 bps
- Severe round-trip cost: 70 bps
- BH-FDR threshold: q ≤ 0.10

Sample counts produced by the frozen causal pipeline:

- 2021: 8,737 hourly samples
- 2022: 8,760
- 2023: 8,758
- 2024: 8,783

## Gate summary

Across the 12 discovery configurations:

- mean Base-net > 0: 3/12
- mean Severe-net > 0: 0/12
- median Base-net > 0: 3/12
- Base-net profit factor > 1.10: 2/12
- both 2022 and 2023 mean Base-net > 0: 1/12
- BH-FDR q ≤ 0.10: 0/12
- complete discovery gate pass: 0/12
- complete 2024 challenge pass: 0/12
- `ML_LONG_EDGE_CANDIDATE`: 0

Therefore the 2024 promotion challenge was blocked for every configuration by the frozen discovery policy.

## Closest observations — not promotable

`logistic_p65_h16` had enough support (118 selected OOF events) and both 2022/2023 Base-net means were positive, but it still failed economics and statistical robustness:

- mean Base-net: +0.1012%
- mean Severe-net: -0.2988%
- median Base-net: +0.0831%
- Base-net profit factor: 1.0873, below required 1.10
- FDR q: 0.7699, far above 0.10

`hist_gb_p60_h4` showed +0.3911% Base-net mean and PF 1.546, but only selected 15 events, all effectively from 2022, Severe mean was slightly negative (-0.0089%), and FDR q was 0.7496. It is therefore a sparse observation, not evidence of a stable edge.

## Interpretation

M13 does not prove machine learning can never work. It proves that this frozen, small supervised-ML search over the current 19 causal price/volume/futures/funding/ETH features did not produce a robust cost-surviving edge. The main failure was not merely probability threshold choice: no configuration had positive Severe-cost mean and none survived multiple-testing correction.

No M13 threshold, feature, model hyperparameter, horizon, or sign may now be retuned as a rescue. A materially new information source or materially new research formulation requires a new frozen cycle.

## System state

- strategy promotion: BLOCKED
- risk sizing: BLOCKED
- live execution: BLOCKED
- deterministic Risk Engine remains authoritative
- current trading action: `NO_TRADE`
