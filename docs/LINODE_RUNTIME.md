# Linode 24/7 runtime

This deployment turns the proven Binance **market-data probe** into a persistent Linux service on the owner's Linode Nanode.

## What this service does

- Starts automatically after boot.
- Restarts automatically after a crash.
- Keeps the Binance/Nautilus market-data connection alive without keeping the browser or PWA open.
- Writes logs to systemd journal.
- Uses `live_public` market data by default, so no Binance API secret is required for the data-only service.

## What this service does not do yet

- It does not submit Binance orders.
- It is not the PWA backend/API.
- It does not persist paper trades yet.
- It does not turn the current research strategy into live execution.

Those are separate gates and must not be implied by a green market-data feed.

## First install

From `/opt/Eba-Trader` on the Linode:

```bash
git checkout main
git pull --ff-only origin main
bash scripts/install_linode_runtime.sh
```

After installation, the Weblish/SSH terminal can be closed. The process runs under `systemd`.

Check status:

```bash
systemctl status eba-binance-data --no-pager
```

Follow live logs:

```bash
journalctl -u eba-binance-data -f
```

## Updating after a GitHub release

```bash
cd /opt/Eba-Trader
bash scripts/update_linode_runtime.sh
```

The updater fast-forwards `main`, refreshes the Python environment including the `trading` extra, and restarts the service.

## Environment

Runtime environment lives at:

`/etc/eba-trader/eba-trader.env`

Default:

```text
EBA_BINANCE_DATA_ENV=live_public
```

Binance Demo data requires `demo` plus demo API credentials in that root-readable env file. Do not commit secrets to GitHub.

## Persistence plan

The current data service is stateless. Before the PWA paper engine is moved from the temporary host, add a durable ledger under `/var/lib/eba-trader` (SQLite first; migration path to PostgreSQL later). Open positions, entries/exits, TP/SL, strategy metadata, and completed-trade history must survive service restarts and deploys.
