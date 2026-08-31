# 06 — Workspace Contract Proposal (freeze fields only, do NOT implement)

Based on repo evidence, the minimum viable workspace abstraction reuses what
already exists (`plant.id`, `--config`, `--scenario`, `ModelRegistry`,
`OutputPolicy`) and adds only the missing **workspace identity + provenance +
semantic-source pinning**. No field is implemented in PH00.

## 6.1 Frozen manifest fields

```yaml
workspace_id: SHW-WTP              # stable logical VF workspace identity (NOT a semantic id)
workspace_type: plant_simulation   # enum: plant_simulation | demo | benchmark
domain: water_treatment            # coarse domain tag (vs natural_gas, discrete_assembly, generic)
plant_id: PLANT-SHW                # must equal plant_config.plant.id

runtime:
  engine: continuous_process       # engine discriminator (NOT vf-core)
  fidelity_ceiling: logical_only    # enum: logical_only | synthetic_reference | first_order

semantic_binding:
  mode: required                    # required | optional | none  (SH WTP = required)

semantic_sources:                  # immutable/versioned upstream artifacts (PIM-owned identity)
  pim_contract:
    artifact: <name>
    version: <semver>
    commit_sha: <full sha>
  state_templates:
    artifact: <name>
    version: <semver>
    commit_sha: <full sha>

compatibility:                     # owned by VF/PIM integration review, NOT solely by PIM
  consumer: vf
  consumer_contract_version: ...
  status: compatible | review_required | incompatible
  reviewed_by_gate: ...

plant_config:
  ref: configs/workspaces/shw-wtp/plant.yaml

scenarios:                                 # workspace-scoped, plant-coupled
  - id: ...
    ref: ...

outputs:
  namespace: shw-wtp              # protocol/path-safe namespace; bound to workspace_id, not string-equal
  origin: VF-Simulation           # fixed provenance origin
```

### Field ownership rules (frozen)

| Field | Owner | Notes |
|---|---|---|
| `workspace_id` | Workspace manifest | stable logical VF workspace identity; globally unique; never re-derived from plant id; NEVER a canonical semantic id |
| `runtime.engine` | Workspace manifest (selects existing engine; must NOT invent a new engine) | `continuous_process` for SH WTP; `vf-core` is NOT an engine discriminator |
| `semantic_sources.*` (artifact/version/commit_sha) | PIM/upstream (read-only) | VF consumes; never modifies; PIM owns the identity |
| `compatibility.*` | VF/PIM integration review | compatibility is a relationship between the exact upstream artifact and the exact VF consumer contract/runtime |
| `plant_config.ref` | Workspace manifest | points at a loadable `PlantConfig` |
| `scenarios[].ref` | Workspace manifest | points at loadable `ScenarioConfig` files |
| `outputs.namespace` | Workspace manifest | protocol/path-safe namespace; uniquely & deterministically bound to `workspace_id`, string equality NOT required |

## 6.2 Required invariants (frozen)

1. `workspace_id`, `canonical_signal_id`, and `outputs.namespace` are THREE
   DISTINCT concepts (B2). `canonical_signal_id` is PIM-owned and consumed
   read-only — VF never invents/rewrites it.
2. `outputs.namespace` MUST be uniquely and deterministically bound to
   `workspace_id`; string equality is NOT required (e.g.
   `workspace_id: SHW-WTP` / `outputs.namespace: shw-wtp`).
3. `plant_config.plant.id` == `plant_id` (must match, validated at load).
4. `runtime.engine` ∈ existing engine kinds — **no new engine**.
5. `semantic_binding.mode: required` for SH WTP: missing artifact/version/SHA,
   SHA mismatch, or non-`compatible` status makes the workspace invalid to
   load/run (contract-only; validation not implemented in C02).
6. Scenarios are workspace-scoped: a `configs/workspaces/<id>/scenarios/*` file
   must only reference equipment/sensor ids present in that workspace's plant.
7. No workspace may import another workspace's objects/config.

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
3. `outputs.namespace` is a non-empty, collision-free token deterministically
   bound to `workspace_id`.
4. `semantic_sources` carry artifact+version+commit_sha; `compatibility` carries
   consumer + consumer_contract_version + status + reviewed_by_gate.
5. If `semantic_binding.mode == required`, the above semantic references and a
   `compatible` status are mandatory.
