# M13 ML Edge Engine — Frozen Research Protocol

Status: `FROZEN_PREDECLARED_NOT_RUN`

## Objective

Test whether a small, deterministic supervised-ML search can identify BTCUSDT Spot long / NO_TRADE states with positive net expectancy after realistic costs, using only already-qualified 2021–2024 development data. This is research only. It does not authorize live trading.

## Data boundary

- Training / walk-forward discovery: 2021-01-01 through 2024-01-01 exclusive.
- Reused development challenge: 2024-01-01 through 2025-01-01 exclusive.
- 2025-01-01 through 2026-01-01 is frozen OOS and remains `LOCKED_NOT_ACCESSED`.
- No 2025 download, read, inference, tuning, label construction, threshold selection, or model fitting is allowed.

Exact frozen inputs:

- BTCUSDT Spot 15m 2021–2023 SHA-256: `253c6ae35856e58e35df17eaa71caeea5caaa3681c38dd7214a2872afccd8d63`
- BTCUSDT Spot 15m 2024 SHA-256: `3a96b6b668cfacb0fefabb8665675d4ca589cc712b0681fb57e7a13356eda0f2`
- BTCUSDT USD-M perpetual 15m 2021–2024 SHA-256: `3c97c9b59ded32595f129a480a23e920823c0edbbf2e4f32c5d66e5020e35947`
- BTCUSDT funding 2021–2024 SHA-256: `73b9decde0d54a0609d55ccfd49131a6e825416b595d728457bb01a968b55fd6`
- ETHUSDT USD-M perpetual 15m 2021–2024 SHA-256: `69855dcaf2f34c2a529ddb7f83964fa61b39ed0a27ae8796a6c0eaafd5b744f5`

## Causal sample semantics

- Source frequency: 15m.
- Candidate sample only on UTC-aligned hourly bars (`open_time_ms % 3_600_000 == 0`) to reduce serial dependence and turnover.
- Feature vector at completed 15m bar `t` may use `t` and earlier only.
- Diagnostic entry is BTC Spot next contiguous 15m open `t+1`.
- Horizons are exactly 4, 16, 48 bars (about 1h, 4h, 12h).
- Exit is BTC Spot close at `t+H`.
- Reject any sample whose BTC entry/exit path crosses an unexpected source gap.
- Long-only. ML never grants short authority.

## Frozen feature vector

All features are deterministic, causal and computed without 2025:

1. BTC Spot return 1h
2. BTC Spot return 4h
3. BTC Spot return 12h
4. BTC Spot realized absolute-return mean 4h
5. BTC Spot volume / prior-96-bar median volume
6. BTC Spot close / prior-96-bar VWAP - 1
7. BTC perpetual return 1h
8. BTC perpetual taker-buy share 1h
9. BTC perpetual quote-volume intensity 1h vs prior 96 one-hour windows
10. BTC perpetual-minus-Spot price premium
11. latest known BTC funding rate
12. latest funding rate minus trailing-90-funding-record mean
13. ETH perpetual return 1h
14. ETH perpetual return 4h
15. ETH perpetual return 12h
16. ETH perpetual taker-buy share 1h
17. ETH perpetual quote-volume intensity 1h vs prior 96 one-hour windows
18. ETH-minus-BTC 1h relative return
19. ETH-minus-BTC 4h relative return

Missing feature values are median-imputed from each model's training fold only.

## Frozen target

For each horizon H, binary target = 1 only when the BTC Spot forward gross return from next open to `t+H` close is greater than the Base round-trip cost of 30 bps. Otherwise target = 0.

The target is used for model fitting only. Promotion economics are evaluated on actual signed long returns after both Base and Severe costs.

## Frozen model families and configurations

Exactly two model families:

1. `logistic`
   - `StandardScaler`
   - `LogisticRegression(C=1.0, class_weight="balanced", max_iter=1000, solver="lbfgs", random_state=13)`

2. `hist_gb`
   - `HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, max_depth=3, l2_regularization=1.0, random_state=13)`

Exactly two fixed probability gates: `0.60`, `0.65`.

Exactly three horizons: `4`, `16`, `48`.

Total frozen model tests: 2 × 2 × 3 = 12.

No hyperparameter search, feature selection, threshold tuning, model stacking, calibration, sign flip, or rescue filter is allowed after the first complete evidence run.

## Walk-forward discovery

Discovery predictions must be out-of-sample in time:

- Fold A: train on 2021, predict 2022.
- Fold B: train on 2021–2022, predict 2023.

A model configuration is measured on the combined 2022–2023 out-of-fold predictions and separately by prediction year.

2021 is training-only and does not count as discovery evidence.

## 2024 reused challenge

Only configurations that pass all discovery gates may be evaluated for promotion on 2024.

For challenge fitting, refit the same frozen model configuration on all 2021–2023 samples and predict 2024. No 2024 outcome may alter features, model hyperparameters, probability gate, or selection rules.

## Economics

- Base round-trip screening cost: 30 bps.
- Severe round-trip screening cost: 70 bps.
- Signal when predicted probability >= frozen gate.
- NO_TRADE otherwise.
- Maximum one diagnostic entry per hourly sample by construction.
- These are event-study diagnostics, not fill-accurate live execution.

## Multiple-testing control

For each of the 12 discovery configurations:

- Aggregate Base-net selected returns by UTC signal day.
- One-sided normal-approximation p-value for positive mean daily Base-net return.
- Benjamini-Hochberg FDR across all 12 configurations.
- Required `q <= 0.10`.

## Discovery gates — all required

1. at least 80 selected OOF events across 2022–2023;
2. at least 30 distinct UTC event days;
3. at least 25 selected events in each of 2022 and 2023;
4. mean Base-net return > 0;
5. mean Severe-net return > 0;
6. median Base-net return > 0;
7. profit factor on Base-net event returns > 1.10;
8. 2022 mean Base-net > 0;
9. 2023 mean Base-net > 0;
10. Benjamini-Hochberg q <= 0.10.

## 2024 challenge gates — all required

Only if discovery passed:

1. at least 40 selected events;
2. mean Base-net return > 0;
3. mean Severe-net return > 0;
4. median Base-net return > 0;
5. Base-net profit factor > 1.10;
6. at least 6 of 12 UTC calendar months with selected events have positive mean Base-net return.

## Classification

- A configuration passing discovery and 2024 challenge is `ML_LONG_EDGE_CANDIDATE`.
- Otherwise it is `OBSERVATION_ONLY`.
- If no configuration passes both stages, decision is `NO_STABLE_ML_EDGE_FOUND`.
- Even a promoted configuration is not live-ready. It only becomes eligible for a separately frozen paper-strategy / risk-sized validation cycle.

## Anti-overfit / safety rules

After the first complete M13 evidence report:

- no threshold tuning;
- no feature addition/removal;
- no horizon changes;
- no model hyperparameter changes;
- no selecting a model because its 2024 result looked best unless it already passed frozen discovery gates;
- no 2025 access;
- no live execution;
- deterministic Risk Engine remains superior to any future ML/AI signal.
