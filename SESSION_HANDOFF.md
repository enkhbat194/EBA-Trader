# EBA Trader — Session Handoff

_Last handoff prepared: 2026-08-27 (Asia/Ulaanbaatar)_

## What was completed

- PR #40 merged at `8876bc22b59f236e8df038440aaa6116c5d1afdf`.
- #40 codified production journald limits, persistent research DB/dataset/evidence paths, bounded research worker/timer, `eba-m5-real-ablation`, initial Delta/CVD gate set and the one-command real development runner.
- The production PWA now reports server build `8876bc2`, confirming #40 reached the active Linode runtime.
- The user entered a real Binance Demo key/secret through the PWA. The UI reports the credential is encrypted and saved securely on Linode; the saved secret is not returned to the browser.
- PR #41 implements lifecycle policy v2:
  - current path is `GENERATED -> BACKTESTED -> ROBUSTNESS_VERIFIED -> OOS_VERIFIED -> PAPER_CANDIDATE -> ...`;
  - legacy pre-OOS rows can migrate safely to v2;
  - legacy post-OOS rows stay policy v1/frozen and must enter `RETEST_REQUIRED` before v2 re-entry;
  - robustness fan-out requires v2 `BACKTESTED`;
  - a passed robustness verdict can promote only to `ROBUSTNESS_VERIFIED`, never directly to OOS;
  - migration tests cover legacy SQLite schema/state handling.
- PR #41 pre-continuity head passed full Python regression, Ruff, shell syntax, deployment contract, Linode runtime checks and continuity guard.

## Current project state

- GitHub `main` is authoritative; Linode is the sole active runtime target.
- M4 research foundation is complete; M5 Strategy Factory/order-flow research remains active.
- Runtime paper state stays in `/var/lib/eba-trader/eba_trader.db`.
- Research state stays under `/var/lib/eba-trader/research/` and remains separate from runtime `TradeLedger`.
- Fast Momentum remains paper-only.
- Binance Demo credential persistence has real production save proof; no-paste reconnect after a real restart is still unproven.
- Real-money execution remains locked.
- Frozen OOS remains locked until a strategy passes lifecycle-v2 robustness evidence.

## Still pending / not proven

- Final continuity-updated PR #41 CI and squash merge.
- Direct server-internal proof that the #40 journald drop-in, persistent research paths and `eba-research-worker.timer` are active.
- Standalone Chart / Positions / Research production smoke.
- Demo no-paste reconnect after a real app/server restart.
- Active Fast Momentum `OPEN -> restart recovery -> MARK/CLOSE` production proof.
- Older carry paper engine audit and explicit persist-or-retire decision.
- Real BTCUSDT USD-M development dataset and candle-only vs Delta/CVD evidence run.
- Stacked imbalance, absorption, exhaustion and price/delta-divergence candidate features.
- LOB depth reconstruction remains a separate future sequence-sensitive data plane.

## Important decisions / constraints

- GitHub main + Linode is canonical; Replit/Render backend paths are deprecated.
- API secrets never go to Git, chat or browser persistent storage.
- Persistent research state lives outside `/opt/Eba-Trader` so research cannot dirty the auto-deploy checkout.
- Journald limits are a host-safety invariant.
- The research worker is bounded and research-only; it has no exchange/OOS authority.
- Order-flow executed trades and resting LOB liquidity are separate data domains.
- Spot and USD-M futures data must not be mixed inside a perpetual ablation.
- Same-candle still-forming footprint data cannot enter a candle decision.
- Development wins/ranking are not promotion evidence.
- Deterministic risk retains veto authority.

## Next exact task

1. Re-run required CI on the final #41 continuity-updated head and squash-merge if all gates remain green.
2. Verify #40 server-internal runtime contract on Linode.
3. Finish Chart / Positions / Research production smoke.
4. Verify Demo no-paste reconnect and Fast Momentum active-position restart recovery during a real restart window.
5. Audit the carry paper engine and choose persist/recover vs explicit retirement.
6. Run a real BTCUSDT USD-M development-only window through `scripts/run_m5_real_ablation.sh` outside frozen OOS.
7. Compare immutable candle-only vs Delta/CVD evidence under identical costs; do not open frozen OOS unless v2 robustness evidence passes.
8. Only after the real executed-trade pipeline is proven, add stacked imbalance/absorption/exhaustion candidates; LOB stays separate.

## Notes for the next AI session

Read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, and this file before coding. Inspect actual PR/main/runtime state before relying on prose. Never request an API secret in chat; Binance Demo credential entry belongs in the PWA only.
