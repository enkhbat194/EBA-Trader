# EBA Trader — Session Handoff

_Last handoff prepared: 2026-08-27 (Asia/Ulaanbaatar)_

## What was completed

- PR #35 merged at `178611f535e95d61747a726b73cf7346f94358e4`: venue-matched USD-M candle + order-flow feature-dataset workflow and `eba-build-orderflow-features` CLI.
- PR #36 merged at `06248eb9c901b44ca0a91ccd96bd15d23e156c9a`: one-time encrypted Binance Demo API credential persistence, masked status, auto-connect, Replace/Delete, no browser persistent secret storage. Release `0.12.2 / LINODE-M7`, PWA cache `eba-trader-ui-v15`.
- User screenshots prove persisted Fast Paper History and trade-detail/chart rendering from server truth.
- PR #37 merged at `9b265a4a880c380d66943e3964586be12ebfb9da`: fail-closed Linode auto-update recovery and persistent diagnostics.
- The one-time recovery was executed successfully on Linode: production advanced from build `050cd9b` to `da6f9123...`, `/api/app-info` reported `0.12.2 / LINODE-M7`, HTTPS ready, and `eba-auto-update.timer` active.
- Disk investigation on production found root filesystem usage near 90% because `/var/log` had grown to about 18 GB: `/var/log/syslog` about 15 GB plus journald about 2.5 GB.
- `tail /var/log/syslog` identified `eba-binance-data` flooding every Binance `QuoteTick`/`TradeTick` at INFO.
- Source root cause was confirmed in `src/eba_trader/binance_probe.py`: Nautilus `DataTesterConfig(log_data=True)`.
- PR #38 fixes the flood by disabling per-tick data logging while preserving subscriptions, adds a service-level systemd log burst cap, and adds regression tests. It is pending final CI/merge at this handoff.

## Current project state

- GitHub `main` is the code/continuity source of truth; Linode is the sole active runtime target.
- M4 research platform is complete; M5 AI Strategy Factory is in progress.
- Historical USD-M acquisition/repair, causal feature materialization, allowlisted adapters, deterministic ablation orchestration and real feature-dataset workflow are merged.
- Encrypted one-time Binance Demo credential persistence is merged; production no-paste credential persistence still needs verification.
- Auto-update recovery has been production-verified and the timer is active.
- Production log flood is the immediate operational blocker until PR #38 is merged/deployed and old logs are safely vacuumed/truncated.
- `m5-real-ablation-cli` remains the next research branch after the production log issue is closed.
- Real Binance order submission remains locked.
- Automated frozen OOS remains locked pending lifecycle-order reconciliation.

## Still pending production proof

- merge/deploy PR #38 and confirm `eba-binance-data` no longer emits raw ticks at INFO;
- reduce existing oversized syslog/journal storage and verify free disk space;
- verify one real encrypted Demo credential save followed by no-paste auto-connect;
- standalone Chart / Positions / Research smoke;
- one active Fast Momentum position surviving service/server restart and later MARK/CLOSE;
- persist/recover or explicitly retire the older carry paper engine.

## Next exact task

1. Finish CI and squash-merge PR #38.
2. Let Linode auto-update to the merged build, restart `eba-binance-data`, and confirm tick-log flooding is gone.
3. Safely reclaim `/var/log/syslog` and journal space, then verify disk usage.
4. Resume `m5-real-ablation-cli`: persistent research paths outside the Git checkout plus deterministic feature-manifest -> M4 ablation queue CLI.
5. Build a real BTCUSDT USD-M development dataset outside frozen OOS and run the controlled candle-only vs Delta/CVD ablation batch through M4 queue/worker/evidence/gates.

## Notes for the next AI session

Read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, and this file before coding. Actual code/Git overrides stale text. Never request that the user paste an API secret into chat; credential entry belongs in the PWA only.
