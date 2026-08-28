# EBA Trader Repository Hygiene

This repository keeps `main` deployable and uses short-lived task branches.

## Branch lifecycle

- `main` is the only long-lived implementation branch.
- One task or milestone uses one focused feature/fix branch.
- Do not reuse an old merged branch for new work.
- Open PR heads are always preserved.
- After a merge to `main`, `.github/workflows/branch-hygiene.yml` prunes same-repository branches that are confirmed merged or contain no commits unique to `main`.
- Protected branches and `main` are never pruned.

## Tracked-file policy

Do not commit runtime or machine-local state:

- research evidence/artifacts;
- logs;
- raw/cache/catalog datasets;
- SQLite/runtime databases and journals;
- virtual environments and tool caches;
- `.env` files, private keys, certificates, or other secrets;
- editor/OS temporary files.

`python scripts/check_repo_hygiene.py` enforces this policy in CI.

## Code organization

- Production/research Python code lives under `src/eba_trader/`.
- Deterministic tests live under `tests/`.
- Deployment assets live under `deploy/` and operational scripts under `scripts/`.
- Versioned research configuration lives under `config/`.
- Long-form implementation/evidence documentation lives under `docs/`.
- Canonical continuity files remain at repository root because agents must find them immediately.

## PR standard

Before merge:

1. compare the task branch with current `main`;
2. keep the diff task-scoped;
3. run relevant tests, Ruff and deployment/runtime checks;
4. run continuity and repository-hygiene guards;
5. update continuity when the task changes project state;
6. merge only an exact green PR head;
7. let branch-hygiene automation remove the merged branch.

## Active-work exception

A branch with an open PR is not stale and must not be deleted by cleanup automation. This protects in-progress work such as the current M5 development-corpus materializer while unrelated merged branches are pruned.
