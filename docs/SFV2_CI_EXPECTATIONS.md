# Strategy Factory v2 — CI Expectations

The foundation branch must pass existing repository protections without weakening them.

Required before merge:

- full pytest regression;
- Ruff lint;
- runtime checks;
- continuity guard;
- repository hygiene;
- deployment-contract checks that apply to non-runtime research changes.

No CI fix may:

- relax Frozen OOS locks;
- enable real execution;
- change Demo into promotion authority;
- remove immutable trial/campaign checks;
- raise candidate caps silently;
- remove D0/D1/D2/D3 separation;
- weaken lifecycle policy v2.
