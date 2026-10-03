# DDAY-B2 — 10. Scope and leakage audit

**Machine evidence:** [`machine-evidence.json`](./machine-evidence.json) → `leakage`,
`git.name_status_vs_b1`; full patch [`implementation.patch`](./implementation.patch).

## A. Allowlist compliance

Complete changed-file set relative to the B1 baseline:

```
A  .ai-harness/tasks/DDAY-B2.json
A  configs/workspaces/bottled-water-dday/line.yaml
M  src/virtual_factory/assembly/demo_controller.py
M  src/virtual_factory/assembly/line_runtime.py
A  tests/test_dday_b2_bottled_water_line.py
```

| SA-allowed path | Used |
|---|---|
| `configs/workspaces/bottled-water-dday/` | yes — `line.yaml` (new) |
| `src/virtual_factory/assembly/line_runtime.py` | yes |
| `src/virtual_factory/assembly/demo_controller.py` | yes |
| `src/virtual_factory/assembly/demo_composition.py` | **not modified** (deliberately; see evidence 02) |
| `src/virtual_factory/ui/api.py` | **not modified** — the allowed config-selection seam was not necessary, so it was not added |
| relevant `tests/` | yes — one new module |
| `.ai-harness/tasks/DDAY-B2.json` | yes |
| `.ai-harness/sa-review/evidence/DDAY-B2/` | yes |
| `.ai-harness/sa-review/reports/DDAY-B2.md` | yes |
| `.ai-harness/sa-review/CURRENT.md` | yes |

Two extra entries appear in the contract's `allowed_paths`:
`docs/plans/PLANTOS_DDAY_TRACK_B_VF_SA_HANDOFF.md` and
`docs/plans/PLANTOS_DDAY_TRACK_B_B1_WORKSPACE_CONTRACT.md`. These are **frozen B1
artifacts already committed on this branch**, which appear in the diff against
`origin/main`. They are listed only so the harness allowlist diff check is
truthful, and they are **not modified** by B2 (the change set above proves it).
The exact SA list is preserved verbatim in the contract as `sa_allowed_paths`.

**Forbidden paths: none touched.** `core/`, `telemetry/`, `protocols/`,
`scenarios/`, `equipment/`, `balance/`, `control/`, `instrumentation/`,
`actuation/`, `assy_mes_bridge.py`, `observation_bridge.py`, `simulators/`,
`deploy/`, `docs/deployment/`, the compose files, `Dockerfile`,
`pyproject.toml` and `configs/plants/tipa_assy_demo.yaml` are all unmodified.

## B. Domain-isolation audit

Surfaces scanned for the forbidden tokens
(`TIPA`, `ASSY`, `PRE-ASSY`, `AP05_JAM`, `SSO2`, `RSO2`, and `\bAP\d{2}\b`):

| Surface | Strings scanned | Findings |
|---|---|---|
| Workspace configuration file | 2411 | **0** |
| Runtime outward raw facts (`line_facts()`) | 121 | **0** |
| Runtime trace events (type/station/unit/detail) | 223 | **0** |
| Station contracts (`to_dict()`) | 8 | **0** |
| Unit identities | 12 | **0** |
| Quality records | 8 | **0** |

`clean: true` — the audit was run on the **reject** scenario (12 cycles), i.e. the
most state-rich case, covering both the good and the reject paths.

The legacy demo-snapshot path is verified to publish **no** Bottled Water state:

```json
{"positions": [], "genealogy": [], "quality_records": [],
 "active_operations": [], "recent_quality_events": [],
 "production_wips_on_line": 0}
```

The Bottled Water outward raw-fact surface is
`DemoController.line_facts()` → `AssyLineRuntime.line_facts()`.

## C. KPI boundary

No OEE, availability, performance, quality-percentage, energy-per-unit,
utilization or health-score value is computed anywhere in the change set. The new
runtime API exposes counts and raw facts only (`unit_counts()`, `units_on_line()`,
`operating_state()`, `line_facts()`). The contract's `kpi_boundary` is preserved.

## D. Interaction policy

Only `START` / `PAUSE` / `RESUME` / `STOP` / `RESET` were implemented (plus the
automatic unit feed). No manual checklist, manual inspection result, quality
disposition, release, retry, rework or operator approval exists in the Bottled
Water path — asserted structurally by `test_t02` (`OPERATION_WAITING_COMMAND`
never occurs) and by the absence of any non-`DONE` command in the generic profile.

## E. New-foundation check

| Forbidden construction | Present? |
|---|---|
| New bottled-water simulation engine | no |
| New bottled-water telemetry framework | no |
| New bottled-water scenario framework | no |
| New bottled-water protocol stack | no |
| Parallel runtime controller | no — the existing `DemoController` gained a mode |
| Forked legacy engine | no — the same `AssyLineRuntime` class runs both profiles |
| New source module under `src/` | no — all changes are inside the two allowlisted files |

## F. B3+ scope check

| Later slice | Started? |
|---|---|
| B3 dedicated 2D Bottled Water skin | no |
| B4 Water Treatment / Utilities / Warehouse runtime | no |
| B5 Capper deterministic abnormal scenario | no |
| B6 PlantOS local integration proof | no |
| B7 VPS deployment | no |

No MQTT, OPC UA, REST/WebSocket, PlantOS or PIM work was performed.

## G. Residuals disclosed (not claimed as complete)

1. `FAULT`, `DOWNTIME` and `UNKNOWN` operating states are **not** produced by B2.
   `STOPPED != FAULT` is structurally guaranteed; the missing states belong to B5.
2. The legacy `AssyDemoSnapshot` type is not used to publish Bottled Water state
   (verified empty), and no generic outward snapshot schema replaces it — a
   generic schema is a B3 concern.
3. The Bottled Water workspace is not wired to `api.py`; its runnable entry point
   is `DemoController` plus the smoke/evidence scripts.
4. The reject path reuses the engine's existing terminal-FAIL quality semantics
   (the disposition label for a failed visual inspection is `NG`, as it already is
   for the legacy visual inspection station). No new quality vocabulary was
   invented for Bottled Water.
