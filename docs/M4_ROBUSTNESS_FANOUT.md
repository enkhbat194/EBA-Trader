# M4 — Robustness Fan-out and Verdict

## Goal

Extend the M4 research control plane from a single development backtest into bounded,
auditable robustness experiments without unlocking frozen OOS or changing live/runtime state.

## Flow

```text
BACKTESTED strategy version
  -> RobustnessPlan
  -> deterministic RobustnessBatch
  -> parameter-neighborhood experiments
  -> cost-stress experiments
  -> existing ExperimentQueue / ResearchBacktestWorker
  -> immutable per-experiment evidence
  -> RobustnessVerdictEngine
  -> immutable aggregate verdict
```

The aggregate verdict does **not** change the strategy lifecycle. This is intentional.
The current lifecycle machine places `OOS_VERIFIED` before `ROBUSTNESS_VERIFIED`; M4 does
not silently rewrite that authority model or bypass the separately frozen OOS workflow.
A later milestone must reconcile the canonical validation order before adding automated OOS
or robustness promotion.

## Fan-out constraints

- strategy must already be `BACKTESTED` (or later `OOS_VERIFIED` for replay/retest work),
- strategy version/spec remains immutable,
- fixed strategy fields cannot be overridden by the robustness plan,
- cost scenarios may change only `fee_bps` and `slippage_bps`,
- deterministic batch and experiment identities make repeat creation idempotent,
- hard cap: 250 robustness jobs per plan,
- queue retry/lease/recovery behavior is inherited from the M4 experiment queue.

## Verdict constraints

A robustness verdict can be produced only when every experiment in the batch is `PASSED` and
has an evidence reference. The same declared `GateSet` is evaluated against every scenario.
The batch passes only when every scenario passes all rules.

The verdict is content-addressed and stored in `robustness_verdicts`. Re-evaluating the same
batch under the same gate policy is idempotent; a conflicting result cannot silently replace
prior authority.

## Safety boundary

- no Binance order submission,
- no runtime `TradeLedger` mutation,
- no frozen OOS unlock,
- no automatic `OOS_VERIFIED` or `ROBUSTNESS_VERIFIED` promotion,
- no paper/demo/live promotion,
- deterministic risk authority remains unchanged.

## M4 completion boundary

With this slice, M4 contains the control-plane primitives required before an AI strategy
factory is introduced:

1. unified strategy contract,
2. immutable strategy versions and lifecycle,
3. durable research database,
4. restart-safe experiment queue,
5. allowlisted generic backtest worker,
6. immutable provenance evidence,
7. development screening/verdict and `GENERATED -> BACKTESTED` gate,
8. bounded robustness fan-out and aggregate verdict.

The next milestone should build strategy hypothesis generation and experiment-family planning
on top of these primitives. Frozen OOS orchestration remains a separate validation milestone,
not an AI-factory shortcut.
