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
   `--> POC
```

Closed footprint `[t-step,t)` may be used by the candle opening at `t`; the still-forming footprint `[t,t+step)` cannot be used in that same candle decision.

Current enabled executed-trade feature registry entries are `of_buy_volume`, `of_sell_volume`, `of_delta`, `of_delta_ratio`, `of_cvd`, and `of_poc_price`. Stacked imbalance, absorption and exhaustion remain future candidates. Resting order-book/LOB liquidity is a different sequence-sensitive dataset and must not be inferred from footprint.

### Diagnostic logging is not a dataset

`eba-binance-data.service` keeps quote/trade/bar subscriptions active but does not emit every `QuoteTick`/`TradeTick` as INFO. PR #38 disables per-tick `DataTester` logging and adds a service burst cap. Canonical research data comes only from explicit acquisition/materialization pipelines with provenance and integrity checks.

## 6. Real M5 ablation execution path

PR #40 adds the controlled production research path:

```text
Explicit development-only UTC window
   |
   v
eba-build-orderflow-features
   |  verifies venue/range/gaps/provenance/causal alignment
   v
immutable PR #35 workflow + feature CSV/manifest
   |
   v
eba-m5-real-ablation
   |  verifies schema, USD-M venue, symbol/range,
   |  path containment, SHA-256, feature manifest,
   |  and frozen first-cycle OOS non-overlap
   v
PR #34 deterministic control + Delta/CVD treatments
   |
   v
M4 queue -> bounded worker -> immutable evidence
```

`scripts/run_m5_real_ablation.sh` composes the build, queue and exact emitted job count into one root-side command with a process lock.

The initial versioned gate set includes a permissive Delta-ratio arm as a sanity invariant plus bounded Delta/CVD hypotheses. It does not define promotion thresholds.

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

Strategy specs/evidence are immutable by version/content hash. Changed specifications require a new version/evidence chain.

## 8. Strategy lifecycle and open architecture issue

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

Accepted methodology wants robustness before opening frozen OOS. This mismatch is acknowledged and automated frozen OOS remains locked. A deliberate migration must change lifecycle semantics/storage/tests; manual bypass is prohibited.

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

## 13. Validation direction

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
