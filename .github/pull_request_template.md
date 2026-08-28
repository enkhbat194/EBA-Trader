## Summary

Describe the code/research/deployment change.

## Validation

- [ ] Relevant tests passed
- [ ] Ruff/lint passed where applicable
- [ ] Deployment/runtime checks passed where applicable
- [ ] `python scripts/check_repo_hygiene.py` passed
- [ ] External production proof is clearly separated from repository CI proof

## Repository hygiene

- [ ] Branch is task-scoped and not a reused merged branch
- [ ] Existing open PR/branch work was checked before duplicating implementation
- [ ] No runtime DB/log/artifact/cache/raw-data files are committed
- [ ] Unrelated refactors or generated files are not mixed into this diff
- [ ] Merged branch may be safely auto-pruned after merge

## Continuity

- [ ] `PROJECT_STATE.md` still matches the implementation
- [ ] `TODO.md` task status is current
- [ ] `DECISIONS.md` updated if architecture/research authority changed
- [ ] `CHANGELOG.md` updated when appropriate
- [ ] `SESSION_HANDOFF.md` contains the next exact task
- [ ] `python scripts/check_continuity.py` passes

## Safety / authority

- [ ] No secrets committed
- [ ] No unintended lifecycle/OOS promotion
- [ ] No unintended real-order execution path
