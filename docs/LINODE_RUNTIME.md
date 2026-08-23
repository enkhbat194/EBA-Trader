# EBA Trader — Linode 24/7 runtime

Status: active runtime target as of 2026-08-24.

## Canonical server

- Provider: Akamai/Linode
- Plan: Nanode 1 GB
- Region: Singapore 2
- OS: Ubuntu 24.04 LTS
- Repo: `/opt/Eba-Trader`
- Persistent state: `/var/lib/eba-trader`
- SQLite ledger: `/var/lib/eba-trader/eba_trader.db`
- Market-data service: `eba-binance-data.service`
- Runtime API service: `eba-runtime-api.service`
- Local API: `127.0.0.1:8765`

This Linode is the sole active backend/runtime target. Replit and Render.com are deprecated for EBA Trader backend/runtime work.

## What already works

- Binance public market data runs through NautilusTrader on Linode.
- Market-data service starts after boot and restarts after failure.
- Runtime API runs as a separate systemd service.
- SQLite-backed `TradeLedger` exists outside the Git working tree.
- Git updates do not remove the database.
- Runtime API exposes health, positions and events.

## Current limitation

The ledger exists, but the paper execution engine still needs complete persistence integration. A paper position is only restart-safe after every OPEN / UPDATE / CLOSE is written to SQLite and startup recovery reloads OPEN positions.

The API is deliberately bound to localhost until authenticated HTTPS is added.

Real Binance order submission is not enabled.

## Canonical scripts

First install:

```bash
cd /opt/Eba-Trader
bash scripts/install_linode_runtime.sh
```

Routine update:

```bash
cd /opt/Eba-Trader
bash scripts/update_linode_runtime.sh
```

The update script fast-forwards GitHub `main`, refreshes the Python environment, installs the canonical systemd units, restarts both runtime services and checks the local health endpoint.

## Verification

```bash
systemctl status eba-binance-data eba-runtime-api --no-pager
curl http://127.0.0.1:8765/health
```

Persistent data must remain under `/var/lib/eba-trader`; do not place the ledger inside `/opt/Eba-Trader`.

## PWA/dashboard migration

The old Render-backed PWA/dashboard is temporary only. Render is not the target backend anymore.

Migration order:

1. finish persistent paper OPEN / UPDATE / CLOSE integration;
2. implement startup recovery from SQLite;
3. expand history/trade-detail API;
4. add authenticated HTTPS reverse proxy on Linode;
5. locate/migrate the actual PWA frontend source and point it at Linode;
6. validate positions/history/chart-detail against server state;
7. retire the Render service after Linode-backed PWA is proven working.

Do not switch off the old client before the frontend source and Linode endpoint are confirmed, otherwise the UI can be lost even though the trading runtime continues running.

## Automatic deployment target

Manual Weblish updates are transitional. The target is GitHub `main` -> Linode automated deployment with:

- fast-forward-only source update,
- dependency refresh only when required,
- service restart,
- health check,
- failed-deploy detection/rollback,
- persistent database untouched.

## Next engineering order

1. Paper engine -> `TradeLedger` integration.
2. Restart recovery.
3. Completed-trade/history/detail API.
4. Authenticated HTTPS.
5. PWA migration off Render.
6. GitHub-to-Linode automatic deployment.
7. Fast Momentum LONG/SHORT paper validation.
8. Only then design separately gated real Binance execution.
