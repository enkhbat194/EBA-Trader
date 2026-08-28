# EBA Trader — Session Handoff

_Last handoff prepared: 2026-08-28 (Asia/Ulaanbaatar)_

## Exact continuation point

Repository: `enkhbat194/EBA-Trader`

Current production `main` before this continuity-only update:

`523567785f928bfc63972894f19bf6d2541a633d`

Only three repository branches remain:

1. `main` — production/deploy branch;
2. `m5-development-corpus-materializer` — active PR #64;
3. `archive/legacy-experiments-20260828` — history-only archive.

Do not recreate deleted legacy branches. Their unique histories were preserved in archive commit `c18496388af394890ea441e15477ff733292b350`; see `docs/LEGACY_BRANCH_ARCHIVE_20260828.md`.

## What was completed

PR #67 `Repository hygiene cleanup` merged as `8ebf6c6ce87840c95c071c15ed53cedf43f722d7` and added safe branch pruning, repository-hygiene CI, tracked runtime/cache/secret-like artifact protection, stronger ignore rules and branch lifecycle policy.

PR #68 `Archive and prune legacy unique branches` merged as `523567785f928bfc63972894f19bf6d2541a633d`. It preserved 16 unique old branch histories under one archive ref, then safely removed the redundant branch names.

Exact current-main validation after cleanup:

- Repository hygiene: PASS;
- Continuity guard: PASS;
- Linode production bundle: PASS;
- Branch hygiene: PASS;
- Public production smoke run `33138685742`: PASS;
- Linode external exact-build proof run `33138685809`: PASS.

No trading logic, research authority, Frozen OOS permission or real execution permission changed during cleanup.

## Research work to resume — PR #64

PR #64 `M5: materialize resumable development corpus` is still open.

- branch: `m5-development-corpus-materializer`
- existing head: `39cd2b6dbea75b36307c03cf9080769b49a23123`
- base when opened: older `main` (`4e863026...`)

Its existing implementation already includes deterministic/resumable materialization of the 12 pre-registered development windows, immutable checkpoints/final manifest, archive order-flow default, provenance/hash verification, replay/resume/tamper tests and `eba-materialize-m5-corpus`.

**Do not restart or duplicate that work.** Compare PR #64 with current main and bring it forward cleanly.

## Next exact task

1. Read canonical continuity files and query actual GitHub state.
2. Compare PR #64 branch against latest `main`.
3. Reconcile the existing branch without dropping its materializer commits.
4. Run exact-head full regression, Ruff, deployment/runtime, continuity and repository-hygiene checks; fix every failure.
5. Merge PR #64 only when green.
6. Deploy exact merged main to Linode.
7. Materialize only the 12 pre-registered development windows.
8. Verify 12/12 hashes, provenance, sequence integrity and resumable replay.
9. Build/run the multi-window evaluator for Strategy Factory screening.
10. Continue to robustness before any Frozen-OOS consideration.

## Hard locks

- Legacy 2025 Frozen OOS remains locked.
- M5 Frozen OOS (`2026-08-15 -> 2026-08-22` UTC) remains sealed, not acquired/opened.
- Real Binance execution remains locked.
- Development/ranking results have no promotion authority.
- Fast Momentum remains paper-only and deterministic risk keeps final veto authority.

## Startup rule

Read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, this file and `docs/CONTINUITY_PROTOCOL.md`; then query actual GitHub state and resume PR #64 from its first unfinished task.
