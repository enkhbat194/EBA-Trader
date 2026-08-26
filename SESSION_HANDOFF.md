# EBA Trader — Session Handoff

_Last handoff prepared: 2026-08-27 (Asia/Ulaanbaatar)_

## What was completed

- M4 research foundation remains complete; M5 Strategy Factory/order-flow work remains the active milestone.
- PRs #35-#39 are already in `main`: verified USD-M feature workflow, encrypted Demo credential vault, fail-closed Linode auto-update recovery, Binance raw-tick log-flood fix, and continuity reconciliation.
- Production log incident is resolved: old logs were reclaimed, root disk fell from ~90.1% used to ~21%, and raw `QuoteTick`/`TradeTick` INFO flooding stopped after #38.
- PR #40 implements the next M5 runtime package on branch `m5-real-ablation-cli`:
  - versioned journald policy `SystemMaxUse=250M`, `SystemKeepFree=1G`, `MaxRetentionSec=7day` installed by both Linode install/update paths;
  - persistent research control plane under `/var/lib/eba-trader/research/` with separate DB, dataset and immutable-evidence paths;
  - idempotent upgrade of existing `/etc/eba-trader/eba-trader.env` without overwriting explicit operator values;
  - bounded `eba-research-worker.service` + minute-scale timer (8 jobs/run, CPU/memory bounds, write access limited to research state);
  - `eba-m5-real-ablation` CLI that verifies PR #35 workflow/feature integrity, USD-M venue, dataset containment and frozen-OOS separation before deterministic PR #34 experiment emission;
  - versioned initial Delta/CVD gate set;
  - `scripts/run_m5_real_ablation.sh`, a root-side one-command real development build -> queue -> worker/evidence runner.
- PR #40 tests cover journald provisioning, persistent research paths, worker bounds, env reconciliation, deterministic/idempotent queue emission, tampered feature CSV rejection, wrong-venue rejection and path traversal rejection.
- PR #40 pre-continuity validation: full Python regression PASS, Ruff PASS after import-format correction, shell syntax PASS, deployment contract PASS, Linode runtime checks PASS and continuity guard PASS. Final continuity-updated head must pass the same CI set before merge.

## Current project state

- GitHub `main` is authoritative; Linode is the sole active runtime target.
- Runtime paper state stays in `/var/lib/eba-trader/eba_trader.db`; research experiments/evidence use a separate persistent namespace.
- Fast Momentum remains paper-only.
- Binance Demo credential persistence is implemented, but the real one-time save/no-paste reconnect has not yet been production-proven.
- PR #40 does not submit exchange orders and cannot open frozen OOS.
- Real-money execution remains locked.
- Automated frozen OOS remains locked because lifecycle ordering still places `OOS_VERIFIED` before `ROBUSTNESS_VERIFIED`.

## What currently works in code

- Public HTTPS PWA/server runtime and restart-safe Fast Paper ledger.
- Venue-specific Binance USD-M candle + aggregate-trade acquisition and gap repair.
- Causal footprint feature datasets with immutable provenance.
- Same-dataset candle-only and Delta/CVD order-flow adapters.
- Deterministic M5 ablation batches into the restart-safe M4 queue.
- Persistent research worker/evidence runtime package in PR #40.
- Fail-closed real-ablation workflow verification and first-cycle frozen-OOS guard in PR #40.

## Still pending / not proven

- PR #40 must be squash-merged only after its final continuity-updated CI is green.
- Linode must then auto-deploy the merged PR #40; production must confirm journald policy, `/var/lib/eba-trader/research/...`, and `eba-research-worker.timer` are installed/active.
- A real BTCUSDT USD-M development window outside frozen OOS has not yet been built/run through the new one-command path.
- Therefore no empirical claim is yet made that Delta/CVD improves the candle-only baseline.
- Standalone Chart / Positions / Research production smoke remains open.
- The user must enter a real Binance Demo key/secret once in the PWA; the secret must never be pasted into chat. After that, no-paste reconnect needs verification.
- Active Fast Momentum `OPEN -> restart recovery -> MARK/CLOSE` production proof remains open.
- Older carry paper engine disposition remains open and requires code/runtime audit before persistence or retirement.
- Lifecycle ordering must be deliberately redesigned/migrated/tested before automated frozen OOS.
- Stacked imbalance, absorption, exhaustion and LOB features are not yet approved as implemented edge features.

## Important decisions / constraints

- GitHub main + Linode is canonical; Replit/Render backend paths are deprecated.
- Persistent research state lives outside `/opt/Eba-Trader` so research cannot dirty the auto-deploy checkout.
- Journald resource limits are a host-safety invariant and are not rolled back with application code.
- The research worker is bounded and research-only; it has no exchange/OOS/lifecycle-promotion authority.
- Order-flow executed trades and resting LOB liquidity are separate data domains.
- Spot and USD-M futures data must not be mixed inside a real perpetual ablation.
- Same-candle still-forming footprint data cannot enter a candle decision.
- Development wins/ranking are not promotion evidence.
- Deterministic risk retains veto authority.

## Validation / evidence status

- #37 auto-update repair and #38 log-flood correction are production-verified.
- #39 continuity reconciliation is in main.
- PR #40 functional regression passed before the final continuity update; final CI must be green before merge.
- Real M5 market-data acquisition/ablation execution on production has not yet occurred.

## Next exact task

1. Finish PR #40 final CI and squash-merge only if every gate is green.
2. Confirm Linode auto-deployed #40 and verify journald limits, persistent research paths and research-worker timer.
3. Run `scripts/run_m5_real_ablation.sh` on an explicit BTCUSDT USD-M development-only window outside frozen OOS.
4. Inspect the immutable M4 evidence for the candle-only control and each Delta/CVD treatment; verify the permissive treatment reproduces the control invariant.
5. Add a deterministic comparison/verdict artifact if the real run is sound; do not open frozen OOS.
6. Separately redesign lifecycle ordering with migration/tests so robustness precedes frozen OOS.
7. Continue production proofs (Chart/Positions/Research, Demo no-paste reconnect, Fast Momentum active-position restart recovery) and audit carry engine disposition.
8. Only after real raw-trade integrity/ablation evidence exists, implement stacked imbalance/absorption/exhaustion candidates; treat LOB as a separate future dataset.

## Notes for the next AI session

Read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, and this file before coding. Inspect PR #40/main status and actual code/tests before relying on prose. Never request that the user paste an API secret into chat; Binance Demo credential entry belongs in the PWA only.
