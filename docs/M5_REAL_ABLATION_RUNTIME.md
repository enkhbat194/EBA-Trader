# M5 Real Ablation Runtime

## Purpose

Run controlled BTCUSDT USD-M candle-only versus order-flow development experiments on Linode without using the Git checkout as durable research storage and without granting frozen-OOS or execution authority.

## Persistent paths

- Research DB: `/var/lib/eba-trader/research/eba_research.db`
- Feature datasets: `/var/lib/eba-trader/research/datasets`
- Immutable evidence: `/var/lib/eba-trader/research/evidence`

These paths survive Git deployments and remain separate from the runtime `TradeLedger`.

## Host safeguards

`deploy/journald/eba-trader.conf` versions the production limits that were first applied manually after the Binance per-tick logging incident:

- `SystemMaxUse=250M`
- `SystemKeepFree=1G`
- `MaxRetentionSec=7day`

The journald drop-in is treated as a host-safety invariant and intentionally survives application rollback.

## Research worker

`eba-research-worker.timer` checks the persistent research queue approximately once per minute. The oneshot worker is bounded to eight jobs per invocation, 50% CPU quota and 512 MB memory. It only consumes already queued research jobs; it does not create strategies, open frozen OOS or submit exchange orders.

## Real ablation queue CLI

`eba-m5-real-ablation` consumes:

1. a PR #35 M5 USD-M feature-workflow manifest;
2. the exact feature CSV under the configured persistent dataset root;
3. the sibling feature manifest;
4. a versioned order-flow gate-set JSON.

It verifies venue, symbol, interval, time range, dataset path containment and feature CSV SHA-256 before emitting a deterministic PR #34 ablation batch into the M4 queue. The stage is fixed to `m5_orderflow_ablation_dev`.

The initial gate policy is `config/m5_orderflow_gate_set_v1.json`. It contains a permissive `delta_ratio_threshold=-1.0` sanity arm plus bounded delta/CVD treatments. The permissive arm is useful as an invariant check against the candle-only control; the remaining treatments are hypotheses, not promotion thresholds.

## One-command Linode runner

Run from the Linode console as root:

```bash
bash /opt/Eba-Trader/scripts/run_m5_real_ablation.sh \
  --start 2026-08-01T00:00:00Z \
  --end 2026-08-02T00:00:00Z
```

The command builds a verified USD-M development feature dataset, queues the deterministic batch and runs exactly the emitted number of development jobs through the immutable evidence worker.

The requested window must remain outside the frozen first-cycle OOS range. The existing holdout guard fails closed if the workflow overlaps that holdout.

## Authority boundary

This runtime does **not**:

- open frozen OOS;
- promote a strategy merely because it wins a development comparison;
- submit Binance Demo or real orders;
- bypass deterministic risk;
- make PWA Research / AI Lab a mutation control plane.

Development results remain evidence for later screening and lifecycle reconciliation only.
