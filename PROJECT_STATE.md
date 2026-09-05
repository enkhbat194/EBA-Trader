# EBA Trader — Project State

_Last reconciled: 2026-09-05 (Asia/Ulaanbaatar)_

Actual merged code, exact-build production evidence and the latest explicit frozen decisions override stale prose. Query GitHub and production before editing.

## Current goal

Find genuinely repeatable net trading edge with deterministic, causal, cost-aware verification. Do not manufacture winners by weakening gates. Real-money execution remains locked.

## Canonical repository state

- Repository: `enkhbat194/EBA-Trader`.
- Production PWA: `https://eba-trader-172-236-150-62.sslip.io`.
- Current main: `c8befb7799abbffc740399a941632fcdc0adb273`.
- PR #140: local-only next-D0 materializer + shared checkout lock.
- PR #141: read-only exact-production next-D0 progress proof.
- PR #142: sanitized read-only systemd telemetry.
- PR #144: confirmed materializer preflight repair + complete builder-source identity regression guard.
- PR #146: PR production transport failures became diagnostic-only while main stayed strict; progress-proof concurrency is isolated per PR/ref.
- PR #147: read-only PWA Research / AI Lab next-D0 progress surface with explicit evaluation/confirmation locks.
- Factory D1: **SEALED**.
- Frozen OOS: **SEALED**.
- SF4: **SEALED until 2026-09-13T00:00:00Z**.
- Real-money execution: **LOCKED**.

## First Strategy Factory v2 D0 — immutable result

Campaign `sfv2-discovery-pilot-v1`, authority `DISCOVERY_ONLY`:

- 406 candidates / 8 mechanism families;
- 12 D0 strata;
- 4,872 / 4,872 terminal trials;
- 254 rejected/incomplete;
- 152 complete non-rejected candidates;
- frozen survivors: **0**;
- D1 opened: false;
- Frozen OOS opened: false.

The zero-survivor result is immutable. No threshold was weakened and unused search slots are not a post-hoc retuning budget.

The production postmortem found all 152 complete non-rejected candidates had non-positive net return, expectancy and benchmark-relative return. Important failure modes included high one-minute turnover/cost, ATR and Donchian next-open chase, and inactive/rejected mechanisms. There is still **no verified profitable strategy**.

## Frozen next campaign

Campaign: `sfv2-existing-data-low-turnover-v1`.
Design: `sfv2-next-existing-data-v1`.

Implemented causal families:

1. `mtf_trend_pullback_v1`;
2. `breakout_retest_entry_v1`;
3. `path_efficiency_persistence_v1`;
4. `low_turnover_flow_persistence_v1`.

Causal closed-1m -> 5m/15m/60m aggregation is implemented. Breakout-retest cannot fill on the breakout bar. Flow persistence structurally limits turnover with minimum-hold/cooldown rules.

Frozen catalog:

- 32 candidates per family;
- 128 total;
- prior inspected search history: 406;
- cumulative search-history count if evaluated: 534;
- catalog SHA-256: `0aa793ca70ba8719486ba6edae314c77803e1b87884665d17ec88019ec71654a`;
- authority: `CATALOG_FREEZE_ONLY`.

No performance was inspected during catalog freeze.

## Protected data boundary

The next-D0 discovery path cannot consume:

- 2025 first-cycle Frozen OOS;
- M5 Frozen OOS: `2026-08-15T00:00:00Z -> 2026-08-22T00:00:00Z`;
- SF4 prospective interval: `2026-09-01T00:00:00Z -> 2026-09-13T00:00:00Z`.

Previously inspected development data is not fresh confirmation evidence.

## Frozen next-D0 dataset plan

Authority: `D0_DATA_MATERIALIZATION_ONLY` / `D0_DISCOVERY_ONLY_NOT_CONFIRMATION`.

- BTCUSDT Binance USD-M Futures;
- base interval 1m;
- price bucket 5.0;
- verified public Binance USD-M `aggTrades` archive;
- dataset-plan SHA-256 `c3ae7735f657d905c2931613062fa9091c72dd9458d7cdfae678a01bcea26171`;
- 10 windows from `2026-08-22T00:15:00Z` through exactly `2026-09-01T00:00:00Z`.

All ten feature datasets and receipts must be complete and validated before any performance evaluator authorization exists.

## Production materialization architecture

`eba-sfv2-next-d0-materialization.service` is local/root-side only:

- one frozen window maximum per invocation;
- shared `/run/lock/eba-trader-runtime-mutation.lock` with deployment;
- persistent research writes only under `/var/lib/eba-trader/research/...`;
- bounded CPU/memory/runtime;
- no public/PWA mutation endpoint;
- status is written only after a whole window succeeds;
- final dataset bundle SHA appears only after all ten receipts are complete.

Each successful window receipt must bind exact row count, feature SHA-256, workflow ID, candle provenance, order-flow provenance/archive integrity, causal timestamps and frozen builder source identity.

## Confirmed failure and repair

Before PR #144 production telemetry proved a same-second preflight failure:

- `activeState=failed`;
- `result=exit-code`;
- `execMainStatus=1`;
- start and exit both at `2026-09-05 09:22:57 UTC`.

Root cause was a nonexistent pinned source path `src/eba_trader/footprint.py` in the builder source-contract hash. PR #144 corrected it to `footprint_dataset.py`, added omitted direct order-flow feature dependencies to the source identity and added regression coverage requiring every pinned path to exist. No dataset receipt existed before this repair, so no immutable receipt identity was invalidated.

## Current empirical production state

Current exact main/deployed build: `c8befb7799abbffc740399a941632fcdc0adb273`.

Strict next-D0 production proof run `33966683013`, job `101307967313`, completed `success`. At `2026-09-05T12:41:42Z` it proved:

- exact build `c8befb77...` reached production;
- `productionHealthy=true`;
- next-D0 status receipt still unavailable;
- completed windows: **0 / 10**;
- dataset bundle SHA: null;
- source-code SHA: null because no first receipt has completed;
- service loaded and `activeState=activating`;
- `result=success`;
- `execMainStatus=0`;
- service start: `2026-09-05 12:41:29 UTC`;
- performance/D1/Frozen-OOS/SF4/live/real authority flags remain false/closed.

This proves current code/deployment and the local materialization path are healthy at the strict proof checkpoint. It does **not** prove next-d0-01 completed.

The earlier PR #145 observation timeout was a GitHub-runner -> production TLS handshake failure. PR #146 now reports such PR transport failures as non-authoritative diagnostics; main strict proof remains fail-closed and authoritative.

PR #147 added a read-only Research / AI Lab card showing receipt progress, service state and explicit `LOCKED` / `NO · DISCOVERY ONLY` labels. It contains no materialization mutation path and cannot promote a dataset into a profitability claim.

Classification:

- materializer: **CODE READY**;
- current exact main: **PRODUCTION VERIFIED**;
- materialization service execution: **EMPIRICALLY STARTED**;
- completed next-D0 receipts: **0 / 10**;
- ten-window corpus: **NOT YET EMPIRICALLY VERIFIED COMPLETE**;
- 128-candidate D0 performance evaluation: **NOT AUTHORIZED**;
- verified profitable strategy: **NONE**.

## Future research direction — separate campaign only

After the current frozen campaign is completed without contamination, future DESIGN_ONLY work may expand hypothesis quality and information diversity through:

- a Professional Strategy Hypothesis Library converted into deterministic causal rules rather than copied trader claims;
- historical funding-rate acquisition/provenance;
- historical open-interest acquisition/alignment;
- historical futures basis/premium data;
- a predeclared multi-symbol universe for relative-strength/relative-value mechanisms;
- a versioned regime engine;
- historical L2/order-book research only if sequence and integrity reconstruction are defensible.

These inputs may **not** be retrofitted post-hoc into the frozen 128-candidate campaign after observing performance.

## Validation

- First D0: 4,872 / 4,872 terminal, 0 frozen survivors.
- PR #144 repaired the confirmed source-contract preflight failure and passed exact-head CI before merge.
- PR #146 exact-head checks passed before merge; main strict proof remained fail-closed.
- PR #147 exact head `f08b351668492d64894f3231e7cac582d9c93931` passed all relevant checks before merge.
- Current-main Linode production bundle run `33966683041`: `success`.
- Current-main strict next-D0 proof run `33966683013`: `success` on exact `c8befb7799abbffc740399a941632fcdc0adb273`.
- Performance/D1/Frozen-OOS/SF4/live/real authority remains closed throughout materialization.

## Safety invariants

- profitability/expectancy/sample/statistical gates are not lowered;
- fees/slippage remain included;
- causality/no-lookahead is mandatory;
- inspected data is never relabelled fresh;
- Demo is execution plumbing, not verification;
- discovery ranking is not promotion authority;
- D1 remains closed until a frozen non-empty survivor set exists;
- Frozen OOS remains sealed until prerequisites pass;
- deterministic risk keeps veto authority;
- real execution remains locked.

## Next exact tasks

1. Read the next production service/receipt evidence after the active first materialization cycle.
2. If an operational failure is proven, fix only the proven cause while preserving the frozen scientific contract.
3. If next-d0-01 completes, validate row count, feature SHA, workflow ID, candle/order-flow provenance, checksum, causal timestamps and pinned `sourceCodeSha`.
4. After the first receipt pins `sourceCodeSha`, do not modify frozen builder/source-contract files between windows.
5. Continue one-window-at-a-time until all ten validated receipts exist.
6. Freeze one immutable corpus receipt binding plan SHA, catalog SHA, ten feature SHAs, ten workflow IDs, row counts, provenance and source identity.
7. Only then create a separate explicit 128-candidate D0 evaluator authorization package and freeze selection rules before performance inspection.
8. D0 survivors remain discovery-only; zero survivors is acceptable.

## Continuity protocol

New sessions read `AGENTS.md`, this file, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, `SESSION_HANDOFF.md`, `BACKTEST_PROTOCOL.md`, `STRATEGY_SPEC.md`, `docs/SFV2_NEXT_D0_PRODUCTION_MATERIALIZATION_2026-09-04.md` and current SFv2 design/result documents, then query actual GitHub/production state before editing.
