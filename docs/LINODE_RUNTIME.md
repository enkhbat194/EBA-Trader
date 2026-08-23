# EBA Trader — Linode 24/7 runtime

Status: persistent-runtime implementation started 2026-08-24.

## Current server

- Provider: Akamai/Linode
- Plan: Nanode 1 GB
- Region: Singapore 2
- OS: Ubuntu 24.04 LTS
- Repo path: `/opt/Eba-Trader`
- Persistent state path: `/var/lib/eba-trader`
- Public Binance market-data service: `eba-binance-data.service`

## What already works

- Starts Binance public market data automatically after boot.
- Restarts the market-data process automatically after a crash.
- Keeps the Binance/Nautilus data connection alive without keeping the browser or PWA open.
- Writes logs to systemd journal.
- Uses `live_public` market data by default, so no Binance API secret is required for the data-only service.

## Persistent runtime milestone

This branch adds restart-safe local state using SQLite at:

`/var/lib/eba-trader/eba_trader.db`

The ledger stores positions and append-only runtime events. It is outside the Git working tree, so `git pull`, deploys, and application upgrades do not delete it.

A lightweight local runtime API is also added:

- `GET /health`
- `GET /api/v1/positions`
- `GET /api/v1/positions?status=OPEN`
- `GET /api/v1/positions/<position_id>`
- `GET /api/v1/events?limit=100`

The API binds to `127.0.0.1:8765` by default. It is deliberately not exposed directly to the public internet. A later reverse-proxy/authentication step will connect the PWA safely.

## Services

- `eba-binance-data.service` — Binance market-data runtime
- `eba-runtime-api.service` — local persistent-state API

Both are enabled by `scripts/install_linode_runtime.sh` and refreshed by `scripts/update_linode_runtime.sh`.

## Important limitation

The persistent ledger now exists in code, but the paper execution engine still needs to write every OPEN / UPDATE / CLOSE event into it. Until that integration is complete, SQLite cannot recover paper positions that only existed in another process's RAM.

This service still does **not** submit Binance orders. A green market-data feed is not proof of safe order execution.

## Deployment

From `/opt/Eba-Trader` after the branch is merged to `main`:

```bash
bash scripts/update_linode_runtime.sh
```

The updater fast-forwards `main`, refreshes the Python environment, installs both systemd units, restarts both services, and verifies the local API health endpoint.

Check status:

```bash
systemctl status eba-binance-data eba-runtime-api --no-pager
```

Check local API:

```bash
curl http://127.0.0.1:8765/health
```

## Next strict order

1. Merge and deploy the persistent-runtime branch.
2. Verify `/health` and SQLite file creation on Linode.
3. Integrate the paper execution engine with `TradeLedger` for OPEN / UPDATE / CLOSE events.
4. Add recovery-on-start so open paper positions are restored after process/server restart.
5. Add authenticated HTTPS reverse proxy.
6. Point PWA positions/history/chart-detail screens at the Linode runtime API.
7. Only after paper execution is proven restart-safe, consider exchange order execution.
