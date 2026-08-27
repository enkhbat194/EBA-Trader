# EBA Trader — Project State

_Last reconciled: 2026-08-27 17:57 (Asia/Ulaanbaatar)_
_Current implementation frontier: M5 real Delta/CVD evidence interpreted; stacked/diagonal imbalance implementation is in progress on an unmerged feature branch._

This is the primary cross-chat continuation summary. Actual GitHub code, PR/workflow state and production proof override stale prose.

## Current goal

Operate EBA Trader as a restart-safe 24/7 Linode paper/research system; build a controlled AI Strategy Factory on the M4 evidence platform; discover strategies through deterministic historical simulation/backtest, screening, robustness and later forward/demo validation; maintain a verified strategy knowledge base; and keep real-money execution locked until the full evidence/lifecycle chain permits it.

## Current stage

- Production/runtime foundation: **VERIFIED on exact main `93e684794cd692bf1534ec46a5c9186bb974bbb9`**.
- M4 research/evidence platform: **COMPLETE**.
- M5 AI Strategy Factory/order-flow research: **IN PROGRESS**.
- First real candle-control vs Delta/CVD development ablation: **COMPLETE AND INTERPRETED**.
- Next candidate family: **STACKED/DIAGONAL IMBALANCE — IMPLEMENTATION IN PROGRESS**.
- Continuity system: **INSTALLED / ENFORCED**.
- Frozen OOS: **LOCKED**.
- Real-money execution: **LOCKED**.

## Source of truth and active infrastructure

- Repository: `enkhbat194/EBA-Trader`
- Default/base branch: `main`
- Exact `main` SHA at this reconciliation: `93e684794cd692bf1534ec46a5c9186bb974bbb9`
- Verified production build: `93e684794cd692bf1534ec46a5c9186bb974bbb9`
- Active unmerged research branch: `m5-stacked-imbalance-feature`
- Active branch head: `ec015d6b54e72d8906cd1e80d299f4d2ed213de1`
- Branch relation at reconciliation: 3 commits ahead of main, 0 behind; no open PR yet.
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

The exact `93e684794cd...` build passed public/external proof for HTTPS PWA, exact-main deployment, encrypted saved Binance Demo reconnect, Chart, Positions, Research safety locks, terminal M5 evidence and Fast restart proof. The user-visible PWA at 2026-08-27 17:53 Asia/Ulaanbaatar also showed server build `93e6847`, runtime LINODE, HTTPS READY, scanner ACTIVE and matching client/server `eba-trader-ui-v15` cache.

Fast Momentum remains the sole active production paper engine. Legacy carry has no active production entry authority. Real exchange execution remains disabled.

## Completed research milestones

### M4 — complete

PRs #20-#24 established immutable strategy versions, deterministic experiment IDs, restart-safe queue/leases, allowlisted workers, content-addressed evidence, development screening and bounded robustness contracts.

### M5 — foundation + first real research loop

Completed work includes executed-trade footprint/order-flow foundation, constrained strategy DSL/factory, family templates/screening, verified USD-M acquisition and causal alignment, same-dataset candle/order-flow adapters, deterministic ablation orchestration, persistent research runtime, immutable comparison reports, official Binance USD-M historical archive acquisition with SHA-256 checksum verification, exact production proof and sanitized production M5 metric reporting.

The fixed first real development window remains `2026-08-01T00:00:00Z -> 2026-08-01T04:00:00Z`. It is intentionally not shifted to work around provider retention.

## First real M5 development evidence

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

Interpretation: the Delta filter reduced absolute loss by about 71.6% and reduced cost/drawdown on this small development sample, but return and expectancy remained negative. CVD-only showed no incremental improvement here. This is useful development evidence, **not** proof of edge or promotion authority.

## Active implementation frontier

Branch `m5-stacked-imbalance-feature` at `ec015d6b54e72d8906cd1e80d299f4d2ed213de1` currently modifies only:

- `src/eba_trader/orderflow.py`
- `src/eba_trader/footprint_dataset.py`
- `src/eba_trader/orderflow_feature_dataset.py`

The branch has started deterministic diagonal imbalance, consecutive stacked imbalance and causal feature materialization. It has no completed test/CI/PR/merge proof yet and must not be treated as complete.

## Next exact tasks

1. Resume `m5-stacked-imbalance-feature` if it remains the valid unmerged branch; do not duplicate it.
2. Inspect the three-file diff against current main.
3. Add complete deterministic unit/regression tests for diagonal/stacked imbalance and causal availability.
4. Finish allowlisted feature registry, feature-dataset and backtest adapter/gate integration.
5. Run full regression, Ruff, shell/deployment/continuity gates.
6. Open PR, require exact-PR-head green workflows, then merge.
7. Deploy exact main to Linode and rerun the same fixed development comparison.
8. Compare stacked treatment vs candle baseline and prior Delta evidence using return, expectancy, drawdown, costs, trade count and win rate.
9. Then implement absorption/exhaustion, followed by price/delta divergence.
10. Keep LOB/order-book reconstruction as a separate later sequence-sensitive data plane.

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

- Exact production build `93e684794cd692bf1534ec46a5c9186bb974bbb9` has passed the external public proof chain described above.
- First real M5 batch is terminal and evidence-complete, but its metrics are development-only.
- Active stacked-imbalance branch `ec015d6b...` has not yet passed regression/CI/PR review and is not validated for merge or production.
- New-chat continuation must verify actual GitHub state again before implementation.

## Continuity protocol

Canonical continuation files: `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, `SESSION_HANDOFF.md`, `docs/CONTINUITY_PROTOCOL.md`.

A new chat must first read these files, query actual GitHub main/branch/open-PR/workflow state, compare the active branch against main, then continue the existing task. Work remains sequential: one core architecture task/branch at a time -> deterministic tests -> CI/log inspection -> fixes -> PR -> exact-head workflows -> merge -> production proof -> continuity update.
