# EBA Trader — Session Handoff

_Last handoff prepared: 2026-08-27 (Asia/Ulaanbaatar)_

## What was completed

- M4 strategy-platform/evidence foundation remains complete and authoritative.
- Production recovery/logging work remains deployed, including bounded journald and disabled per-tick Binance INFO logging.
- Encrypted one-time Binance Demo credential persistence/reconnect remains production verified; secrets are never returned to browser JavaScript.
- Fast Momentum remains the sole active production paper engine; legacy carry cannot create new production entries.
- PR #51 **Use verified Binance archive for historical M5 order flow** merged at `1c1b683b7bfc9dd62cff9d96fcb3160213cd2595`.
  - Root cause repaired: the fixed `2026-08-01T00:00:00Z -> 04:00:00Z` M5 development window was too old for the Binance USD-M REST `aggTrades` path and returned HTTP 400.
  - The fixed window was preserved for reproducibility rather than shifted to recent data.
  - Historical USD-M order flow now comes from official Binance public daily `aggTrades` archives with `.CHECKSUM` SHA-256 verification.
  - Archive ZIPs are streamed to temporary storage and only the exact requested `[start,end)` window is retained for the research dataset.
  - Cross-midnight acquisition supports the prior closed-footprint minute required by causal alignment.
  - Actual archive provenance is preserved in immutable acquisition evidence; recent REST acquisition remains available for recent data.
  - Historical archive data fails closed on checksum mismatch, malformed archive/rows, gaps, or an empty requested window.
- PR #52 **Harden production proof for terminal M5 evidence** merged at `7e24df486839c92f9c324cbd910efc00dfe7bc4d`.
  - External production proof can no longer pass merely because the exact application build deployed while an old M5 FAILED/RUNNING marker remains.
  - It now waits for `phase=COMPLETE`, `safe=true`, `allTerminal=true`, `evidenceComplete=true`, frozen OOS closed, and live execution locked.
- Exact production build `7e24df486839c92f9c324cbd910efc00dfe7bc4d` passed the hardened external proof and public production smoke.
- The first real fixed-window BTCUSDT USD-M M5 development ablation completed successfully:
  - phase: `COMPLETE`
  - safe: `true`
  - all terminal: `true`
  - all experiments passed: `true`
  - evidence complete: `true`
  - batch: `abl_6c4a8eeb83a662894a3f2816`
  - report: `/var/lib/eba-trader/research/evidence/m5-real-ablation-20260801T000000Z-20260801T040000Z.json`
  - frozen OOS stayed locked and real execution stayed locked.
- Fast restart production proof is also reported `PASS` by the exact-build external proof.

## Current project state

- GitHub `main` is authoritative; Linode is the active runtime target.
- Current verified production build: `7e24df486839c92f9c324cbd910efc00dfe7bc4d`.
- M4 is complete.
- M5 Strategy Factory/order-flow foundation is active, and the first real candle-control vs Delta/CVD development batch has now completed with immutable evidence.
- This development result is **not** frozen-OOS proof, lifecycle promotion, or permission for real trading.
- Runtime `TradeLedger` and research DB/dataset/evidence storage remain separate.
- Real-money execution remains locked.
- Frozen OOS remains locked.

## Still pending / not proven

- Inspect the immutable per-treatment metrics from batch `abl_6c4a8eeb83a662894a3f2816` before making any claim that Delta/CVD adds incremental edge over the candle-only control.
- Add stacked/diagonal imbalance, absorption/exhaustion, and price/delta divergence candidates only after the first report is interpreted as development evidence.
- LOB depth reconstruction remains a separate later sequence-sensitive data plane.
- Fresh-install provisioning of the M5 autorun timer remains a separately audited small follow-up if not already covered by the fresh-install path.
- Do not open frozen OOS automatically and do not unlock real execution.

## Important decisions / constraints

- API secrets never go to Git, chat, logs, or browser persistent storage.
- Persistent research state lives outside `/opt/Eba-Trader`.
- Journald limits are a host-safety invariant.
- Research workers and ablation jobs have no exchange-order or frozen-OOS authority.
- Executed-trade order flow and resting LOB liquidity are separate domains.
- Spot and USD-M futures data are not silently mixed.
- Same-candle still-forming footprint data cannot enter a candle decision.
- Historical fixed-window research must remain reproducible; do not silently roll the window forward to work around provider retention limits.
- Historical archive integrity must be cryptographically verified and gaps fail closed.
- Development wins/rankings are not promotion evidence.
- Deterministic risk retains veto authority.

## Next exact task

1. Read the immutable report for batch `abl_6c4a8eeb83a662894a3f2816` and compare candle-only control vs Delta/CVD treatments using the recorded fees/slippage and screening metrics.
2. Record the interpretation explicitly as **development evidence only**; no frozen-OOS opening or lifecycle promotion.
3. If the first report is structurally sound, add stacked/diagonal footprint imbalance candidates with causal definitions and regression tests.
4. Then add absorption/exhaustion and price/delta divergence candidates, keeping cheap screening and M4 evidence gates deterministic.
5. Keep LOB reconstruction as a separate later data plane and keep real execution locked.

## Notes for the next AI session

Read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, and this file before coding. Inspect actual PR/main/runtime state before relying on prose. Never request an API secret in chat; Binance Demo credential entry belongs in the PWA only.
