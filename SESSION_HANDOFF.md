# EBA Trader — Session Handoff

_Last handoff prepared: 2026-08-27 (Asia/Ulaanbaatar)_

## What was completed

- PR #35 merged at `178611f535e95d61747a726b73cf7346f94358e4`: venue-matched USD-M candle + order-flow feature-dataset workflow and `eba-build-orderflow-features` CLI.
- PR #36 merged at `06248eb9c901b44ca0a91ccd96bd15d23e156c9a`: one-time encrypted Binance Demo API credential persistence, masked status, auto-connect, Replace/Delete, no browser persistent secret storage. Release `0.12.2 / LINODE-M7`, PWA cache `eba-trader-ui-v15`.
- User screenshots prove persisted Fast Paper History and trade-detail/chart rendering from server truth.
- PR #37 merged at `9b265a4a880c380d66943e3964586be12ebfb9da`: fail-closed Linode auto-update recovery and persistent diagnostics.
- The recovery helper was executed successfully on Linode; production advanced from stuck build `050cd9b` to current main and `eba-auto-update.timer` returned to active/waiting.
- Production disk investigation found `/var/log` near 18 GB: `/var/log/syslog` about 15 GB plus journald about 2.5 GB.
- Root cause was `eba-binance-data` / Nautilus `DataTesterConfig(log_data=True)`, which emitted every Binance `QuoteTick`/`TradeTick` at INFO.
- PR #38 merged at `2ef162bf975b8a1ace1adb86af269976d3c7c578`: per-tick data logging disabled while quote/trade/bar subscriptions remain active, service log burst cap added, regression coverage added.
- PR #38 was deployed and production-verified: `eba-binance-data.service` is active and `journalctl` after the deployment window showed no per-tick raw-tick flood.
- Old logs were reclaimed manually. Production disk fell from about 90.1% used to 21% (`4.8G` used / `19G` available); `/var/log` fell to about `162M`.
- A production-local journald drop-in was applied manually: `SystemMaxUse=250M`, `SystemKeepFree=1G`, `MaxRetentionSec=7day`.
- The stale `m5-real-ablation-cli` branch had no unique implementation commits and was safely fast-forwarded to current main before continuation.

## Current project state

- GitHub `main` is the code/continuity source of truth; Linode is the sole active runtime target.
- M4 research platform is complete; M5 AI Strategy Factory is in progress.
- Historical USD-M acquisition/repair, causal feature materialization, allowlisted adapters, deterministic ablation orchestration and real feature-dataset workflow are merged.
- Encrypted one-time Binance Demo credential persistence is merged; production no-paste save/reconnect still needs real verification.
- Auto-update recovery is production-verified and timer diagnostics persist under `/var/lib/eba-trader/deploy-state`.
- Binance market-data log flood is fixed and production-verified; old logs are cleaned.
- The manual journald retention cap is not yet repo-provisioned, so a rebuild/new server would not inherit it automatically.
- `m5-real-ablation-cli` is the next research implementation track after codifying the log-retention guard.
- Real Binance order submission remains locked.
- Automated frozen OOS remains locked pending lifecycle-order reconciliation.

## What currently works

- Public HTTPS PWA from iPhone.
- Home / Scan / Settings server-backed state.
- Fast Momentum server scanner and paper-only LONG/SHORT flow.
- Persistent Fast Paper History and trade detail/chart.
- Auto-update recovery + timer health.
- Active Binance market-data probe without per-tick INFO flooding.
- Encrypted Demo credential vault code path is deployed.
- M4 research queue/evidence/gates and M5 order-flow dataset/orchestrator foundation are in main.

## Still pending / not proven

- repo-provision the journald/free-space limits currently applied manually on production;
- verify one real encrypted Demo credential save followed by no-paste auto-connect after app/server restart;
- standalone Chart / Positions / Research smoke against server truth;
- one active Fast Momentum position surviving service/server restart and later MARK/CLOSE;
- persist/recover or explicitly retire the older carry paper engine;
- long-running Linode research storage path outside Git checkout;
- real BTCUSDT USD-M development dataset and controlled candle-only vs Delta/CVD empirical run;
- lifecycle-order redesign before any automated frozen OOS opening.

## Important decisions / constraints

- GitHub main + Linode is canonical; Replit/Render backend paths are deprecated.
- Real-money execution is locked.
- Frozen OOS is locked until lifecycle ordering is deliberately reconciled.
- Runtime `TradeLedger` and research persistence remain separate.
- API secrets never go to Git/browser persistent storage/chat; only Binance Demo uses the current encrypted vault.
- High-frequency raw market ticks are data, not normal INFO diagnostic logs.
- Research data/evidence for long-running Linode work must live outside the Git checkout.
- Spot and USD-M futures data must not be silently mixed.
- Same-candle still-forming footprint data must not leak into candle decisions.

## Validation / evidence status

- PR #37 merged; recovery helper exercised successfully on real Linode.
- PR #38 merged; data service remains active and post-deploy raw-tick flood is absent.
- Manual cleanup reclaimed old log growth and verified healthy free space.
- Public HTTPS/latest-main proof is established.
- Restart-recovery of an active Fast position is still not established.

## Next exact task

1. Add the journald retention/free-space drop-in to repository install/update provisioning and test the deployment contract; do not rely on production-local manual state.
2. Resume `m5-real-ablation-cli` from latest main.
3. Move Linode research DB/data/evidence to persistent paths under `/var/lib/eba-trader/research/...` while keeping runtime `TradeLedger` separate.
4. Implement the deterministic verified feature-manifest/`dataset_ref` -> #34 ablation batch -> M4 queue CLI with machine-readable batch/experiment IDs.
5. Build a real BTCUSDT USD-M development dataset outside frozen OOS.
6. Run candle-only vs Delta/CVD development ablations through M4 queue/worker/evidence/gates and compare survivors under identical cost assumptions.
7. In parallel, verify Demo credential no-paste reconnect and remaining Chart/Positions/Research + active-position restart-recovery production proof.

## Notes for the next AI session

Read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, and this file before coding. Then inspect recent Git history and current branch/PR state; actual code/Git overrides stale prose. Never request that the user paste an API secret into chat; credential entry belongs in the PWA only.
