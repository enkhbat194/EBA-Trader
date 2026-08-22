# M18.1 Demo Deployment

Status: `DEMO_ONLY_LIVE_LOCKED`

## Source of truth

GitHub remains the only development/source-of-truth system for EBA-Trader.

Branch: `m18-fee-aware-execution-economics`

Render is used only as a temporary runtime for the Python-backed mobile PWA. Replit is not used.

## Render blueprint

The repository root contains `render.yaml` with the frozen Demo deployment settings:

- service: `eba-trader-demo`;
- runtime: Python;
- plan: Free;
- region: Singapore;
- source branch: `m18-fee-aware-execution-economics`;
- Python: `3.12.14`;
- start: `PYTHONPATH=src python -m eba_trader.web_server`;
- health check: `/api/health`;
- auto deploy: only after linked GitHub checks pass.

No Binance API key or secret belongs in Render environment variables. Demo credentials are entered only through the in-app Binance Demo form.

## Free-runtime behavior

Render Free web services can spin down after 15 minutes without inbound traffic. This is acceptable for the current Demo stage.

- while the paper scanner is open, its 15-second snapshot requests provide inbound traffic;
- if the service spins down or restarts, all RAM-only Binance Demo sessions disappear;
- the UI must then reconnect with the Demo credential;
- losing a RAM session is intentionally fail-closed and cannot enable trading.

The Free service is not approved for unattended 24/7 trading or production execution.

## Public web safety

The Python server adds:

- Content Security Policy;
- `X-Content-Type-Options: nosniff`;
- `X-Frame-Options: DENY`;
- `Referrer-Policy: no-referrer`;
- restrictive Permissions Policy;
- HSTS;
- `Cache-Control: no-store` on API responses.

The PWA service worker never caches `/api/*` responses and uses network-first delivery for app assets so GitHub updates do not remain hidden behind a stale cache.

Remote/provider error text is HTML-escaped before it enters connection-card markup.

## Session model

A successful Binance Unified Demo connection creates a cryptographically random opaque token.

- Demo API key/secret remain only in server process memory;
- TTL is 30 minutes;
- browser persistent storage is not used;
- user can explicitly choose `DISCONNECT DEMO SESSION` to revoke the RAM session immediately;
- server restart, free-instance spin-down, or TTL expiry also destroys/rejects the session.

## Explicitly prohibited

- real-money Binance API credentials;
- Live mode;
- order placement;
- order cancellation;
- withdrawals or transfers;
- leverage changes;
- putting API secrets in GitHub or Render configuration;
- treating the Demo scanner as a profitability proof.

## First phone test

After the Render service is created from this GitHub Blueprint:

1. Open the generated HTTPS `onrender.com` URL on the phone.
2. Open Settings → Connections → Binance.
3. Open Binance Demo Trading from the provided link.
4. Create one Demo API key/secret in Demo Trading API Management.
5. Paste the Demo credential pair into EBA-Trader and choose `TEST BINANCE DEMO`.
6. Confirm Spot and USD-M Demo balances appear.
7. Start `PAPER SCANNER` and verify fee-aware `NO_TRADE` / `PAPER_CANDIDATE` snapshots.
8. Do not enable or use any real-money API key.
