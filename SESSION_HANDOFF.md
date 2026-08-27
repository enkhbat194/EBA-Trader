# EBA Trader — Session Handoff

_Last handoff prepared: 2026-08-28 (Asia/Ulaanbaatar)_

## Purpose

This is the exact continuation point. A new session must read the canonical continuity files, then query actual GitHub `main`, open PRs/branches and workflows before editing. Git/code/runtime evidence overrides stale prose.

## Exact repository state

- Repository: `enkhbat194/EBA-Trader`
- Authoritative base: `main`
- Latest functional production hotfix main before this continuity-only update: `b1afa22fcfa459d2a8a3789291b74a0566041545`
- PR #65 scanner-status hotfix: **MERGED**.
- Hotfix exact PR head: `7d6e67ffed44228bec6df093c2041f43cb66b5cf`.
- Hotfix merge SHA: `b1afa22fcfa459d2a8a3789291b74a0566041545`.
- Open research PR #64: `M5: materialize resumable development corpus`.
- PR #64 branch: `m5-development-corpus-materializer`.
- PR #64 existing head before the hotfix merge: `39cd2b6dbea75b36307c03cf9080769b49a23123`.
- PR #64 is based on older main; **do not restart its work**. Compare it against actual latest main and bring it forward.

## What was completed — scanner-status incident

The user reported Settings showing red `Server scanner: UNREACHABLE` plus:

`Can't find variable: mt5PositionMarkup`

while Runtime/HTTPS/build information was otherwise healthy.

Root cause was confirmed in repository code:

1. `web/trade_detail.js` called `mt5PositionMarkup(...)` without defining it. It also depended on an undefined `paperPositionMarkup(...)` helper.
2. Settings' runner sync put network/API fetching and optional browser UI rendering inside one catch path. A JavaScript renderer error therefore falsely changed server status to `UNREACHABLE`.
3. Settings used legacy aggregate `threadAlive`; the active production scanner is Fast Momentum and its health is represented by `fastThreadAlive`, `fastRunning`, `fastPaperAvailable`, and `lastFastScanAtMs`.
4. PWA static asset fetching was hardened to reduce mixed stale/new JavaScript across deploys.

PR #65 fixed all four points:

- safe shared MT5 and legacy-paper position renderers are defined before `trade_detail.js` loads;
- Settings uses Fast Momentum heartbeat for scanner truth;
- `UNREACHABLE` is now reserved for actual `/api/runner/status` transport/API failure;
- renderer faults are shown as `UI sync warning` without turning a healthy scanner red;
- service worker revalidates static assets from the network and refreshes its cache;
- regression tests lock function definitions/load order, scanner health fields, error classification and cache behavior.

## Validation / production proof

PR #65 exact head `7d6e67ff...` passed:

- full Python regression;
- Ruff;
- shell/deployment checks;
- Linode runtime checks;
- continuity guard.

Exact merged main `b1afa22f...`:

- external exact-build production proof run `33111336161`: **PASS**;
- exact production build verified as `b1afa22fcfa459d2a8a3789291b74a0566041545`;
- HTTPS, encrypted Demo reconnect, Chart, Positions and Fast restart proof: **PASS**;
- M5 research evidence remained safe/development-only;
- Frozen OOS remained closed;
- real execution remained locked.

Public smoke run `33111336195` attempt 1 observed a transient nginx `502 Bad Gateway` from `/api/chart` while deployment was converging. The same run was re-executed after deploy convergence; attempt 2: **PASS** on the exact same `b1afa22f...` main.

No trading strategy, risk rule, lifecycle permission or execution authority changed in the hotfix.

## Research state to resume

The single-window isolated candidate cycle is closed without an edge claim. Do not keep fitting new indicators to the already-inspected `2026-08-01 00:00Z -> 04:00Z` sample.

PR #63 already merged a chronological M5 policy:

- development: `2026-07-01 -> 2026-08-15` UTC;
- sealed M5 Frozen OOS: `2026-08-15 -> 2026-08-22` UTC;
- 12 fresh non-overlapping four-hour development windows;
- the old inspected four-hour proof window is excluded;
- normal development acquisition cannot fetch/open the sealed M5 OOS.

PR #64 already contains the next real implementation package:

- deterministic 12-window corpus materialization;
- archive order flow by default;
- immutable materialization identity/final manifest;
- immutable per-window checkpoints;
- resumable interrupted runs;
- completed replay without re-fetching completed data;
- workflow/domain/range/source/hash verification;
- fail-closed tamper/missing-path behavior;
- `eba-materialize-m5-corpus` CLI;
- deterministic replay/resume/tamper/provenance tests.

Do not duplicate this implementation.

## Next exact task

1. Query actual `main`, PR #64 head and all open PR/workflow state.
2. Compare `m5-development-corpus-materializer` with actual latest main, which now includes the scanner hotfix/continuity commits.
3. Update PR #64 branch cleanly without dropping existing materializer commits.
4. Run exact-head full regression, Ruff, shell/deployment, runtime and continuity workflows; fix all failures.
5. Merge PR #64 only when green.
6. Deploy exact main to Linode.
7. Materialize only the 12 pre-registered development windows; do **not** acquire or open sealed M5 Frozen OOS.
8. Verify 12/12 immutable hashes/provenance and resumable replay.
9. Build multi-window evaluation/aggregation, then use it for Strategy Factory screening across fresh development evidence.
10. Robustness remains mandatory before any Frozen-OOS stage.

## Hard constraints

- Real-money execution stays locked.
- Both legacy and M5 Frozen OOS locks remain in force.
- Development/ranking evidence cannot grant promotion authority.
- Fast Momentum remains paper-only.
- Deterministic risk retains final veto authority.
- Browser UI errors must not masquerade as backend/server reachability failures.
- API secrets never go to Git/chat/logs/browser persistent storage.
- Runtime persistence and research persistence remain separate.
- Executed-trade footprint and resting order-book liquidity remain separate research data planes.

## Startup rule for the next chat

Read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, this `SESSION_HANDOFF.md`, and `docs/CONTINUITY_PROTOCOL.md`; query actual GitHub state; compare PR #64 to main; resume the existing diff from the first unfinished task instead of rebuilding it.
