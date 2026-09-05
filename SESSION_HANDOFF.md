# EBA Trader — Session Handoff

_Last handoff prepared: 2026-09-05 (Asia/Ulaanbaatar)_

## Startup rule

Repository: `enkhbat194/EBA-Trader`.

Before editing, query current `main`, open/recent PRs, exact production workflows and continuity docs. Merged code + exact production evidence + latest explicit frozen decisions override stale prose.

## Current main checkpoint

Current main:

`c8befb7799abbffc740399a941632fcdc0adb273`

Relevant sequence:

- #140 — local-only next-D0 materializer + shared checkout lock;
- #141 — read-only exact-production progress proof;
- #142 — sanitized read-only systemd telemetry;
- #144 — confirmed preflight failure repair + complete builder-source identity regression guard;
- #146 — PR transport failures are diagnostic-only while main proof stays strict; concurrency isolated per PR/ref;
- #147 — read-only Research / AI Lab next-D0 progress UI with explicit scientific locks.

## Immutable first Strategy Factory v2 D0 result

Campaign `sfv2-discovery-pilot-v1`:

- 406 candidates / 8 families;
- 12 strata;
- 4,872 / 4,872 terminal trials;
- frozen survivors: **0**.

D1 did not open. Frozen OOS did not open. No winner was manufactured by threshold changes. There is still **no verified profitable strategy**.

The postmortem concluded the first factory was too parameter-centric and heavily exposed to one-minute friction/turnover. The next campaign therefore expands mechanism/horizon diversity rather than neighboring parameter count.

## Frozen next campaign

Campaign: `sfv2-existing-data-low-turnover-v1`.
Design: `sfv2-next-existing-data-v1`.

Implemented causal families:

1. `mtf_trend_pullback_v1`;
2. `breakout_retest_entry_v1`;
3. `path_efficiency_persistence_v1`;
4. `low_turnover_flow_persistence_v1`.

Causal closed-1m -> 5m/15m/60m aggregation is implemented. Breakout requires a later fully closed retest rather than breakout-bar fill. Flow persistence uses minimum hold/cooldown.

Frozen catalog:

- 32 candidates/family;
- 128 total;
- prior inspected count 406;
- cumulative search history on evaluation 534;
- SHA-256 `0aa793ca70ba8719486ba6edae314c77803e1b87884665d17ec88019ec71654a`;
- authority `CATALOG_FREEZE_ONLY`.

No performance was inspected during catalog freeze.

## Frozen next-D0 data plan

Authority: `D0_DATA_MATERIALIZATION_ONLY` / `D0_DISCOVERY_ONLY_NOT_CONFIRMATION`.

- BTCUSDT Binance USD-M Futures;
- 1m base interval;
- verified Binance public USD-M `aggTrades` archive;
- price bucket 5.0;
- plan SHA-256 `c3ae7735f657d905c2931613062fa9091c72dd9458d7cdfae678a01bcea26171`;
- ten windows from `2026-08-22T00:15:00Z` through exactly `2026-09-01T00:00:00Z`.

Protected ranges remain sealed:

- 2025 first-cycle Frozen OOS;
- M5 Frozen OOS `2026-08-15T00:00:00Z -> 2026-08-22T00:00:00Z`;
- SF4 prospective `2026-09-01T00:00:00Z -> 2026-09-13T00:00:00Z`.

## Production materializer contract

`eba-sfv2-next-d0-materialization.service`:

- local/root-side only; no public mutation endpoint;
- at most one frozen window per invocation;
- shared `/run/lock/eba-trader-runtime-mutation.lock` with deployment;
- research state under `/var/lib/eba-trader/research/...` outside Git checkout;
- bounded CPU/memory/time;
- status written only after a complete window succeeds;
- final dataset bundle SHA only after ten completed receipts.

Each successful receipt must bind exact feature SHA-256, row count, workflow ID, candle provenance, order-flow provenance/archive integrity, causal timestamp validity and frozen source identity.

## Confirmed failure and repair

Pre-#144 telemetry proved a same-second failure:

- `activeState=failed`;
- `result=exit-code`;
- `execMainStatus=1`;
- start/exit `2026-09-05 09:22:57 UTC`.

Root cause: the builder source-contract hash referenced nonexistent `src/eba_trader/footprint.py` before any network/materialization work. PR #144 corrected the path to `footprint_dataset.py`, added omitted direct order-flow feature dependencies to the frozen builder identity and added regression protection requiring every pinned source path to exist.

No first receipt existed before #144, so correcting the source identity did not invalidate immutable evidence.

## Current empirical production evidence

Current exact main/deployed build: `c8befb7799abbffc740399a941632fcdc0adb273`.

Current-main Linode production bundle run `33966683041`: `success`.

Strict next-D0 production proof run `33966683013`, job `101307967313`: `success`. At `2026-09-05T12:41:42Z`:

- exact `c8befb77...` build was live;
- `productionHealthy=true`;
- status receipt remained unavailable;
- completed windows: **0 / 10**;
- source-code SHA: null;
- final dataset bundle SHA: null;
- service loaded and `activeState=activating`;
- `result=success`, `execMainStatus=0`;
- service start `2026-09-05 12:41:29 UTC`;
- performance/D1/Frozen-OOS/SF4/live/real authority flags all remained false/closed.

The service has entered real local materialization execution, but next-d0-01 is **not proven complete**.

PR #145's earlier SSL handshake timeout was transport evidence from a GitHub runner, not strategy evidence. PR #146 makes PR base-observation transport failure diagnostic-only and keeps the main strict proof authoritative/fail-closed. It also prevents unrelated PRs from cancelling one another's progress-proof runs.

PR #147 adds a read-only PWA progress card showing receipt count, service state and explicit `LOCKED` / `NO · DISCOVERY ONLY` labels. It has no start/stop/materialize mutation authority and cannot label a complete dataset as verified profitability.

Classification:

- materializer: **CODE READY**;
- exact current deployment: **PRODUCTION VERIFIED**;
- service execution: **EMPIRICALLY STARTED**;
- completed receipts: **0 / 10**;
- ten-window corpus: **NOT YET EMPIRICALLY VERIFIED COMPLETE**;
- 128-candidate evaluation: **NOT AUTHORIZED**;
- **VERIFIED PROFITABLE: NONE**.

## Future professional research direction

Do not retrofit these ideas into the frozen 128-candidate campaign. A later versioned DESIGN_ONLY research track may add:

- Professional Strategy Hypothesis Library with trader/systematic archetypes converted into deterministic causal rules;
- historical funding-rate data;
- historical open-interest data;
- historical futures basis/premium data;
- predeclared multi-symbol relative-strength/relative-value universe;
- versioned regime engine;
- historical L2/order-book only if sequence/integrity reconstruction is defensible.

Any such future campaign must freeze data/provenance, universe, mechanisms and search budget before performance inspection.

## What was completed

- Reconciled actual GitHub/production state instead of trusting stale handoff prose.
- Proved and repaired the materializer's preflight source-contract bug in #144.
- Kept scientific gates unchanged and evaluation closed.
- Fixed PR production-proof transport semantics and cross-PR concurrency in #146; exact-head checks were green before merge.
- Built a read-only next-D0 Research / AI Lab progress UI in #147 with regression protection against promotion/profitability mislabeling; exact-head checks were green before merge.
- Merged #147 as current main `c8befb7799abbffc740399a941632fcdc0adb273`.
- Verified current main with successful production bundle and strict next-D0 proof run `33966683013`.
- Current authoritative receipt count remains 0/10.
- No strategy performance was inspected during these operational/UI changes.

## Next exact task

1. Read the next terminal production service/receipt evidence after the active first materialization cycle.
2. If next-d0-01 completes, validate exact row count, feature SHA, workflow ID, candle/order-flow provenance/checksum, causal timestamps and newly pinned `sourceCodeSha`.
3. If an operational failure is proven, fix only that proven cause; do not alter the scientific contract based on speculation.
4. After the first successful receipt pins `sourceCodeSha`, do not modify frozen builder/source-contract files between windows.
5. Continue one-window-at-a-time until ten validated receipts exist.
6. Freeze one immutable corpus receipt binding plan SHA, catalog SHA, ten feature SHAs, ten workflow IDs, row counts, provenance and source identity.
7. Only then create a separate explicit 128-candidate D0 evaluator authorization package and freeze selection rules before performance inspection.
8. Keep SF4 sealed until `2026-09-13T00:00:00Z` and real money locked.

## Hard locks

- profitability/expectancy/sample/statistical gates unchanged;
- fees/slippage mandatory;
- causal/no-lookahead execution mandatory;
- inspected data cannot become fresh confirmation;
- D1 sealed until a frozen non-empty survivor set exists;
- Frozen OOS sealed;
- Demo execution plumbing only;
- real Binance execution locked;
- deterministic risk retains veto authority.

## Files to read on continuation

`AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, this file, `BACKTEST_PROTOCOL.md`, `STRATEGY_SPEC.md`, `docs/SFV2_NEXT_D0_PRODUCTION_MATERIALIZATION_2026-09-04.md` and current SFv2 design/result documents, then actual GitHub/production state.
