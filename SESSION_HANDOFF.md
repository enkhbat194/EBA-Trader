# EBA Trader — Session Handoff

_Last handoff prepared: 2026-08-27 17:57 (Asia/Ulaanbaatar)_

## Purpose

This file is the exact cross-chat continuation point. A new AI session must restore project state from GitHub/runtime evidence before coding; it must not restart the project from memory or invent missing state.

## Exact repository state at handoff

- Repository: `enkhbat194/EBA-Trader`
- Authoritative base branch: `main`
- Exact `main` SHA: `93e684794cd692bf1534ec46a5c9186bb974bbb9`
- Open PRs at handoff: `0`
- Active unmerged research branch: `m5-stacked-imbalance-feature`
- Active branch head: `ec015d6b54e72d8906cd1e80d299f4d2ed213de1`
- Active branch relation to main: `3 commits ahead`, `0 behind`
- Active branch changed source files only:
  - `src/eba_trader/orderflow.py`
  - `src/eba_trader/footprint_dataset.py`
  - `src/eba_trader/orderflow_feature_dataset.py`
- No PR/CI proof exists yet for the active stacked-imbalance branch. Do not call it complete or production-ready.

## Verified production state

- Active runtime: Linode.
- Exact verified production build: `93e684794cd692bf1534ec46a5c9186bb974bbb9`.
- App/server release: `0.12.2 · LINODE-M7`.
- PWA cache: `eba-trader-ui-v15`.
- Public HTTPS PWA: `https://eba-trader-172-236-150-62.sslip.io/`.
- User-visible PWA check at 2026-08-27 17:53 Asia/Ulaanbaatar showed:
  - Server build `93e6847`
  - Runtime `LINODE`
  - `HTTPS READY`
  - Server scanner `ACTIVE`
  - Installed UI/server release both `0.12.2 · LINODE-M7`
  - PWA cache client/server both `eba-trader-ui-v15`
- Exact-main external production proof passed: public smoke, encrypted Demo reconnect, Chart, Positions, M5 terminal evidence, Fast restart proof, frozen-OOS lock and real-execution lock.
- The displayed `Released 2026-08-26` value is release metadata; it does not contradict the newer exact build SHA.

## What was completed

- M4 strategy platform/evidence foundation: complete.
- Restart-safe experiment queue, immutable evidence, deterministic development screening and robustness contracts: complete.
- Linode auto-update/recovery/logging hardening: deployed.
- Raw Binance per-tick INFO flood: fixed; market-data subscriptions remain active while per-tick service logging stays disabled/bounded.
- Persistent runtime/research storage: separate and production-deployed.
- One-time Binance Demo API credentials: encrypted on Linode; secret never returns to browser JS.
- Fast Momentum: sole active production paper engine; real orders remain disabled.
- Historical fixed-window BTCUSDT USD-M executed-trade data: official Binance public archive with SHA-256 checksum verification and causal alignment.
- First real fixed-window M5 development ablation: terminal COMPLETE with immutable evidence.
- Sanitized M5 report metrics: exposed through production Research API/proof on `main` SHA `93e684794cd...`.

## First real M5 development result — interpreted

Batch: `abl_6c4a8eeb83a662894a3f2816`

Fixed development window: `2026-08-01T00:00:00Z -> 2026-08-01T04:00:00Z`.

Candle-only baseline:

- total return: `-0.004244488397751933` (~`-0.42445%`)
- final equity: `9957.55511602248`
- trade count: `4`
- win rate: `0.25`
- max drawdown: `-0.004244488397751933`
- expectancy: `-10.611220994379892`
- total cost: `43.90484437829747`

Best observed tested Delta treatment: `delta_ratio_threshold=0.2`

- total return: `-0.0012055415604976805` (~`-0.12055%`)
- final equity: `9987.944584395023`
- trade count: `2`
- win rate: `0.5`
- max drawdown: `-0.0026586496267955173`
- expectancy: `-6.027707802488294`
- total cost: `21.99920182120285`

Interpretation:

- Delta filtering materially reduced loss/cost/drawdown on this tiny development window.
- Absolute loss was reduced by about 71.6% versus the candle-only baseline.
- The treatment was still negative-return and negative-expectancy.
- CVD-only did not demonstrate incremental improvement in this run.
- This is **development evidence only**. It is not an edge claim, frozen-OOS proof, lifecycle promotion, or trading authorization.

## Active work — DO NOT RESTART FROM SCRATCH

Branch `m5-stacked-imbalance-feature` has already started the next candidate family.

Implemented so far on that branch:

- deterministic executed-trade footprint diagonal imbalance calculation;
- buy/sell adjacent price-level comparison;
- configurable imbalance ratio contract;
- protection against false infinite imbalance from empty diagonal cells;
- consecutive imbalance-level stack measurement;
- buy stack / sell stack / signed stacked score plumbing;
- causal closed-footprint feature propagation into footprint/feature dataset code;
- feature-dataset schema work/backward-compatibility work has started.

Not yet proven on that branch:

- regression tests for all new stacked-imbalance behavior;
- complete feature registry/adapter/gate/orchestration integration;
- full Python regression and Ruff;
- CI/deployment/continuity gates;
- PR review/merge;
- real same-window controlled stacked-imbalance ablation;
- production deployment/proof.

## Next exact task

1. First inspect actual GitHub state. If `m5-stacked-imbalance-feature` still exists at/after `ec015d6b...` with no replacement PR, **resume that branch**; do not create a duplicate feature branch.
2. Inspect its three-file diff against current `main` before editing.
3. Complete deterministic unit/regression tests for diagonal/stacked imbalance, including zero-volume/empty-diagonal, directionality, consecutive-stack, deterministic replay and causal availability cases.
4. Finish the feature-dataset/registry/backtest adapter contract so stacked imbalance can be consumed as an allowlisted development feature without future leakage.
5. Add a bounded controlled gate set for stacked imbalance; keep the candle-only baseline and recorded fees/slippage identical.
6. Run full regression + Ruff + shell/deployment/continuity checks on the exact branch head.
7. Open PR only after local/CI contract is ready; merge only when required workflows pass on the exact PR head.
8. After merge/exact Linode deploy, run the same fixed development window and compare return, expectancy, drawdown, cost, trade count and win rate against baseline/Delta evidence.
9. Only after that proceed to absorption/exhaustion, then price/delta divergence.
10. Keep LOB reconstruction separate and later.

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
- Historical fixed windows are not silently shifted to hide provider retention limitations.
- Archive checksum/sequence/integrity problems fail closed.
- High-frequency raw market ticks are not normal INFO service logs.

## Continuous-work / new-chat startup protocol

The next AI session must perform this sequence before implementation:

1. Read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, this `SESSION_HANDOFF.md`, and `docs/CONTINUITY_PROTOCOL.md`.
2. Query GitHub and verify actual `main` SHA, active branch head, open PRs and workflow state.
3. Compare the active branch against `main`; inspect the existing implementation before changing it.
4. Treat GitHub code/workflow/runtime proof as source of truth. This handoff is context, not permission to invent state.
5. Continue the existing branch/task when valid rather than starting the project or task over.
6. Work sequentially: one core architecture task/branch/package at a time, then deterministic tests -> CI/log inspection -> fixes -> PR -> exact-head workflows -> merge -> production proof -> continuity update.
7. At chat/session exit, update repo continuity with exact files, branch, PR, CI, merge SHA, production proof, unresolved risks and the next exact action.

The goal of this protocol is uninterrupted cross-chat work: a new chat should recover state from the repository and continue, not ask the user to reconstruct prior work.
