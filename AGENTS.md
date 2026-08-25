# AGENTS.md

## Repository continuity contract

This repository is the authoritative shared memory for EBA Trader. A ChatGPT branch, new chat, Codex session, IDE agent, or other AI session must recover state from the repository before changing the project.

Chat memory is advisory. Current code/configuration, Git history, and the continuity files below are authoritative when they disagree with chat history.

## Mandatory start-of-session protocol

Before coding or changing architecture, read in this order:

1. `AGENTS.md`
2. `PROJECT_STATE.md`
3. `ARCHITECTURE.md`
4. `DECISIONS.md`
5. `TODO.md`
6. `SESSION_HANDOFF.md`
7. `CHANGELOG.md` when recent user-visible/research-platform changes matter
8. relevant canonical docs under `docs/`, especially the current milestone documents

Then inspect repository reality:

- current branch / HEAD and recent commits;
- changed files or dirty working tree when a local checkout is available;
- the actual modules, tests, workflows and deployment scripts relevant to the requested task;
- open PR/CI state when work is being continued from a branch.

If a continuity document is stale, correct it from code/Git evidence before relying on it. Do not restart the project from chat summaries.

## EBA Trader source-of-truth hierarchy

Use this precedence when facts conflict:

1. current implementation, configuration and tests in Git;
2. current Git history / merged PR evidence;
3. `PROJECT_STATE.md` and `SESSION_HANDOFF.md`;
4. `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`;
5. older milestone/evidence documents;
6. chat memory.

Historical M1/M2/M3 documents are evidence records, not current runtime architecture.

## Mandatory work rules

- Keep real-money Binance order submission locked unless a separately validated milestone explicitly changes it.
- Deterministic risk retains veto authority.
- Never commit API secrets; withdrawal permission is never required.
- Keep runtime position persistence (`TradeLedger`) separate from research metadata/evidence persistence.
- Strategy versions and evidence are immutable; changed specifications require a new version/evidence chain.
- Generic research workers must not silently open frozen OOS or skip lifecycle gates.
- M5 AI strategy generation must emit constrained schema/DSL data, not arbitrary production Python.
- Order-flow/footprint features are research candidates derived from raw executed market events, not chart pixels; resting order-book data is a separate dataset.
- Incomplete/gapped historical order-flow data is not backtest-ready.
- Replit and Render are deprecated backend/runtime paths for EBA Trader; GitHub `main` + Linode is canonical.

## Mandatory end-of-session protocol

After meaningful work, before declaring the work finished:

1. run the relevant tests/lint/validation where possible;
2. update `PROJECT_STATE.md` with the real current milestone and validation status;
3. update `TODO.md` as tasks move between NOW/NEXT/BLOCKED/DONE;
4. append/update `DECISIONS.md` for meaningful architectural or research-policy decisions;
5. update `CHANGELOG.md` for meaningful platform/user-visible changes;
6. replace `SESSION_HANDOFF.md` with an exact continuation handoff;
7. verify continuity files against the code changed in the same branch;
8. commit and push / open a PR when the available workflow permits it.

A meaningful coding session is incomplete if code changed but the handoff/state was left stale.

## Handoff minimum

`SESSION_HANDOFF.md` must state:

- what completed;
- exact files/components changed;
- tests/CI results;
- what currently works;
- what is not proven or broken;
- blockers and risks;
- important decisions;
- the next exact task in executable order.

## Branch-chat rule

Sibling ChatGPT branches do not automatically exchange later messages. They synchronize through Git:

`Chat A -> repository -> Chat B -> repository -> Chat A`

Therefore every new branch/session must re-read repository state, even when it inherited older chat context.

## Continuity guard

Run `python scripts/check_continuity.py` after changing continuity files. CI also runs this guard. Do not replace real state with template placeholders merely to satisfy the guard.
