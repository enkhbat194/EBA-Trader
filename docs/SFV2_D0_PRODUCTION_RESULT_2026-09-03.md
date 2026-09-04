# Strategy Factory v2 — D0 Production Result

Date: 2026-09-03 (Asia/Ulaanbaatar)

## Result

The first Strategy Factory v2 production D0 campaign is complete and the survivor outcome is frozen.

Exact production evidence:

- production build/source SHA: `bdb84a4a926dac53d13116364e8315e98b35e6e1`;
- GitHub Actions workflow: `Strategy Factory v2 D0 production campaign proof`;
- run ID: `33674168891` (run #3);
- conclusion: `success`;
- campaign ID: `sfv2-discovery-pilot-v1`;
- authority: `DISCOVERY_ONLY`;
- candidates: 406;
- D0 strata: 12;
- expected candidate/stratum trials: 4,872;
- terminal candidate/stratum trials: 4,872;
- complete candidates: 406;
- rejected candidates: 254;
- behaviorally eligible candidates: 152;
- behavioral clusters: 127;
- frozen D0 survivors: **0**;
- D1 opened: false;
- Frozen OOS opened: false;
- live execution allowed: false;
- real execution allowed: false.

The zero-survivor selection is a valid immutable negative discovery outcome under the rule preregistered before production results were observed.

## Economic interpretation

No candidate satisfied the fixed D0 survivor economics and activity rule simultaneously:

- mean total return > 0;
- mean expectancy > 0;
- mean benchmark-relative return > 0;
- total D0 trades >= 12;
- complete/non-rejected evidence;
- behavioral fingerprint available;
- at most one survivor per behavioral cluster.

The highest-ranked sanitized discovery candidate was `dc_41ef5a002157b82e92bd8df9` (`mean_reversion_z_v1`) and still failed the economic rule:

- mean total return: `-0.000596638634337889`;
- mean expectancy: `-2.5838131662228028`;
- total trades: `23`;
- mean benchmark-relative return: `-0.001547214383630785`;
- selected survivor: false.

The next ranked candidates shown by the production proof were also net-negative. Therefore this D0 result does not justify D1 access, robustness, Frozen OOS, Demo promotion or any profitability claim.

## What the result does and does not say

The campaign produced 127 behavioral clusters from 152 behaviorally eligible candidates. The failure was therefore not simply a complete collapse into one duplicated behavior. The decisive failure was economic: no cluster representative met the preregistered positive net-return/expectancy/benchmark-delta rule after costs.

The pilot catalog intentionally contained 406 candidates even though the hard cap is 500. The remaining numerical headroom is not a quota. It must not be filled with post-hoc parameter variants merely because the first outcome had zero survivors.

## Research decision after D0

1. Close `sfv2-discovery-pilot-v1` with zero survivors. Do not rewrite or extend its immutable survivor selection.
2. Do not open D1 because there is no frozen survivor to confirm.
3. Do not lower the D0 survivor gates or later strict verification gates.
4. Do not post-hoc retune the same eight pilot families and call the result independent evidence.
5. Preserve all 406 inspected candidates in the broad-search/multiple-testing history.
6. Any further Strategy Factory search is a new versioned campaign decision with a new deterministic candidate catalog and explicit search budget.
7. The next campaign should prioritize genuinely new mechanisms, data planes and/or execution horizons rather than consuming the unused cap with neighboring parameters.
8. D0 may remain reusable/adaptive discovery evidence, but it can never be relabelled fresh confirmation evidence.
9. D1 remains untouched and may be used only after a future campaign freezes non-empty survivors under a predeclared confirmation protocol.
10. SF4 prospective replication remains untouched until its preregistered unlock time `2026-09-13T00:00:00Z`.

## Locks after closeout

- verified profitable Strategy Factory candidate: **0**;
- D1: **SEALED**;
- D2 robustness for Factory survivors: **NOT APPLICABLE** because survivor count is zero;
- D3 / M5 Frozen OOS: **SEALED**;
- real-money execution: **LOCKED**.
