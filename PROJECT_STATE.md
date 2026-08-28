# EBA Trader — Project State

_Last reconciled: 2026-08-28 (Asia/Ulaanbaatar)_

Actual GitHub code, PR/workflow state and Linode production proof override stale prose.

## Current goal

Keep `main` production-clean, resume the existing M5 development-corpus work without duplication, validate strategies across fresh multi-window development data, then require robustness before any sealed Frozen-OOS stage. Real-money execution stays locked.

## Current stage

- Production/runtime foundation: **VERIFIED**.
- Fast Momentum: **sole active production paper scanner**.
- Scanner-status UI incident: **FIXED / PRODUCTION VERIFIED**.
- M4 research/evidence platform: **COMPLETE**.
- M5 isolated single-window candidate cycle: **CLOSED WITHOUT EDGE CLAIM**.
- M5 chronological study policy: **MERGED / ENFORCED**.
- M5 development-corpus materializer: **PR #64 OPEN / EXISTING IMPLEMENTATION; DO NOT RESTART**.
- Legacy 2025 Frozen OOS: **LOCKED / INDEPENDENT**.
- M5 Frozen OOS (`2026-08-15 -> 2026-08-22` UTC): **SEALED / NOT ACQUIRED / NOT OPENED**.
- Real-money execution: **LOCKED**.

## Canonical repository state

- Repository: `enkhbat194/EBA-Trader`
- Current `main`: `523567785f928bfc63972894f19bf6d2541a633d`
- Active research PR: `#64 M5: materialize resumable development corpus`
- PR #64 branch/head: `m5-development-corpus-materializer` @ `39cd2b6dbea75b36307c03cf9080769b49a23123`
- PR #64 was created from older main and must be refreshed/compared against current main without recreating its existing work.

Only three branches remain:

1. `main` — production/deploy branch;
2. `m5-development-corpus-materializer` — active PR #64 work;
3. `archive/legacy-experiments-20260828` — history-only archive.

Legacy unique experiment history is preserved under `archive/legacy-experiments-20260828` at `c18496388af394890ea441e15477ff733292b350`. Recovery details: `docs/LEGACY_BRANCH_ARCHIVE_20260828.md`.

Repository hygiene is enforced by branch auto-pruning, repository-hygiene CI, hardened `.gitignore`, `AGENTS.md`, PR checklist and `docs/REPOSITORY_HYGIENE.md`.

Cleanup merges:

- PR #67 -> `8ebf6c6ce87840c95c071c15ed53cedf43f722d7`;
- PR #68 -> `523567785f928bfc63972894f19bf6d2541a633d`.

## Validation status

Exact current main `523567785f928bfc63972894f19bf6d2541a633d` passed:

- Repository hygiene: **PASS**;
- Continuity guard: **PASS**;
- Linode production bundle: **PASS**;
- Branch hygiene: **PASS**;
- Public production smoke run `33138685742`: **PASS**;
- Linode external exact-build proof run `33138685809`: **PASS**.

The cleanup did not change trading logic, strategy authority, Frozen OOS access or real execution.

## M5 research state

The inspected `2026-08-01T00:00Z -> 04:00Z` sample is closed for isolated indicator tuning. Delta, stacked imbalance, absorption/exhaustion and price/Delta divergence remained non-promotable development evidence.

Current chronological policy:

- development: `2026-07-01T00:00Z -> 2026-08-15T00:00Z`;
- sealed M5 Frozen OOS: `2026-08-15T00:00Z -> 2026-08-22T00:00Z`;
- 12 fresh non-overlapping four-hour development windows are pre-registered;
- the already-inspected proof window is excluded.

PR #64 already implements resumable/immutable materialization of those 12 development windows. Resume it rather than rebuilding it.

## Safety invariants

- Frozen OOS cannot be opened by normal development workflows.
- Real Binance order execution remains disabled.
- Development rankings have no promotion authority.
- Lifecycle v2 requires robustness before OOS.
- Deterministic risk keeps final veto authority.
- Runtime persistence and research persistence remain separate.
- Spot and USD-M futures data are never silently mixed.
- Executed footprint and resting LOB/order-book liquidity remain separate data planes.
- Gapped/tampered/missing-version research data fails closed.

## Next exact task

1. Resume existing PR #64; compare its current diff/head with latest `main`.
2. Bring PR #64 forward without dropping/recreating its materializer work.
3. Run exact-head full CI and fix every failure.
4. Merge PR #64 only when green.
5. Deploy exact main to Linode.
6. Materialize only the 12 pre-registered development windows.
7. Verify 12/12 hashes, provenance, sequence integrity and resumable replay.
8. Build the multi-window evaluator/aggregator and use it for Strategy Factory screening.
9. Continue to robustness before any Frozen-OOS consideration.

## Continuity protocol

New sessions read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, `SESSION_HANDOFF.md`, and `docs/CONTINUITY_PROTOCOL.md`, then query actual GitHub state before editing.
