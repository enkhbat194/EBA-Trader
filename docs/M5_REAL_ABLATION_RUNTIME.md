# M5 Real Ablation Runtime

## Purpose

Run controlled BTCUSDT USD-M candle-only versus order-flow development experiments on
Linode without using the Git checkout as durable research storage and without granting
frozen-OOS or execution authority.

## Persistent paths

- Research DB: `/var/lib/eba-trader/research/eba_research.db`
- Feature datasets: `/var/lib/eba-trader/research/datasets`
- Immutable evidence: `/var/lib/eba-trader/research/evidence`
- Autorun state: `/var/lib/eba-trader/research/m5-real-ablation-latest.json`

These paths survive Git deployments and remain separate from the runtime `TradeLedger`.

## Host safeguards

`deploy/journald/eba-trader.conf` versions the production limits that were first applied
manually after the Binance per-tick logging incident:

- `SystemMaxUse=250M`
- `SystemKeepFree=1G`
- `MaxRetentionSec=7day`

The journald drop-in is treated as a host-safety invariant and intentionally survives
application rollback.

## Research worker

`eba-research-worker.timer` checks the persistent research queue approximately once per
minute. The oneshot worker is bounded to eight jobs per invocation, 50% CPU quota and
512 MB memory. It only consumes already queued research jobs; it does not create
strategies, open frozen OOS or submit exchange orders.

## Real ablation queue CLI

`eba-m5-real-ablation` consumes:

1. an M5 USD-M feature-workflow manifest;
2. the exact feature CSV under the configured persistent dataset root;
3. the sibling feature manifest;
4. a versioned order-flow gate-set JSON.

It verifies venue, symbol, interval, time range, dataset path containment and feature CSV
SHA-256 before emitting a deterministic ablation batch into the M4 queue. The stage is
fixed to `m5_orderflow_ablation_dev`.

The initial gate policy is `config/m5_orderflow_gate_set_v1.json`. It contains a
permissive `delta_ratio_threshold=-1.0` sanity arm plus bounded delta/CVD treatments.
The permissive arm is an invariant check against the candle-only control; the remaining
treatments are hypotheses, not promotion thresholds.

## Automatic first real development batch

Production deployment provisions `eba-m5-real-ablation.timer`. The timer starts a bounded
oneshot job after the runtime is healthy and retries a failed/incomplete research run
without operator input.

The first automatic batch is intentionally small enough for the Linode runtime:

- symbol: `BTCUSDT`
- venue: Binance USD-M futures
- interval: `1m`
- development window: `2026-08-01T00:00:00Z` through `2026-08-01T04:00:00Z`
- CPU quota: 40%
- memory ceiling: 700 MB
- service timeout: 45 minutes

The wrapper is idempotent. After a terminal batch with complete evidence exists, later
timer invocations only refresh the sanitized COMPLETE marker and do not rerun the batch.
The timer starts after deployment rather than inside the deployment transaction, so a
large data download cannot block or roll back the trading runtime.

## Comparison report

`run_m5_real_ablation.sh --result-json ...` writes an immutable comparison report only
after the emitted experiments reach terminal state with evidence references. The report
contains the candle baseline, each Delta/CVD treatment and finite numeric metric deltas
versus the baseline.

The report explicitly records:

- `developmentComparisonOnly=true`
- `edgeClaimAllowed=false`
- `promotionAuthority=false`
- `frozenOosOpened=false`
- `liveExecutionAllowed=false`

A treatment outperforming the baseline is therefore an observation, not proof of a
tradable edge and not permission to advance lifecycle state.

## Manual diagnostic runner

The underlying bounded pipeline can still be invoked manually on Linode when diagnosing
a failed autorun:

```bash
bash /opt/Eba-Trader/scripts/run_m5_real_ablation.sh \
  --start 2026-08-01T00:00:00Z \
  --end 2026-08-01T04:00:00Z \
  --result-json /var/lib/eba-trader/research/evidence/manual-m5-report.json
```

The requested window must remain outside the frozen first-cycle OOS range. The existing
holdout guard fails closed if the workflow overlaps that holdout.

## Authority boundary

This runtime does **not**:

- open frozen OOS;
- promote a strategy merely because it wins a development comparison;
- submit Binance Demo or real orders;
- bypass deterministic risk;
- make PWA Research / AI Lab a mutation control plane.

Development results remain evidence for later screening and lifecycle reconciliation only.
