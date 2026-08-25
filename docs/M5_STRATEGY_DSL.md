# M5 Constrained Strategy DSL

M5 must not let an AI write arbitrary production or execution code. AI output is accepted only as structured hypothesis data that passes an approved feature registry and deterministic expansion rules.

## Current contract

A hypothesis contains:

- family and schema version;
- LONG or SHORT direction;
- timeframe;
- explicit approved feature names;
- entry conditions joined by AND;
- optional exit conditions joined by AND;
- human/AI rationale that does not affect structural identity.

Conditions currently support only numeric `gt`, `gte`, `lt`, and `lte` comparisons. No arbitrary Python, expression strings, filesystem access, networking, exchange access, or custom callbacks are accepted.

## Approved feature registry

Enabled now:

- candle: close, EMA fast/slow, RSI, ATR, volume;
- order flow: buy volume, sell volume, delta, delta ratio, CVD, POC price.

Reserved but disabled until implemented and validated:

- stacked imbalance;
- absorption;
- exhaustion;
- limit-order-book depth imbalance.

A hypothesis referencing a disabled or unknown feature fails closed.

## Identity and duplicate control

Structural hypothesis identity excludes free-text rationale. Two hypotheses with the same family/version/direction/timeframe/features/conditions therefore receive the same fingerprint even if the AI explanation differs.

Parameter families are deterministically expanded with a hard cap of 500 variants per family. Duplicate parameter values are rejected.

## M4 integration

`M5ExperimentEmitter`:

1. validates the hypothesis;
2. creates a deterministic strategy ID from the hypothesis fingerprint;
3. registers the immutable hypothesis as a M4 `ResearchStore` strategy version;
4. expands the bounded parameter family;
5. enqueues each candidate into the restart-safe M4 `ExperimentQueue`;
6. relies on existing M4 deterministic experiment identity to suppress exact duplicate work.

Changing the dataset changes experiment identity. Re-emitting the same hypothesis/parameters/dataset is idempotent.

## Next batch

The next M5 batch should add strategy-family templates, near-duplicate similarity checks beyond exact structural fingerprints, and a cheap-screen/development orchestration layer. Historical order-flow ingestion/provenance is developed separately before order-flow hypotheses are allowed to claim empirical value.

Frozen OOS and exchange execution remain locked.
