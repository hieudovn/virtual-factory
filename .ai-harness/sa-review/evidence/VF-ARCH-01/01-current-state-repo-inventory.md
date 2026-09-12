# 01 — Current-State Repo Evidence Inventory

Repo-first discovery of actual canonical structures relevant to hierarchy and
composition. File paths and responsibilities recorded at canonical baseline
`main @ f5261c8ca18cd4e01779c0274b55270ba028b4e5`.

## 1.1 TIPA ASSY identity hierarchy

| File | Current responsibility |
|---|---|
| `src/virtual_factory/assembly/sub_line_identity.py` | Canonical ASSY identity model. `AssyProductionLineIdentity(plant_id="TIPA", production_line_id="ASSY", sub_lines=(6))`; `AssySubLineIdentity(production_line_id, sub_line_id, variant, label)`. Hierarchy: **TIPA Plant → ASSY Production Line → ASSY-SL01..06** sub-lines (SL01-03 hydraulic, SL04-06 thermal). Frozen anti-language: never "six ASSY lines", never flatten `line_id="ASSY-SL01"`. |
| `src/virtual_factory/assembly/demo_composition.py` | `AssyDemoComposition` manages **six** `AssyDemoContext` instances, each wrapping **one `AssyLineRuntime`**. `selected_sub_line_id` (default `ASSY-SL01`). `demo_step_number` presentation clock. Demo feed policy (`ContinuousFeedPolicy`) is explicitly DEMO-only, not plant truth. |
| `src/virtual_factory/assembly/line_runtime.py` | `AssyLineRuntime` — authoritative stop-and-go indexed line runtime (M6-S02). ONE conveyor lane; WIP lifecycle; stations AP01-AP06; genealogy; quality records; auto-timing; operation execution. **Single source of simulation truth.** |
| `src/virtual_factory/assembly/station_contracts.py` | `StationContract` + `Capabilities` + `CompletionMode` + `StationCommand`. Capability-driven gating (no hard-coded station branches). |
| `src/virtual_factory/assembly/tipa.py` | `build_tipa_topology()` — hard-coded single-line TIPA topology (2 SSO2 sources → shared buffer → AP01..06 → final quality → sink / rework AP04). Legacy single-line representation. |
| `src/virtual_factory/assembly/carrier.py`, `conveyor.py`, `wip.py`, `upstream.py`, `genealogy.py` | Object/state models: carriers, single conveyor lane, WIP, upstream SSO2/RSO2 producers, genealogy records. |

## 1.2 Per-sub-line runtime contexts

`AssyDemoContext` (in `demo_composition.py`) holds, per sub-line: `identity`,
`config` (deep-copied + normalized), `runtime` (`AssyLineRuntime`), and
per-context feed state (`carrier_seq`, `sso2_idx`, `sso2_ids`). State is
**isolated per context** — nothing shared across contexts. Each context is
independently steppable (`step_context`) and independently inspectable.

## 1.3 Generic runtime / config / workspace abstractions

| File | Current responsibility |
|---|---|
| `src/virtual_factory/core/schema.py` | `PlantConfig` — flat plant config: `PlantMetadata(id, name, type)` + `equipment`/`sensors`/`controllers`/`actuators`/`connections`/`signals`. **No scope/workspace layer.** |
| `src/virtual_factory/core/engine_factory.py` | `resolve_engine_kind` (`model_type` discriminator; default `continuous_process`), `create_engine`. Single construction seam. |
| `src/virtual_factory/core/engine_contract.py` | `SimulationEngineProtocol` (structural, not an ABC hierarchy). |
| `src/virtual_factory/core/runtime_factory.py` | `build_runtime(config)` → `RuntimeAssembly` (graph, state, equipment/sensors/controllers/actuators, alarm manager, output policy, telemetry store). |
| `src/virtual_factory/core/plant_graph.py` | `PlantGraph` (nodes + edges) built from config — graph connectivity for configured plants. |
| `src/virtual_factory/core/ports.py` | `Port` typed interface (`physical|measurement|signal|command|publication`, direction in/out/inout). |
| `src/virtual_factory/core/model_registry.py` | `ModelRegistry.from_directory(configs/model_types)`. |
| `src/virtual_factory/discrete/*` | Domain-neutral discrete-event kernel: `DiscreteSimulationEngine`, `FutureEventScheduler`, `DiscreteRunController`, `DiscreteRunService`, `RunContext`, `EventDispatcherProtocol`, `HandlerRegistry`. |

**Key finding:** there is **no production `Workspace`, `SimulationScope`,
`scope_id`, or `workspace_id` abstraction** anywhere in `src/` (verified by
grep). The workspace concept exists only as a frozen field proposal in
`.ai-harness/sa-review/evidence/SHW-VF-PH00/06-workspace-contract-proposal.md`.
Therefore there is **no competing generic hierarchy abstraction** to conflict
with this proposal.

## 1.4 UI context / sub-line selection

| File | Current responsibility |
|---|---|
| `src/virtual_factory/ui/api.py` | `/assy-demo/*` endpoints (reset/step/observations/snapshot/jam/recover with optional `sub_line_id` in body) + `/demo-assy-mes/*` (single-sub-line MES demo). |
| `src/virtual_factory/ui/static/assy_demo.js` | Sub-line cards (`ASSY-SL01..06`), `_selectedSubLineId`, `openFrameB(subLineId)`, per-sub-line context (`_subLineId`) and `fetch /assy-demo/sub-line/{id}`. Presentation-level selection; not identity. |
| `src/virtual_factory/ui/static/assy_demo.html` | Sub-line cards grouped by variant (hydraulic / thermal). |
| `src/virtual_factory/ui/runtime_service.py` | Generic runtime service façade over engines. |

UI sub-line selection is a **view/presentation selector over the composition**,
not an identity or topology authority.

## 1.5 Accepted evidence / docs constraining terminology

| Doc | Constraint carried into this gate |
|---|---|
| `.ai-harness/sa-review/evidence/SHW-VF-PH00/06-workspace-contract-proposal.md` | Freezes `workspace_id` (logical VF identity, NOT semantic id), `outputs.namespace` (distinct, deterministically bound to workspace_id), `runtime.engine` discriminator, `semantic_sources` + `compatibility`. Invariant: `workspace_id` / `canonical_signal_id` / `outputs.namespace` are THREE distinct concepts. |
| `.ai-harness/sa-review/evidence/SHW-VF-PH00/13-recommended-target-architecture.md` | Platform = SharedCore (`core/` + `discrete/`) + reusable DomainModels; Workspaces = TIPA ASSY, SH WTP, Compressor/Continuous; Legacy = `simulators/wtp` (VF-1), `simulators/vf2` (VF-2). ASSY stays as-is (self-contained discrete workspace). |
| `.ai-harness/sa-review/evidence/SHW-VF-PH00/11-shw-placement-options.md` | SH WTP workspace container `configs/workspaces/shw-wtp/` (config-level). |
| `.ai-harness/sa-review/evidence/SHW-PIM-VF-*` (ALIGN/EXPORT/COMPAT) | PIM owns canonical semantic identity (`PLANT-SHW`, `AREA-SHW-*`, `UNIT-SHW-*`, `SIG-SHW-*`); VF structural identity must not replace it. |
| `ARCHITECTURE.md`, `docs/design-principles.md` | Plant model is config-driven and graph-based; equipment interacts through typed ports; physical truth internal; sensors create industrial reality. |
| `docs/graph-model.md`, `docs/data-model.md` | Graph nodes/edges model; data model for telemetry frames. |

## 1.6 Reusable pattern vs TIPA/ASSY-specific

| Pattern | Classification |
|---|---|
| Workspace identity + `outputs.namespace` (PH00 §06) | **Reusable** (all workspaces). |
| `PlantConfig` + `PlantGraph` + `RuntimeAssembly` + `SimulationEngine` (core) | **Reusable** (continuous archetype). |
| `discrete/` kernel (scheduler/engine/controller/service) | **Reusable** (discrete archetype). |
| `AssyProductionLineIdentity` / `AssySubLineIdentity` | **ASSY-specific** encoding of a **reusable** pattern (Workspace → Scope → child Scope). |
| `AssyDemoComposition` (6 contexts over `AssyLineRuntime`) | **ASSY-specific** composition over the **reusable** standalone/federated pattern. |
| `build_tipa_topology()` (hard-coded) | **Legacy/reference** single-line topology; not the vNext structural authority. |
| `simulators/wtp`, `simulators/vf2` | **Legacy / out-of-platform** (PH00 B7). |
