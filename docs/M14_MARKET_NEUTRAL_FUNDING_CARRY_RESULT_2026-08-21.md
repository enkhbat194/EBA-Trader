# M14 Market-Neutral Funding Carry Result — 2026-08-21

Status: `CLOSED_REJECTED`
Decision: **`NO_STABLE_FUNDING_CARRY_EDGE_FOUND`**

## Frozen mechanism tested

M14 was intentionally different from the prior directional/ML cycles. It tested a market-neutral carry structure only:

- long `1.0 USD` BTCUSDT Spot;
- short `1.0 USD` BTCUSDT USD-M perpetual;
- 1:1 hedge only;
- leverage forbidden;
- naked short forbidden;
- overlapping positions forbidden;
- positive funding-rate entry thresholds: `1 bp`, `3 bp`, `5 bp`;
- holding periods: `3` or `9` funding records (~24h / ~72h under the observed historical cadence);
- Base friction: `15 bps` per side per leg;
- Severe friction: `35 bps` per side per leg;
- discovery window: 2021-01-01 through 2024-01-01 exclusive;
- reused development challenge: 2024 only, and only for a configuration that first passed discovery;
- 2025 OOS: `LOCKED_NOT_ACCESSED`.

The measured PnL included the paired Spot/perpetual price movement, realized funding cashflow, and the frozen friction assumptions. No live trading or risk sizing was permitted.

## Authoritative evidence

- source commit: `32a12c230af4fb99661f14d1669f20787ba112cf`
- GitHub Actions run: `32446970715`
- artifact: `9434444012`
- evidence JSON SHA-256: `c5bd418a60260fb1619f8d0f563bf7ff93a1d66ee76525051df5f0c4bda136ec`
- artifact ZIP SHA-256: `e9e27051ef31a23da69cd1698f4d531ce6fae4bd78b09606af8fd91698cb845a`
- pytest: PASS
- Ruff: PASS
- frozen contract verification: PASS
- tracked working tree clean: true

Frozen input hashes were reproduced before the evidence run:

- funding: `73b9decde0d54a0609d55ccfd49131a6e825416b595d728457bb01a968b55fd6`
- BTC perpetual 15m: `3c97c9b59ded32595f129a480a23e920823c0edbbf2e4f32c5d66e5020e35947`
- BTC Spot research 2021-2023: `253c6ae35856e58e35df17eaa71caeea5caaa3681c38dd7214a2872afccd8d63`
- BTC Spot challenge 2024: `3a96b6b668cfacb0fefabb8665675d4ca589cc712b0681fb57e7a13356eda0f2`

## Frozen search result

Total frozen configurations: `6`

- discovery passing: `0 / 6`
- challenge passing: `0 / 6`
- `MARKET_NEUTRAL_CARRY_CANDIDATE`: `0`
- all classifications: `OBSERVATION_ONLY`

| Config | Trades | Mean gross | Mean Base net | Mean Severe net | Median Base | PF Base | Win rate Base | FDR q |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1bp / 3 records | 676 | +0.03099% | -0.26894% | -0.66884% | -0.28007% | 0.000 | 0.00% | 1.0 |
| 1bp / 9 records | 261 | +0.08198% | -0.21800% | -0.61798% | -0.25522% | 0.0396 | 6.51% | 1.0 |
| 3bp / 3 records | 145 | +0.09097% | -0.20942% | -0.60995% | -0.23282% | 0.000 | 0.00% | 1.0 |
| 3bp / 9 records | 62 | +0.23100% | -0.06982% | -0.47090% | -0.11492% | 0.3664 | 24.19% | 1.0 |
| 5bp / 3 records | 86 | +0.12309% | -0.17748% | -0.57825% | -0.18050% | 0.000 | 0.00% | 1.0 |
| 5bp / 9 records | 37 | +0.31666% | +0.01499% | -0.38722% | -0.04003% | 1.2504 | 45.95% | 1.0 |

## Why M14 failed

The historical funding cashflow itself was positive enough to create positive gross carry in every configuration, but the frozen paired-entry/exit friction plus basis movement removed the edge.

The closest observation was `carry_funding_5bp_hold_9`:

- 37 trades / 37 distinct entry days;
- mean gross return `+0.31666%`;
- mean Base-net `+0.01499%`;
- Base PF `1.2504`;
- Base win rate `45.95%`;
- median Base-net `-0.04003%`;
- mean Severe-net `-0.38722%`;
- FDR q-value `1.0`;
- 2022 trade count `0`;
- 2023 trade count `1` with negative Base-net mean.

Therefore the closest observation failed robustness, support/year stability, Severe-cost economics, and statistical promotion gates. It cannot be selected after the result.

The other five configurations had negative mean Base-net returns in discovery. Challenge was correctly not run because discovery produced no passing configuration.

## Final interpretation

M14 does **not** validate a profitable market-neutral BTC funding-carry strategy under the frozen assumptions. It also does not prove that all possible funding/basis arbitrage is impossible; it only rejects this predeclared six-configuration mechanism on the qualified 2021-2024 development data.

Do not rescue M14 by lowering costs, changing thresholds, changing hold lengths, selecting the 5bp/9-record observation after the fact, allowing leverage, or loosening support/statistical gates.

Risk sizing remains blocked. Live execution remains blocked. 2025 remains `LOCKED_NOT_ACCESSED`.
