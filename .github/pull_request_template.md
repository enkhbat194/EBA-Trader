## Summary

Describe the code/research/deployment change.

## Validation

- [ ] Relevant tests passed
- [ ] Ruff/lint passed where applicable
- [ ] Deployment/runtime checks passed where applicable
- [ ] External production proof is clearly separated from repository CI proof

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
