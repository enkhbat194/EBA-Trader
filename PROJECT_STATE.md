# EBA Trader — Project State

_Last reconciled: 2026-08-26 (Asia/Ulaanbaatar)_
_Verified through GitHub `main` PR #35 merge `178611f535e95d61747a726b73cf7346f94358e4`; PR #36 encrypted Binance Demo credential persistence is implemented and under final validation._

This is the primary cross-chat continuation summary. Actual current implementation/config/tests and Git history override stale text.

## Current goal

Operate EBA Trader as a restart-safe 24/7 Linode paper/research system, build a controlled AI Strategy Factory on top of the M4 evidence platform, test whether order-flow/footprint features add incremental edge over candle-only baselines, expose research/runtime progress in the phone-first PWA, and keep real-money execution locked until a separate evidence chain proves it.

## Current stage

- Research platform: **M4 COMPLETE**.
- AI Strategy Factory: **M5 IN PROGRESS**.
- Continuity system: **INSTALLED / ENFORCED IN CI**.
- Deterministic order-flow ablation orchestration: **MERGED in #34**.
- Venue-matched real USD-M development feature-dataset workflow: **MERGED in #35**.
- Encrypted one-time Binance Demo credential persistence: **IMPLEMENTED in PR #36 pending final CI/merge**.
- Next research frontier: build a real BTCUSDT USD-M development dataset on Linode outside frozen OOS, then execute the deterministic candle-only vs delta/CVD ablation batch through M4.
- Real-money execution: **LOCKED**.
- Frozen OOS automation: **LOCKED pending lifecycle-order reconciliation**.

## Source of truth and active infrastructure

- Repository: `enkhbat194/EBA-Trader`
- Code source of truth: GitHub `main`
- Active runtime target: Akamai/Linode Nanode 1 GB, Singapore 2, Ubuntu 24.04 LTS
- Server repository path: `/opt/Eba-Trader`
- Persistent runtime DB: `/var/lib/eba-trader/eba_trader.db`
- Market-data service: `eba-binance-data.service`
- Runtime API service: `eba-runtime-api.service` on `127.0.0.1:8765`
- PWA/web service: `eba-web.service` on `127.0.0.1:8000` behind nginx/Let's Encrypt HTTPS
- Public PWA verified on 2026-08-26: `https://eba-trader-172-236-150-62.sslip.io/`
- Auto deploy: `eba-auto-update.timer`; exact `origin/main`, dirty-checkout refusal, service/API health checks and rollback are implemented in `scripts/update_linode_runtime.sh`
- Replit/Render: deprecated EBA Trader backend/runtime paths

## Completed research milestones

### M4 — complete

Merged PRs #20-#24 provide immutable strategy versions, deterministic experiment IDs, restart-safe queue/leases, allowlisted workers, content-addressed evidence, declarative gates and bounded robustness evidence. Generic workers do not unlock frozen OOS or execution.

### M5 — completed foundation so far

- #25 order-flow/footprint research foundation.
- #26 constrained strategy DSL, approved feature registry, bounded deterministic parameter expansion and M4 candidate emission.
- #27 strategy-family templates, near-duplicate guard, cheap screening and deterministic survivor ranking.
- #28 historical Binance aggregate-trade normalization/cache, sequence/integrity gate and deterministic footprint windows.
- #30 venue-aware historical aggregate-trade acquisition, request/range provenance, missing-ID repair and causal closed-footprint/candle alignment.
- #31 causal feature-dataset materialization plus allowlisted candle-only/order-flow backtest adapters on the exact same aligned feature CSV.
- #32 phone-first Research / AI Lab PWA dashboard.
- #33 carry-label clarification and Fast Momentum heartbeat observability.
- #34 deterministic one-control-to-many-treatment order-flow ablation orchestration.
- #35 venue-aware USD-M candle acquisition plus one-command verified candle+order-flow feature-dataset workflow, merge `178611f535e95d61747a726b73cf7346f94358e4`.

Enabled order-flow features: executed buy/sell volume, delta, delta ratio, CVD and POC price. Stacked imbalance, absorption, exhaustion and LOB depth imbalance remain disabled/unimplemented.

## Current implementation reality

### M5 Strategy Factory and ablation

`M5OrderFlowAblationOrchestrator` emits one deduplicated `ema_feature_baseline_v1` control and bounded deterministic `ema_orderflow_v1` treatments. All arms share dataset identity, symbol/time window, EMA parameters, initial capital, fees, slippage and trade-start semantics; only allowlisted delta/CVD thresholds differ. Fan-out is capped at 64 and the stage is fixed to development only.

### Real USD-M feature dataset workflow

PR #35 prevents Spot/Futures contamination end to end:

- USD-M futures candles come from the futures kline endpoint with request provenance and exact interval coverage;
- USD-M `aggTrades` cover one prior footprint window plus the development candle range;
- aggregate-trade gaps are repaired and unresolved integrity errors fail closed;
- candle/order-flow manifests are content-linked and hash verified;
- closed footprint `[t-step,t)` becomes available to the candle opening at `t`;
- `eba-build-orderflow-features` writes immutable feature/workflow manifests plus an M4-safe relative `dataset_ref`;
- the existing frozen-OOS guard remains authoritative.

### Encrypted Binance Demo credential persistence

PR #36 adds one-time credential storage without weakening the existing security model:

- the PWA sends a Binance **Demo** API key/secret only when the user explicitly saves/replaces it;
- the backend validates the Demo credential before writing anything;
- successful credentials are encrypted at rest using Fernet authenticated encryption;
- master key: `/etc/eba-trader/demo-credential.key` with mode `0600`;
- encrypted credential blob: `/var/lib/eba-trader/credentials/binance-demo.fernet` with mode `0600`;
- install and auto-update provision the master key once and never rotate it implicitly;
- browser status receives only configured/masked metadata; the saved secret is never returned;
- browser `localStorage`/`sessionStorage` are not used for credentials;
- future app opens/server restarts may auto-connect using the encrypted server credential;
- explicit Replace and Delete controls exist; deleting the key still leaves public-data Fast Paper available;
- live/non-Binance credentials are rejected and real execution remains locked.

Release target for PR #36 is `0.12.2 / LINODE-M7`, PWA cache `eba-trader-ui-v15`.

## Runtime / PWA

- Fast Momentum runs server-side every ~15 seconds and remains paper-only.
- `TradeLedger` runtime persistence is separate from M4/M5 research state.
- Fast Momentum supports persistent OPEN/MARK/CLOSE state/history.
- Research / AI Lab and scanner heartbeat are read-only observability.
- The PWA consumes server truth rather than browser memory.

## Production proof — manual evidence on 2026-08-26

Confirmed:

- external iPhone access to the public HTTPS PWA succeeded;
- Home, Scan and Settings displayed server-backed state;
- History displayed persisted Fast Paper trades with entry/exit, fees and exit reasons;
- Fast Paper trade detail displayed execution facts, strategy evidence and trade chart.

Still unproven:

- standalone Chart / Positions / Research screen smoke against server truth;
- PR #36 real-Linode encrypted-save + subsequent no-paste auto-connect after deployment;
- active Fast Momentum paper position surviving a service/server restart and later MARK/CLOSE;
- final disposition of the older carry paper engine.

## Known architecture issue

Current lifecycle path is:

`GENERATED -> BACKTESTED -> OOS_VERIFIED -> ROBUSTNESS_VERIFIED -> PAPER_CANDIDATE -> ...`

Desired methodology conceptually wants robustness before opening frozen OOS. Do not bypass the machine lifecycle; redesign/migrate/test it before automated frozen-OOS orchestration.

## Immediate Next

1. Final-CI and squash-merge PR #36.
2. Add a deterministic CLI/workflow that consumes a PR #35 feature `dataset_ref`, emits a PR #34 ablation batch into the M4 research store/queue and reports machine-readable experiment IDs.
3. Build a real BTCUSDT USD-M development dataset on Linode outside frozen OOS.
4. Run the deterministic ablation batch through M4 queue/worker/evidence/gates.
5. Persist/rank survivors only for triage; do not open frozen OOS from ranking results.
6. Verify one-time encrypted Demo save/no-paste auto-connect and finish remaining production smoke/restart-recovery proof in parallel.

## Important constraints

- No API secrets in Git or browser persistent storage; withdrawal permission is never required.
- Only Binance Demo credentials may use the encrypted credential vault in this milestone.
- Deterministic risk has veto authority.
- Runtime state must survive Git pulls, browser refreshes and process/server restarts.
- Strategy versions/evidence are immutable.
- AI strategy generation does not execute arbitrary generated Python.
- Order-flow executed trades and resting LOB liquidity are separate data domains.
- Order-flow dataset gaps fail closed.
- Spot and USD-M futures data are separate experiment datasets and must not be silently mixed.
- Same-candle still-forming footprint data cannot be used in candle decisions.
- A development win-rate increase is not promotion evidence.
- Generic research workers and ablation orchestration cannot open frozen OOS or real execution.

## Validation status

- PRs #29-#35 passed full regression/Ruff/deployment/runtime/continuity gates before merge.
- PR #36 core head passed full regression, Ruff, Linode runtime checks, Linode production bundle and Continuity guard after stale contract-test and lint-only findings were corrected.
- PR #36 continuity-updated final head must pass the same gates before merge.
- External HTTPS/latest-main proof is manually established; active-position restart-recovery proof remains open.

## Continuity system

Canonical continuity files are `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, `SESSION_HANDOFF.md`, and `docs/CONTINUITY_PROTOCOL.md`. Every meaningful AI/coding session must update them when state changes.
