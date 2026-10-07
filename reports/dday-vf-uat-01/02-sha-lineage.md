# DDAY-VF-UAT-01 — SHA reconciliation

## Blocker A — accepted SHA ≠ accepted FR1 profile

| Revision | `runtime.profile.yaml` | `RuntimeProfileScheduler` | `publish_live_mqtt` | Dictionary SHA-256 |
|---|---|---|---|---|
| `320d82fb2fb3339461553e258b09ebee6689615a` (C03 accepted) | **absent** | **absent** | **absent** | `cbe389ec7d3c022a78b7853044f08ba148a7b8a41e374931973683c8886b07ca` |
| `dd6cfe466832b4c167f49861d27f718291f78699` (FR1 implementation) | `dday-bw-runtime-fr1` | present | present | same |
| `96a43b92dbbf99f178407048b44117124a022eae` (FR1 evidence refresh) | same blob as dd6cfe4 | unchanged | unchanged | same |

Issue #118's pairing `accepted SHA 320d82f` + `runtime profile dday-bw-runtime-fr1` is **not one immutable source revision**.

FR1 lineage from C03:

1. `0ea4527` contract from Issue #117
2. `b8b2cdb` mixed-cadence profile + scheduler
3. `cc99983` evidence refresh (stale head field)
4. `dd6cfe4` RESET-clock observation under lock — **FR1 implementation SA reviewed**
5. `96a43b9` evidence-only `head` rewrite to dd6cfe4

`git diff dd6cfe4..96a43b9` is four harness files. Dictionary SHA is unchanged C03→FR1.

A later deployment slice needs **one new explicitly accepted executable SHA** that contains FR1 plus a durable launcher (not implemented here).
