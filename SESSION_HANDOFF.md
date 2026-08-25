# EBA Trader — Session Handoff

_Last handoff prepared: 2026-08-26 (Asia/Ulaanbaatar)_

## Session objective

Install a repository-backed continuity system for ChatGPT branch chats / AI sessions and reconcile the continuity documents with the actual EBA Trader repository after M5 PRs #25-#28.

## What was completed

- Read the full uploaded `EBA_Chat_Branch_Repo_Continuity_Package`.
- Inspected GitHub `main`, root structure, recent commits, architecture, lifecycle, M5 feature registry, deployment update script and current M5 state.
- Added mandatory repo-level agent continuity rules in `AGENTS.md`.
- Added authoritative architectural/research decisions in `DECISIONS.md`.
- Added prioritized `TODO.md` based on current implementation and known proof gates.
- Added this `SESSION_HANDOFF.md` and `CHANGELOG.md`.
- Added a continuity protocol document and automated guard/CI check.
- Reconciled `PROJECT_STATE.md`, `ARCHITECTURE.md`, and stale `README.md` statements with current code/deployment behavior.

## Current code baseline verified before this continuity branch

GitHub `main` baseline: `2f823ca918bc8d8b2866a5e77fa8372063121a25`.

Immediately preceding merged M5 milestones:

- #25 order-flow/footprint research foundation;
- #26 constrained strategy DSL + approved feature registry + M4 emission;
- #27 family templates + similarity guard + cheap screening + survivor ranking;
- #28 historical aggregate-trade dataset integrity + deterministic footprint windows.

## Current system state

- Runtime source of truth: GitHub `main`.
- Runtime host target: Akamai/Linode, Ubuntu 24.04 LTS.
- Canonical runtime services: `eba-binance-data.service`, `eba-runtime-api.service`, `eba-web.service`.
- Persistent runtime DB: `/var/lib/eba-trader/eba_trader.db`.
- Auto-update timer deploys exact `origin/main`, requires local service/API health, and rolls back on runtime failure.
- Public HTTPS bootstrap exists and is retried independently from runtime rollback.
- M4 research control plane is complete.
- M5 AI Strategy Factory is in progress.
- Order-flow features enabled today: executed buy/sell volume, delta, delta ratio, CVD, POC.
- Stacked imbalance, absorption, exhaustion and LOB depth imbalance remain disabled/unimplemented feature-registry entries.
- Historical order-flow cache now has strict duplicate/timestamp/hash/sequence-gap integrity rules and fixed closed footprint windows.
- Real Binance order submission remains locked.

## Important unresolved issue

`src/eba_trader/lifecycle.py` currently defines promotion as:

`GENERATED -> BACKTESTED -> OOS_VERIFIED -> ROBUSTNESS_VERIFIED -> ...`

The desired research process conceptually wants robustness before opening frozen OOS. Do not bypass the implemented lifecycle. Resolve this deliberately before automated frozen-OOS orchestration.

## Next exact task

1. Implement a deterministic historical Binance `aggTrades` downloader with paged/range provenance.
2. Implement missing-ID-range detection/repair and only mark a dataset research-ready once gaps are resolved.
3. Add causal footprint-to-candle alignment.
4. Add an allowlisted M4 backtest adapter for approved order-flow features.
5. Run controlled candle-only vs candle+delta/CVD development ablations under identical cost assumptions and gates.
6. Keep frozen OOS closed while development/robustness design is being reconciled.

## Parallel production-proof task

Confirm current `main` deployment on Linode, public HTTPS from an external phone, and one real restart/recovery persistence test. Repository CI is not proof of these external conditions.

## Files that define continuity

- `AGENTS.md`
- `PROJECT_STATE.md`
- `ARCHITECTURE.md`
- `DECISIONS.md`
- `TODO.md`
- `CHANGELOG.md`
- `SESSION_HANDOFF.md`
- `docs/CONTINUITY_PROTOCOL.md`
- `scripts/check_continuity.py`
- `.github/workflows/continuity.yml`

## Instruction for the next AI session

Do not rely on this handoff alone. Start by reading `AGENTS.md` and all continuity files, then verify the relevant implementation and recent Git history. If this handoff is stale, update it from repository reality before continuing.
