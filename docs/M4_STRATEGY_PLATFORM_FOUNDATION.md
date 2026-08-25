# M4 — Strategy Research Platform Foundation

## Goal

Turn the existing EBA Trader research/runtime codebase into a versioned strategy research
platform before adding a mass AI strategy generator. M4 must make strategy identity,
experiment evidence and promotion state durable and auditable.

## Why this milestone comes before the AI Strategy Factory

Generating thousands of strategies without a durable registry, immutable versions,
experiment deduplication and lifecycle gates would create untraceable backtest files and
selection bias. M4 creates the control plane that the later AI factory must use.

## M4 scope

1. Unify the generic strategy decision contract around `LONG`, `SHORT`, `EXIT` and
   `NO_TRADE` while preserving a transitional `BUY -> LONG` compatibility path for
   historical V1 code.
2. Add a strict strategy lifecycle state machine.
3. Add a separate durable research metadata database for strategy versions, experiments
   and lifecycle history.
4. Add deterministic experiment identities so duplicate parameter/dataset work can be
   recognized.
5. Next: add experiment queue/worker state, generic backtest adapters, evidence records and
   automated screening gates.

## Lifecycle

Primary promotion path:

```text
GENERATED
  -> BACKTESTED
  -> OOS_VERIFIED
  -> ROBUSTNESS_VERIFIED
  -> PAPER_CANDIDATE
  -> PAPER_VERIFIED
  -> DEMO_CANDIDATE
  -> DEMO_VERIFIED
  -> SHADOW_VERIFIED
  -> MICRO_LIVE_ELIGIBLE
  -> LIVE_ELIGIBLE
  -> LIVE_ACTIVE
```

Failure/revalidation states:

```text
REJECTED
QUARANTINED
RETEST_REQUIRED
RETIRED
```

Promotion transitions require an evidence reference. Gate skipping is rejected by code.
The deterministic risk layer remains higher authority than lifecycle eligibility.

## Research database boundary

The research database is intentionally separate from runtime `TradeLedger` position state.
This prevents mass experiments and metadata writes from becoming coupled to active paper or
future live positions.

Initial tables:

- `strategies`
- `strategy_versions`
- `experiment_runs`
- `lifecycle_history`

Strategy versions are immutable. Changing a strategy specification requires a new version.
Experiment IDs are deterministic from strategy/version/stage/parameters/dataset, which is
the base for later duplicate detection and resumable queues.

## Safety constraints

- No real order submission is introduced by M4.
- Existing Linode/PWA/Fast Momentum runtime remains the active paper runtime.
- `TradeLedger` remains the source of runtime position/event persistence.
- Research evidence cannot directly promote itself to live execution.
- OOS and robustness rules in the existing backtest protocol remain mandatory.

## Acceptance criteria for the foundation slice

- LONG and SHORT proposal stop-direction invariants are unit tested.
- Historical `Decision.BUY` resolves to LONG during migration.
- Lifecycle gate skipping is rejected.
- Promotion without `evidence_ref` is rejected.
- Strategy version mutation is rejected.
- Experiment IDs are deterministic across JSON key order.
- Experiment metadata/results round-trip through SQLite.

## Next implementation slice

1. `ExperimentQueue` with `QUEUED/RUNNING/PASSED/FAILED/CANCELLED` state.
2. Worker claim/lease and restart recovery.
3. Generic adapter from strategy spec to existing backtest runner.
4. Evidence table with source data/provenance hashes.
5. Automated cheap-screen -> development -> robustness -> OOS gates.
