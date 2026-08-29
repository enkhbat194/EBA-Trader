# EBA Trader — Project State

_Last reconciled: 2026-08-29 (Asia/Ulaanbaatar)_

Actual GitHub code, workflow state and Linode production proof override stale prose.

## Current goal

Keep `main` production-clean while building a verified automated trading research pipeline. Development evidence must pass robustness before any sealed Frozen-OOS stage. Real-money execution stays locked.

## Current stage

- Production/runtime foundation: **VERIFIED**.
- Fast Momentum: **sole active production paper scanner**.
- M4 research/evidence platform: **COMPLETE**.
- M5 single-window order-flow candidate cycle: **CLOSED WITHOUT EDGE CLAIM**.
- M5 chronological study policy: **MERGED / ENFORCED**.
- 12-window M5 development corpus: **MATERIALIZED / VERIFIED**.
- 17-candidate multi-window evaluator: **IMPLEMENTED / PRODUCTION-RUN**.
- `absorption_020` robustness stage: **COMPLETE BUT NOT VERIFIED**.
- Binance USD-M Futures Demo execution plumbing: **REAL DEMO ROUND-TRIP VERIFIED**.
- M5 Frozen OOS (`2026-08-15 -> 2026-08-22` UTC): **SEALED / NOT OPENED**.
- Legacy 2025 Frozen OOS: **LOCKED**.
- Real-money execution: **LOCKED**.

## Canonical repository/runtime state

- Repository: `enkhbat194/EBA-Trader`
- Production URL: `https://eba-trader-172-236-150-62.sslip.io`
- Production `main` before the current closeout PR: `9ab6e70a4d5cbef7854facd48b13607ea3356b4b`
- Current closeout branch: `closeout-binance-demo-v4`
- Open PRs at closeout start: none.
- Linode exact-build production proof for `9ab6e70a...`: **PASS**.

Recent durable milestones:

- `8f7d27922c60caf92e3f23fc988f0dbbba2b7e84` — resumable 12-window development corpus materializer.
- `d0de5fbfe33ecfaff50693637ec6ff38829ad81c` — materialize the pre-registered corpus on Linode.
- `40ec7761e27616621b563665697cbe0ff783336f` — deterministic 17-candidate multi-window evaluator.
- `e7d398903ebb635b3645b5ceca36112a07f0f4a7` — run the evaluator across all 12 development windows on Linode.
- `3dcfe48995b3662899105b710aa82c6a68ad093c` — fixed 9-scenario robustness stage for `absorption_020`.
- `1667a0fd918a2af8f0a1796414bc536def26c9ad` and follow-up fixes — one-shot Binance USD-M Demo execution/latency proof infrastructure.
- `9ab6e70a4d5cbef7854facd48b13607ea3356b4b` — resolve zero-price Demo fills through exact order lookup/account trade history.

## Validation status

### M5 robustness

Production proof run `33215478581` completed successfully as a proof collector, but the candidate itself **did not pass robustness**:

- robustness ID: `m5rob_0ddaad97c4954b46ff7e9bcb`
- candidate: `absorption_020`
- scenarios: 9
- `robustnessVerified=false`
- `centerProfitable=false`
- `sampleSufficient=false`
- `costStressStable=true`
- `emaStable=true`
- `parameterNeighborhoodStable=true`
- minimum baseline-beating windows: 9
- minimum center trades requirement: 30

Interpretation: the plumbing and robustness evaluation completed safely, but this candidate is **not eligible for Frozen OOS**. Do not promote it.

### Binance USD-M Futures Demo round-trip v4

Production one-shot probe `usdm-btcusdt-roundtrip-20260829-v4` completed with `phase=COMPLETE`, `passed=true` on exact build `9ab6e70a...`.

Execution proof:

- environment: Binance USD-M Futures **Demo** (`demo-fapi.binance.com`)
- symbol: `BTCUSDT`
- position mode: one-way
- quantity: `0.0007 BTC`
- effective notional: `54.30901 USDT`
- available Demo USDT before: `4999.89709561`
- BUY average fill: `77584.6`
- SELL average fill: `77584.1`
- BUY fill source: exact order query
- SELL fill source: exact order query
- BUY slippage: `+0.0386676170 bps`
- SELL slippage: `+0.0322229934 bps`
- BUY order acknowledgement: `212.033707 ms`
- SELL order acknowledgement: `221.393951 ms`
- BUY fill lookup: `216.710555 ms`
- SELL fill lookup: `270.355526 ms`
- latest market-data age: `618.613281 ms`
- full probe round-trip: `3987.621519 ms`
- pre-position zero: true
- post-position zero: true
- real money used: false
- real execution lock: true
- Frozen OOS lock: true

This proves the **Demo execution plumbing and measurement path**, not strategy profitability and not live-readiness.

## Demo one-shot closeout

The current closeout changes make the successful v4 probe permanently inactive after proof:

- `config/binance_demo_execution_probe_v1.json` becomes `enabled=false`;
- a disabled probe preserves an already-terminal Demo proof instead of overwriting it with `DISABLED`;
- regression coverage guarantees disabled state cannot submit another order;
- the existing successful proof remains observable for continuity/production checks.

## Research interpretation

The system has now proven:

1. deterministic historical research/data materialization;
2. multi-window candidate evaluation;
3. a bounded robustness stage;
4. actual Binance Futures Demo BUY/SELL execution plumbing with measured latency/slippage and flat-position recovery.

What it has **not** proven is a robust profitable strategy. `absorption_020` failed the required profitability/sample sufficiency checks, so the research pipeline must return to development rather than open Frozen OOS.

## Safety invariants

- Frozen OOS cannot be opened by normal development workflows.
- M5 Frozen OOS stays sealed until a candidate actually passes robustness.
- Real Binance order execution remains disabled.
- Demo execution plumbing has no lifecycle-promotion authority.
- Development rankings have no promotion authority.
- Lifecycle v2 requires robustness before OOS.
- Deterministic risk keeps final veto authority.
- Runtime persistence and research persistence remain separate.
- Spot and USD-M futures data are never silently mixed.
- Executed footprint and resting LOB/order-book liquidity remain separate data planes.
- Gapped/tampered/missing-version research data fails closed.

## Next exact task

1. Finish CI for `closeout-binance-demo-v4`.
2. Merge only if full regression/runtime/continuity checks pass.
3. Verify production exact build and confirm the preserved v4 proof remains `COMPLETE` after the probe is disabled.
4. Clean temporary proof branches when branch-deletion authority is available; keep `main` plus the intentional legacy archive.
5. Return Strategy Factory work to **development-only** candidate discovery/evaluation.
6. Increase independent evidence/sample size and candidate quality without reusing Frozen OOS.
7. Require the next candidate to satisfy center profitability, sample sufficiency, cost stress and parameter-neighborhood stability before Frozen OOS can be considered.
8. Do not open M5 Frozen OOS and do not enable real-money execution.

## Continuity protocol

New sessions read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, `SESSION_HANDOFF.md`, and `docs/CONTINUITY_PROTOCOL.md`, then query actual GitHub/production state before editing.
