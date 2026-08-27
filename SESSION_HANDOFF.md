# EBA Trader — Session Handoff

_Last handoff prepared: 2026-08-27 (Asia/Ulaanbaatar)_

## What was completed

- PR #41 lifecycle policy v2 merged at `32a39c57cb9c86bd2b956ea670fa3031229d0efc` with robustness-before-OOS and legacy migration safeguards.
- PR #42 external public smoke merged at `a1425c5eb0e839bed4645f4a31bd95512c8d1995`; exact deployed build passed Demo vault/autoconnect, Chart, Positions and Research checks.
- PR #43 production proof + passive Fast restart watcher merged at `4a46a0fbec7d20007bda9061572756841de190c6`. The watcher waits for a natural Fast paper OPEN, restarts `eba-web.service` once, requires the same position to recover and then waits for MARK/CLOSE. It never manufactures a trade.
- PR #44 legacy carry active-entry retirement merged at `0df5f4d9a7ce054b1a2b65002b9329ba0c8143aa`.
- Exact #44 production proof passed: production smoke, encrypted Demo reconnect, Chart, Positions, frozen OOS lock and real-execution lock.
- PR #45 candidate implements the first automatic real M5 development ablation:
  - BTCUSDT Binance USD-M, 1m;
  - fixed 2026-08-01 00:00Z -> 04:00Z development window;
  - existing verified candle/aggTrade feature builder and deterministic M4 ablation queue;
  - bounded systemd oneshot/timer with 40% CPU quota, 700 MB memory ceiling and 45-minute timeout;
  - idempotent retry/no-op marker under persistent research storage;
  - immutable candle-baseline vs Delta/CVD comparison report;
  - sanitized production-proof state;
  - `edgeClaimAllowed=false`, `promotionAuthority=false`, frozen OOS closed and live execution locked.
- PR #45 pre-continuity head passed full regression, Ruff, shell syntax, deployment contract, active Linode runtime and continuity checks.

## Current project state

- GitHub `main` is authoritative; Linode is the active runtime target.
- M4 is complete; M5 order-flow/Strategy Factory work is active.
- Fast Momentum is the sole active production paper engine and uses restart-safe SQLite state.
- Legacy carry remains compatibility/historical code only and cannot create new production entries by default.
- Binance Demo credentials are encrypted on Linode and have real no-paste application/service restart reconnect proof.
- Runtime `TradeLedger` and research DB/dataset/evidence storage remain separate.
- Real-money execution remains locked.
- Frozen OOS remains locked.

## Still pending / not proven

- Final reconciled PR #45 CI + merge + exact production deploy proof.
- Actual terminal result of the first automated real BTCUSDT M5 development dataset/batch. Do not claim Delta/CVD edge before the report exists and is inspected.
- Natural Fast Momentum `OPEN -> restart -> same-position recovery -> MARK -> CLOSE` production proof. The passive watcher is installed but its market-dependent proof may still be waiting for a qualifying OPEN.
- Stacked imbalance, absorption, exhaustion and price/delta divergence candidates come only after the first real executed-trade run is verified.
- LOB depth reconstruction remains a separate later sequence-sensitive data plane.
- Fresh-install provisioning of the new M5 autorun timer should be added later through a separately audited small change; the current Linode upgrade path already provisions it.

## Important decisions / constraints

- API secrets never go to Git, chat or browser persistent storage.
- Persistent research state lives outside `/opt/Eba-Trader`.
- Journald limits are a host-safety invariant.
- Research workers and ablation jobs have no exchange-order or frozen-OOS authority.
- Executed-trade order flow and resting LOB liquidity are separate domains.
- Spot and USD-M futures data are not silently mixed.
- Same-candle still-forming footprint data cannot enter a candle decision.
- Development wins/rankings are not promotion evidence.
- Deterministic risk retains veto authority.

## Next exact task

1. Re-run required CI on the final PR #45 continuity-updated head and squash-merge only if all gates stay green.
2. Verify the exact #45 merge on public production and confirm the M5 autorun timer is provisioned.
3. Observe the sanitized M5 marker until COMPLETE or a real failure; repair actual runtime/data problems if exposed.
4. Inspect immutable candle-only vs Delta/CVD evidence as development evidence only.
5. Observe the passive Fast restart watcher until a natural qualifying paper position completes the restart/recovery/MARK/CLOSE proof.
6. Then implement stacked imbalance, absorption/exhaustion and divergence research candidates; keep LOB separate.

## Notes for the next AI session

Read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, and this file before coding. Inspect actual PR/main/runtime state before relying on prose. Never request an API secret in chat; Binance Demo credential entry belongs in the PWA only.
