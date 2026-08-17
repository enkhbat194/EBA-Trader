# M2 — Final Frozen OOS

## Authority

The final 2025 OOS is not authorized by the signal-only baseline.

A final freeze requires **both**:

1. signal development evidence + eligible signal verdict;
2. risk-sized execution evidence + eligible risk verdict.

The final freeze also verifies:

- signal and risk evidence came from the same Git commit;
- signal/risk evidence and verdict hashes still match;
- development research/validation CSV hashes still match;
- the 2025 OOS cache does not already exist.

The final freeze snapshots the complete market and execution configuration.

## Final freeze

After both development layers pass and reports are reviewed:

```bash
python -m eba_trader.final_freeze
```

Output:

```text
artifacts/m2_final_frozen_candidate.json
```

## One-shot OOS open

Only then:

```bash
python -m eba_trader.final_oos --confirm-frozen
```

Before any network fetch, the OOS runner:

- requires the current tracked Git tree to be clean;
- requires the current Git commit to equal the development/freeze commit;
- re-verifies all bound evidence/verdict hashes;
- re-verifies development dataset hashes;
- refuses any pre-existing OOS cache/report/open marker.

It then writes an **OPENED_PENDING_RESULT** marker before fetching 2025. This makes interrupted runs fail closed: an interrupted holdout is not silently rerun.

On success it writes:

```text
artifacts/m2_final_oos_opened.json
artifacts/m2_final_oos_2025.json
```

and the marker becomes `COMPLETE`.

## Predeclared OOS screening

The frozen OOS must meet all gates fixed before opening 2025:

- at least 20 closed trades;
- positive base return;
- positive expectancy;
- profit factor > 1.0;
- planned risk per trade <= 0.5%;
- no leverage / invested notional <= equity;
- no 8% hard drawdown halt;
- positive severe-cost return;
- severe-cost run also avoids the 8% hard drawdown halt.

Run after the OOS report exists:

```bash
python -m eba_trader.final_oos_verdict
```

Possible statuses:

- `ELIGIBLE_FOR_FORWARD_PAPER`
- `REJECT_HISTORICAL_CYCLE`

Even `ELIGIBLE_FOR_FORWARD_PAPER` explicitly sets `live_trading_approved=false`.

## 2026 and later

2026+ is not treated as pristine historical OOS because M1 already observed live 2026 BTC data.

If 2025 passes, evidence from 2026 onward is **forward PAPER/SHADOW evidence from the freeze timestamp forward**, not retrospective holdout evidence.
