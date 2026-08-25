# M4 — Experiment Queue and Worker Leases

## Purpose

The strategy factory needs a restart-safe work queue before it can safely generate and test
large numbers of strategy variants. The queue is research-only and is stored in the separate
research SQLite database; it does not share runtime position state with `TradeLedger`.

## State model

```text
QUEUED
  -> RUNNING
      -> PASSED
      -> FAILED
      -> QUEUED   (retryable failure while attempts remain)
      -> QUEUED   (expired lease while attempts remain)
      -> FAILED   (expired lease at attempt limit)
```

A strategy experiment is identified independently of worker scheduling by the deterministic
experiment ID created from strategy ID, immutable strategy version, stage, parameters and
dataset reference.

## Claim contract

`ExperimentQueue.claim_next()` uses a SQLite `BEGIN IMMEDIATE` transaction before selecting
and updating a queued experiment. This serializes competing claimers at the database write
boundary and prevents two workers from leasing the same queued row.

Each successful claim records:

- `worker_id`
- `attempt_count`
- `max_attempts`
- `lease_expires_at_ms`
- `claimed_at`

A second worker receives no claim for the same experiment while the first lease remains
active.

## Lease contract

Workers must renew long-running experiments before their lease expires. Renewal succeeds only
when all of these remain true:

1. experiment state is `RUNNING`;
2. the requesting worker still owns the lease;
3. the lease has not already expired.

A stale worker cannot publish a pass/fail result after lease expiry. This prevents a process
that resumed late from overwriting work that may already have been reassigned.

## Crash and restart recovery

`recover_expired()` and the recovery step inside `claim_next()` inspect expired `RUNNING`
rows.

- If `attempt_count < max_attempts`, the experiment is returned to `QUEUED`.
- If the attempt limit is exhausted, the experiment becomes terminal `FAILED`.
- Worker ownership and the expired lease are cleared before reassignment.

This makes worker process death or server restart recoverable without manually editing the
research database.

## Retry behavior

A worker may mark a failure as retryable and optionally apply a retry delay. Retryable work is
returned to `QUEUED` only while attempts remain. The next claim increments `attempt_count`.
When the limit is reached, another failure is terminal.

## Duplicate-work guard

`ResearchStore.create_experiment()` already uses deterministic experiment IDs. Enqueueing the
same strategy/version/stage/parameters/dataset combination returns the same experiment row
instead of creating a duplicate. The lease transaction then guarantees one active worker for
that row.

These are two separate protections:

1. deterministic identity prevents duplicate rows;
2. transactional leasing prevents duplicate simultaneous execution.

## Safety boundary

- No exchange order API is called by the queue.
- No runtime/paper position is created by the queue.
- Queue completion does not automatically promote a strategy lifecycle state.
- Lifecycle promotion still requires its own validated evidence reference and transition gate.
- Real-money execution remains locked.

## Acceptance tests

The queue test suite covers:

- idempotent enqueue;
- single-owner claim behavior;
- stage-filtered workers;
- lease renewal ownership;
- stale-worker result rejection;
- delayed retry;
- attempt exhaustion;
- expired-lease recovery;
- persistence of passed metrics/evidence.

## Next slice

1. Generic strategy-spec -> existing backtest adapter.
2. Evidence/provenance records with dataset and code hashes.
3. Worker executor that runs adapters through this queue contract.
4. Automated cheap-screen -> development -> robustness -> OOS gate orchestration.
