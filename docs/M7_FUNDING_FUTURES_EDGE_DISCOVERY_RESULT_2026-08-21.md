# M7 Funding + Futures Edge Discovery Result — 2026-08-21

## Decision

**`NO_STABLE_DERIVATIVES_EDGE_FOUND`**

M7 was executed once from the predeclared frozen search contract. No post-result parameter change,
threshold relaxation, sign reversal, or rescue filter is permitted.

## Validation before the first result

- Python target: 3.12
- Full deterministic suite: **191 passed**
- Ruff: **PASS**
- Implementation-only lint/format fixes were applied before evidence; the frozen research contract was unchanged.
- Final implementation-only fix commit before the evidence workflow: `67d10f26cfd4b5f7f8691c629a22d9328d21db57`
- Evidence workflow source commit: `bbc6df7caf2bbf191710d3b975824e4d90980668`

## Frozen inputs

Every input was independently seeded and required to match the SHA-256 frozen before the search:

- funding 2021-2024: `73b9decde0d54a0609d55ccfd49131a6e825416b595d728457bb01a968b55fd6`
- USDⓈ-M perpetual 15m activity 2021-2024: `3c97c9b59ded32595f129a480a23e920823c0edbbf2e4f32c5d66e5020e35947`
- Spot research 2021-2023: `253c6ae35856e58e35df17eaa71caeea5caaa3681c38dd7214a2872afccd8d63`
- Spot reused development challenge 2024: `3a96b6b668cfacb0fefabb8665675d4ca589cc712b0681fb57e7a13356eda0f2`

The seed manifest reported all four as `SEEDED_AND_FROZEN_HASH_VERIFIED`.

## Frozen search

- candidates: **12**
- causal forward horizons: **4 / 16 / 48** 15m bars
- total discovery tests: **36**
- Base round-trip screening cost: **30 bps**
- Severe round-trip screening cost: **70 bps**
- same-direction unconditional Spot baseline uplift required: **>= 10 bps**
- BH-FDR threshold: **q <= 0.10** across all 36 tests
- discovery stability: 2021, 2022 and 2023 each had to satisfy the frozen per-year gates
- 2024 remained a reused development challenge, not pristine OOS

## Result summary

- `LONG_EDGE_CANDIDATE`: **0**
- `NO_TRADE_VETO_CANDIDATE`: **0**
- `OBSERVATION_ONLY`: **12**
- discovery-passing candidate/horizons: **0/36**
- final discovery + 2024 challenge passing candidate/horizons: **0/36**

Discovery gate diagnostics across the 36 frozen candidate/horizon tests:

- >=60 discovery events: **27/36**
- >=20 distinct UTC event days: **33/36**
- >=10 discovery events in each of 2021/2022/2023: **27/36**
- positive mean Base net return: **3/36**
- positive mean Severe net return: **0/36**
- positive median Base net return: **0/36**
- >=10 bps same-direction baseline uplift: **12/36**
- frozen yearly economic/uplift stability: **0/36**
- BH-FDR q <= 0.10: **0/36**

The three observations with positive mean Base net return were still far from promotion:

| Observation | Horizon | Events | Mean Base net | Mean Severe net | Median Base net | Baseline uplift | FDR q |
|---|---:|---:|---:|---:|---:|---:|---:|
| `funding_negative_post_buy` | 16 bars | 18 | +0.1577% | -0.2423% | -0.4221% | +0.4421% | 1.0 |
| `funding_extreme_negative` | 48 bars | 285 | +0.0830% | -0.3170% | -0.3240% | +0.3385% | 1.0 |
| `funding_positive_post_buy` | 48 bars | 56 | +0.0186% | -0.3814% | -0.2322% | +0.2741% | 1.0 |

These are observations only. None survived Severe costs, median-return, FDR and yearly-stability requirements,
and two also missed the frozen 60-event discovery minimum.

## Evidence provenance

- GitHub Actions run: `32424800002`
- immutable artifact ID: `9427083252`
- evidence file: `artifacts/m7_funding_futures_edge_discovery.json`
- evidence SHA-256: `0c341876395f573b6c82bb14a91763c2387b34a51d28066b30e773ceede20bf6`
- uploaded artifact ZIP digest: `sha256:dafe8cec93b5e2b0b0dc6db39b248d23780642c938370309985e5a8d8d493301`

## OOS / deployment status

- 2025 OOS: **`LOCKED_NOT_ACCESSED`**
- strategy generation from M7: **FORBIDDEN**
- AI module: **excluded**
- live execution: **forbidden**
- short authority: **not granted**

## Research decision

Close M7 as a failed frozen edge-discovery family. Do not retune the 12 candidates after observing
this result. Any next research cycle must introduce materially new information or a separately
predeclared methodology rather than rescuing M7.
