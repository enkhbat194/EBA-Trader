# Deprecated OOS Paths

## Status

The following earlier commands are **deprecated for the final first-cycle decision**:

```text
eba-freeze-oos-candidate
eba-oos-study
```

Reason: they were created when M2 evaluated only the signal/allocation baseline. The methodology audit established that the final 2025 holdout must evaluate the risk-sized execution model that obeys the bot's deterministic risk policy.

Do not use the signal-only freeze/OOS path to make a PAPER or live decision.

## Final first-cycle authority

Use only:

```bash
python -m eba_trader.final_freeze
python -m eba_trader.final_oos --confirm-frozen
python -m eba_trader.final_oos_verdict
```

The final path requires both signal screening and risk-execution screening, binds development dataset hashes, freezes the complete execution configuration, enforces same-code-commit OOS execution, and opens the 2025 holdout once.

The deprecated entry points should be removed from public packaging after the current offline audit/full-suite migration test is complete. Until then, their existence is compatibility debt, not authorization to use them.
