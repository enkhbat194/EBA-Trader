# EBA Trader — Project State

_Last reconciled: 2026-08-27 22:25 (Asia/Ulaanbaatar)_
_Current implementation frontier: M5 absorption/exhaustion implementation and exact Linode fixed-window proof are complete; next candidate family is price/delta divergence._

This is the primary cross-chat continuation summary. Actual GitHub code, PR/workflow state and production proof override stale prose. A new session must query actual GitHub state before implementation.

## Current goal

Operate EBA Trader as a restart-safe 24/7 Linode paper/research system; build a controlled AI Strategy Factory on the M4 evidence platform; discover strategies through deterministic historical simulation/backtest, screening, robustness and later forward/demo validation; maintain a verified strategy knowledge base; and keep real-money execution locked until the full evidence/lifecycle chain permits it.

## Current stage

- Production/runtime foundation: **VERIFIED**.
- M4 research/evidence platform: **COMPLETE**.
- M5 AI Strategy Factory/order-flow research: **IN PROGRESS**.
- Delta/CVD fixed-window candidate: **COMPLETE / INTERPRETED — NO EDGE/PROMOTION CLAIM**.
- Stacked/diagonal imbalance candidate: **COMPLETE / INTERPRETED — NO EDGE/PROMOTION CLAIM**.
- Absorption/exhaustion candidate: **COMPLETE / INTERPRETED — NO EDGE/PROMOTION CLAIM**.
- Next candidate family: **PRICE / DELTA DIVERGENCE**.
- Continuity system: **INSTALLED / ENFORCED**.
- Frozen OOS: **LOCKED**.
- Real-money execution: **LOCKED**.

## Canonical repository/runtime

- Repository: `enkhbat194/EBA-Trader`
- Default/base branch: `main`
- Latest functional M5 response-proof main SHA before this continuity update: `a49790838064769768fe4ca9fe500f6ed941ba82`
- PR #59 absorption/exhaustion implementation merge: `a48fdb6a7845390cf3dcad9f5e649d4b716a12b1`
- PR #60 fixed-window production-proof merge: `a49790838064769768fe4ca9fe500f6ed941ba82`
- Active implementation branch: none after response candidate closure; next branch must start from actual latest `main`.
- Runtime: Linode Nanode, Ubuntu 24.04 LTS
- Server repo: `/opt/Eba-Trader`
- Runtime DB: `/var/lib/eba-trader/eba_trader.db`
- Research DB: `/var/lib/eba-trader/research/eba_research.db`
- Research datasets: `/var/lib/eba-trader/research/datasets`
- Research evidence: `/var/lib/eba-trader/research/evidence`
- Public PWA: `https://eba-trader-172-236-150-62.sslip.io/`
- App/server release: `0.12.2 · LINODE-M7`
- PWA cache: `eba-trader-ui-v15`
- Auto deploy: `eba-auto-update.timer`
- Replit/Render backend paths: deprecated.

## Verified production reality

Exact main `a49790838064769768fe4ca9fe500f6ed941ba82` passed:

- Linode production bundle;
- Linode runtime checks;
- public production smoke;
- exact-build external Linode production proof;
- encrypted saved Binance Demo reconnect;
- Chart and Positions checks;
- Fast restart proof;
- terminal/evidence-complete M5 absorption/exhaustion development report;
- exactly four response treatments: absorption `0.10/0.20`, exhaustion `0.01/0.03`;
- Frozen OOS closed;
- real execution locked.

External proof run `33081041663` completed successfully at `2026-08-27T14:24:41Z` (`22:24:41` Asia/Ulaanbaatar).

Production response report:

`/var/lib/eba-trader/research/evidence/m5-absorption-exhaustion-ablation-20260801T000000Z-20260801T040000Z.json`

Fast Momentum remains the sole active production paper engine. Real exchange execution remains disabled.

## Research platform completed so far

### M4 — complete

PRs #20-#24 established immutable strategy versions, deterministic experiment IDs, restart-safe queue/leases, allowlisted workers, content-addressed evidence, development screening and bounded robustness contracts.

Lifecycle policy v2 is:

`GENERATED -> BACKTESTED -> ROBUSTNESS_VERIFIED -> OOS_VERIFIED -> PAPER_CANDIDATE -> PAPER_VERIFIED -> DEMO_CANDIDATE -> DEMO_VERIFIED -> SHADOW_VERIFIED -> MICRO_LIVE_ELIGIBLE -> LIVE_ELIGIBLE -> LIVE_ACTIVE`

Frozen OOS cannot be opened directly from `BACKTESTED`.

### M5 — current foundation

Completed infrastructure includes:

- constrained strategy DSL / approved feature registry;
- bounded strategy family generation and duplicate/near-duplicate filtering;
- historical Binance USD-M aggregate-trade acquisition, checksum/sequence/integrity validation and causal alignment;
- deterministic executed-trade footprint windows;
- versioned feature datasets;
- same-dataset candle-only/order-flow adapters;
- deterministic one-control-to-many-treatment development ablations;
- persistent bounded Linode research runtime;
- candidate-specific immutable comparison reports;
- exact public/external production proof;
- sanitized Research proof surfaced through the server/PWA.

Current versioned order-flow feature path:

- v1: buy/sell volume, Delta, Delta ratio, CVD, POC;
- v2: diagonal and stacked imbalance;
- v3: absorption/exhaustion executed-flow response proxies.

These are research features, not assumed alpha. Resting LOB/order-book liquidity remains a separate future data plane.

## Fixed development window

All current real M5 comparisons use the same development window:

`2026-08-01T00:00:00Z -> 2026-08-01T04:00:00Z`

The window has not been shifted between candidate families.

### Candle-only baseline

- total return: `-0.004244488397751933` (~`-0.42445%`)
- final equity: `9957.55511602248`
- trade count: `4`
- win rate: `0.25`
- max drawdown: `-0.004244488397751933`
- expectancy: `-10.611220994379892`
- total cost: `43.90484437829747`

## Delta/CVD evidence

Batch: `abl_6c4a8eeb83a662894a3f2816`.

Best tested Delta arm (`delta_ratio_threshold=0.2`):

- return ~`-0.12055%`
- final equity `9987.9446`
- 2 trades
- 50% win rate
- max drawdown ~`-0.26586%`
- expectancy `-6.0277`
- total cost `21.9992`
- absolute baseline loss reduction ~`71.60%`

Still negative-return/negative-expectancy; no promotion authority.

## Stacked / diagonal evidence

Batch: `abl_232b7cb262de90363283356d`.

Best stacked threshold `1`:

- return ~`-0.12408%`
- final equity `9987.5918`
- 2 trades
- 50% win rate
- max drawdown ~`-0.24164%`
- expectancy `-6.2041`
- total cost `21.9825`
- absolute baseline loss reduction ~`70.77%`

It improved the candle baseline but did not beat Delta `0.2` on return or expectancy. Thresholds `2/3` produced one losing trade. No promotion authority.

## Absorption / exhaustion evidence

Batch: `abl_c9bf89e7fb1dd4971345d87d`.

Workflow dataset: `m5ds_eadc90a3c97b12f599de21fa`.

### Absorption `0.10` and `0.20`

Both produced the same result:

- total return: `-0.0016739996904260313` (~`-0.16740%`)
- final equity: `9983.26000309574`
- trade count: `1`
- win rate: `0.0`
- max drawdown: `-0.0016739996904260313`
- expectancy: `-16.739996904259897`
- total cost: `10.99299019778177`
- absolute baseline loss reduction: ~`60.56%`

Interpretation: absorption reduced exposure/loss versus candle-only baseline, but the remaining trade lost. It was worse than prior Delta `0.2` and stacked threshold `1` on return and expectancy.

### Exhaustion `0.01` and `0.03`

Both produced zero trades:

- total return `0.0`
- trade count `0`
- exposure `0.0`
- cost `0.0`
- expectancy `0.0`

Interpretation: the tested thresholds were too restrictive for this four-hour sample. Zero trades are **not profitable-edge evidence** and must not be ranked as a winning strategy just because loss is zero.

### Response-feature conclusion

Absorption/exhaustion infrastructure is retained for future combinations, but this isolated candidate family is closed without an edge claim. Delta `0.2` remains the least-negative tested development arm on this fixed window, but it is still negative and not promotable.

See `docs/M5_ABSORPTION_EXHAUSTION.md` for the exact candidate record.

## Next exact tasks — price/delta divergence

1. Query actual GitHub `main`, open PRs and workflow state after this continuity merge.
2. Create one fresh branch for price/delta divergence from actual latest `main`.
3. Define divergence causally: local price high/low versus already-closed executed-flow Delta confirmation/failure; no future pivots/look-ahead.
4. Specify deterministic lookback, confirmation and minimum-activity rules; fail closed on insufficient history/data.
5. Add directionality, flat/zero-volume, boundary, replay/input-order and no-future-leakage tests.
6. Extend versioned feature materialization/registry/backtest gate only through bounded allowlisted fields.
7. Use a small controlled treatment set while preserving the exact candle baseline, EMA, capital, fees/slippage and fixed development window.
8. Run full regression + Ruff + shell/deployment/runtime/continuity checks and fix all failures.
9. Open one PR, require exact-head green CI, merge, deploy exact main to Linode and obtain exact production proof.
10. Run the same fixed development comparison and interpret return, expectancy, drawdown, cost, trade count and win rate versus baseline/Delta/stacked/response evidence.
11. Do not open Frozen OOS from a development win. Continue through robustness before OOS under lifecycle policy v2.
12. Keep LOB reconstruction separate and later.

## Important constraints

- No API secrets in Git, chat, logs or browser persistent storage.
- Deterministic Risk Engine has final veto authority.
- Runtime and research persistence remain separate.
- Strategy versions/evidence are immutable.
- AI-generated strategy descriptions cannot execute arbitrary generated Python.
- Executed-trade order flow and resting LOB liquidity are separate domains.
- Gapped/tampered historical data fails closed.
- Spot and USD-M futures are not silently mixed.
- Same-candle still-forming footprint data cannot be used in candle decisions.
- Fixed historical research windows are not silently shifted.
- Missing versioned feature columns fail closed.
- Zero-trade treatments are not interpreted as profitable edge.
- Development rankings/wins are not promotion evidence.
- Generic research workers cannot open frozen OOS or exchange execution.
- Frozen OOS and real-money execution remain locked.

## Continuity protocol

Canonical continuation files: `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, `SESSION_HANDOFF.md`, `docs/CONTINUITY_PROTOCOL.md`.

A new chat must read these files, query actual GitHub main/branch/open-PR/workflow state, compare any active branch to main, then continue the next valid task. Work remains sequential: one core architecture/research package at a time -> deterministic tests -> CI/log inspection -> fixes -> PR -> exact-head workflows -> merge -> exact production proof -> continuity update.
