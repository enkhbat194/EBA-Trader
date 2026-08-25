# M4 — Development Screening Gates and Verdicts

## Purpose

A completed backtest experiment is not automatically a validated strategy. This slice adds a
separate screening authority between persisted experiment evidence and lifecycle promotion.

The screening layer is deliberately fail-closed:

```text
experiment PASSED
      |
      v
immutable evidence verified
      |
      v
versioned GateSet evaluated
      |
      +---- any rule FAIL ---> verdict persisted; lifecycle stays GENERATED
      |
      `---- all rules PASS --> verdict persisted; GENERATED -> BACKTESTED
```

No later lifecycle state is reachable from this development screening path.

## Versioned GateSet

Thresholds are not hardcoded into the engine. A GateSet is a versioned declarative policy:

```json
{
  "name": "development-screen",
  "version": 1,
  "rules": [
    {
      "name": "minimum-trades",
      "metric": "trade_count",
      "operator": "gte",
      "threshold": 30
    },
    {
      "name": "max-drawdown",
      "metric": "max_drawdown",
      "operator": "gte",
      "threshold": -0.20
    }
  ]
}
```

Supported operators are `gte`, `lte`, `gt`, `lt` and `eq`. Missing, non-numeric or non-finite
metrics fail the affected rule.

Gate definitions are canonicalized and SHA-256 hashed. The gate-set ID is content-addressed.
The pair `(name, version)` is immutable: changing a rule requires incrementing the version.
This prevents a policy from silently changing while retaining the same human label.

## Evidence verification before screening

Before evaluating any metric, the orchestrator requires all of the following:

1. the strategy/version exists;
2. lifecycle is `GENERATED`, or `BACKTESTED` only for exact idempotent replay;
3. the experiment belongs to that exact immutable strategy version;
4. stage is exactly `development_backtest`;
5. experiment state is `PASSED`;
6. experiment contains an `evidence:<id>` reference;
7. the referenced evidence DB row belongs to the same experiment;
8. the evidence JSON file exists and its SHA-256 matches the indexed hash;
9. the artifact is canonical immutable JSON using the supported evidence schema;
10. evidence strategy ID/version/spec SHA matches the current immutable strategy version;
11. experiment metrics exactly match the metrics in immutable evidence.

Any mismatch rejects screening before a verdict can authorize promotion.

## Immutable verdict

A screening verdict is content-addressed from:

- strategy ID/version/spec hash;
- experiment ID;
- evidence ID and artifact hash;
- GateSet ID/definition hash;
- metrics hash;
- full rule evaluation.

The verdict is persisted in `screening_verdicts`. Gate policies are persisted in
`screening_gate_sets`.

## Promotion rule

Only `all(rule.passed)` permits:

```text
GENERATED -> BACKTESTED
```

The lifecycle transition evidence is:

```text
verdict:<verdict_id>
```

A failed screening verdict does not automatically mark the strategy `REJECTED`; it remains
`GENERATED`. Rejection policy can be added separately when the factory has explicit discard /
retest rules.

If a strategy is already `BACKTESTED`, only an exact replay of the verdict that authorized the
existing transition is accepted. A different verdict cannot silently replace prior authority;
a new immutable strategy version or explicit retest workflow is required.

## CLI

The package exposes:

```text
eba-development-screen
```

Required arguments identify the strategy version, experiment and JSON GateSet. Output is
machine-readable JSON containing verdict ID, gate-set ID, pass/fail, promotion status and each
rule result.

## Safety boundary

- Screening reads research evidence only.
- It cannot submit exchange orders.
- It cannot open frozen OOS data.
- It cannot promote beyond `BACKTESTED`.
- Failed gates never promote.
- Real-money execution remains locked.

## Next slice

1. Cost-stress and parameter-neighborhood experiment fan-out.
2. Robustness aggregation and verdict persistence.
3. Walk-forward orchestration.
4. Only after development freeze: separately authorized frozen OOS execution and verdict.
