# 02 — Changed-File Classification

Comparison `main` (`fda1db44`) ↔ accepted ASSY lineage (`240d8db`), restricted
to architecture-relevant paths (`src/`, `configs/`, `simulators/`, `examples/`,
`deploy/`, `pyproject.toml`, `Dockerfile`, `docker-compose*.yml`).

## Classification legend

- **UNIQUE-TO-MAIN (must preserve)** — exists only on `main`, absent on baseline.
- **UNIQUE-TO-ASSY (must preserve)** — exists only on baseline, absent on `main`.
- **EQUIVALENT / SUPERSET** — both have it; one is a superset.
- **CONFLICTING** — both changed the same lines with different content.

## Classification

### UNIQUE-TO-MAIN (single-sub-line MES-01) — PRESERVED by the merge
| Path |
|---|
| `src/virtual_factory/assembly/demo_assy_mes/` (10 modules: `__init__`, `__main__`, `bridge`, `controller`, `fixtures`, `model`, `oee`, `runner`, `scenario`) |
| `src/virtual_factory/ui/static/demo_assy_mes.html` |
| `tests/test_demo_assy_mes_v1.py` |
| `.ai-harness/sa-review/reports/VF-DM-DEMO-ASSY-MES-01.md` + evidence dir |
| `.ai-harness/tasks/VF-DM-DEMO-ASSY-MES-01.json` |
| `docs/deployment/demo-assy-mes.md` |

### UNIQUE-TO-ASSY (six-sub-line + MES v1.1) — PRESERVED by the merge
| Path |
|---|
| `src/virtual_factory/assembly/` six-sub-line modules: `line_runtime`, `demo_controller`, `demo_composition`, `demo_snapshot`, `assy_mes_bridge`, `observation_bridge`, `quality_records`, `operation_execution`, `station_contracts`, `genealogy`, `sub_line_identity`, `upstream`, `carrier`, `conveyor`, `auto_timing`, `primitives/`, `demo_assy_mes` replaced by these |
| `src/virtual_factory/ui/static/assy_demo.{html,js,css}` + `VF_VISUAL_REVIEW_HARNESS.html` |
| `configs/plants/tipa_assy_demo.yaml` |
| `docker-compose.assy.yml` |
| `tests/test_assy_*`, `test_ops0*`, `test_m6_int_01`, `test_sim_val_01_feed`, `test_vf_contract_finality_01`, `test_auto_equiv_01`, `test_manual_e2e_01`, `test_m3_*`, `test_m4_*`, `test_quality*` |
| `.ai-harness/sa-review/reports/` + `evidence/` for the six-sub-line gates (MES-02, MES-03, VF-DEPLOY-01, VF-CONTRACT-FINALITY-01, etc.) |

### EQUIVALENT / SUPERSET
| Path | Verdict |
|---|---|
| `src/virtual_factory/observation/projections/mes.py` | baseline is a strict SUPERSET: contains all MES-01 mappings (`LINE_OUT`, `WIP_ENTERED`, `DOWNTIME_START`, `DOWNTIME_END`, `oee_summary`) **plus** `CHECKLIST_CONFIRMED`, `release`, `measurement_result` (M6-INT-01 / MES-02 / MES-03) |
| `Dockerfile` | baseline is a SUPERSET: adds `SOURCE_SHA`/`VF_SOURCE_SHA` bake (MES-02); `main` never modified Dockerfile after merge-base |
| `pyproject.toml` | baseline is a SUPERSET: adds `jsonschema>=4.0` dev dep (OPS-02-C03-R1); `main` never modified it |

### CONFLICTING (both changed same lines) — resolved by union, all mechanical
| Path | Nature | Resolution |
|---|---|---|
| `src/virtual_factory/ui/api.py` | both appended endpoint blocks at the same location | union: keep `/demo-assy-mes/*` (MES-01) AND `/assy-demo/*` (six-sub-line) |
| `src/virtual_factory/observation/projections/mes.py` | both edited the same dict regions (comment-only diff + superset mappings) | take baseline (superset) |
| `.ai-harness/sa-review/CURRENT.md` | both added a different inbox | combined inbox |

### Unchanged between the two heads (verified identical)
`configs/` (except `tipa_assy_demo.yaml`), `simulators/wtp`, `simulators/vf2`,
`examples/`, `deploy/`, the continuous/compressor engine (`core/`,
`equipment/`, `balance/`, `control/`, `instrumentation/`, `actuation/`,
`telemetry/`, `protocols/`), `discrete/`, `observation/`, `integration/`.

## Verdict

No file is in a state where a change is lost by the union merge. Every
unique-to-main file and every unique-to-ASSY file is retained; the three
conflicting files resolve deterministically by union/superset.
