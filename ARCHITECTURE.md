# EBA Trader Architecture

## 1. System goal

EBA Trader is a research-first autonomous trading system with deterministic risk control and a persistent 24/7 Linux runtime. The browser/PWA is a client; market-data state, paper positions, trade history, research evidence and safety authority live server-side.

The system has three deliberately separated planes:

1. **Runtime plane** — market data, paper decisions, risk, positions and trade history.
2. **Research control plane** — immutable strategy versions, experiments, evidence, gates and M5 strategy-factory candidates.
3. **Continuity/control-document plane** — repository state that lets new ChatGPT branches/AI sessions recover and continue the project without relying on chat memory.

## 2. Active deployment boundary

```text
GitHub main
   |
   v
Akamai/Linode — Ubuntu 24.04 LTS
   |
   +--> eba-binance-data.service
   |       `--> Binance / NautilusTrader public market data
   |
   +--> Trading / risk / paper execution layer
   |       `--> /var/lib/eba-trader/eba_trader.db (TradeLedger)
   |
   +--> eba-runtime-api.service
   |       `--> 127.0.0.1:8765
   |
   +--> eba-web.service
   |       `--> 127.0.0.1:8000
   |
   +--> eba-research-worker.timer
   |       `--> bounded M4 worker
   |            +--> /var/lib/eba-trader/research/eba_research.db
   |            +--> /var/lib/eba-trader/research/datasets
   |            `--> /var/lib/eba-trader/research/evidence
   |
   +--> eba-m5-real-ablation.timer
   |       `--> bounded development-only fixed-window M5 proof
   |
   +--> eba-auto-update.timer/service
   |       `--> exact origin/main deployment + diagnostics
   |
   `--> nginx / Let's Encrypt public HTTPS PWA
```

GitHub `main` is the code source of truth. Linode is the sole active backend/runtime target. Replit and Render are deprecated backend paths.

`scripts/update_linode_runtime.sh` refuses dirty runtime checkouts, resets to exact `origin/main`, installs the package, updates systemd units, restarts services, checks local API health and rolls back on runtime deployment failure. HTTPS bootstrap retries independently so transient DNS/CA failure does not roll back an otherwise healthy runtime.

PR #37 adds fail-closed root-side recovery plus persistent deploy diagnostics under `/var/lib/eba-trader/deploy-state`. The PWA/web API has no systemd/deployment authority.

## 3. Runtime data flow

```text
Binance market data
   |
   v
Data Engine
   |
   +--> freshness / normalized market state
   +--> indicators / feature state
   +--> regime / setup classification
   |
   v
Strategy proposal: LONG / SHORT / EXIT / NO_TRADE
   |
   v
Deterministic Risk Engine (veto authority)
   |
   v
Paper Execution: OPEN / MARK / CLOSE
   |
   v
SQLite TradeLedger
   |
   v
Runtime API -> PWA positions / history / trade detail
```

Browser RAM is never the authoritative position store.

## 4. Research control plane

### M4 foundation

```text
Immutable Strategy Version
   |
   v
Experiment Queue / Worker Lease
   |
   v
Allowlisted Backtest Adapter
   |
   v
Immutable Evidence / Provenance
   |
   v
Development / Robustness Gates
```

The research store is separate from `TradeLedger`. Generic research workers cannot mutate runtime positions and cannot silently unlock frozen OOS or execution.

### Persistent Linode research runtime

PR #40 implements the production research persistence boundary:

- DB: `/var/lib/eba-trader/research/eba_research.db`
- datasets: `/var/lib/eba-trader/research/datasets`
- immutable evidence: `/var/lib/eba-trader/research/evidence`

These paths are outside `/opt/Eba-Trader`, so long-running research cannot dirty the Git checkout and block fail-closed deployment. Existing `/etc/eba-trader/eba-trader.env` files are upgraded idempotently with research defaults without overwriting explicit operator values.

The systemd research worker is oneshot and bounded: at most eight jobs per invocation, 50% CPU quota, 512 MB memory cap, and filesystem write access limited to the research namespace. The timer runs approximately once per minute and only consumes already queued work.

The fixed-window M5 autorun is also development-only and resource-bounded. It writes only under the research namespace, cannot open frozen OOS and has no exchange-order authority.

### M5 AI Strategy Factory

```text
AI / template hypothesis
   |
   v
Constrained Strategy DSL
   |
   +--> approved feature registry
   +--> bounded parameter family
   +--> duplicate / near-duplicate guard
   +--> cheap static screen
   |
   v
Deterministic candidate IDs
   |
   v
M4 immutable strategy version + experiment queue
   |
   v
Development evidence
   |
   v
Survivor ranking (triage only)
```

M5 does not accept arbitrary generated production Python as the normal strategy-generation contract.

## 5. Order-flow / footprint data plane

Executed order flow is derived from raw Binance aggregate trades, not chart pixels or diagnostic logs:

```text
Binance USD-M aggregate trades
   |
   v
Strict normalization + venue provenance
   |
   +--> trade ID / timestamp / price / quantity
   `--> aggressor BUY/SELL
   |
   v
Integrity gate
   |
   +--> duplicate/conflict reject
   +--> backward-time reject
   +--> missing-ID repair / unresolved-gap reject
   `--> content hashes
   |
   v
Causal fixed footprint windows [start,end)
   |
   +--> buy/sell volume
   +--> delta / delta ratio
   +--> CVD
   +--> POC
   +--> diagonal buy/sell imbalance
   +--> consecutive stacked imbalance + signed score
   +--> absorption response proxy
   `--> exhaustion response proxy
```

Closed footprint `[t-step,t)` may be used by the candle opening at `t`; the still-forming footprint `[t,t+step)` cannot be used in that same candle decision.

### Versioned feature datasets

The feature dataset evolves only through explicit schema versions and fail-closed compatibility rules:

- **v1** — Delta/CVD-era causal footprint fields.
- **v2** — adds deterministic diagonal/stacked imbalance fields while preserving legacy v1 replay.
- **v3** — adds causal absorption/exhaustion response-proxy fields.

If a research gate requires a v2/v3 physical column, a legacy dataset without that column is rejected. The adapter must not silently inject zero and claim the feature was evaluated.

Current enabled executed-trade registry includes the earlier volume/Delta/CVD/POC family plus the implemented stacked/diagonal and absorption/exhaustion research fields. These are experimental research features, not validated alpha.

Absorption/exhaustion are explicitly **executed-flow response proxies**. They do not prove that passive institutional liquidity, iceberg intent, hidden orders or OTC flow was observed. Resting order-book/LOB liquidity remains a separate future sequence-sensitive data plane.

### Diagnostic logging is not a dataset

`eba-binance-data.service` keeps quote/trade/bar subscriptions active but does not emit every `QuoteTick`/`TradeTick` as INFO. PR #38 disables per-tick `DataTester` logging and adds a service burst cap. Canonical research data comes only from explicit acquisition/materialization pipelines with provenance and integrity checks.

## 6. Real M5 ablation execution path

The controlled production research path is:

```text
Explicit development-only UTC window
   |
   v
eba-build-orderflow-features
   |  verifies venue/range/gaps/provenance/causal alignment
   v
immutable workflow + versioned feature CSV/manifest
   |
   v
eba-m5-real-ablation
   |  verifies schema, USD-M venue, symbol/range,
   |  path containment, SHA-256, feature manifest,
   |  and frozen first-cycle OOS non-overlap
   v
one deterministic candle-only control
   + bounded allowlisted order-flow treatments
   |
   v
M4 queue -> bounded worker -> immutable evidence
   |
   v
sanitized comparison report -> exact external production proof
```

`scripts/run_m5_real_ablation.sh` composes the build, queue and exact emitted job count into one root-side command with a process lock.

The one-shot production wrapper pins the development window and an explicit versioned gate set, uses a candidate-specific immutable report path, and records a sanitized marker. External proof requires the expected candidate/gate family so stale evidence from an earlier candidate cannot satisfy a later milestone.

Completed fixed-window development candidate families now include:

- Delta/CVD;
- stacked/diagonal imbalance;
- absorption/exhaustion response proxies.

All use the same BTCUSDT USD-M development window and same baseline/execution assumptions for comparability. These outputs are experiment policies/evidence only; they do not define lifecycle-promotion thresholds.

This path is fixed to `m5_orderflow_ablation_dev`; it has no OOS, lifecycle-promotion, Binance Demo-order or real-order authority.

## 7. Persistence boundaries

### Runtime persistence

`/var/lib/eba-trader/eba_trader.db` owns paper/runtime trade state and must survive browser refreshes, process restarts, Git pulls and server restarts.

### Research persistence

`/var/lib/eba-trader/research/...` owns research strategies, experiments, datasets and evidence on Linode. Local development may still use `artifacts/research/...`, but production research must not write durable state into the Git checkout.

### Credential persistence

Binance Demo credentials use a separate encrypted server vault:

- master key: `/etc/eba-trader/demo-credential.key`
- encrypted blob: `/var/lib/eba-trader/credentials/binance-demo.fernet`

The saved secret is never returned to browser JavaScript and browser persistent storage is not used for API secrets.

### Evidence

Strategy specs/evidence are immutable by version/content hash. Changed specifications require a new version/evidence chain. Candidate-specific Linode comparison reports are preserved rather than overwritten by later candidate families.

## 8. Strategy lifecycle policy v2

Current research promotion policy is versioned. New/current work uses policy v2:

```text
GENERATED
 -> BACKTESTED
 -> ROBUSTNESS_VERIFIED
 -> OOS_VERIFIED
 -> PAPER_CANDIDATE
 -> PAPER_VERIFIED
 -> DEMO_CANDIDATE
 -> DEMO_VERIFIED
 -> SHADOW_VERIFIED
 -> MICRO_LIVE_ELIGIBLE
 -> LIVE_ELIGIBLE
 -> LIVE_ACTIVE
```

### Robustness-before-OOS authority

- `BACKTESTED -> OOS_VERIFIED` is invalid under policy v2.
- Robustness fan-out requires policy v2 and exact `BACKTESTED` state.
- A passing immutable robustness verdict may promote only to `ROBUSTNESS_VERIFIED`.
- `OOS_VERIFIED` requires a separate later evidence-bearing transition from `ROBUSTNESS_VERIFIED`.
- The generic research worker, PWA and ablation orchestrator still have no OOS-unlock authority.

### Legacy SQLite migration

Historical M4 databases used policy v1, whose order was `BACKTESTED -> OOS_VERIFIED -> ROBUSTNESS_VERIFIED`. Persisted state cannot be reinterpreted by changing enum order alone.

Policy-v2 migration therefore records `lifecycle_policy_version`:

- legacy `GENERATED`, `BACKTESTED` and `RETEST_REQUIRED` rows may adopt v2 safely because they have not already consumed frozen OOS under the old methodology;
- legacy rows at `OOS_VERIFIED` or later remain policy v1 and promotion-frozen;
- a legacy post-OOS row must move to `RETEST_REQUIRED`, explicitly upgrade to v2, return to `BACKTESTED` on fresh development evidence, then pass fresh robustness before OOS can be opened again;
- lifecycle history records the policy version so historical evidence keeps its original semantics.

Manual state skipping remains prohibited.

## 9. PWA / API boundary

The PWA is presentation/control UI, not the trading engine. It reads server truth for positions, history, trade detail and research status.

The PWA may save/replace/delete Binance Demo credentials through the constrained encrypted-vault API, but it does not receive the saved secret back and has no deployment, OOS-promotion or real-execution authority.

External phone/browser verification remains a production-proof requirement distinct from repository CI.

## 10. Continuity architecture

```text
ChatGPT branch / AI agent
   |
   v
AGENTS.md
   |
   v
PROJECT_STATE + ARCHITECTURE + DECISIONS + TODO + HANDOFF
   |
   v
actual code / tests / Git history
   |
   v
work -> validation -> continuity update -> PR/merge
   |
   v
next chat / agent
```

Actual code/tests/Git history override stale prose, and stale continuity must be repaired before a new session relies on it.

## 11. Deployment and host-protection rules

- Canonical install: `scripts/install_linode_runtime.sh`.
- Canonical update: `scripts/update_linode_runtime.sh`.
- Canonical stuck-update recovery: `scripts/repair_linode_auto_update.sh`.
- Canonical systemd units: `deploy/systemd/`.
- Do not create new Replit/Render runtime paths.
- Do not use browser memory as durable trade state.
- Do not couple research experiment metadata to runtime position persistence.
- Do not make DNS/CA availability a reason to roll back a locally healthy runtime deployment.
- High-frequency market events must not be emitted as normal INFO service logs.
- Production journald policy is versioned under `deploy/journald/eba-trader.conf`: `SystemMaxUse=250M`, `SystemKeepFree=1G`, `MaxRetentionSec=7day`.
- The journald resource cap is a host-safety invariant and intentionally is not removed by application rollback.

## 12. Safety invariants

1. API keys/secrets are never committed to Git or pasted into chat.
2. Withdrawal permission is never required.
3. Stale/malformed market data blocks unsafe new decisions.
4. Deterministic risk controls have veto authority.
5. Every simulated/future executed trade must be auditable and persistent.
6. Real order submission remains disabled until separately implemented, tested and promoted.
7. Strategy lifecycle evidence cannot bypass deterministic risk authority.
8. Strategy specs/evidence are immutable; changed specs require a new version.
9. Generic workers cannot silently open frozen OOS.
10. AI-generated hypotheses must pass the constrained M5 validation surface.
11. Order-flow data with unresolved integrity gaps fails closed.
12. Development ranking is not promotion authority.
13. Browser/PWA code has no systemd deployment authority.
14. Raw diagnostic logs are not canonical research datasets.
15. Runtime trade state, research state and encrypted credential state remain separate persistence domains.
16. The real-ablation CLI accepts only contained, hash-verified development datasets and cannot open frozen OOS.
17. Persisted lifecycle states are interpreted only under their recorded lifecycle-policy version.
18. Policy v2 requires passing robustness evidence before frozen OOS can become eligible.
19. Missing versioned order-flow feature columns fail closed; legacy datasets cannot silently simulate newer features with zero values.
20. Zero-trade development arms are not treated as profitable edge simply because return and drawdown are zero.
21. Executed-flow response proxies are not represented as direct observation of resting/hidden order-book liquidity.

## 13. Validation direction

```text
Hypothesis
 -> cheap/static screen
 -> development backtest + costs
 -> robustness / walk-forward / perturbation
 -> ROBUSTNESS_VERIFIED
 -> frozen OOS
 -> OOS_VERIFIED
 -> forward paper
 -> restart/recovery proof
 -> exchange Demo
 -> shadow
 -> explicit micro-live eligibility
```

A profitable-looking backtest, a higher development win rate, or a zero-trade loss-avoidance arm alone is not a production promotion criterion.
