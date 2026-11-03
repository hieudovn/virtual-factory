# 01 — Verified source ownership and exact SHAs

Read-only audit. No VF, MES or PlantOS file was modified. MES and PlantOS were
cloned to `/tmp` only for inspection; the working tree of the VF repo contains
only task/report/evidence files.

## Verified remote heads at execution

| Repository | Default branch | Observed head | Verification |
|---|---|---|---|
| `hieudovn/virtual-factory` | `main` | `04fb9413bd5af3c4f0457047267a60b3ea4e94fe` | `git rev-parse origin/main`; `git ls-remote` |
| `hieudovn/MES-dev-and-demo-project` | `main` | `2c4d01d437bf25b44adffd610350e9df6773a853` | `gh api repos/...`; `git ls-remote`; shallow clone HEAD |
| `hieudovn/PlantOS` | `main` | `23126a470c0a5faff0046251bb979117b115a169` | `git ls-remote`; shallow clone HEAD |
| Design input (unmerged) | `sa/design/tipa-vf-g1-approved-baseline` | `ff485d5bb50e55e91b90008465e4cc87ab7a9f22` | `git ls-remote`; PR #132 head |

MES head message: `Merge PR #136: S02 release candidate - #129 + #130 + #131`.
Those are MES-side issue numbers, not VF Issue #129. The observed MES head is
the read-only audit target; it is not pinned as a future SHA.

VF `main` did not advance from the planning reference during this audit.
PR #132 remains unmerged design input, not implementation truth.

## Writer authority

| Contract | Authoritative writer | Not an owner | Evidence |
|---|---|---|---|
| C1 raw IoT topic/packet | TIPA PLC / IoT source | VF synthetic runtime; MES projection | MES `ingest/tipa_iot/validator.py`, `source_profile.py`; VF must not publish into live TIPA topics |
| C2 `tipa-mes-semantic-v1` | MES normalizer from accepted C1 | VF; reconstructed dashboard | MES `ingest/tipa_iot/normalizer.py:96-186` |
| C2b `tipa-cycle-evidence-v1` | MES raw order packet evidence, exact original bytes | VF; C2 reverse-transform | MES `ingest/tipa_iot/cycle_evidence.py:11-49` |
| C3 `tipa-mes-finished-v1` | MES append-only Finished | VF `LINE_OUT`; quality | MES `odoo/custom_addons/mes_iot_integration/services/finished_product_service.py:8,52-105` |
| C4 `tipa-assy-demo-v1.1` | VF six-sub-line bridge | MES (consumer only) | VF `src/virtual_factory/assembly/assy_mes_bridge.py:81`; MES adapter |
| C5 `vf-qms-evidence-v1` candidate | **NEW PLANNED — no writer** | VF; MES C4 | VF design draft PR #132; MES allowlist excludes it |
| PlantOS synthetic VF export | VF workspace exporter | PlantOS production `.63` topic namespace | VF `src/virtual_factory/workspaces/plantos_export.py`; PlantOS contract docs |

## Crosswalk: VF logical sub-lines ↔ physical AA10 ↔ MES lines

| VF logical | Physical machine | MES line | Authority |
|---|---|---|---|
| `ASSY-SL01` | `AA10-01` | `ASSY-SL01` | MES `deploy/tipa-assy/line_masters_v1.json` |
| `ASSY-SL02` | `AA10-02` | `ASSY-SL02` | same |
| `ASSY-SL03` | `AA10-03` | `ASSY-SL03` | same |
| `ASSY-SL04` | `AA10-04` | `ASSY-SL04` | same |
| `ASSY-SL05` | `AA10-05` | `ASSY-SL05` | same |
| `ASSY-SL06` | `AA10-06` | `ASSY-SL06` | same |

MES records this as canonical identity seeded into `canonical.identity.map`;
`ingest/config/tipa_assy_v1.yaml` owns MQTT/profile/status mapping only and must
not declare `mes_line` (MES `deploy/tipa-assy/check_line_masters_align.py`).
This is an **observed MES mapping**, not a VF-invented foreign key. VF C4
actually carries logical `ASSY-SLxx`; the AA10 mapping is MES-side.

## Repository access

| Repo | Access | Read-only use |
|---|---|---|
| VF | local clone | inspection and tests |
| MES | authenticated clone (`/tmp/opencode/mes-audit`) | source inspection; no test runtime |
| PlantOS | authenticated clone (`/tmp/opencode/plantos-audit`) | contract/edge inspection; no deployment |
| MES Odoo runtime | **unavailable** (`odoo` import resolves to the repo folder; `psycopg2` absent) | MES adapter tests **NOT RUN** |

No credentials, broker, database or live endpoint was written to.
