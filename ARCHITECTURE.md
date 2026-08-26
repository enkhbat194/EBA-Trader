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
   |       `--> Binance / NautilusTrader market data
   |
   +--> Trading / risk / paper execution layer
   |       `--> TradeLedger (SQLite)
   |
   +--> eba-runtime-api.service
   |       `--> 127.0.0.1:8765
   |
   +--> eba-web.service
   |       `--> 127.0.0.1:8000
   |
   +--> eba-auto-update.timer/service
   |       `--> exact origin/main deployment + diagnostics
   |
   `--> nginx / Let's Encrypt public HTTPS PWA
```

GitHub `main` is the code source of truth. Linode is the sole active backend/runtime target. Replit and Render are deprecated backend paths.

`scripts/update_linode_runtime.sh` refuses dirty runtime checkouts, resets to exact `origin/main`, installs the package, updates systemd units, restarts services, checks local API health and rolls back on runtime deployment failure. HTTPS bootstrap retries independently so a transient DNS/CA problem does not roll back an otherwise healthy runtime.

PR #37 adds a fail-closed root-side recovery helper plus persistent deploy diagnostics under `/var/lib/eba-trader/deploy-state`. The PWA/web API does not receive systemd/deployment authority.

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
Strategy proposal
   |
   +--> LONG
   +--> SHORT
   +--> EXIT
   `--> NO_TRADE
   |
   v
Deterministic Risk Engine (veto authority)
   |
   v
Paper Execution
   |
   +--> OPEN
   +--> MARK / state update
   `--> CLOSE
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
Strategy specification
   |
   v
Immutable Strategy Version
   |
   v
Experiment Queue / Worker Lease
   |
   v
Immutable Evidence / Provenance
   |
   v
Development / Robustness Gates
   |
   +--> reject / quarantine / retest
   `--> eligible next lifecycle state
```

The M4 research SQLite store is separate from `TradeLedger`. Generic research workers cannot mutate runtime position state and cannot silently unlock frozen OOS or execution.

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
Development backtest evidence
   |
   v
Survivor ranking (triage only)
```

M5 does not accept arbitrary generated production Python as the normal strategy-generation contract.

Core modules include `m5_hypothesis.py`, `m5_features.py`, `m5_factory.py`, `m5_emitter.py`, `m5_family.py`, `m5_similarity.py`, `m5_selection.py`, and `m5_ablation.py`.

## 5. Order-flow / footprint data plane

Executed order flow is a separate research feature domain layered on top of raw market events:

```text
Binance aggregate trades
   |
   v
Strict normalization
   |
   +--> aggregate trade ID
   +--> timestamp
   +--> price / quantity
   `--> aggressor BUY/SELL from buyer-maker semantics
   |
   v
Integrity gate
   |
   +--> duplicate/conflict reject
   +--> backward-time reject
   +--> sequence-gap accounting
   `--> SHA-256/content-addressed cache
   |
   v
Fixed causal footprint windows [start,end)
   |
   +--> buy volume
   +--> sell volume
   +--> delta / delta ratio
   +--> CVD
   `--> POC
```

Unresolved sequence gaps are not backtest-ready. Resting order-book/LOB liquidity is not inferred from footprint; it requires a separate future snapshot/diff reconstruction pipeline with its own sequence-integrity contract.

Current enabled feature registry entries are `of_buy_volume`, `of_sell_volume`, `of_delta`, `of_delta_ratio`, `of_cvd`, and `of_poc_price`. Stacked imbalance, absorption, exhaustion and LOB depth imbalance remain disabled until implemented and validated.

### Diagnostic logging is not a dataset

`eba-binance-data.service` keeps instrument/quote/trade/bar subscriptions active, but raw `QuoteTick`/`TradeTick` events are not written one-by-one as normal INFO diagnostics. PR #38 sets `DataTesterConfig(log_data=False)` and adds a service-level log burst cap.

Research data must come from explicit acquisition/materialization pipelines with provenance and integrity checks. Syslog/journald output is operational diagnostics and must never be treated as canonical order-flow research data.

## 6. Persistence boundaries

### Runtime persistence

Current durable single-node runtime store:

`/var/lib/eba-trader/eba_trader.db`

It owns paper/runtime trade state and must survive browser refreshes, process restarts, Git pulls and server restarts.

### Credential persistence

Binance Demo credentials use a separate encrypted server vault:

- master key: `/etc/eba-trader/demo-credential.key`;
- encrypted blob: `/var/lib/eba-trader/credentials/binance-demo.fernet`.

The saved secret is never returned to browser JavaScript and browser persistent storage is not used for API secrets.

### Research persistence

M4/M5 research metadata remains logically separate from `TradeLedger`.

- Local/development defaults may use `artifacts/research/...`.
- Before long-running real Linode ablations, production research DB/data/evidence must move outside the Git checkout under a persistent namespace such as `/var/lib/eba-trader/research/...`.
- Research artifacts must not dirty `/opt/Eba-Trader`, because the fail-closed auto-deployer refuses dirty checkouts.

This production research-path migration is the current pending M5 implementation task.

### Evidence

Strategy specs/evidence are immutable by version/content hash. Changed specifications require a new version/evidence chain.

## 7. Strategy lifecycle and open architecture issue

Current machine promotion path in `src/eba_trader/lifecycle.py` is:

```text
GENERATED
 -> BACKTESTED
 -> OOS_VERIFIED
 -> ROBUSTNESS_VERIFIED
 -> PAPER_CANDIDATE
 -> PAPER_VERIFIED
 -> DEMO_CANDIDATE
 -> DEMO_VERIFIED
 -> SHADOW_VERIFIED
 -> MICRO_LIVE_ELIGIBLE
 -> LIVE_ELIGIBLE
 -> LIVE_ACTIVE
```

The desired research methodology conceptually wants robustness before opening frozen OOS. This is an acknowledged mismatch. Current code remains authoritative until a deliberate migration changes lifecycle policy and tests. Manual bypass is prohibited.

## 8. PWA / API boundary

The PWA is presentation/control UI, not the trading engine. It reads server truth for position, history, TP/SL, leverage, indicators, fees, P&L, research status and trade-specific chart data.

Canonical services:

- `eba-runtime-api.service` -> local runtime API on `127.0.0.1:8765`;
- `eba-web.service` -> web/PWA service on `127.0.0.1:8000`;
- nginx/Let's Encrypt exposes the web service externally.

The PWA may save/replace/delete Binance Demo credentials through the constrained encrypted-vault API, but it does not receive the saved secret back and has no systemd/deployment, OOS-promotion or real-execution authority.

External phone/browser verification remains a production-proof requirement distinct from repository CI.

## 9. Continuity architecture

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
work
   |
   v
update code + continuity state
   |
   v
Git commit / PR
   |
   v
next chat / agent
```

`AGENTS.md` defines the mandatory session protocol. `scripts/check_continuity.py` and `.github/workflows/continuity.yml` protect the required continuity surface. Actual code/tests/Git history override stale prose, and stale continuity must be repaired before a new session relies on it.

## 10. Deployment and log-retention rules

- Canonical install: `scripts/install_linode_runtime.sh`.
- Canonical update: `scripts/update_linode_runtime.sh`.
- Canonical stuck-update recovery: `scripts/repair_linode_auto_update.sh`.
- Canonical systemd units: `deploy/systemd/`.
- Do not create new Replit/Render runtime paths.
- Do not use browser memory as durable trade state.
- Do not couple research experiment metadata to runtime position persistence.
- Do not make DNS/CA availability a reason to roll back a locally healthy runtime deployment.
- High-frequency market events must not be emitted as normal INFO service logs.
- Production journald must have bounded retention/free-space protection. The current real server has a manually-applied `SystemMaxUse=250M`, `SystemKeepFree=1G`, `MaxRetentionSec=7day` drop-in; repository provisioning of this policy is still pending and is an explicit next task.

## 11. Safety invariants

1. API keys/secrets are never committed to Git.
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

## 12. Validation direction

Current intended methodology is:

```text
Hypothesis
 -> cheap/static screen
 -> development backtest + costs
 -> robustness / walk-forward / perturbation
 -> frozen OOS (after lifecycle order is reconciled)
 -> forward paper
 -> restart/recovery proof
 -> exchange Demo
 -> shadow
 -> explicit micro-live eligibility
```

A profitable-looking backtest or higher development win rate alone is not a production promotion criterion.
