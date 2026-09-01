# EBA Trader — Project State

_Last reconciled: 2026-09-01 (Asia/Ulaanbaatar)_

Actual merged code, exact-build production evidence and latest explicit decision documents override stale prose. Query GitHub for the live head before editing. The code-bearing baseline before this completion package is `48bdb0fa95cb6b1ae6a32e3ff6c9cf519fba68c3` (PR #127); current `main` before package merge is `f1e42865cb99af81640701a569663989c9b1b3ac`.

## Current goal

Build a research-first autonomous trading system that discovers genuinely repeatable edges efficiently while minimizing data-mining bias and preserving strict statistical/research integrity. Broad discovery and strict verification are separate authorities. Real-money execution remains locked.

The immediate owner-directed task is to complete the existing Strategy Factory v2 **D0 discovery campaign** as one coherent production package instead of continuing the ChatGPT hourly automation. The hourly automation has been stopped. This does not authorize D1, Frozen OOS or live execution.

## Canonical repository/runtime state

- Repository: `enkhbat194/EBA-Trader`.
- Production URL: `https://eba-trader-172-236-150-62.sslip.io`.
- Latest pre-package code-bearing research baseline: `48bdb0fa95cb6b1ae6a32e3ff6c9cf519fba68c3` (PR #127).
- Strategy Factory v2 remains the existing 8-family / deterministic 406-candidate pilot under a 500 raw-candidate hard cap and 30 survivor cap.
- PR #109 added resume-safe all-strata D0 campaign orchestration.
- PR #110 bound campaign source provenance to the actual clean checkout.
- PR #112 added the shared checkout lock between auto-update and production D0 execution.
- PR #115 added discovery-only behavioral cluster accounting.
- PR #117 suppressed partial/rejected aggregate D0 selection economics.
- PR #119 fails closed on missing/non-finite D0 selection metrics.
- PR #121 added the Factory-specific survivor-freeze completeness/diversity boundary.
- PR #122 rebuilt survivor eligibility from immutable registered campaign/candidate/trial-ledger evidence and requires terminal full-catalog D0 coverage before selection write.
- PR #124 makes `zero survivors is valid` executable after the same full-catalog terminal checks.
- PR #127 binds every declared D0 stratum to its exact materialized dataset SHA and verifies the same mapping at survivor freeze.
- The production 406-candidate × 12-strata campaign has not yet completed at the time this package is authored.
- M5 Frozen OOS remains **SEALED / NOT OPENED**.
- Factory v2 D1 hidden confirmation remains sealed.
- Real-money execution remains **LOCKED**.

## Exact production D0 source evidence

Latest completed exact production D0 source proof before the completion package is build `48bdb0fa95cb6b1ae6a32e3ff6c9cf519fba68c3`, GitHub Actions run `33498788797`, verify job `99827022315`. The exact-build wait and existing-only D0 source inspection both completed successfully.

Canonical existing D0 source:

- source kind: `INSPECTED_M5_DEVELOPMENT_CORPUS`;
- materialization ID: `m5corpusmat_25007f47e456b5f2d42ef16b`;
- policy ID: `m5policy_3b90b051bd27eeab0e79be74`;
- corpus ID: `m5corpus_28c69171b3657be02bffd556`;
- declaration SHA-256: `88365779d6821c1fb30372148bbcedbfadf11471843f57722723286a43cbc77c`;
- dataset SHA-256: `aa13bcfc111c00f6da19621353a3ca8044f58eca1ab95e837d9490a205aa72eb`;
- candle SHA-256: `6368c9f41ff635d2474860a8d4579fc00e57488871020a9df38222f32d9f4744`;
- order-flow SHA-256: `3398d17c48dd282c86a13a3ccf9daafcd2784e1e64732bb52c29b9b294e82da3`;
- rows: 2,880;
- windows/strata: 12 / 12;
- authority: `DISCOVERY_ONLY`;
- provenance: `INSPECTED_REUSABLE_DISCOVERY_DATA`;
- fresh confirmation evidence: false;
- verification authority: false;
- D1 opened: false;
- Frozen OOS opened: false;
- live execution allowed: false.

This source proof is not profitability evidence.

## Owner-authorized D0 completion package

`docs/SFV2_D0_PRODUCTION_AUTHORIZATION_2026-09-01.md` records the explicit one-time authorization `sfv2-d0-prod-20260901-v1`.

The package deliberately removes only the practical operator-shell blocker for this exact D0 pilot:

- no HTTP/PWA/public research mutation endpoint is added;
- the existing local root-side systemd research-maintenance path invokes the single-use request;
- the wrapper holds the same checkout lock as the five-minute updater;
- exact D0 source declaration/dataset hashes, 406 candidates, 12 strata and 0.90 behavioral threshold are frozen in the authorization;
- campaign trials remain immutable `DISCOVERY_ONLY` evidence;
- a sanitized read-only campaign status is exposed as `strategyFactoryV2` in `/api/research/status`;
- an external GitHub proof observes completion but cannot mutate research state.

### Predeclared D0 survivor rule

Before production results are observed, D0 survivor nomination is frozen to:

- complete and non-rejected D0 evidence;
- behavioral fingerprint available;
- mean total return > 0;
- mean expectancy > 0;
- mean benchmark-relative return > 0;
- at least 12 D0 trades;
- at most one survivor per behavioral cluster;
- deterministic lexicographic economic ranking;
- at most 30 survivors;
- zero survivors valid.

The 12-trade D0 floor is only a discovery resource-allocation gate. It does **not** replace or lower any later strict sample/statistical gate.

No extra adaptive higher-fidelity D0 rule is inserted after looking at results. Any future D0 fidelity change must be a new pre-result versioned decision.

## SF4 prospective replication

The exact `s3_vsm_s150` and `s3_cex_s075` hypotheses remain frozen. Replication uses only new BTCUSDT USD-M data from `2026-09-01T00:00:00Z` through `2026-09-13T00:00:00Z`. Evaluation remains fail-closed before `2026-09-13T00:00:00Z`; parameters may not be retuned and SF3 evidence may not be pooled into SF4 qualification. The conservative 48-test search budget remains carried forward.

The D0 completion package does not inspect or evaluate SF4 data.

## Strategy Factory v2 state

- `DISCOVERY_ONLY` authority.
- 8 existing causal strategy families; exact deterministic pilot catalog: 406 candidates.
- Hard caps: 500 raw candidates, 64 per family, 30 survivors.
- Common causal evaluator includes fees/slippage.
- D0/D1/D2/D3 evidence zoning remains enforced.
- D0 is inspected/reusable discovery evidence only; it cannot become fresh confirmation.
- Immutable campaign/candidate/trial accounting and source/dataset provenance are active.
- Behavioral dedup/clustering uses the fixed 0.90 threshold.
- Incomplete/rejected/schema-invalid candidates cannot expose aggregate selection economics or enter behavioral eligibility.
- Authorized Factory survivor freeze is `freeze_d0_pilot_survivors()`; the generic ledger freeze is not the sanctioned Factory path.
- The full catalog must be terminal over exact registered D0 strata and exact stratum dataset SHAs before any survivor/zero-survivor outcome can be frozen.
- Survivor freeze leaves D1, Frozen OOS and live authority false.

## Validation status

There is still **no verified profitable strategy**. SF1, SF2 and SF3 closed with zero promoted candidates. SF4 is prospective replication only. Factory v2 D0 ranking, clustering and survivor nomination have discovery authority only.

Historical strict reference gates remain unchanged. No profitability, expectancy, sample-size, cross-window, statistical, causal, cost, robustness or OOS gate is lowered by the D0 completion package.

## Safety invariants

- Development/discovery ranking is not promotion authority.
- A discovery survivor is not verified; zero survivors is valid.
- Reused/adaptively inspected data cannot be relabelled fresh evidence.
- Full search/multiple-testing history must remain accounted for.
- Robustness precedes Frozen OOS.
- Frozen OOS cannot be opened by discovery workflows.
- Demo is execution plumbing evidence, not verification.
- Deterministic risk retains veto authority.
- Spot and USD-M futures data are never silently mixed.
- Real Binance execution remains disabled.

## Next exact tasks

1. Merge the owner-authorized D0 completion package only after full exact-head CI is green.
2. Wait for that exact build to deploy to Linode through the existing five-minute updater.
3. Let the existing root-side research-maintenance timer execute/resume the single-use D0 authorization locally.
4. Require all 4,872 candidate/stratum trials to be terminal.
5. Freeze 0–30 cluster-diverse D0 survivors through the predeclared rule and `freeze_d0_pilot_survivors()` only.
6. Capture exact external production proof and record the empirical raw/spec/family/eligible/cluster/survivor counts.
7. Design D1 hidden confirmation separately only after the D0 outcome is frozen.
8. Keep SF4 untouched until `2026-09-13T00:00:00Z`.
9. Keep Frozen OOS and real-money execution locked.

## Continuity protocol

New sessions read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, `SESSION_HANDOFF.md`, `BACKTEST_PROTOCOL.md`, `docs/STRATEGY_FACTORY_V2_DESIGN.md` and `docs/SFV2_D0_PRODUCTION_AUTHORIZATION_2026-09-01.md`, then query actual GitHub/production state before editing.
