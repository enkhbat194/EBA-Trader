# Current runtime state — 2026-08-24

## Verified manually on Linode

- Linode Nanode 1 GB created in Singapore 2.
- Ubuntu 24.04 LTS running.
- Firewall attached with inbound SSH/HTTP/HTTPS and default inbound Drop; outbound Accept.
- Repository cloned to `/opt/Eba-Trader`.
- Python 3.12 and Git available.
- Virtual environment created.
- EBA Trader installed.
- Initial `eba-binance-data` failure was caused by installing the base package without the optional `trading` extra, so `nautilus_trader` was absent.
- After installing the trading dependency, live Binance `QuoteTick` output was visibly streaming on the Linode console.

## Current interpretation

The screenshot proves the Linode can maintain the NautilusTrader/Binance **market-data** connection. It does not by itself prove order execution, PWA backend migration, persistent paper trading, or production readiness.

## Work added in branch `linode-runtime`

- systemd unit: `deploy/systemd/eba-binance-data.service`
- first-install script: `scripts/install_linode_runtime.sh`
- update script: `scripts/update_linode_runtime.sh`
- runtime documentation: `docs/LINODE_RUNTIME.md`

These make the data process independent of the browser terminal and automatically restart it after reboot/crash.

## Next engineering tasks

1. Merge `linode-runtime` after review.
2. Install/enable the systemd unit on Linode.
3. Add persistent trade ledger (SQLite on this single-node VPS first).
4. Identify and migrate the actual PWA paper-scanner/backend code to Linode; the current research repo contains the data/research engine but no confirmed HTTP/PWA backend entrypoint.
5. Add health endpoint + server status visible in PWA Settings.
6. Add GitHub-to-Linode deploy automation only after the runtime service is stable.
7. Keep real-money execution locked until the execution path is separately validated.
