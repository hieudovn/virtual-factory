# 06 — Workspace Contract Proposal (freeze fields only, do NOT implement)

Based on repo evidence, the minimum viable workspace abstraction reuses what
already exists (`plant.id`, `--config`, `--scenario`, `ModelRegistry`,
`OutputPolicy`) and adds only the missing **workspace identity + provenance +
semantic-source pinning**. No field is implemented in PH00.

## 6.1 Frozen manifest fields

```yaml
workspace_id: SHW-WTP              # unique; becomes output namespace + dispatch key
workspace_type: plant_simulation   # enum: plant_simulation | demo | benchmark
domain: water_treatment            # coarse domain tag (vs natural_gas, discrete_assembly, generic)
plant_id: PLANT-SHW                # must equal plant_config.plant.id

runtime:
  engine: vf-core                  # enum: continuous_process | discrete_assembly | discrete_generic
  fidelity_ceiling: logical_only    # enum: logical_only | synthetic_reference | first_order

semantic_sources:                  # immutable/versioned upstream artifacts (see 12)
  pim_contract:
    artifact: <name>
    version: <semver>
    commit_sha: <full sha>
    compatibility_status: compatible|review_required|incompatible
  state_templates:
    artifact: <name>
    version: <semver>
    commit_sha: <full sha>
    compatibility_status: compatible|review_required|incompatible

plant_config:
  ref: configs/plants/shw_wtp.yaml        # OR configs/workspaces/shw-wtp/plant.yaml

scenarios:                                 # workspace-scoped, plant-coupled
  - id: ...
    ref: ...

outputs:
  namespace: SHW                        # threaded into telemetry frame + MQTT prefix + OPC UA ns + file dirs
  origin: VF-Simulation                 # fixed provenance origin
```

### Field ownership rules (frozen)

| Field | Owner | Notes |
|---|---|---|
| `workspace_id` | Workspace manifest | globally unique; never re-derived from plant id |
| `runtime.engine` | Workspace manifest (selects existing engine; must NOT invent a new engine) | maps to `engine_factory.resolve_engine_kind` extension |
| `semantic_sources.*` | PIM/upstream (read-only reference + content hash) | VF consumes; never modifies |
| `plant_config.ref` | Workspace manifest | points at a loadable `PlantConfig` |
| `scenarios[].ref` | Workspace manifest | points at loadable `ScenarioConfig` files |
| `outputs.namespace` | Workspace manifest | one-way: manifest → runtime → telemetry → gateway |

## 6.2 Required invariants (frozen)

1. `workspace_id` == `outputs.namespace` == telemetry/observation provenance `workspace_id`.
2. `plant_config.plant.id` == `plant_id` (must match, validated at load).
3. `runtime.engine` ∈ existing `_SUPPORTED_KINDS` (extended set) — **no new engine**.
4. `semantic_sources` are immutable references; a change to any upstream
   `commit_sha` requires explicit compatibility review before the workspace can run.
5. Scenarios are workspace-scoped: a `configs/workspaces/<id>/scenarios/*` file
   must only reference equipment/sensor ids present in that workspace's plant.
6. No workspace may import another workspace's objects/config (enforced by
   namespace, not by directory).

## 6.3 Dispatch extension (conceptual, NOT implemented)

`engine_factory.resolve_engine_kind` today only knows `continuous_process`.
The workspace manifest's `runtime.engine` would map to an **extended** kind set:

```text
continuous_process  → core.simulation_engine.SimulationEngine        (existing)
discrete_assembly   → assembly.demo_controller.DemoController         (existing, ASSY)
discrete_generic    → discrete.run_service.DiscreteRunService         (existing, M4 demo)
```

This is a **future, separate CORE gate** (see 08). PH00 only freezes the field
name and enum values.

## 6.4 What the manifest does NOT contain (deliberately)

- No runtime code / behavior — engine and models stay in shared layers.
- No physics/equations — that belongs to `equipment/*` model classes.
- No gateway/output implementation — `protocols/` and `integration/` stay shared.
- No PIM ontology edits — PIM is consumed read-only (see 12).

## 6.5 Minimal-viability test (a manifest is valid iff)

1. `workspace_id`, `plant_id`, `runtime.engine`, `plant_config.ref`,
   `outputs.namespace` are all present and non-empty.
2. `plant_config.ref` resolves and passes `load_plant_config` validation.
3. `outputs.namespace` is a non-empty, collision-free token.
4. `semantic_sources` (if any) carry artifact+version+commit_sha+compatibility_status.
