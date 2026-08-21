# M18 / M18.1 GitHub-Only App Development Decision

Date: 2026-08-21
Branch: `m18-fee-aware-execution-economics`
PR: #14

## Decision

All EBA-Trader UI, provider-adapter, secure connection-test backend, tests, CI and documentation work continues directly in GitHub.

Replit is not part of the M18/M18.1 development workflow and must not be treated as a source of truth, code-writing environment, or required preview dependency.

GitHub repository state is authoritative.

## Current app scope

The current mobile-first PWA includes:

- Dashboard / Home;
- Opportunities;
- Positions;
- History;
- Settings / Connections;
- Binance / MetaTrader 5 / MetaTrader 4 provider-neutral connection architecture;
- Demo-first environment;
- `LIVE` hard-locked;
- Binance Demo credential form and `Test Connection` flow;
- secure Python web bridge;
- no secret persistence in browser storage or repository files;
- no live order, cancel, withdrawal, transfer or leverage-change capability.

## Development workflow

1. Make all source changes on GitHub branch `m18-fee-aware-execution-economics`.
2. Keep PR #14 as the engineering validation PR until the app checkpoint is complete.
3. Every change must pass repository-wide pytest, Ruff and M18/M18.1 safety checks.
4. Binance credentials must never be committed to GitHub.
5. Demo/Test environment is mandatory before any future live-account consideration.
6. MT5/MT4 remain provider scaffolds until their real bridges are separately implemented and tested.
7. Live execution remains blocked unless a later explicit safety/research approval cycle authorizes it.

## Preview / deployment boundary

GitHub is the development and source-control platform. GitHub Pages may later be used for a static UI-only preview, but the real EBA-Trader app requires a runtime capable of serving the Python backend for `/api/*` routes. The eventual hosting target must be chosen separately; Replit is not required.

## Immediate next work

- finish the GitHub-hosted source implementation of the approved mobile UI;
- keep Binance Demo as the first functional provider;
- verify the in-app Demo `Test Connection` path against a demo credential;
- wire demo balance, account-specific fee snapshot and fee-aware opportunity data into Dashboard / Opportunities;
- keep paper-only bot controls and deterministic NO_TRADE gates active;
- do not enable Live mode.
