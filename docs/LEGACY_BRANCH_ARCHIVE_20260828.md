# Legacy branch archive — 2026-08-28

The repository had many old experimental branches with commits not reachable from `main`. They were consolidated before pruning so history is not lost.

Canonical archive ref:

`archive/legacy-experiments-20260828`

Archive commit:

`c18496388af394890ea441e15477ff733292b350`

The archive commit uses the current `main` tree and records the legacy experiment tips as additional Git parents. This preserves their complete commit ancestry without changing the production source tree.

Archived branch tips:

- `deploy/linode-m18-runtime` -> `c63dedf4e2d535705c00ae651d69bc142d187afc`
- `edge-discovery-engine` -> `79d7dddda43a8e4a12f3dfd841822abef0e70c2d`
- `m6-derivatives-data-audit` -> `73e915d9f932d5a6a3e2cdd23ba1694a0f00e1d1`
- `m7-funding-futures-edge-discovery` -> `dcc59076b56e5b9356207bf0042d11990c387a11`
- `m8-alt-derivatives-data-audit` -> `56908b5e1cb3197e746f83b01fc0904294b0d493`
- `m9-bookdepth-microstructure-edge` -> `981e3d2fdd733b6f17332dae623c3f93b0b6d5ed`
- `m10-cross-asset-data-audit` -> `6834940adcfa7f3a30447b7b28a0e9264befec47`
- `m11-eth-perpetual-data-audit` -> `a4d3fff9f57cb2cae05d2120d26b512c527f1268`
- `m12-cross-asset-eth-btc-edge` -> `3bb82523b51ec438dd528f3888a55ed548bd2848`
- `m13-ml-edge-engine` -> `43ef1e77f02491dd6255912fd998e1dcc9747300`
- `m14-market-neutral-funding-carry` -> `727e2742d69327700d72eba72e69135aa37b548a`
- `m15-market-neutral-basis-convergence` -> `f8c3f05b94965c3613a89c360d1f2e3e73c79cbd`
- `m16-delivery-futures-data-audit` -> `003b3cf9925319837f430564839a769d4c87a182`
- `m17-usdm-quarterly-cash-carry` -> `ed6b9f3f3261ebae46af85fbc8115db30c25257b`
- `m18-fee-aware-execution-economics` -> `c63dedf4e2d535705c00ae651d69bc142d187afc`
- `v3-bull-pullback-recovery` -> `dfbddf944a462d499e4a9917ad842794c4319266`

`deploy/linode-m18-runtime` and `m18-fee-aware-execution-economics` pointed at the same commit and therefore share the same preserved history.

The active `m5-development-corpus-materializer` branch is **not** part of this archive because PR #64 is still open and must be resumed rather than pruned.

## Recovery

If a historical branch ever needs to be inspected again, use the recorded SHA directly or recreate a temporary branch from that SHA. Do not turn an archive ref into a production/deployment branch.
