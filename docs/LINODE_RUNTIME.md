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
- PWA/web service: `eba-web.service`
- Auto-deploy timer: `eba-auto-update.timer`
- Local runtime API: `127.0.0.1:8765`
- Local web/PWA: `127.0.0.1:8000`

This Linode is the sole active backend/runtime target. Replit and Render.com are deprecated for EBA Trader backend/runtime work.

## Current runtime layout

`eba-binance-data.service` keeps Binance market data alive, `eba-runtime-api.service` serves persistent runtime state, and `eba-web.service` serves the PWA/dashboard and paper scanner. All three are systemd-managed and restart after failure. The browser is not the source of truth: persistent state stays in SQLite under `/var/lib/eba-trader`.

Fast Momentum paper state is stored through the persistent momentum layer so OPEN/MARK/CLOSE records and restart recovery are not dependent on browser RAM.

Real Binance order submission remains disabled.

## First install

```bash
cd /opt/Eba-Trader
bash scripts/install_linode_runtime.sh
```

The installer creates/updates the Python environment, installs all systemd units, starts the three runtime services, and enables the automatic deployment timer.

## Automatic GitHub main deployment

Routine Weblish commands are no longer the intended update path. `eba-auto-update.timer` checks GitHub `main` every five minutes.

When a new main commit appears, `scripts/update_linode_runtime.sh --auto`:

1. refuses to overwrite local uncommitted server edits;
2. records the previous and target commit SHAs under `/var/lib/eba-trader/deploy-state`;
3. updates the checkout to the exact `origin/main` commit;
4. refreshes Python dependencies and systemd units;
5. restarts market-data, runtime API and web services;
6. requires all services and both local health endpoints to pass;
7. automatically rolls back to the previous commit if deployment or health verification fails;
8. never replaces or deletes the SQLite ledger.

Manual forced check remains available:

```bash
cd /opt/Eba-Trader
bash scripts/update_linode_runtime.sh
```

Useful status commands:

```bash
systemctl status eba-binance-data eba-runtime-api eba-web eba-auto-update.timer --no-pager
journalctl -u eba-auto-update.service --no-pager -n 100
curl http://127.0.0.1:8765/health
curl http://127.0.0.1:8000/api/health
```

## HTTPS / public PWA

The application itself intentionally remains bound to loopback. Public access should go through Nginx HTTPS, not by opening port 8000.

Before running the HTTPS script, point a hostname's DNS A/AAAA record at the Linode and ensure firewall inbound TCP 80 and 443 are allowed. Then run once:

```bash
cd /opt/Eba-Trader
bash scripts/configure_linode_https.sh trader.example.com owner@example.com
```

The script installs Nginx + Certbot, reverse-proxies the hostname to `127.0.0.1:8000`, obtains a TLS certificate, and redirects HTTP to HTTPS. Certbot's system integration handles certificate renewal.

Do not expose `8765` or `8000` directly to the internet.

## Persistent data rule

Persistent data must remain under `/var/lib/eba-trader`; never place the ledger inside `/opt/Eba-Trader`. Git checkout/reset operations are therefore isolated from trade history and deployment state.

## Deployment/state troubleshooting

Successful deployment state is written to:

- `/var/lib/eba-trader/deploy-state/current_sha`
- `/var/lib/eba-trader/deploy-state/succeeded_at`

A failed deployment records `failed_at` and `rolled_back_to`. Check `journalctl -u eba-auto-update.service` for the actual failure.

## Remaining engineering direction

1. Prove the Linode-backed PWA over HTTPS on the phone.
2. Retire the old Render instance only after that URL is verified.
3. Continue Fast Momentum LONG/SHORT paper-forward evidence, leverage-tier comparison, fee/slippage accounting and trade-detail chart improvements.
4. Keep real Binance execution separately gated until the paper/runtime path is proven reliable.
