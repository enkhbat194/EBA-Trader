# Deprecated OOS Paths

## Status

The following earlier commands are **removed from public packaging**:

```text
eba-freeze-oos-candidate
eba-oos-study
```

Reason: they were created when M2 evaluated only the signal/allocation baseline. The methodology audit established that the final 2025 holdout must evaluate the risk-sized execution model that obeys the bot's deterministic risk policy.

Their internal compatibility modules remain covered by tests, but they are not installed as console
commands and must not be used to make a PAPER or live decision.

## Final first-cycle authority

Use only:

```bash
eba-final-freeze
eba-final-oos --confirm-frozen
eba-final-oos-verdict
```

The final path requires both signal screening and risk-execution screening, binds development dataset hashes, freezes the complete execution configuration, enforces same-code-commit OOS execution, and opens the 2025 holdout once.

The deprecated entry points were removed after the full Python 3.12 suite and packaging migration
audit passed on 2026-08-20.
