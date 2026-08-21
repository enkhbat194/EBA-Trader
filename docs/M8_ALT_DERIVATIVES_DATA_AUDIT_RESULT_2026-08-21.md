# M8 Alternative Derivatives Historical Data Audit — Final Result

Date: 2026-08-21
Branch: `m8-alt-derivatives-data-audit`
Frozen audit window: `2021-01-01T00:00:00Z` to `2025-01-01T00:00:00Z` exclusive
2025 OOS: **`LOCKED_NOT_ACCESSED`**

## Final decision

**`M8_ALT_DERIVATIVES_DATA_AUDIT_FAIL`**

This is a data-eligibility result only. M8 computed no forward returns, no PnL, no strategy, no AI
signal and no live execution evidence.

Authoritative complete GitHub Actions run: `32433740347`
Authoritative source commit: `02889240376c915a330492bc0ceaca49ace8952c`
Evidence artifact ID: `9430097001`
Evidence JSON SHA-256: `1bcfd0f44917d608b0d0c413d22aa7ce851e55ee4d54b1b81f87f588682a887f`
Uploaded artifact ZIP SHA-256: `9a6e94ff90ebe73c24bc38c36a90310c6e007075499499cf0a9ecfd75afc9ae8`

Preflight on the authoritative run passed the frozen-policy verification, the complete deterministic
pytest suite, and Ruff before historical source acquisition began.

## Primary source results

### Binance USD-M 5m metrics — FAIL

All `1461/1461` expected daily archives existed and all `1461` ZIP files passed their official
Binance Vision `.CHECKSUM` verification.

Observed evidence:

- accepted rows: `420,167`
- expected frozen five-minute slots: `420,767`
- coverage: `99.857403%`
- maximum missing run: `125` five-minute slots
- missing daily archive files: `0`
- exact duplicate timestamps collapsed under the frozen identical-row rule: `40,151`
- conflicting duplicate timestamps: `2`
- timestamps unique after deterministic normalization: yes
- timestamps strictly increasing after deterministic normalization: yes
- all timestamps five-minute aligned: **no**
- all frozen metric values finite and strictly positive: **no**
- normalized dataset SHA-256: `3d72009a881b381605b93822a5d2475bdff2a96bd8d3c486911f2d345d5e9b39`

Coverage and maximum-gap thresholds alone would have passed. The family nevertheless fails the frozen
contract because conflicting duplicates are forbidden, every accepted timestamp must be five-minute
aligned, and every frozen numeric metric must be finite and strictly positive.

During implementation validation the official archive exposed at least one blank metric field
(`sum_taker_long_short_vol_ratio`). The audit adapter converts malformed/non-finite/non-positive frozen
metric values to a deterministic zero sentinel only so the existing positivity gate can record a FAIL
instead of crashing before a complete report is produced. The value is not repaired, imputed or made
eligible for research.

### Bybit public primary families — ERROR / INCONCLUSIVE ON THIS RUNNER

The authoritative GitHub-hosted runner received HTTP 403 from the official public Bybit V5 endpoints:

- 1h kline: `ERROR`
- 1h open interest: `ERROR`
- 1h account ratio: `ERROR`
- funding history: `ERROR`

Endpoint parameter construction was separately regression-tested before the final run: kline uses
`start`/`end`, while the positioning endpoints use `startTime`/`endTime` as required by their public
interfaces. The 403 result therefore records transport/access failure in the GitHub-hosted execution
environment; it does **not** prove those historical datasets themselves are incomplete or invalid.
They cannot be promoted under M8 because the frozen audit did not obtain reproducible evidence.

### Cross-exchange hourly alignment — FAIL

- expected hourly slots: `35,064`
- aligned slots: `0`
- coverage: `0%`

This result follows from the unavailable Bybit primary series in the authoritative environment. It is
not a separate predictive result.

## Secondary source results

### Binance USD-M bookDepth — PARTIAL_WINDOW_ELIGIBLE

Frozen secondary window: `2023-01-01` to `2025-01-01` exclusive.

- expected daily files: `731`
- existing/checksum-verified files: `728`
- daily file coverage: `99.589603%`
- missing files: `3`
- parse-error files: `0`
- invalid rows: `0`
- rows parsed: `20,685,850`
- cadence observations: `2,067,857`
- positive gaps <=120 seconds: `99.998066%`
- status: **`PARTIAL_WINDOW_ELIGIBLE`**

This is the one materially useful M8 outcome. It is **not** full-window evidence and may not be mixed
into a 2021-2024 full-window test after seeing this result. Any future book-depth edge study must use a
new predeclared contract that explicitly freezes the shorter 2023-2024 development window before
computing forward returns.

### Binance liquidationSnapshot — EXCLUDED_INCOMPLETE_HISTORY

- expected daily files: `1461`
- existing files: `0`
- coverage: `0%`
- status: **`EXCLUDED_INCOMPLETE_HISTORY`**

This family is excluded from later M8 confirmatory use under the frozen contract.

## Implementation defects corrected before authoritative evidence

Earlier workflow attempts were incomplete implementation runs and are not data verdicts. Before the
authoritative complete result, the following implementation-only defects were corrected without
changing M8 source families, thresholds, windows, OOS lock or decision gates:

1. exact audit-start Binance metrics boundary handling;
2. recursion in the boundary parser adapter;
3. malformed metric rows crashing before a frozen-gate verdict;
4. Bybit endpoint-specific time parameter names;
5. regression-test fixtures that intentionally sit inside the frozen development window.

The final evidence run completed end-to-end and uploaded its immutable report.

## Research consequence

M8 is closed and must not be rescued by weakening its frozen criteria.

- Full-window Binance metrics are rejected under the M8 contract.
- Bybit primary families remain unqualified under this execution provenance because they returned 403.
- liquidationSnapshot is excluded for incomplete official archive history.
- bookDepth is eligible only for a **separate, explicitly shorter 2023-2024 research contract**.

No 2025 data was requested or inspected. `oos_2025` remains **`LOCKED_NOT_ACCESSED`**.
