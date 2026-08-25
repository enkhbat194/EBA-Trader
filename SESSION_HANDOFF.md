# EBA Trader — Session Handoff

_Last handoff prepared: 2026-08-26 (Asia/Ulaanbaatar)_

## What was completed

- Fully read the uploaded `EBA_Chat_Branch_Repo_Continuity_Package`.
- Audited GitHub `main`, root tree, recent commits, current architecture, lifecycle code, M5 feature registry, order-flow modules and Linode update/rollback script.
- Installed the continuity system as PR #29 and merged it to `main` at `368679fd232a1b9ef943147361346f57c36ff01c`.
- Added `AGENTS.md` with mandatory start/end-of-session rules for connected AI/coding sessions.
- Added real EBA-specific `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, and `SESSION_HANDOFF.md` instead of generic templates.
- Added `docs/CONTINUITY_PROTOCOL.md` with the new-branch bootstrap/recovery protocol.
- Added `scripts/check_continuity.py` and `.github/workflows/continuity.yml` so the continuity surface is CI-enforced.
- Added a PR checklist requiring state/TODO/decision/handoff verification.
- Reconciled `PROJECT_STATE.md`, `ARCHITECTURE.md`, and stale `README.md` statements with actual code and deployment scripts.
- Follow-up state reconciliation commit: `4d9b9df0600d6236ddf73fb157582fcc9b138195`.

## Tests/checks run

PR #29 passed before merge:

- dedicated **Continuity guard**;
- Python full regression suite;
- Ruff;
- shell syntax;
- deployment contract;
- Linode runtime checks.

These prove repository consistency, not current external Linode/public-network state.

## Current project state

- GitHub `main` is the code and continuity source of truth.
- Linode remains the sole active EBA Trader backend/runtime target.
- M4 research platform is complete.
- M5 AI Strategy Factory is in progress.
- M5 foundations through PR #28 are merged: constrained DSL, feature registry, deterministic candidate emission, family templates, similarity guard, cheap screening/ranking, historical aggregate-trade integrity/cache and deterministic footprint windows.
- Enabled order-flow research features: executed buy/sell volume, delta, delta ratio, CVD, POC.
- Stacked imbalance, absorption, exhaustion and LOB depth imbalance remain disabled/unimplemented.
- Real Binance order submission remains locked.
- Frozen OOS automation remains locked pending lifecycle-order reconciliation.

## Problems / blockers

### Lifecycle order

`src/eba_trader/lifecycle.py` currently enforces:

`GENERATED -> BACKTESTED -> OOS_VERIFIED -> ROBUSTNESS_VERIFIED -> ...`

Desired methodology conceptually wants robustness before frozen OOS. Do not bypass the code. Resolve with an explicit lifecycle migration and tests before automated OOS orchestration.

### External production proof

Still not proven by repository CI:

- latest `main` actually consumed by Linode;
- external-phone HTTPS availability;
- real service/server restart recovery of an active Fast Momentum paper position through later MARK/CLOSE;
- final disposition of the older carry paper engine.

## Important decisions made

- Repository state is the cross-chat shared memory bridge.
- Actual code/config/tests + Git history override stale chat memory.
- Every meaningful connected AI/coding session must read continuity files first and write state/handoff back after work.
- M5 uses constrained strategy DSL/schema rather than arbitrary generated Python.
- Footprint/order flow remains an experimentally validated feature family, not assumed edge.
- Gapped historical order-flow data fails closed.
- Cheap screening/ranking has no OOS/execution promotion authority.

## Next exact task

1. Implement deterministic historical Binance `aggTrades` downloader/pagination with request/range provenance.
2. Implement missing aggregate-trade ID range detection and repair; only gap-free verified datasets become research-ready.
3. Add causal footprint-to-candle alignment and boundary tests.
4. Add an allowlisted order-flow backtest adapter through the M4 worker/control plane.
5. Run candle-only vs candle+delta/CVD development ablations with identical fees, slippage and gates.
6. Keep frozen OOS closed during this development work.
7. In parallel, perform the external Linode HTTPS + restart/recovery proof.

## Notes for the next AI session

Start with `AGENTS.md`, then `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, and this file. Inspect recent Git history and the actual modules relevant to the next task before coding. If any text here is stale, repair it from repository reality first.
