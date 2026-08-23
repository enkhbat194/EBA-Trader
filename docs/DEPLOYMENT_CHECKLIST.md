# EBA Trader — Linode production checklist

This checklist is for the one-time transition from manual Weblish updates to the canonical GitHub-main -> Linode runtime.

## One-time server activation

1. Pull the main commit that contains this bundle.
2. Run `bash scripts/install_linode_runtime.sh` once as root.
3. Confirm `eba-binance-data`, `eba-runtime-api`, `eba-web` and `eba-auto-update.timer` are active.
4. Confirm local health endpoints return success.
5. Configure the public hostname with `bash scripts/configure_linode_https.sh <host> <email>`.
6. Open the HTTPS PWA from the phone and verify Dashboard / Positions / History / Settings.
7. Confirm a paper position/history survives a web-service restart.
8. Only after the Linode HTTPS PWA is proven working, retire the old Render deployment.

## Normal operation after activation

- Commit/merge changes into GitHub `main`.
- Linode checks `main` automatically every five minutes.
- A healthy deployment becomes the new runtime automatically.
- A failed deployment is rolled back to the previous server commit automatically.
- SQLite trade state is outside the Git checkout and is not removed by deployments.

## Never do

- Do not expose ports 8000 or 8765 publicly.
- Do not store Binance secrets in Git.
- Do not delete `/var/lib/eba-trader/eba_trader.db` during deployment.
- Do not make manual source edits inside `/opt/Eba-Trader`; automatic deployment deliberately stops if the checkout is dirty.
- Do not reactivate Render/Replit as competing backend runtimes.
