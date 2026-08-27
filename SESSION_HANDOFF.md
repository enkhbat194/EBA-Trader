# EBA Trader — Session Handoff

_Last handoff prepared: 2026-08-27 20:09 (Asia/Ulaanbaatar)_

## Purpose

This file is the exact cross-chat continuation point. A new AI session must restore project state from GitHub/runtime evidence before coding; it must not restart the project from memory or invent missing state. The continuity-only merge containing this handoff advances `main` beyond the functional proof SHA below, so actual GitHub state must always be queried first.

## Exact functional repository state behind this handoff

- Repository: `enkhbat194/EBA-Trader`
- Authoritative base branch: `main`
- Functional stacked-proof main SHA: `738ed32e557045abb6b738c7f5236962ee3dd516`
- PR #56: stacked/diagonal implementation — merged.
- PR #56 implementation merge SHA: `d15c29895d39ae6db5fabea4895daf7ad5facfa6`.
- PR #57: stacked fixed-window Linode proof — merged.
- PR #57 merge / functional proof SHA: `738ed32e557045abb6b738c7f5236962ee3dd516`.
- Completed feature branch: `m5-stacked-imbalance-feature`; do not resume or recreate it.
- Completed production-proof branch: `m5-stacked-production-proof`; do not resume or recreate it.
- Continuity branch preparing this file: `continuity-m5-stacked-proof`.
- After this continuity-only PR merges, query actual `main` SHA and open PR state; do not assume the functional SHA above is still tip.

## Verified production state

Exact functional main `738ed32e557045abb6b738c7f5236962ee3dd516` passed:

- Linode production bundle (`33070015955`);
- Linode runtime checks (`33070015882`);
- public production smoke (`33070015880`);
- hardened external exact-build stacked production proof (`33070015871`).

External stacked proof completed successfully at `2026-08-27T12:08:54Z` (`20:08:54` Asia/Ulaanbaatar) and verified:

- server build exactly `738ed32e557045abb6b738c7f5236962ee3dd516`;
- HTTPS/public runtime ready;
- encrypted saved Binance Demo reconnect;
- Chart and Positions checks;
- Fast restart proof PASS;
- stacked M5 phase `COMPLETE`;
- all experiments passed;
- all experiments terminal;
- evidence complete;
- stacked treatment thresholds exactly `[1,2,3]`;
- Frozen OOS remained closed;
- real execution remained locked.

Production stacked report:

`/var/lib/eba-trader/research/evidence/m5-stacked-imbalance-ablation-20260801T000000Z-20260801T040000Z.json`

App/server release remains `0.12.2 · LINODE-M7`; PWA cache `eba-trader-ui-v15`. Fast Momentum remains the sole active production paper engine. Real exchange orders remain disabled.

## What was completed in this package

### PR #56 — stacked / diagonal implementation

The existing `m5-stacked-imbalance-feature` work was resumed rather than restarted.

Completed:

- deterministic bullish/bearish diagonal imbalance from executed-trade footprint levels;
- exact `price_step` adjacency; missing price buckets break comparisons/stacks;
- zero/empty diagonal protection against false infinite imbalance;
- longest consecutive bullish/bearish stacks and signed stacked score;
- causal prior-closed-footprint propagation;
- feature-dataset schema v2 with legacy v1 Delta/CVD replay compatibility;
- allowlisted `of_stacked_imbalance`;
- fail-closed stacked gate on legacy datasets without physical stacked columns;
- bounded gate thresholds `1/2/3`;
- deterministic directionality, zero-volume, missing-bucket, replay, schema, causal-availability, adapter and gate-version regression tests;
- full regression, Ruff, shell/deployment/runtime and continuity CI before merge.

### PR #57 — exact Linode stacked evidence

Completed:

- prior Delta/CVD immutable report preserved;
- Linode one-shot M5 autorun switched explicitly to `config/m5_stacked_imbalance_gate_set_v2.json`;
- separate immutable stacked report path used;
- idempotent COMPLETE acceptance requires all-terminal/evidence-complete, locks closed, treatmentCount `3` and stacked thresholds `[1,2,3]`;
- external production proof rejects stale Delta-only evidence and requires the stacked-specific report path/thresholds;
- existing 40% CPU / 700 MB memory / 45-minute / research-only-write systemd bounds retained;
- exact-head PR CI passed before merge;
- exact-main Linode proof passed after merge.

## Prior Delta/CVD result for comparison

Fixed development window:

`2026-08-01T00:00:00Z -> 2026-08-01T04:00:00Z`

Prior Delta batch: `abl_6c4a8eeb83a662894a3f2816`.

Candle-only baseline:

- total return: `-0.004244488397751933` (~`-0.42445%`)
- final equity: `9957.55511602248`
- trade count: `4`
- win rate: `0.25`
- max drawdown: `-0.004244488397751933`
- expectancy: `-10.611220994379892`
- total cost: `43.90484437829747`

Best prior tested Delta treatment (`delta_ratio_threshold=0.2`):

- total return: `-0.0012055415604976805` (~`-0.12055%`)
- final equity: `9987.944584395023`
- trade count: `2`
- win rate: `0.5`
- max drawdown: `-0.0026586496267955173` (~`-0.26586%`)
- expectancy: `-6.027707802488294`
- total cost: `21.99920182120285`
- absolute baseline loss reduction: ~`71.60%`

This remains negative-return/negative-expectancy development evidence only.

## Stacked / diagonal fixed-window result — interpreted

Stacked batch: `abl_232b7cb262de90363283356d`.

Dataset workflow: `m5ds_ca555c0ee588e17847d4c477`.

The candle baseline reproduced exactly, confirming comparability with the prior run.

### Threshold 1 — best stacked treatment on this window

- total return: `-0.0012408244799629875` (~`-0.12408%`)
- final equity: `9987.59175520037`
- trade count: `2`
- win rate: `0.5`
- max drawdown: `-0.0024163539692870772` (~`-0.24164%`)
- expectancy: `-6.204122399814878`
- total cost: `21.98249146741619`
- absolute baseline loss reduction: ~`70.77%`

### Thresholds 2 and 3

Both produced the same result in this window:

- total return: `-0.0013709100484625703` (~`-0.13709%`)
- final equity: `9986.290899515374`
- trade count: `1`
- win rate: `0.0`
- max drawdown: `-0.0013709100484625703`
- expectancy: `-13.709100484626106`
- total cost: `10.994657857876607`

### Research conclusion

Stacked threshold `1` is a substantial filter versus candle-only baseline, but it does **not** beat prior Delta `0.2` on return or expectancy. Its absolute loss is about `2.93%` larger than the Delta treatment's absolute loss. It has a slightly smaller drawdown and marginally lower total cost, with the same two trades and 50% win rate.

Thresholds `2/3` mostly suppress exposure; the remaining trade loses and expectancy is worse.

Therefore stacked/diagonal imbalance is closed as useful development evidence/infrastructure, **not** as proven edge or promoted survivor. It receives no Frozen-OOS, paper, Demo, shadow, micro-live or real-execution authority.

## Next exact task — absorption / exhaustion

Do not reopen the completed stacked branches. Start the next candidate only after verifying actual GitHub state following this continuity merge.

1. Read canonical continuity files, then query actual `main`, branches, open PRs and workflows.
2. Create one new absorption/exhaustion branch from actual latest `main`.
3. Define absorption/exhaustion strictly from causal executed-trade footprint data; do not infer resting LOB liquidity.
4. Specify bounded allowlisted feature fields/parameters and fail-closed unavailable-data behavior.
5. Add deterministic directionality, zero/low-volume, boundary, replay/input-order and no-future-leakage tests.
6. Extend feature materialization/registry/backtest adapter only as needed for the bounded candidate.
7. Add a small controlled gate set; preserve exact candle baseline, EMA, initial capital, fee/slippage assumptions and fixed development window.
8. Run full regression + Ruff + shell/deployment/continuity checks; fix all failures.
9. Open one PR, require exact-head green workflows, merge, deploy exact main and obtain external exact-build Linode proof.
10. Run the same fixed `2026-08-01T00:00Z -> 04:00Z` comparison and interpret metrics versus candle baseline, Delta and stacked evidence.
11. Only then move to price/delta divergence.
12. LOB reconstruction stays separate and later.

## Hard safety / architecture constraints

- Real-money execution remains locked.
- Frozen OOS remains locked until lifecycle policy explicitly permits it.
- Deterministic Risk Engine retains final veto authority; AI/lifecycle code cannot bypass it.
- Development rankings/wins have no promotion authority.
- API secrets never go to Git, chat, logs or browser persistent storage.
- Research workers/ablation jobs have no exchange-order authority.
- Runtime TradeLedger and research DB/evidence/datasets remain separate.
- Spot and USD-M futures data are never silently mixed.
- Executed-trade footprint and resting LOB liquidity remain separate data planes.
- Same-candle still-forming footprint data cannot enter a candle decision.
- Historical fixed windows are not silently shifted.
- Archive checksum/sequence/integrity problems fail closed.
- High-frequency raw market ticks are not normal INFO service logs.

## Continuous-work / new-chat startup protocol

The next AI session must:

1. Read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, this `SESSION_HANDOFF.md`, and `docs/CONTINUITY_PROTOCOL.md`.
2. Query GitHub and verify actual `main` SHA, active branch head, open PRs and workflow state.
3. Compare any active branch against `main` before editing; do not duplicate existing work.
4. Treat GitHub code/workflow/runtime proof as source of truth.
5. Work sequentially: one core architecture/research package at a time -> deterministic tests -> CI/log inspection -> fixes -> PR -> exact-head workflows -> merge -> production proof -> continuity update.
6. At session exit, record exact files, branch, PR, CI, merge SHA, production proof, unresolved risks and next exact action.
