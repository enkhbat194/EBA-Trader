# EBA Trader — Project State

_Last reconciled: 2026-08-28 03:22 (Asia/Ulaanbaatar)_
_Current implementation frontier: isolated M5 order-flow candidate cycle is closed without an edge claim; chronological M5 study policy and a fresh pre-registered multi-window development corpus are being finalized in PR #63._

This is the primary cross-chat continuation summary. Actual GitHub code, PR/workflow state and production proof override stale prose. A new session must query actual GitHub `main`, open PRs and workflow state before implementation.

## Current goal

Operate EBA Trader as a restart-safe 24/7 Linode paper/research system; build a controlled AI Strategy Factory on the M4 evidence platform; discover strategies through deterministic historical simulation/backtest, multi-window development screening, robustness and later frozen-OOS/forward/demo validation; maintain a verified strategy knowledge base; and keep real-money execution locked until the evidence/lifecycle chain permits it.

## Current stage

- Production/runtime foundation: **VERIFIED**.
- M4 research/evidence platform: **COMPLETE**.
- M5 AI Strategy Factory/order-flow research: **IN PROGRESS**.
- Delta/CVD isolated candidate: **COMPLETE / NO EDGE-PROMOTION CLAIM**.
- Stacked/diagonal imbalance isolated candidate: **COMPLETE / NO EDGE-PROMOTION CLAIM**.
- Absorption/exhaustion isolated candidate: **COMPLETE / NO EDGE-PROMOTION CLAIM**.
- Price/Delta divergence isolated candidate: **COMPLETE / NO EDGE-PROMOTION CLAIM**.
- Original single-window isolated-candidate cycle: **CLOSED**; do not keep tuning new gates on the same four-hour smoke window.
- M5 chronological study policy + fresh development corpus: **PR #63 IN PROGRESS**.
- Legacy first-cycle 2025 Frozen OOS: **LOCKED / INDEPENDENT**.
- New M5 2026 Frozen OOS: **SEALED / NOT ACQUIRED OR OPENED**.
- Real-money execution: **LOCKED**.

## Canonical repository/runtime

- Repository: `enkhbat194/EBA-Trader`
- Default/base branch: `main`
- Latest functional main before PR #63: `a8ddbcbd3d17fa17bebf1ba11b08d11edccd439d`
- PR #62 price/Delta divergence merge: `a8ddbcbd3d17fa17bebf1ba11b08d11edccd439d`
- Active branch: `m5-study-policy-corpus`
- Active PR: `#63 M5: seal chronological study policy and development corpus`
- PR #63 exact code/test head that first passed all three required workflows: `629a065355db8e6a3642690f99c66630c84617c8`; documentation commits follow and require final exact-head CI before merge.
- Runtime: Linode Nanode, Ubuntu 24.04 LTS
- Server repo: `/opt/Eba-Trader`
- Runtime DB: `/var/lib/eba-trader/eba_trader.db`
- Research DB: `/var/lib/eba-trader/research/eba_research.db`
- Research datasets: `/var/lib/eba-trader/research/datasets`
- Research evidence: `/var/lib/eba-trader/research/evidence`
- Public PWA: `https://eba-trader-172-236-150-62.sslip.io/`
- App/server release: `0.12.2 · LINODE-M7`
- PWA cache: `eba-trader-ui-v15`
- Auto deploy: `eba-auto-update.timer`
- Replit/Render backend paths: deprecated.

## Production reality through price/Delta divergence

Exact main `a8ddbcbd3d17fa17bebf1ba11b08d11edccd439d` passed production bundle, Linode runtime checks and continuity. The exact-build external production proof run `33102562299` completed successfully at `2026-08-27T18:22:09Z`.

Price/Delta divergence report:

`/var/lib/eba-trader/research/evidence/m5-price-delta-divergence-ablation-20260801T000000Z-20260801T040000Z.json`

Batch: `abl_21f419216c4734955d389da6`

Workflow dataset: `m5ds_53cd6f3d1a306c26b151362d`

Proof confirmed COMPLETE/safe/terminal/evidence-complete development comparison only, with `edgeClaimAllowed=false`, `promotionAuthority=false`, `frozenOosOpened=false` and `liveExecutionAllowed=false`.

Fast Momentum remains the sole active production paper engine. Real exchange execution remains disabled.

## Research platform

### M4 — complete

M4 provides immutable strategy versions, deterministic experiment IDs, restart-safe queue/leases, allowlisted workers, content-addressed evidence, development screening and bounded robustness contracts.

Lifecycle policy v2 is:

`GENERATED -> BACKTESTED -> ROBUSTNESS_VERIFIED -> OOS_VERIFIED -> PAPER_CANDIDATE -> PAPER_VERIFIED -> DEMO_CANDIDATE -> DEMO_VERIFIED -> SHADOW_VERIFIED -> MICRO_LIVE_ELIGIBLE -> LIVE_ELIGIBLE -> LIVE_ACTIVE`

A development result cannot skip robustness and open frozen OOS.

### M5 — current foundation

Completed infrastructure includes:

- constrained strategy DSL / approved feature registry;
- bounded strategy family generation and duplicate/near-duplicate filtering;
- Binance USD-M historical aggregate-trade acquisition with checksum/sequence/integrity validation;
- deterministic causal executed-trade footprint windows;
- versioned feature datasets and same-dataset candle/order-flow adapters;
- deterministic one-control-to-many-treatment development ablations;
- persistent bounded Linode research worker/runtime;
- immutable candidate comparison reports and external exact-build production proof;
- read-only research observability in the server/PWA.

Current executed-trade feature path:

- v1: buy/sell volume, Delta, Delta ratio, CVD, POC;
- v2: diagonal and stacked imbalance;
- v3: absorption/exhaustion executed-flow response proxies;
- v4: causal bullish/bearish price/Delta divergence plus signed divergence score.

These are research features, not assumed alpha. Resting L2/LOB liquidity remains a separate future data plane.

## Original fixed-window evidence — interpreted as smoke/development evidence, not sufficient alpha validation

All isolated candidates below used the same window:

`2026-08-01T00:00:00Z -> 2026-08-01T04:00:00Z`

### Candle-only baseline

- total return: `-0.004244488397751933` (~`-0.42445%`)
- final equity: `9957.55511602248`
- trade count: `4`
- win rate: `0.25`
- max drawdown: `-0.004244488397751933`
- expectancy: `-10.611220994379892`
- total cost: `43.90484437829747`

### Delta/CVD — best tested Delta threshold 0.2

- return ~`-0.12055%`
- final equity `9987.9446`
- 2 trades
- 50% win rate
- max drawdown ~`-0.26586%`
- expectancy `-6.0277`
- total cost `21.9992`
- still negative; no promotion authority.

### Stacked imbalance — threshold 1

- return ~`-0.12408%`
- final equity `9987.5918`
- 2 trades
- 50% win rate
- max drawdown ~`-0.24164%`
- expectancy `-6.2041`
- total cost `21.9825`
- improved baseline but did not beat Delta 0.2; no promotion authority.

### Absorption/exhaustion

Absorption `0.10/0.20` both produced one losing trade:

- return ~`-0.16740%`
- expectancy ~`-16.74`
- cost ~`10.993`

Exhaustion `0.01/0.03` produced zero trades. Zero trades are not edge evidence.

### Price/Delta divergence

Thresholds `0.01`, `0.05` and `0.10` all produced the same one losing trade:

- total return: `-0.0013709100484625703` (~`-0.13709%`)
- final equity: `9986.290899515374`
- trade count: `1`
- win rate: `0.0`
- max drawdown: `-0.0013709100484625703`
- expectancy: `-13.709100484626106`
- profit factor: `0.0`
- exposure: `0.018779342723004695`
- total cost: `10.994657857876607`
- baseline return delta: `+0.002873578349289363`

Interpretation: it reduced absolute loss versus candle baseline but did not demonstrate positive return/expectancy and was worse than Delta 0.2 on return/expectancy. No edge/promotion claim.

## Why the research methodology changes now

Four isolated order-flow families have already been inspected on the same four-hour window. Continuing to add/tune feature gates on that same sample would increase adaptive data-snooping risk and can manufacture apparent improvement without generalizable edge.

A second chronology issue was identified: the repository's original first-cycle Frozen OOS covers 2025, while M5 order-flow development already used 2026 data. That 2025 holdout remains historically valid for the older first-cycle policy but cannot honestly serve as a later temporal OOS for M5 after 2026 development.

Therefore M5 gets a separate chronological study policy. The 2025 lock is preserved rather than reinterpreted.

## M5 chronological study policy — PR #63

Domain:

- symbol: `BTCUSDT`
- venue: Binance USD-M futures
- interval: `1m`
- version: `1`
- deterministic policy identity: `m5policy_*`

Chronology:

- development: `2026-07-01T00:00:00Z -> 2026-08-15T00:00:00Z`
- new sealed M5 Frozen OOS: `2026-08-15T00:00:00Z -> 2026-08-22T00:00:00Z`
- forward begins: `2026-08-22T00:00:00Z`

Normal M5 development acquisition has no authority to fetch/read the new OOS. An overlapping request is rejected before any Binance candle/order-flow network request.

The workflow manifest is upgraded to `m5_usdm_feature_build_v2` with immutable `study_policy_id` and `study_phase=development` provenance. Real ablation independently verifies the sealed policy/phase before queue emission.

See `docs/M5_STUDY_POLICY.md`.

## Pre-registered fresh development corpus

The corpus contains 12 non-overlapping four-hour windows and deliberately excludes the already-inspected `2026-08-01 00:00 -> 04:00 UTC` proof window:

1. `2026-07-02 00:00 -> 04:00`
2. `2026-07-06 08:00 -> 12:00`
3. `2026-07-10 16:00 -> 20:00`
4. `2026-07-14 00:00 -> 04:00`
5. `2026-07-18 08:00 -> 12:00`
6. `2026-07-22 16:00 -> 20:00`
7. `2026-07-26 00:00 -> 04:00`
8. `2026-07-30 08:00 -> 12:00`
9. `2026-08-03 16:00 -> 20:00`
10. `2026-08-07 00:00 -> 04:00`
11. `2026-08-11 08:00 -> 12:00`
12. `2026-08-14 16:00 -> 20:00`

Corpus identity is deterministic (`m5corpus_*`), window names must be unique, chronology/non-overlap is enforced and corpus fan-out has a hard cap of 24.

## PR #63 validation status

PR #63 initially exposed two implementation issues and both were corrected before merge:

1. corpus initialization preceded guard-function definition, causing import-time `NameError` — fixed by reordering initialization;
2. Ruff import-order failure in the new policy test — fixed.

Exact head `629a065355db8e6a3642690f99c66630c84617c8` then passed:

- full Python regression suite;
- Ruff;
- shell syntax;
- deployment contract;
- Continuity guard;
- Linode runtime checks;
- Linode production bundle.

Documentation commits follow that head, so final merge requires a fresh exact-head green CI check. No new M5 OOS data has been acquired/read by this package.

## Next exact tasks after PR #63

1. Confirm final exact-head PR #63 CI is green and squash-merge only that verified head.
2. Update actual `main` SHA/continuity after merge.
3. Add an immutable/resumable **M5 development corpus materializer** that builds the 12 pre-registered windows and records policy ID, corpus ID, workflow IDs, dataset refs and hashes.
4. Add a **multi-window evaluation aggregator** that requires complete per-window evidence before issuing an aggregate development verdict.
5. Evaluate existing/Strategy-Factory candidate hypotheses across the fresh corpus under identical fees/slippage and causal contracts.
6. Treat incomplete/zero-activity/insufficient-trade candidates conservatively; do not reward inactivity as edge.
7. Only positive development survivors proceed to bounded robustness under lifecycle policy v2.
8. Do not acquire/open the new M5 Frozen OOS until robustness evidence and an explicit OOS-stage contract authorize it.
9. Keep L2/LOB reconstruction separate and later.
10. Keep real exchange execution locked.

## Important constraints

- No API secrets in Git, chat, logs or browser persistent storage.
- Deterministic Risk Engine has final veto authority.
- Runtime, research and credential persistence remain separate domains.
- Strategy versions/evidence are immutable.
- AI-generated strategy descriptions cannot execute arbitrary generated Python.
- Executed-trade order flow and resting LOB liquidity are separate domains.
- Gapped/tampered historical data fails closed.
- Spot and USD-M futures are not silently mixed.
- Same-candle still-forming footprint data cannot enter that candle's decision.
- Missing versioned feature columns fail closed.
- Zero-trade treatments are not interpreted as profitable edge.
- Development rankings/wins are not promotion evidence.
- Repeated tuning on the original four-hour smoke window is closed.
- Legacy 2025 Frozen OOS and new M5 2026 Frozen OOS are independent locks.
- Generic research workers cannot open frozen OOS or exchange execution.
- Frozen OOS and real-money execution remain locked.

## Continuity protocol

Canonical continuation files: `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, `SESSION_HANDOFF.md`, `docs/CONTINUITY_PROTOCOL.md`.

A new chat must read these files, query actual GitHub main/branch/open-PR/workflow state, compare any active branch to main, then continue the next valid task. Work remains sequential: one core architecture/research package at a time -> deterministic tests -> CI/log inspection -> fixes -> PR -> exact-head workflows -> merge -> production/runtime proof as applicable -> continuity update.
