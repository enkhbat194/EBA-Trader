# Linode auto-update recovery

## Symptom confirmed on 2026-08-27

The public PWA reported:

- installed UI `0.11.0 / LINODE-M2`;
- server release `0.12.0 / LINODE-M5`;
- server build `050cd9b`;
- newer GitHub `main` was already available;
- `RELOAD LATEST VERSION` did not advance the server build.

This means the failure is server-side deployment, not merely a stale browser cache. The reload button updates the PWA/service-worker layer; it does not run Git/systemd deployment on Linode.

## Safe one-time recovery

Open the Linode LISH/Cloud Manager console and run as root:

```bash
curl -fsSL https://raw.githubusercontent.com/enkhbat194/EBA-Trader/main/scripts/repair_linode_auto_update.sh | bash
```

The helper is fail-closed. If `/opt/Eba-Trader` has local changes it refuses to reset the checkout, writes `/var/lib/eba-trader/deploy-state/dirty-checkout.txt`, and exits without deleting those changes.

On a clean checkout it downloads and executes the latest `main` deployment script, then enables/restarts the five-minute auto-update timer and prints current app info.

## Persistent diagnostics after recovery

`eba-auto-update.service` runs through `scripts/auto_update_entrypoint.sh`. Every timer attempt records:

- `last_attempt_at`
- `last_output.log`
- `failed_at` and `last_error` when a deployment fails

under `/var/lib/eba-trader/deploy-state/`.

Useful server checks:

```bash
systemctl status eba-auto-update.timer --no-pager
systemctl list-timers --all eba-auto-update.timer --no-pager
journalctl -u eba-auto-update.service -n 100 --no-pager
cat /var/lib/eba-trader/deploy-state/last_error 2>/dev/null || true
curl -fsS http://127.0.0.1:8000/api/app-info
```

## Safety boundary

The PWA is not granted shell/systemd deployment authority. Recovery and deployment stay on the Linode control plane. Trading execution and frozen OOS locks are unchanged.
