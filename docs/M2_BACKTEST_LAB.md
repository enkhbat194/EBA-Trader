# M2 — Historical Data & Backtest Laboratory

## Goal

Build a zero-cost research path that can test BTC/USDT Spot strategies before any paper or live execution is introduced.

## Safety invariant

M2 contains no exchange account access and no order-execution code. Historical data is downloaded from Binance public market-data-only REST.

## Baseline design

- market: BTC/USDT Spot;
- interval: 15 minutes;
- strategy: long-only **strict** EMA 20/50 crossover;
- signal uses only the completed current candle;
- execution is modeled at the **next candle open**;
- being already fast>slow at a window boundary does not synthesize a BUY;
- benchmark: BTC buy-and-hold over the same effective period;
- parameter tuning: disabled for the first baseline.

### Frozen evidence windows

- `research`: 2021-01-01 inclusive → 2024-01-01 exclusive;
- `validation`: 2024-01-01 inclusive → 2025-01-01 exclusive;
- `out_of_sample`: 2025-01-01 inclusive → 2026-01-01 exclusive;
- 2026+ remains outside the first baseline cycle.

The 2025 OOS is locked during development. Development code also refuses to claim the holdout is clean if a 2025 cache file already exists.

## One-command network run

Repo development and test authoring happen outside Replit whenever possible. When a networked Linux runtime is finally needed, the preferred wrapper is:

```bash
git pull && bash scripts/run_m2_full_development.sh
```

That script:

1. reuses or creates `.venv`;
2. overrides Replit/Nix `PIP_USER` only inside the process;
3. installs the latest project/development dependencies;
4. runs the complete `pytest` suite;
5. stops immediately if any test fails;
6. runs locked signal development evidence and screening;
7. runs the predeclared risk-sized execution evidence and screening;
8. leaves 2025 OOS untouched.

The user should not need to manually run a chain of installation/backtest commands.

## Development evidence

The underlying study command is:

```bash
eba-development-study
```

It accepts no EMA override and always uses the predeclared EMA 20/50 first-cycle baseline.

It:

1. verifies no 2025 OOS cache exists;
2. downloads/caches only 2021–2024 development data;
3. requires exact start/end/candle-count/interval coverage;
4. runs EMA 20/50 under base/adverse/severe costs;
5. runs parameter-neighborhood robustness on research data;
6. runs rolling walk-forward using causal train history as EMA warm-up while test trading starts only at the test boundary;
7. runs causal regime diagnostics on research and validation;
8. writes `artifacts/m2_development_evidence.json`;
9. records `oos_2025=LOCKED_NOT_ACCESSED`.

The neighborhood test is a fragility check. It does **not** authorize selecting a better-looking neighboring EMA pair for this first cycle.

## Final candidate freeze gate

If development evidence rejects EMA 20/50, stop the cycle and create a new hypothesis without opening 2025.

If both signal and risk-sized execution evidence pass:

```bash
eba-final-freeze
```

The command accepts no strategy/risk parameters. It:

- recomputes both predeclared screening layers;
- binds signal evidence, risk evidence, verdicts, Git commit, and development dataset hashes;
- verifies the OOS cache is still absent;
- writes `artifacts/m2_final_frozen_candidate.json`.

Changing the development report after freeze invalidates the freeze. Creating an OOS cache before authorized opening also invalidates the gate.

## Frozen OOS opening

Only after the candidate freeze exists:

```bash
eba-final-oos --confirm-frozen
```

The command verifies the frozen evidence/candidate and clean matching Git commit, writes an open
marker before fetching, opens 2025 once, writes `artifacts/m2_final_oos_2025.json`, and refuses
reruns or interrupted-run retries.

The earlier signal-only `eba-freeze-oos-candidate` and `eba-oos-study` commands are removed from
public packaging and are not authoritative for promotion decisions.

Retuning after OOS is opened is forbidden. A failed OOS returns the project to a **new** research cycle; 2025 must not become a tuning dataset.

## Data integrity gates

Every opened dataset must pass:

- strictly increasing timestamps;
- no duplicate candles;
- sane OHLC relationships;
- exact leading boundary;
- exact trailing boundary;
- expected candle count after any explicitly predeclared source outage;
- zero unexpected missing 15-minute intervals.

The Binance public source has seven reproducible BTCUSDT/15m outage ranges in the 2021–2023
research window (70 absent source candles total). Their exact timestamps are frozen in
`data_policy.py`; four outage-adjacent and one standalone early-close timestamp are frozen there as
well. Reports disclose both. Any other gap or close-time anomaly remains a hard failure. The 2024 validation
window has complete 35,136-candle coverage.

All window end timestamps are exclusive to prevent boundary leakage.

## Cost stress

| Scenario | Fee / side | Slippage / side |
|---|---:|---:|
| Base | 10 bps | 5 bps |
| Adverse | 10 bps | 10 bps |
| Severe | 15 bps | 20 bps |

These are research assumptions, not claims about a future account fee tier.

## Required metrics

- final equity;
- total and annualized return;
- BTC buy-and-hold return;
- benchmark-relative return;
- maximum drawdown;
- trade count;
- win rate;
- profit factor;
- expectancy;
- average win/loss;
- Sharpe and Sortino;
- exposure;
- estimated transaction/slippage costs.

## Interpretation rules

1. Positive return alone is not a pass.
2. Buy-and-hold is mandatory.
3. Lower return must be justified by materially better risk characteristics.
4. Very low trade count is insufficient evidence.
5. High win rate with weak profit factor/expectancy is failure-prone.
6. Results erased by adverse/severe costs are fragile.
7. One winning EMA pair surrounded by failures is an overfitting warning.
8. The frozen OOS is never a tuning dataset.
9. No M2 result authorizes live money.

## Acceptance path

### M2A — Plumbing
Historical data, exact integrity gates, strict crossover/next-bar execution, costs, benchmark, deterministic tests.

### M2B — Development evidence
Research/validation, cost stress, parameter neighborhood, causal walk-forward, causal regime diagnostics, development review.

### M2C — Risk-sized execution evidence
Apply the deterministic ATR stop/risk sizing model to the unchanged development datasets and pass
its predeclared cost/risk gates.

### M2D — Final frozen OOS
Freeze the complete signal and execution configuration, bind evidence/dataset hashes, verify OOS
cache absence, open 2025 once, screen it, and do not retune.

M2D must pass before forward PAPER/SHADOW execution is considered.
