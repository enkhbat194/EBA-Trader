# EBA Trader — Session Handoff

_Last handoff prepared: 2026-08-27 (Asia/Ulaanbaatar)_

## What was completed

- PR #35 merged at `178611f535e95d61747a726b73cf7346f94358e4`: venue-matched USD-M candle + order-flow feature-dataset workflow and `eba-build-orderflow-features` CLI.
- PR #36 merged at `06248eb9c901b44ca0a91ccd96bd15d23e156c9a`: one-time encrypted Binance Demo API credential persistence, masked status, auto-connect, Replace/Delete, no browser persistent secret storage. Release `0.12.2 / LINODE-M7`, PWA cache `eba-trader-ui-v15`.
- User screenshots prove persisted Fast Paper History and trade-detail/chart rendering from server truth.
- New 2026-08-27 screenshots prove production Linode did **not** auto-deploy newer main: installed UI remained `0.11.0 / LINODE-M2`, server `0.12.0 / LINODE-M5`, build `050cd9b`, PWA cache `v12 / server v13`.
- `RELOAD LATEST VERSION` on that old UI only refreshes the PWA/service-worker layer; it cannot repair a server-side stalled Git/systemd deployment.
- PR #37 merged at `9b265a4a880c380d66943e3964586be12ebfb9da`: fail-closed Linode auto-update recovery and persistent diagnostics.
  - `scripts/repair_linode_auto_update.sh` downloads/runs the latest main deployment script once from the Linode console.
  - It refuses destructive recovery if `/opt/Eba-Trader` is dirty and writes `dirty-checkout.txt` instead.
  - `eba-auto-update.service` now runs through `scripts/auto_update_entrypoint.sh`.
  - Every timer attempt records `last_attempt_at`, `last_output.log`, and failure state under `/var/lib/eba-trader/deploy-state`.
  - Install path hardens timer activation with `enable --now` and resets failed service state.
  - Local isolated validation passed: shell syntax, wrapper failure/success persistence, dirty-checkout fail-closed behavior, and systemd unit syntax.
  - GitHub connector mutations generated no new Actions check-runs during this hotfix; this limitation was recorded on PR #37 rather than hidden.
- Recovery runbook: `docs/LINODE_AUTO_UPDATE_RECOVERY.md`.

## Current project state

- GitHub `main` is the code/continuity source of truth; Linode is the sole active runtime target.
- M4 research platform is complete; M5 AI Strategy Factory is in progress.
- Historical USD-M acquisition/repair, causal feature materialization, allowlisted adapters, deterministic ablation orchestration and real feature-dataset workflow are merged.
- Encrypted one-time Binance Demo credential persistence is merged but has **not yet been production-verified** because the Linode server is still on old build `050cd9b` until one-time recovery is executed.
- `m5-real-ablation-cli` branch was opened for the next research workflow; implementation is not complete/merged.
- Real Binance order submission remains locked.
- Automated frozen OOS remains locked pending lifecycle-order reconciliation.

## Immediate production action

The old updater is itself stuck, so it cannot fetch its own repair. One one-time bootstrap is required from Linode LISH/Cloud Manager console as root:

```bash
curl -fsSL https://raw.githubusercontent.com/enkhbat194/EBA-Trader/main/scripts/repair_linode_auto_update.sh | bash
```

Expected safe behavior:

- clean checkout -> latest main deploys, timer is re-enabled/restarted, current `/api/app-info` is printed;
- dirty checkout -> exit without reset/deletion and write `/var/lib/eba-trader/deploy-state/dirty-checkout.txt`.

After successful recovery, phone Settings should advance from build `050cd9b` to current main; then `CHECK FOR UPDATE` / PWA reload can update the installed UI/cache.

## Still pending production proof

- execute the one-time updater recovery and confirm latest main on Linode;
- verify one real encrypted Demo credential save followed by no-paste auto-connect;
- standalone Chart / Positions / Research smoke;
- one active Fast Momentum position surviving service/server restart and later MARK/CLOSE;
- persist/recover or explicitly retire the older carry paper engine.

## Next research task after production recovery

1. Continue `m5-real-ablation-cli`: persistent research paths outside the Git checkout plus deterministic feature-manifest -> M4 ablation queue CLI.
2. Build a real BTCUSDT USD-M development dataset outside frozen OOS.
3. Run the controlled candle-only vs delta/CVD ablation batch through M4 queue/worker/evidence/gates.
4. Compare/persist survivors for triage only; do not unlock frozen OOS or execution from ranking.

## Notes for the next AI session

Read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, and this file before coding. Actual code/Git overrides stale text. Never request that the user paste an API secret into chat; credential entry belongs in the PWA only.
