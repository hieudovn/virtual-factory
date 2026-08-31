# VF-DEPLOY-01 — environment.md

Accepted source under test:

| Item | Value |
|---|---|
| Repository | `hieudovn/virtual-factory` |
| Branch | `docs/m6-s01-tipa-baseline` |
| Baseline before deployment work | `18d253d632ee9c939a206e28c27fcebdea61af50` |
| Accepted VF contract/documentation tip | `f72cc9564b251c3812c2b6070bddd37e479d5ea5` |
| Accepted VF production/demo build | `494c12e265d297a389e4463848b9c0b6aafed0b1` |
| ASSY config (container path) | `/app/configs/plants/tipa_assy_demo.yaml` |

Host:

| Item | Value |
|---|---|
| OS | Windows (PowerShell) |
| Docker Engine | 29.5.3 |
| Docker Compose | v5.1.4 |
| Native Python | 3.11.9 (`C:\Users\dotru\AppData\Local\Programs\Python\Python311\python.exe`) |

Runtime feature flags (identical for native and Docker):

- `VF_ENABLE_S04B_OVERVIEW=1` (required for M6-S04B Frame A/B + `/assy-demo/overview`,
  `/assy-demo/sub-lines`, `/assy-demo/sub-line/{id}`)
- `TIPA_ASSY_CONFIG=<config path>` (native: repo-relative path; Docker:
  `/app/configs/plants/tipa_assy_demo.yaml`)

No host-specific absolute Windows path and no credentials are required by the
Docker runtime.
