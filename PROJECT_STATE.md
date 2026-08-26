# EBA Trader — Project State

_Last reconciled: 2026-08-27 (Asia/Ulaanbaatar)_
_Verified through GitHub `main` PR #38 merge `2ef162bf975b8a1ace1adb86af269976d3c7c578` plus manual Linode production evidence on 2026-08-27._

This is the primary cross-chat continuation summary. Actual current implementation/config/tests and Git history override stale text.

## Current goal

Operate EBA Trader as a restart-safe 24/7 Linode paper/research system, build a controlled AI Strategy Factory on top of the M4 evidence platform, test whether order-flow/footprint features add incremental edge over candle-only baselines, expose research/runtime progress in the phone-first PWA, and keep real-money execution locked until a separate evidence chain proves it.

## Current stage

- Research platform: **M4 COMPLETE**.
- AI Strategy Factory: **M5 IN PROGRESS**.
- Continuity system: **INSTALLED / ENFORCED IN CI**.
- Deterministic order-flow ablation orchestration: **MERGED in #34**.
- Venue-matched real USD-M development feature-dataset workflow: **MERGED in #35**.
- Encrypted one-time Binance Demo credential persistence: **MERGED in #36**.
- Linode auto-update recovery/diagnostics: **MERGED in #37 and production-verified**.
- Binance market-data log-flood fix: **MERGED in #38 and production-verified**.
- Current research frontier: persistent Linode research paths + deterministic real-ablation queue CLI, then build a BTCUSDT USD-M development dataset outside frozen OOS and run candle-only vs Delta/CVD experiments through M4.
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
- Public PWA: `https://eba-trader-172-236-150-62.sslip.io/`
- Auto deploy: `eba-auto-update.timer`; exact `origin/main`, dirty-checkout refusal, health checks, rollback and persistent deploy diagnostics are implemented.
- Recovery helper: `scripts/repair_linode_auto_update.sh`; it refuses destructive repair on a dirty runtime checkout.
- Replit/Render: deprecated EBA Trader backend/runtime paths.

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
- #36 encrypted one-time Binance Demo credential vault and no-paste auto-connect path, merge `06248eb9c901b44ca0a91ccd96bd15d23e156c9a`.

Enabled order-flow features: executed buy/sell volume, delta, delta ratio, CVD and POC price. Stacked imbalance, absorption, exhaustion and LOB depth imbalance remain disabled/unimplemented.

## Current implementation reality

### M5 Strategy Factory and ablation

`M5OrderFlowAblationOrchestrator` emits one deduplicated `ema_feature_baseline_v1` control and bounded deterministic `ema_orderflow_v1` treatments. All arms share dataset identity, symbol/time window, EMA parameters, initial capital, fees, slippage and trade-start semantics; only allowlisted delta/CVD thresholds differ. Fan-out is capped at 64 and the stage is fixed to development only.

### Real USD-M feature dataset workflow

PR #35 prevents Spot/Futures contamination end to end:

- USD-M futures candles use futures endpoints with request provenance and exact interval coverage;
- USD-M `aggTrades` include one prior footprint window plus the development candle range;
- aggregate-trade gaps are repaired and unresolved integrity errors fail closed;
- candle/order-flow manifests are content-linked and hash verified;
- closed footprint `[t-step,t)` becomes available to the candle opening at `t`;
- `eba-build-orderflow-features` writes immutable feature/workflow manifests plus an M4-safe relative `dataset_ref`;
- frozen OOS remains locked.

### Encrypted Binance Demo credential persistence

PR #36 adds one-time credential storage without browser secret persistence:

- only Binance Demo credentials are accepted;
- credentials are validated before disk write;
- successful credentials are encrypted at rest using Fernet authenticated encryption;
- master key: `/etc/eba-trader/demo-credential.key` mode `0600`;
- encrypted blob: `/var/lib/eba-trader/credentials/binance-demo.fernet` mode `0600`;
- install/auto-update provision the master key once and never rotate it implicitly;
- browser receives configured/masked metadata only; the saved secret is never returned;
- browser `localStorage`/`sessionStorage` are not used for credentials;
- Replace/Delete controls exist; public-data Fast Paper remains available without credentials;
- real execution remains locked.

Credential-vault release is `0.12.2 / LINODE-M7`, PWA cache `eba-trader-ui-v15`.

## Runtime / PWA

- Fast Momentum runs server-side every ~15 seconds and remains paper-only.
- `TradeLedger` runtime persistence is separate from M4/M5 research state.
- Fast Momentum supports persistent OPEN/MARK/CLOSE state/history.
- Research / AI Lab and scanner heartbeat are read-only observability.
- The PWA consumes server truth rather than browser memory.

## Production operations proof — 2026-08-26/27

Confirmed manually from the external iPhone/Linode console:

- external public HTTPS PWA access succeeded;
- Home / Scan / Settings displayed server-backed state;
- History displayed persisted Fast Paper trades with entry/exit, fees and exit reasons;
- Fast Paper trade detail displayed execution facts, strategy evidence and chart annotations;
- PR #37 recovery advanced a stuck Linode from build `050cd9b` to current main and restored `eba-auto-update.timer` to active/waiting;
- PR #38 build `2ef162bf975b8a1ace1adb86af269976d3c7c578` deployed successfully;
- `eba-binance-data.service` is active after PR #38 while `journalctl` after the deployment window shows no per-tick `QuoteTick`/`TradeTick` flood;
- root cause of disk growth was diagnostic logging, not research/trade data: `/var/log/syslog` reached about 15 GB and journald about 2.5 GB;
- old logs were reclaimed manually; disk usage fell from about 90.1% to 21% (`4.8G` used, `19G` available), and `/var/log` fell to about `162M`;
- production journald currently has a manually-installed `SystemMaxUse=250M`, `SystemKeepFree=1G`, `MaxRetentionSec=7day` drop-in.

Still unproven / not yet fully codified:

- the journald retention drop-in is **production-local manual state** and still needs repo provisioning so rebuilds/new servers inherit it automatically;
- standalone Chart / Positions / Research screen smoke against server truth;
- one real encrypted Demo credential save followed by no-paste auto-connect on production;
- active Fast Momentum paper position surviving a service/server restart and later MARK/CLOSE;
- final disposition of the older carry paper engine.

## Operational fixes after M5 foundation

### PR #37 — auto-update recovery

Merged `9b265a4a880c380d66943e3964586be12ebfb9da`:

- fail-closed one-command repair helper;
- persistent deployment diagnostics under `/var/lib/eba-trader/deploy-state`;
- hardened timer activation;
- no web/PWA endpoint receives systemd/deploy authority.

### PR #38 — Binance data log flood

Merged `2ef162bf975b8a1ace1adb86af269976d3c7c578`:

- `DataTesterConfig(log_data=False)` disables raw per-tick INFO logging while quote/trade/bar subscriptions remain active;
- service-level systemd burst limiting provides defense in depth;
- regression tests prevent silent reintroduction of per-tick flood behavior;
- no execution path changed.

## Known architecture issue

Current lifecycle path is:

`GENERATED -> BACKTESTED -> OOS_VERIFIED -> ROBUSTNESS_VERIFIED -> PAPER_CANDIDATE -> ...`

Desired methodology conceptually wants robustness before opening frozen OOS. Do not bypass the machine lifecycle; redesign/migrate/test it before automated frozen-OOS orchestration.

## Immediate Next

1. Codify the current production journald retention/free-space guard in repository deployment/install tooling so it survives rebuilds.
2. Resume `m5-real-ablation-cli` from latest `main`: move long-running Linode research DB/data/evidence outside the Git checkout (target `/var/lib/eba-trader/research/...`) and add a deterministic feature-manifest/`dataset_ref` -> M4 ablation queue CLI.
3. Build a real BTCUSDT USD-M development dataset on Linode outside frozen OOS.
4. Run the deterministic candle-only vs Delta/CVD ablation batch through M4 queue/worker/evidence/gates.
5. Persist/rank survivors only for triage; do not open frozen OOS from ranking results.
6. Verify encrypted Demo save/no-paste auto-connect and finish remaining production smoke/restart-recovery proof in parallel.

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
- High-frequency raw market ticks must not be emitted as normal INFO service logs.

## Validation status

- PR #37 merged and its repair path was exercised successfully on the real Linode.
- PR #38 merged after regression/runtime/continuity validation and is production-verified by active data service + absence of per-tick flood after deployment.
- External HTTPS/latest-main proof is manually established.
- Disk/log recovery is manually established.
- Active-position restart-recovery proof remains open.

## Continuity system

Canonical continuity files are `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, `CHANGELOG.md`, `SESSION_HANDOFF.md`, and `docs/CONTINUITY_PROTOCOL.md`. Every meaningful AI/coding session must update them when state changes.
