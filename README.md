# EBA Trader

EBA Trader is a research-first, provider-independent trading system with deterministic risk control.

Current active engineering branch: `m18-fee-aware-execution-economics`  
Current validation PR: #14  
Current mode: **Demo / read-only paper scanner**  
Live execution: **LOCKED**

## Open the Demo app

The GitHub repository is the source of truth. Render is used only as a temporary Python runtime so the mobile PWA can be opened from a phone.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https%3A%2F%2Fgithub.com%2Fenkhbat194%2FEBA-Trader%2Ftree%2Fm18-fee-aware-execution-economics)

The repository already contains `render.yaml`. The Demo Blueprint uses the Free plan, Singapore region, Python 3.12.14, `/api/health`, and deploy-after-CI-pass behavior.

**Do not put Binance API keys in GitHub or Render settings.** After the app is running, create a key inside **Binance Demo Trading** and paste that Demo key/secret only into the in-app Binance connection form.

## M18.1 app

The approved mobile-first PWA includes:

- Dashboard / Home;
- Opportunities;
- Positions;
- History;
- Settings / Connections;
- Binance, MetaTrader 5 and MetaTrader 4 provider boundaries;
- Binance Unified Demo Trading connection;
- 30-minute RAM-only Demo credential session;
- account balance display after successful Demo connection;
- fee-aware BTC Spot ↔ USD-M quarterly opportunity scanner;
- deterministic `NO_TRADE` / `PAPER_CANDIDATE` output;
- explicit Demo session disconnect;
- `LIVE 🔒` hard lock.

## Binance Unified Demo Trading

The current Demo integration uses one Binance Demo Trading API key/secret for both:

- Spot Demo: `https://demo-api.binance.com`;
- USD-M Futures Demo: `https://demo-fapi.binance.com`.

Connection and scanning are read-only. Current code contains no order, cancel, withdrawal, transfer, or leverage-change methods.

## Safety rules

- AI is not the final risk authority.
- The deterministic Risk Engine remains superior to strategy/AI/execution layers.
- `NO_TRADE` is a valid decision.
- API secrets must never be committed to Git.
- Browser persistent storage is not used for Demo credentials or session tokens.
- API responses are not cached by the PWA service worker.
- Live environment requests are rejected by the backend.
- Real-money Binance credentials are not approved for M18.1.
- 2025 OOS remains `LOCKED_NOT_ACCESSED`.

## Research status

Historical research cycles M2-M17 did **not** earn promotion to a live profitable strategy. M18/M18.1 are execution-cost and app infrastructure, not a profitability claim.

See [`docs/PROJECT_STATE.md`](docs/PROJECT_STATE.md) for the authoritative cross-chat project checkpoint and [`docs/M18_DEMO_DEPLOYMENT.md`](docs/M18_DEMO_DEPLOYMENT.md) for Demo deployment details.
