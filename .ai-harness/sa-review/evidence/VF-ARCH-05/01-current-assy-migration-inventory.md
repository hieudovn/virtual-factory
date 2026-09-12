# VF-ARCH-05 · Evidence 01 — Decision A: Current ASSY migration inventory

## 1. Scope

Repo-first inventory of the ASSY component set, classified per Issue #44 into
six buckets:

| Bucket | Meaning |
|---|---|
| **R — reuse as-is** | survives unchanged; only hosted/wrapped externally. |
| **W — wrap/host behind generic scope interface** | domain logic untouched; a later host/context adapter supplies scope identity/run boundary. |
| **A — adapt composition/context only** | change only demo orchestration / presentation selection; domain semantics unchanged. |
| **G — generalize later** | projection/visualization helpers that may later become generic primitives; not changed now. |
| **L — legacy/demo-only** | superseded or scaffolding; never promoted into the frozen target. |
| **N — must not rewrite** | domain-semantics freeze boundary. |

## 2. Verified file-level inventory

| File | Responsibility (verified) | Bucket |
|---|---|---|
| `src/virtual_factory/assembly/line_runtime.py` | `AssyLineRuntime` — single domain runtime: conveyor lane, SSO2/RSO2 feed, AP04 JOIN genealogy, AP06/AP08/AP11 quality, WIP lifecycle, deterministic timing | **N** (reuse as-is; host externally) |
| `src/virtual_factory/assembly/conveyor.py` | `ConveyorConfig.positions` = authoritative 12-position route (`PRE-ASSY`, `AP01`…`AP11`) | **R** |
| `src/virtual_factory/assembly/sub_line_identity.py` | `AssyProductionLineIdentity` (TIPA→ASSY) + `AssySubLineIdentity` (ASSY-SL01..06, hydraulic/thermal); canonical id frozensets | **R** |
| `src/virtual_factory/assembly/genealogy.py` | `GenealogyRecord` (AP04 `assembly_join`), `GenealogyStore` | **R** |
| `src/virtual_factory/assembly/quality.py` | `QualityDisposition` (pass/fail/rework/scrap) | **R** |
| `src/virtual_factory/assembly/quality_records.py` | `CheckType`, `QualityStatus` (retest_pending/reinspect_pending/failed_final), `QualityRecord`/`QualityHistory` | **R** |
| `src/virtual_factory/assembly/auto_timing.py` | `TimingResolver` — isolated `random.Random`, DETERMINISTIC mode | **R** |
| `src/virtual_factory/assembly/upstream.py` | SSO2/RSO2 producer semantics | **R** |
| `src/virtual_factory/assembly/carrier.py` | carrier primitive | **R** |
| `src/virtual_factory/assembly/wip.py` | WIP lifecycle (`WipLifecycle.RELEASED` = finished-good) | **R** |
| `src/virtual_factory/assembly/station_contracts.py` | `Capabilities`, `CompletionMode`, `StationCommand` — capability-driven dispatch precedent | **R** |
| `src/virtual_factory/assembly/mes_adapter.py` | `MESAdapter` contract adapter (mes↔simulation), `MESEventType` | **R** |
| `src/virtual_factory/assembly/assy_mes_bridge.py` | MES fact projection (LINE_OUT good/reject, quality/checklist/measurement, deterministic `occurred_at`) | **R** |
| `src/virtual_factory/assembly/observation_bridge.py` | observation point registry + idempotent delivery `(run_id, source_event_id)` | **R** |
| `src/virtual_factory/assembly/demo_assy_mes/` | MES demo projection package (`model.py` STATIONS/StationKind, `scenario.py`) | **L/R** (model=reference, single-sub-line page=demo-only) |
| `src/virtual_factory/assembly/demo_composition.py` | `AssyDemoComposition` — 6 `AssyDemoContext` each wrapping one `AssyLineRuntime`; `selected_sub_line_id`; `demo_step_number`; DEMO-only feed policy | **W + A** (strong reference for federation; not completed federation) |
| `src/virtual_factory/assembly/demo_controller.py` | `DemoController` facade over `AssyDemoComposition`; `runtime` returns selected-context runtime | **A** |
| `src/virtual_factory/assembly/demo_snapshot.py` | snapshot projection + `_CANONICAL_STATION_ORDER` | **G** |
| `src/virtual_factory/assembly/projection.py` | `EventView` projection | **G** |
| `src/virtual_factory/assembly/scene.py` | `EventMarkerView` visualization | **G** |
| `src/virtual_factory/assembly/tipa.py` | `build_tipa_topology()` — **legacy M3-S03 single-line** topology (sso2-1/2 → shared-buffer → AP01..06 → final-quality → finished-sink / rework AP04) | **L** |
| `src/virtual_factory/assembly/topology.py` | generic `AssemblyTopology` adjacency map (no route) | **G** |

## 3. Distinction that must be preserved

| Layer | Component | Authority |
|---|---|---|
| Domain runtime | `AssyLineRuntime` + conveyor/genealogy/quality/timing | domain truth — must not be rewritten |
| Demo orchestration | `AssyDemoComposition`, `DemoController`, feed policy, demo step | composition precedent — not completed federation |
| Identity | `sub_line_identity.py` | structural identity (TIPA→ASSY→SL01..06) |
| UI projection | `assy_demo.js` Frame A/B, inspector, `/assy-demo/*` | presentation, preserved per ARCH-04 |
| MES projection | `assy_mes_bridge.py`, `demo_assy_mes/*` | projection over facts, not a store |

## 4. Hosting-candidate abstractions (current core)

- `core/runtime_factory.py` `RuntimeAssembly` + `build_runtime` — continuous-equipment assembly, no Workspace/Scope layer.
- `core/engine_factory.py` `create_engine` — supports only `continuous_process` kind (`_SUPPORTED_KINDS`); ASSY not an engine kind.
- `core/schema.py` `PlantConfig` — flat plant config; **no scope/workspace layer**.
- `discrete/run_service.py` `DiscreteRunService` + `discrete/state.py` `RunStatus` (CREATED→READY→RUNNING/PAUSED→COMPLETED/STOPPED/FAILED) — run-lifecycle seam usable as a future scope run facade.
- **Confirmed absent:** no generic `Workspace` / `Scope` class anywhere in `src/` (only docstring mentions + `scope_refs` field in `integration/control_boundary.py`).

## 5. Conclusion

- Single domain runtime (`AssyLineRuntime`) already serves both standalone and
  six-sub-line hosts — the "two runtime paths" risk is absent today.
- `AssyDemoComposition` is a strong reference pattern, **not** completed
  federation (its demo feed policy / demo step clock are explicitly DEMO-only).
- `build_tipa_topology()` is legacy and must not be confused with the accepted
  12-position route (authoritative: `conveyor.py`).
- No generic Workspace/Scope abstraction exists — introducing one is
  implementation work deferred to later, not this gate.

No STOP condition triggered by the inventory.
