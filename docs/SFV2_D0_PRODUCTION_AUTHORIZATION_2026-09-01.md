# Strategy Factory v2 — one-time local D0 production authorization

Date: 2026-09-01
Status: **EXPLICITLY AUTHORIZED, DISCOVERY ONLY**
Request ID: `sfv2-d0-prod-20260901-v1`

## Why this exists

The 8-family / 406-candidate Strategy Factory v2 pilot is code-complete through the pre-D1
survivor-freeze boundary, but the empirical 406×12 D0 campaign has not run because connected
project tools do not expose a Linode operator shell action.

The repository owner explicitly requested that the autonomous hourly task be stopped and that this
remaining work be completed as one coherent package. This document records the narrow replacement
for the former operator-shell-only invocation requirement.

## Decision

Authorize **one single local production D0 campaign request** through the already-installed
root-side research-maintenance timer. This is not a general remote execution facility.

The authorization is valid only for:

- campaign `sfv2-discovery-pilot-v1`;
- the existing deterministic **406 candidates** / **8 families**;
- exactly **12 D0 strata**;
- existing inspected D0 declaration SHA
  `88365779d6821c1fb30372148bbcedbfadf11471843f57722723286a43cbc77c`;
- existing inspected D0 dataset SHA
  `aa13bcfc111c00f6da19621353a3ca8044f58eca1ab95e837d9490a205aa72eb`;
- `DISCOVERY_ONLY` authority.

There is **no HTTP, PWA, unauthenticated, public, or exchange-facing trigger**. The production
wrapper runs only from the local root-side systemd maintenance path and holds the same checkout
mutation lock as the auto-updater.

## Predeclared D0 survivor rule

The survivor-selection rule is frozen before production campaign results are observed.

A candidate may be nominated from D0 only when it is:

- complete across all declared D0 strata;
- not rejected;
- behaviorally fingerprinted;
- mean total return > 0 after the existing cost model;
- mean expectancy > 0;
- mean benchmark-relative return > 0;
- total D0 trades >= 12.

The 12-trade threshold is **only a cheap D0 resource-allocation/activity floor**. It does not replace
or weaken the existing strict verification sample requirement (historically >=30 trades where that
protocol applies).

Only one candidate may be selected from each behavioral cluster. Within a cluster, the deterministic
lexicographic order is:

1. higher mean benchmark-relative return;
2. higher mean expectancy;
3. higher mean total return;
4. higher total trade count;
5. better (less negative) mean max drawdown;
6. candidate ID ascending as the final deterministic tie-break.

At most 30 D0 survivors may be frozen. **Zero survivors is valid.**

## Why no extra adaptive D0 stage is inserted now

The current D0 corpus is already inspected/reusable evidence and Stage B already spans all 12
predeclared strata. Adding a new performance-adaptive higher-fidelity rule after seeing campaign
results would create unnecessary selection flexibility. For this pilot, the safer boundary is:

`complete stratified D0 -> predeclared economics/activity filter -> behavioral cluster diversity -> immutable survivor/zero-survivor freeze`.

Any future additional D0 fidelity must be a new versioned decision made before inspecting the
results it would select on.

## Safety remains unchanged

This authorization cannot:

- turn D0 into fresh evidence;
- grant verification authority;
- open D1;
- open Frozen OOS;
- authorize Demo promotion;
- enable live or real-money execution;
- retune or inspect SF4 before its preregistered unlock.

After the D0 outcome is frozen, D1 still requires a separate hidden-confirmation design and explicit
authorization. SF4 remains separately frozen until `2026-09-13T00:00:00Z`.
