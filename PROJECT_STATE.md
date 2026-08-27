# EBA Trader — Project State

_Last reconciled: 2026-08-27 20:09 (Asia/Ulaanbaatar)_
_Current implementation frontier: M5 stacked/diagonal imbalance implementation and exact Linode fixed-window proof are complete; next candidate family is absorption/exhaustion._

This is the primary cross-chat continuation summary. Actual GitHub code, PR/workflow state and production proof override stale prose. A continuity-only merge may advance `main` beyond the functional proof SHA recorded below; a new session must query actual GitHub state first.

## Current goal

Operate EBA Trader as a restart-safe 24/7 Linode paper/research system; build a controlled AI Strategy Factory on the M4 evidence platform; discover strategies through deterministic historical simulation/backtest, screening, robustness and later forward/demo validation; maintain a verified strategy knowledge base; and keep real-money execution locked until the full evidence/lifecycle chain permits it.

## Current stage

- Production/runtime foundation: **VERIFIED**.
- M4 research/evidence platform: **COMPLETE**.
- M5 AI Strategy Factory/order-flow research: **IN PROGRESS**.
- First real candle-control vs Delta/CVD development ablation: **COMPLETE AND INTERPRETED**.
- Stacked/diagonal imbalance candidate: **IMPLEMENTED, MERGED, FIXED-WINDOW PRODUCTION-PROVEN AND INTERPRETED — NO EDGE/PROMOTION CLAIM**.
- Next candidate family: **ABSORPTION / EXHAUSTION**.
- Continuity system: **INSTALLED / ENFORCED**.
- Frozen OOS: **LOCKED**.
- Real-money execution: **LOCKED**.

## Source of truth and active infrastructure

- Repository: `enkhbat194/EBA-Trader`
- Default/base branch: `main`
- Functional M5 stacked-proof main SHA: `738ed32e557045abb6b738c7f5236962ee3dd516`
- Stacked feature implementation merge predecessor: `d15c29895d39ae6db5fabea4895daf7ad5facfa6` (PR #56)
- Stacked fixed-window production-proof merge: `738ed32e557045abb6b738c7f5236962ee3dd516` (PR #57)
- Active implementation branch after this candidate package: **none; next branch should be created from actual latest `main` for absorption/exhaustion**.
- Active runtime target: Linode Nanode, Ubuntu 24.04 LTS
- Server repository path: `/opt/Eba-Trader`
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

Exact main `738ed32e557045abb6b738c7f5236962ee3dd516` passed:

- Linode production bundle;
- Linode runtime checks;
- public production smoke;
- exact-build external Linode production proof;
- encrypted saved Binance Demo reconnect;
- Chart and Positions checks;
- Fast restart proof;
- terminal/evidence-complete stacked M5 development report;
- stacked thresholds exactly `1/2/3` from the stacked-specific immutable report;
- Frozen OOS closed;
- real execution locked.

The stacked external proof completed successfully at `2026-08-27T12:08:54Z` (`20:08:54` Asia/Ulaanbaatar), run `33070015871`. The production report path is:

`/var/lib/eba-trader/research/evidence/m5-stacked-imbalance-ablation-20260801T000000Z-20260801T040000Z.json`

Fast Momentum remains the sole active production paper engine. Legacy carry has no active production entry authority. Real exchange execution remains disabled.

## Completed research milestones

### M4 — complete

PRs #20-#24 established immutable strategy versions, deterministic experiment IDs, restart-safe queue/leases, allowlisted workers, content-addressed evidence, development screening and bounded robustness contracts.

### M5 — foundation + Delta/CVD + stacked/diagonal evidence

Completed work includes executed-trade footprint/order-flow foundation, constrained strategy DSL/factory, family templates/screening, verified USD-M acquisition and causal alignment, same-dataset candle/order-flow adapters, deterministic ablation orchestration, persistent research runtime, immutable comparison reports, official Binance USD-M historical archive acquisition with SHA-256 checksum verification, exact production proof and sanitized production M5 metric reporting.

PR #56 completed deterministic diagonal/stacked imbalance implementation, including true-price-bucket adjacency, zero-volume protection, causal feature-dataset v2 materialization, legacy v1 replay compatibility, allowlisted `of_stacked_imbalance`, fail-closed stacked-gate consumption and bounded thresholds `1/2/3`.

PR #57 moved the Linode one-shot fixed-window development proof to the stacked gate set while preserving the prior Delta/CVD report, and hardened external proof so stale Delta-only evidence cannot satisfy the stacked milestone.

The fixed development window remains `2026-08-01T00:00:00Z -> 2026-08-01T04:00:00Z`. It was not shifted.

## First real M5 Delta/CVD development evidence

Batch: `abl_6c4a8eeb83a662894a3f2816`.

Candle-only control:

- total return ~`-0.42445%`
- final equity `9957.5551`
- 4 trades
- 25% win rate
- max drawdown ~`-0.42445%`
- expectancy `-10.6112`
- total cost `43.9048`

Best tested Delta arm (`delta_ratio_threshold=0.2`):

- total return ~`-0.12055%`
- final equity `9987.9446`
- 2 trades
- 50% win rate
- max drawdown ~`-0.26586%`
- expectancy `-6.0277`
- total cost `21.9992`

Interpretation: Delta reduced absolute loss about 71.6% versus baseline on this small development sample, but return and expectancy remained negative. CVD-only did not add incremental improvement. Development evidence only; no edge or promotion authority.

## Stacked / diagonal imbalance fixed-window evidence

Batch: `abl_232b7cb262de90363283356d`.

Workflow dataset ID: `m5ds_ca555c0ee588e17847d4c477`.

The candle-only baseline reproduced the prior control exactly, confirming same-dataset/execution comparability:

- total return `-0.004244488397751933` (~`-0.42445%`)
- final equity `9957.55511602248`
- trade count `4`
- win rate `0.25`
- max drawdown `-0.004244488397751933`
- expectancy `-10.611220994379892`
- total cost `43.90484437829747`

Best stacked treatment was threshold `1`:

- total return `-0.0012408244799629875` (~`-0.12408%`)
- final equity `9987.59175520037`
- trade count `2`
- win rate `0.5`
- max drawdown `-0.0024163539692870772` (~`-0.24164%`)
- expectancy `-6.204122399814878`
- total cost `21.98249146741619`
- absolute baseline loss reduction ~`70.77%`

Thresholds `2` and `3` produced the same result in this window:

- total return `-0.0013709100484625703` (~`-0.13709%`)
- final equity `9986.290899515374`
- trade count `1`
- win rate `0.0`
- max drawdown `-0.0013709100484625703`
- expectancy `-13.709100484626106`
- total cost `10.994657857876607`

### Interpretation

Stacked threshold `1` materially improved the candle-only baseline, but it **did not beat the prior Delta `0.2` treatment on return or expectancy**. Its absolute loss was about 2.93% larger than the Delta treatment's absolute loss; expectancy was also slightly worse. It had slightly smaller drawdown and marginally lower cost, with the same two trades and 50% win rate. Thresholds `2/3` reduced exposure/cost but had zero wins and worse expectancy.

Therefore the stacked family is retained as useful development evidence and infrastructure, but **does not receive edge, survivor-promotion, Frozen-OOS, paper/demo or execution authority**. The next candidate family is absorption/exhaustion.

## Next exact tasks

1. Query actual GitHub `main`/PR/workflow state after the continuity-only merge.
2. Create one new branch for the absorption/exhaustion candidate family; do not reopen or duplicate completed stacked branches.
3. Define absorption/exhaustion strictly from causal executed-trade footprint data; do not infer resting LOB liquidity.
4. Add deterministic directionality, zero/low-volume, boundary, replay and no-future-leakage tests.
5. Extend feature materialization/registry/backtest adapter only through bounded allowlisted fields/gates.
6. Add a small controlled gate set while keeping baseline, EMA, capital, fees, slippage and fixed development window identical.
7. Run full regression + Ruff + shell/deployment/continuity checks; fix failures before PR.
8. Open PR, require exact-head green CI, merge, deploy exact main to Linode and obtain exact production proof.
9. Run the same fixed development comparison and interpret return, expectancy, drawdown, cost, trade count and win rate versus candle baseline, Delta and stacked evidence.
10. Only then proceed to price/delta divergence. Keep LOB reconstruction as a separate later sequence-sensitive data plane.

## Roadmap after M5 candidate expansion

Continue sequentially through robustness, verified knowledge-base persistence, forward paper, Binance Demo execution lab, Market Brain/regime selection, strategy/portfolio selection, outcome learning, then shadow/micro-live/full-live gates. No later phase may bypass lifecycle or deterministic risk.

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
- Development rankings/wins are not promotion evidence.
- Generic research workers cannot open frozen OOS or exchange execution.
- Frozen OOS and real-money execution remain locked.

## Validation status

- PR #56 implementation and PR #57 production-proof package passed exact-head required CI before merge.
- Exact functional main `738ed32e557045abb6b738c7f5236962ee3dd516` passed production bundle, runtime checks, public smoke and hardened external stacked proof.
- Stacked batch `abl_232b7cb262de90363283356d` is terminal, all experiments passed and evidence-complete.
- External proof confirms `developmentComparisonOnly=true`, `edgeClaimAllowed=false`, `promotionAuthority=false`, `frozenOosOpened=false`, and `liveExecutionAllowed=false`.
- New-chat continuation must verify actual GitHub state again before implementation because the continuity-only merge containing this reconciliation advances `main`.

## Continuity protocol

Canonical continuation files: `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, `SESSION_HANDOFF.md`, `docs/CONTINUITY_PROTOCOL.md`.

A new chat must first read these files, query actual GitHub main/branch/open-PR/workflow state, then continue the next valid task. Work remains sequential: one core architecture task/branch at a time -> deterministic tests -> CI/log inspection -> fixes -> PR -> exact-head workflows -> merge -> production proof -> continuity update.
