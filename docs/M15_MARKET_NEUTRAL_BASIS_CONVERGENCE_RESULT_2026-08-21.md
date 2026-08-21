# M15 Market-Neutral Basis Convergence Result — 2026-08-21

Status: `CLOSED_REJECTED`
Decision: **`NO_STABLE_BASIS_CONVERGENCE_EDGE_FOUND`**

## Frozen mechanism tested

M15 tested a 1:1 market-neutral BTC basis-convergence structure:

- long `1.0 USD` BTCUSDT Spot;
- short `1.0 USD` BTCUSDT USD-M perpetual;
- no leverage, no naked short, no overlap;
- signal from completed 15m basis `perp_close / spot_close - 1`;
- entry next aligned 15m open;
- entry basis thresholds: 75 / 125 / 200 bps;
- fixed convergence exit: completed basis <= 10 bps, exit next open;
- max hold: 96 / 288 / 672 bars;
- 9 frozen configurations;
- funding included only when `entry_time < funding_time < exit_time`;
- Base/Severe friction: 15 / 35 bps per side per leg;
- discovery: 2021-2023;
- reused challenge: 2024 only after full discovery pass;
- 2025 OOS: `LOCKED_NOT_ACCESSED`.

## Authoritative evidence

- source commit: `ad9d5bd2ee2f2d84295eb8c8cb4aadde90d8c71a`
- GitHub Actions run: `32449012036`
- artifact: `9435060914`
- evidence JSON SHA-256: `4bd98328539c9d75f0e17839a631ab80c05c9ee14222d7b144f75ff8c4ae0559`
- artifact ZIP SHA-256: `1b60ed9657f29487f0fd4ba150516578ce7bd56e07222cd4d8019cf991ee7ca7`
- freeze verification: PASS
- repo-wide pytest: PASS
- Ruff: PASS

## Result

- discovery passing configs: `0 / 9`
- challenge passing configs: `0 / 9`
- `MARKET_NEUTRAL_BASIS_CANDIDATE`: `0`

The 125-bps and 200-bps entry families produced zero discovery trades in all holding variants.

The 75-bps family produced exactly the same five non-overlapping discovery trades for all 96/288/672-bar max-hold variants because every observed trade converged before the shortest time stop:

- trades: `5`
- distinct entry days: `5`
- mean gross return: `+0.460616%`
- mean Base-net return: `+0.157798%`
- mean Severe-net return: `-0.245961%`
- median Base-net return: `+0.170301%`
- Base profit factor: effectively infinite because all five Base-net trades were positive
- Base win rate: `100%`
- convergence exit rate: `100%`
- mean actual hold: `8.2` 15m bars (~2.05h)
- BH-FDR q: `0.0002695`
- 2021 trades: `5`, positive Base-net mean
- 2022 trades: `0`
- 2023 trades: `0`

## Why it failed

The five 2021 dislocations look statistically clean under Base friction, but the phenomenon did not repeat in 2022 or 2023 and did not survive Severe friction. It therefore failed minimum trade count, minimum distinct days, per-year support/stability, and Severe-cost economics.

This is precisely why the frozen support/year gates exist: a small cluster of attractive 2021 events is not enough to claim a repeatable trading edge.

Challenge was correctly not run because no configuration passed discovery.

## Final interpretation

M15 rejects this predeclared perpetual-vs-Spot basis-convergence mechanism as a promotable edge on the qualified 2021-2024 development data.

Do not rescue M15 by lowering the 75-bps entry threshold, lowering costs, allowing leverage, changing the 10-bps exit, changing hold periods, using negative-basis trades, or selecting only the five 2021 events after seeing the result.

Risk sizing and live execution remain blocked. 2025 remains `LOCKED_NOT_ACCESSED`.
