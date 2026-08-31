# Strategy Factory v2 Foundation Package — 2026-09-01

Branch: `strategy-factory-v2-discovery-foundation`

This package is intentionally infrastructure-only. It creates no new verified strategy and does
not authorize D1 hidden confirmation, D2 robustness, D3 Frozen OOS, Demo promotion or real money.

## Included

- bounded pilot contract: 500 raw candidates, 64 per family, 30 discovery survivors;
- fail-closed config validation;
- deterministic candidate/spec identity;
- immutable family registry;
- deterministic quasi-random discrete parameter sampling;
- candidate declaration separated from evaluation-trial count;
- immutable candidate/evaluation ledger with source-code and dataset identities;
- behavioral fingerprinting and near-duplicate clustering;
- economic-first discovery selection vector with no statistical authority;
- bounded in-process batch interface with compute stop accounting;
- immutable discovery-survivor selection;
- sealed D1 freeze contract that rejects D0 dataset reuse;
- lifecycle-safety tests proving discovery does not promote StrategyLifecycle;
- project/backtest/TODO continuity reconciliation through completed SF3 production evidence.

## Explicitly not included

- actual 500-candidate search;
- 8–12 production family registration;
- hidden confirmation data access;
- multiple-testing method replacement;
- Frozen OOS access;
- paper/Demo/live promotion;
- real exchange execution changes;
- UI redesign.

## Merge rule

Merge only after exact-head full regression, Ruff, runtime, continuity, repository hygiene and
applicable deployment-contract checks pass. A CI failure must be fixed without weakening research
or safety rules.
