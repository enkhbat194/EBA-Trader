# EBA Trader — Chat Branch / AI Session Continuity Protocol

## Objective

Prevent context loss when a ChatGPT conversation is branched, a new chat starts, or another coding agent continues EBA Trader.

The repository is the persistent bridge:

```text
Chat / Agent A
      |
      v
Git repository (shared state)
      |
      v
Chat / Agent B
```

Sibling chats do not receive each other's later messages automatically.

## Start of every session

Read, in order:

1. `AGENTS.md`
2. `PROJECT_STATE.md`
3. `ARCHITECTURE.md`
4. `DECISIONS.md`
5. `TODO.md`
6. `SESSION_HANDOFF.md`
7. recent `CHANGELOG.md` entries if relevant

Then inspect current branch/HEAD, recent commits, open PR/CI state where applicable, and the implementation/tests/config for the requested task.

Do not begin from chat memory alone when repository access exists.

## During work

- Keep work scoped to a named milestone/branch.
- Update decisions when architecture or research authority changes.
- Move TODO items as their status changes.
- Record newly discovered blockers.
- Distinguish repository-CI proof from external production proof.
- Never turn experimental research output into execution authority implicitly.

## End of meaningful work

Before declaring completion:

1. save code/docs;
2. run relevant tests/lint/validation;
3. update `PROJECT_STATE.md`;
4. update `TODO.md`;
5. update `DECISIONS.md` if a meaningful decision changed;
6. update `CHANGELOG.md` when appropriate;
7. replace `SESSION_HANDOFF.md` with the exact current handoff;
8. run `python scripts/check_continuity.py`;
9. commit/push or open a PR when available.

## Conflict rule

When chat and repo disagree:

1. inspect actual implementation/config/tests;
2. inspect Git history;
3. repair stale continuity docs;
4. continue from repository reality.

## EBA-specific handoff requirements

Every handoff should explicitly state:

- current M4/M5 research milestone;
- whether frozen OOS is locked/open and why;
- runtime/execution safety state;
- current Linode production-proof status;
- current order-flow data integrity status if that work is involved;
- exact next implementation task.

## Bootstrap text for a new branch/chat

When a new session needs an explicit prompt, use:

> This is a continuation of EBA Trader. Do not start from scratch. Read `AGENTS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TODO.md`, and `SESSION_HANDOFF.md`, inspect recent Git history and relevant code, reconcile stale docs, then continue the highest-priority current task. After meaningful work, update state/TODO/decisions/handoff and commit or open a PR when possible.

## What this system can and cannot guarantee

This repository can make any connected coding/AI session independently recoverable and gives coding agents a durable instruction surface through `AGENTS.md`.

It cannot force an unrelated plain ChatGPT chat with no repository connection to fetch Git automatically. Such a chat must first be given/connected to the repository. Once repository access exists, the protocol above is mandatory for EBA Trader work.
