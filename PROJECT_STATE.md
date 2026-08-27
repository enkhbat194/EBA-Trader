# EBA Trader — Project State

_Last reconciled: 2026-08-28 (Asia/Ulaanbaatar)_
_Current implementation frontier: production scanner-status hotfix is merged and externally verified; resume the already-open M5 development-corpus materializer PR #64 from its existing diff after refreshing it against actual latest `main`._

This is the primary cross-chat continuation summary. Actual GitHub code, PR/workflow state and production proof override stale prose. Every new session must query actual GitHub state before editing.

## Current goal

Operate EBA Trader as a restart-safe 24/7 Linode paper/research system; keep operator-facing status truthful; build a controlled AI Strategy Factory on the M4 evidence platform; validate hypotheses across pre-registered development windows, robustness, then sealed Frozen OOS/forward/demo stages; keep real-money execution locked until the full evidence chain permits it.

## Current stage

- Production/runtime foundation: **VERIFIED**.
- Fast Momentum: **SOLE ACTIVE PRODUCTION PAPER SCANNER**.
- Scanner-status UI incident: **FIXED / PRODUCTION VERIFIED**.
- M4 research/evidence platform: **COMPLETE**.
- M5 isolated order-flow candidate cycle: **CLOSED WITHOUT EDGE CLAIM**.
- M5 chronological study policy: **MERGED / ENFORCED**.
- M5 development-corpus materializer: **PR #64 OPEN / IMPLEMENTATION EXISTS; DO NOT RESTART**.
- Legacy 2025 Frozen OOS: **LOCKED / INDEPENDENT**.
- M5 2026 Frozen OOS (`2026-08-15 -> 2026-08-22` UTC): **SEALED / NOT ACQUIRED / NOT OPENED**.
- Real-money execution: **LOCKED**.

## Canonical repository/runtime

- Repository: `enkhbat194/EBA-Trader`
- Base branch: `main`
- Scanner-status hotfix merge/main SHA: `b1afa22fcfa459d2a8a3789291b74a0566041545`
- Hotfix PR: `#65 Hotfix: keep scanner status truthful when UI rendering fails` — squash merged.
- Open research PR: `#64 M5: materialize resumable development corpus`.
- PR #64 branch: `m5-development-corpus-materializer`.
- PR #64 pre-hotfix head: `39cd2b6dbea75b36307c03cf9080769b49a23123`; it is based on older main and must be compared/refreshed against actual main before further edits, without recreating its existing work.
- Runtime: Linode Nanode, Ubuntu 24.04 LTS.
- Server repo: `/opt/Eba-Trader`.
- Runtime DB: `/var/lib/eba-trader/eba_trader.db`.
- Research root: `/var/lib/eba-trader/research`.
- Public PWA: `https://eba-trader-172-236-150-62.sslip.io/`.
- App/server release label: `0.12.2 · LINODE-M7`.
- PWA cache family: `eba-trader-ui-v15`.

## Production scanner-status incident — fixed

### User-visible symptom

Settings showed red `Server scanner: UNREACHABLE` while the same page showed `Runtime: LINODE`, `HTTPS READY`, and the correct deployed build. `Last server scans` showed:

`Can't find variable: mt5PositionMarkup`

### Confirmed root causes

1. `web/trade_detail.js` called `mt5PositionMarkup(...)` although no such function was defined. It also relied on an undefined legacy `paperPositionMarkup(...)` helper.
2. Settings runner synchronization treated **any browser-side renderer exception** as if `/api/runner/status` or the server were unreachable. A UI JavaScript bug could therefore create a false red server outage.
3. Settings relied on legacy aggregate `threadAlive`; Fast Momentum is the active scanner and its authoritative fields are `fastThreadAlive`, `fastRunning`, `fastPaperAvailable`, and `lastFastScanAtMs`.
4. PWA static assets required stronger revalidation so mixed stale/new JavaScript cannot survive a deploy unnecessarily.

### Hotfix behavior

PR #65:

- defines safe shared `mt5PositionMarkup` and `paperPositionMarkup` before `trade_detail.js` loads;
- makes Fast Momentum heartbeat the Settings scanner-health truth;
- reserves `UNREACHABLE` for actual `/api/runner/status` fetch/API failure only;
- reports browser renderer faults as `UI sync warning` without falsifying server/scanner health;
- revalidates service-worker/static assets from network and updates cache on successful fetch;
- adds regression contracts for renderer definition/load order, scanner-health fields, error classification and cache revalidation.

No strategy/risk/order execution behavior was changed by this hotfix.

## M5 research state

The original single four-hour development window (`2026-08-01T00:00Z -> 04:00Z`) was used only for bounded pipeline/candidate proofs. Results were negative and are not promotion evidence:

- candle-only baseline: ~`-0.42445%`, 4 trades;
- best Delta arm (`0.2`): ~`-0.12055%`, 2 trades;
- best stacked arm (`1`): ~`-0.12408%`, 2 trades;
- absorption `0.10/0.20`: ~`-0.16740%`, 1 losing trade;
- exhaustion `0.01/0.03`: 0 trades — not profitable-edge evidence;
- price/Delta divergence `0.01/0.05/0.10`: identical ~`-0.13709%`, 1 losing trade.

Do not continue tuning more isolated indicators on that inspected window.

The accepted next methodology is the sealed chronological M5 policy:

- development: `2026-07-01T00:00Z -> 2026-08-15T00:00Z`;
- M5 Frozen OOS: `2026-08-15T00:00Z -> 2026-08-22T00:00Z`;
- forward begins after the sealed M5 OOS;
- 12 fresh, non-overlapping four-hour development windows are pre-registered; the inspected `2026-08-01 00:00Z -> 04:00Z` proof window is excluded.

PR #64 already implements the next package: resumable/immutable materialization of those 12 development windows. Do not duplicate it.

## Safety invariants

- Frozen OOS cannot be opened by normal development acquisition/ablation.
- Real Binance order execution remains disabled.
- Development wins/rankings have no lifecycle-promotion authority.
- Lifecycle v2 requires robustness before OOS.
- AI-generated hypotheses use constrained/allowlisted structures; arbitrary generated production Python is not an approved execution path.
- Runtime trading persistence and research DB/datasets/evidence remain separate.
- Spot and USD-M futures data are never silently mixed.
- Executed-trade footprint and resting LOB/order-book liquidity remain separate data planes.
- Tampered/gapped/missing-version research data fails closed.
- Browser/UI state must not be treated as proof of backend failure when the backend API succeeded.

## Validation status

Scanner-status hotfix exact PR head `7d6e67ffed44228bec6df093c2041f43cb66b5cf` passed:

- full Python regression;
- Ruff;
- shell/deployment contract;
- Linode runtime checks;
- continuity guard.

PR #65 squash-merged as `b1afa22fcfa459d2a8a3789291b74a0566041545`.

Exact-main production validation:

- Linode external exact-build production proof run `33111336161`: **PASS**; verified exact build `b1afa22...`, HTTPS, Demo reconnect, Chart, Positions, Fast restart proof, M5 safety evidence, Frozen OOS closed and real execution locked.
- Public production smoke run `33111336195`: first attempt hit a transient nginx `/api/chart` HTTP 502 during deploy convergence; rerun attempt 2: **PASS** on the same exact main SHA.
- Linode runtime and continuity workflows: **PASS**.

## Next exact tasks

1. Query actual `main`, open PRs and workflow state; do not assume this file is newer than GitHub reality.
2. Resume existing PR #64 / `m5-development-corpus-materializer`; compare its diff to actual main and bring the branch forward without discarding/recreating the materializer work.
3. Run PR #64 exact-head full CI; fix any conflicts/regressions introduced by the scanner hotfix/main advance.
4. Merge PR #64 only after all required workflows are green.
5. Deploy exact main and materialize only the 12 pre-registered development windows on Linode; do not acquire/open M5 Frozen OOS.
6. Verify 12/12 immutable workflow/dataset hashes/provenance and resumable replay behavior.
7. Build the multi-window evaluator/aggregator and begin Strategy Factory screening across fresh development windows rather than the old single smoke window.
8. Continue to robustness before any OOS consideration.

## Continuity protocol

Canonical continuation files: `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, `SESSION_HANDOFF.md`, `docs/CONTINUITY_PROTOCOL.md`.

New sessions must read them, then query actual GitHub state. Existing active branch/PR work must be compared and resumed rather than recreated. At meaningful session end, update repo state/handoff with exact commits, CI, production proof, unresolved risks and the next exact action.
