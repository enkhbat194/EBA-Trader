# M17 USD-M Quarterly Cash-and-Carry Result

Date: 2026-08-21

Decision: **`NO_STABLE_DELIVERY_CARRY_EDGE_FOUND`**

M17 tested the first profitability cycle on the M16-qualified USD-M quarterly delivery-futures family. The frozen mechanism was fully market-neutral in BTC quantity: long BTCUSDT Spot and short the same BTC quantity in the quarterly USD-M future, fully funded at 1x research margin, with fixed entries 28/14/7 days before delivery and both legs closed 15 minutes before delivery.

No basis threshold, settlement-price reconstruction, leverage, COIN-M, cost relaxation, or after-result rescue was permitted.

## Authoritative evidence

- Source commit: `b3c9dfe8c28c78001b22176851f0f04e2ece3428`.
- GitHub Actions run: `32450971829`.
- Artifact: `9435702647`.
- Evidence JSON SHA-256: `6561361055522f79441492a0ecf667876371eaa4641f9160e8a38821cbbbea4b`.
- Artifact ZIP SHA-256: `55f631db6bc63e55dff3f96a28c377f2f27405a1d6a34ce7f22ba23c48f7ca4d`.
- Freeze verification: PASS.
- Repo-wide pytest: PASS.
- Ruff: PASS.
- 2025 OOS: `LOCKED_NOT_ACCESSED`.

## Frozen search result

Three fixed configurations were measured across exactly 12 discovery contracts in 2021-2023. No configuration passed discovery, therefore 2024 challenge outcomes were not opened by M17 (`challenge_access=BLOCKED_NO_DISCOVERY_PASS`).

### Entry 28 days before delivery

- trades: 12;
- mean gross return: **+0.259543%**;
- mean Base-net: **-0.042706%**;
- mean Severe-net: **-0.445705%**;
- median Base-net: **-0.112108%**;
- median Severe-net: **-0.507876%**;
- Base profit factor: **0.7478**;
- Severe profit factor: **0.1290**;
- Base win rate: **16.67%**;
- Severe win rate: **8.33%**;
- exact sign-flip p-value: 1.0;
- BH-FDR q-value: 1.0;
- all trades passed the frozen margin-safety gate.

Year means, Base / Severe:
- 2021: **+0.295133% / -0.097425%**;
- 2022: **-0.254602% / -0.645142%**;
- 2023: **-0.168650% / -0.594548%**.

### Entry 14 days before delivery

- trades: 12;
- mean gross return: **+0.142694%**;
- mean Base-net: **-0.155358%**;
- mean Severe-net: **-0.552761%**;
- median Base-net: **-0.217991%**;
- median Severe-net: **-0.637378%**;
- Base profit factor: **0.3350**;
- Severe profit factor: **0.0613**;
- Base win rate: **16.67%**;
- Severe win rate: **8.33%**;
- exact sign-flip p-value: 1.0;
- BH-FDR q-value: 1.0;
- all trades passed margin safety.

### Entry 7 days before delivery

- trades: 12;
- mean gross return: **+0.066116%**;
- mean Base-net: **-0.230700%**;
- mean Severe-net: **-0.626456%**;
- median Base-net: **-0.260133%**;
- median Severe-net: **-0.656397%**;
- Base profit factor: **0.1031**;
- Severe profit factor: **0.0000**;
- Base win rate: **16.67%**;
- Severe win rate: **0%**;
- exact sign-flip p-value: 1.0;
- BH-FDR q-value: 1.0;
- all trades passed margin safety.

## Interpretation

The dated-futures premium did converge on average, so the structural mechanism existed at the gross level. However, the frozen premium was too small and too inconsistent to overcome the predeclared transaction-cost model across 2021-2023. The 28-day configuration was the strongest observation, but it still had negative Base expectancy, negative median, PF below 1, only 2/12 Base winners, and negative 2022/2023 Base year means.

This is not a margin/liquidation failure: every trade passed the conservative fully-funded margin gate. The failure is economic after friction and across years.

## Final rule

M17 is retired. Do not add a basis threshold, lower costs, drop weak quarters, change entry offsets, move the exit to settlement, or add leverage to rescue this frozen result.

The correct state remains `NO_TRADE` for this mechanism. A later cycle may investigate a materially different execution/venue mechanism only if independently justified and frozen before its outcomes are inspected. 2025 remains untouched.
