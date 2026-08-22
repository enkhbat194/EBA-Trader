# M18.1 Phone Deploy Ready Checkpoint

Date: 2026-08-22
Status: `READY_FOR_FIRST_EXTERNAL_DEMO_DEPLOY`
Branch: `m18-fee-aware-execution-economics`
PR: #14 (draft, not merged)

## Latest green checkpoint

Source head before this documentation-only checkpoint: `01b4d2f7eeeb37bc7ae3207fd660d47bfc42082b`.

GitHub Actions:
- M18 fee-aware execution validation run `32529862584`: PASS;
- M6 derivatives audit validation run `32529862586`: PASS.

Validated:
- Unified Binance Demo endpoints;
- one Demo API key/secret UI contract;
- live lock;
- read-only provider clients;
- RAM-only Demo session;
- explicit Demo disconnect;
- Demo fee-aware snapshot scanner;
- public security headers / CSP;
- PWA API no-cache contract;
- Render deployment contract;
- repo-wide pytest;
- Ruff.

## Deployment readiness

Repository now contains:
- `render.yaml`;
- `.python-version` pinned to `3.12.14`;
- Render Free / Singapore configuration;
- health check `/api/health`;
- start command `PYTHONPATH=src python -m eba_trader.web_server`;
- auto deploy only after CI checks pass;
- GitHub README `Deploy to Render` button.

GitHub remains source of truth. Render is runtime only. Replit is not used.

## Security behavior

- no Binance credentials in GitHub or Render config;
- only Binance Demo Trading credential is approved;
- Demo secret is accepted by same-origin HTTPS app request;
- credentials live only in server process RAM after validation;
- 30-minute TTL;
- explicit `DISCONNECT DEMO SESSION` revokes the server RAM session;
- service restart/spin-down destroys sessions;
- API responses are `no-store` and service worker does not cache `/api/*`;
- remote error text is escaped before connection-card HTML rendering;
- Live environment remains hard-rejected;
- no order/cancel/withdraw/transfer/leverage methods exist.

## Only external user action now required

Create the first Render Blueprint instance from the repository's `Deploy to Render` button. This requires the user's Render/GitHub authorization and cannot be performed by repository code alone.

After Render returns the public HTTPS `.onrender.com` URL, continue immediately with:
1. phone UI smoke test;
2. create Binance Demo Trading API key/secret;
3. in-app `TEST BINANCE DEMO`;
4. verify Spot + USD-M Demo balances;
5. verify first fee-aware `NO_TRADE` / `PAPER_CANDIDATE` snapshot;
6. keep Live locked.
