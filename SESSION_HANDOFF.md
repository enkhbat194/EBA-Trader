# EBA Trader — Session Handoff

_Last handoff prepared: 2026-08-27 22:25 (Asia/Ulaanbaatar)_

## Purpose

This file is the exact cross-chat continuation point. A new AI session must restore project state from GitHub/runtime evidence before coding; it must not restart the project from memory or invent missing state. Actual GitHub code, workflow state and production proof override this prose if they diverge.

## Exact functional repository state behind this handoff

- Repository: `enkhbat194/EBA-Trader`
- Authoritative base branch: `main`
- Latest functional response-proof main SHA before this continuity-only update: `a49790838064769768fe4ca9fe500f6ed941ba82`
- PR #59: absorption/exhaustion implementation — merged.
- PR #59 merge SHA: `a48fdb6a7845390cf3dcad9f5e649d4b716a12b1`.
- PR #60: absorption/exhaustion fixed-window Linode proof — merged.
- PR #60 merge / functional proof SHA: `a49790838064769768fe4ca9fe500f6ed941ba82`.
- Completed implementation branch: `m5-absorption-exhaustion-feature`; do not recreate completed work if that branch still exists.
- Completed production-proof branch: `m5-absorption-exhaustion-production-proof`; do not resume it.
- Continuity branch preparing this handoff: `continuity-m5-absorption-exhaustion-proof`.
- After the continuity PR merges, query actual `main` SHA/open PR/workflow state; do not assume `a497908...` is still tip.

## Verified production state

Exact functional main `a49790838064769768fe4ca9fe500f6ed941ba82` passed:

- Linode production bundle;
- Linode runtime checks;
- public production smoke;
- hardened external exact-build production proof run `33081041663`.

External proof completed successfully at `2026-08-27T14:24:41Z` (`22:24:41` Asia/Ulaanbaatar) and verified:

- server build exactly `a49790838064769768fe4ca9fe500f6ed941ba82`;
- HTTPS/public runtime ready;
- encrypted saved Binance Demo reconnect;
- Chart and Positions checks;
- Fast restart proof PASS;
- M5 response ablation phase `COMPLETE`;
- all experiments terminal and passed;
- evidence complete;
- exactly four response treatments: absorption `0.10/0.20`, exhaustion `0.01/0.03`;
- response-specific immutable report path;
- Frozen OOS remained closed;
- real execution remained locked.

Production response report:

`/var/lib/eba-trader/research/evidence/m5-absorption-exhaustion-ablation-20260801T000000Z-20260801T040000Z.json`

Batch:

`abl_c9bf89e7fb1dd4971345d87d`

Workflow dataset:

`m5ds_eadc90a3c97b12f599de21fa`

App/server release remains `0.12.2 · LINODE-M7`; PWA cache `eba-trader-ui-v15`. Fast Momentum remains the sole active production paper engine. Real exchange orders remain disabled.

## What was completed in this package

### PR #59 — absorption / exhaustion implementation

Completed:

- causal absorption executed-flow response proxy;
- causal exhaustion weakening-flow proxy;
- explicit distinction from resting/hidden LOB liquidity;
- feature-dataset schema v3;
- allowlisted response-feature research consumption;
- fail-closed adapter behavior if required v3 columns are not physically present;
- bounded response gate support;
- deterministic directionality, boundary, zero/low-volume, replay/input-order and no-future-leakage regression tests;
- full regression, Ruff, shell/deployment/runtime and continuity CI before merge.

### PR #60 — exact Linode response evidence

Completed:

- prior Delta/CVD and stacked immutable reports preserved;
- one-shot M5 autorun switched to the response gate family on the same fixed four-hour development window;
- separate immutable absorption/exhaustion report path;
- exact response treatment set required: absorption `0.10/0.20`, exhaustion `0.01/0.03`;
- stale stacked evidence cannot satisfy the response proof;
- existing bounded systemd/research-only authority retained;
- exact-head PR CI passed before merge;
- exact-main Linode proof passed after merge.

## Fixed development comparison window

`2026-08-01T00:00:00Z -> 2026-08-01T04:00:00Z`

This window has remained unchanged across Delta/CVD, stacked and response candidate comparisons.

## Baseline and prior candidates

### Candle-only baseline

- total return: `-0.004244488397751933` (~`-0.42445%`)
- final equity: `9957.55511602248`
- trade count: `4`
- win rate: `0.25`
- max drawdown: `-0.004244488397751933`
- expectancy: `-10.611220994379892`
- total cost: `43.90484437829747`

### Best prior Delta treatment (`delta_ratio_threshold=0.2`)

- total return: ~`-0.12055%`
- trade count: `2`
- win rate: `0.5`
- expectancy: `-6.0277`
- absolute baseline loss reduction: ~`71.60%`

Still negative-return/negative-expectancy development evidence only.

### Best stacked treatment (threshold `1`)

- total return: ~`-0.12408%`
- trade count: `2`
- win rate: `0.5`
- expectancy: `-6.2041`
- absolute baseline loss reduction: ~`70.77%`

It did not beat Delta `0.2` on return or expectancy.

## Absorption / exhaustion fixed-window result — interpreted

### Absorption thresholds `0.10` and `0.20`

Both produced the same result:

- total return: `-0.0016739996904260313` (~`-0.16740%`)
- final equity: `9983.26000309574`
- trade count: `1`
- win rate: `0.0`
- max drawdown: `-0.0016739996904260313`
- expectancy: `-16.739996904259897`
- total cost: `10.99299019778177`
- absolute baseline loss reduction: ~`60.56%`

Interpretation: absorption materially reduced exposure and absolute loss versus baseline, but the only remaining trade lost. It is worse than prior Delta `0.2` and stacked threshold `1` on total return and expectancy.

### Exhaustion thresholds `0.01` and `0.03`

Both produced:

- total return: `0.0`
- final equity: `10000.0`
- trade count: `0`
- win rate: `0.0`
- max drawdown: `0.0`
- expectancy: `0.0`
- total cost: `0.0`

Interpretation: these thresholds rejected every candidate entry on this small fixed sample. **Zero trades are not evidence of a profitable edge.** Do not rank this as a winner merely because it avoided the baseline loss.

### Research conclusion

Absorption/exhaustion is retained as useful feature infrastructure and future combination material, but this isolated candidate family is closed without edge/survivor promotion. Delta `0.2` remains the least-negative tested development arm on the fixed window, and it is still negative.

No candidate has earned Frozen-OOS, paper/demo, shadow, micro-live or real-execution authority.

See `docs/M5_ABSORPTION_EXHAUSTION.md` for the full exact record.

## Next exact task — price / delta divergence

Do not reopen completed Delta, stacked or response branches. Start the next candidate only after querying actual GitHub state following this continuity merge.

1. Read canonical continuity files and query actual `main`, branches, open PRs and workflows.
2. Create one fresh `price/delta divergence` branch from actual latest `main`.
3. Define divergence causally using price and already-closed executed-flow Delta only.
4. A bearish candidate should mean price makes/extends a local high while Delta fails to confirm; bullish is the symmetric local-low case.
5. Do **not** use future bars to label pivots. Define lookback/local-extreme logic available at decision time.
6. Specify bounded lookback, minimum price excursion, minimum flow activity and confirmation rules; fail closed on insufficient history.
7. Add bullish/bearish directionality, flat/zero-volume, boundary, replay/input-order and no-future-leakage tests.
8. Extend versioned feature materialization/registry/backtest adapter only through bounded allowlisted fields.
9. Add a small controlled treatment set while preserving exact baseline, EMA, initial capital, fees/slippage and fixed development window.
10. Run full regression + Ruff + shell/deployment/runtime/continuity checks and fix all failures.
11. Open one PR, require exact-head green workflows, merge, deploy exact main and obtain external exact-build Linode proof.
12. Run the same fixed development comparison and interpret versus baseline, Delta, stacked and response evidence.
13. A development improvement still cannot open Frozen OOS. Robustness remains required before OOS under lifecycle policy v2.
14. LOB reconstruction stays separate and later.

## Hard safety / architecture constraints

- Real-money execution remains locked.
- Frozen OOS remains locked until lifecycle policy explicitly permits it.
- Deterministic Risk Engine retains final veto authority; AI/lifecycle code cannot bypass it.
- Development rankings/wins have no promotion authority.
- Zero-trade arms are not profitable-edge evidence.
- API secrets never go to Git, chat, logs or browser persistent storage.
- Research workers/ablation jobs have no exchange-order authority.
- Runtime TradeLedger and research DB/evidence/datasets remain separate.
- Spot and USD-M futures data are never silently mixed.
- Executed-trade footprint and resting LOB liquidity remain separate data planes.
- Absorption/exhaustion are proxies, not direct observation of hidden/passive institutional intent.
- Same-candle still-forming footprint data cannot enter a candle decision.
- Historical fixed windows are not silently shifted.
- Archive checksum/sequence/integrity problems fail closed.
- Missing versioned feature columns fail closed.

## Continuous-work / new-chat startup protocol

The next AI session must:

1. Read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, this `SESSION_HANDOFF.md`, and `docs/CONTINUITY_PROTOCOL.md`.
2. Query GitHub and verify actual `main` SHA, active branch head, open PRs and workflow state.
3. Compare any active branch against `main` before editing; do not duplicate existing work.
4. Treat GitHub code/workflow/runtime proof as source of truth.
5. Work sequentially: one core architecture/research package at a time -> deterministic tests -> CI/log inspection -> fixes -> PR -> exact-head workflows -> merge -> production proof -> continuity update.
6. At session exit, record exact files, branch, PR, CI, merge SHA, production proof, unresolved risks and next exact action.
