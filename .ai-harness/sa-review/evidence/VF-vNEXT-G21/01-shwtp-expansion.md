# VF-vNEXT-G21 — SH-WTP Functional Simulation Expansion — Evidence

Gate: `VF-vNEXT-G21` · Implementation gate (additive plant-slice module + tests).
Base: `65a2581ef825a79f8f088c0bc7672b249e96c942` (G20-C01 head).
Model: Pro.

## 1. What was implemented

- `src/virtual_factory/shwtp/expansion.py` — a bounded runnable 5-scope SH-WTP
  plant slice:
  - `PlantSliceScope` descriptors with explicit fidelity/status per scope.
  - Five participant adapters: `LogicalSourceParticipant` (RAW-INTAKE),
    `LogicalJunctionParticipant` (T100), `T106FilterParticipant` (reuses
    `T106LogicalRuntime`), `T108TankParticipant` (reuses `T108TankRuntime`),
    `LogicalSinkParticipant` (DIST-P108).
  - `build_shwtp_plant_slice()` — builds the slice workspace, 4-binding
    CompositionGraph, G18 assumed-topology overlay (3 assumed edges), and the G4
    Coordinator with explicit_lagged orchestration.
- `tests/test_vnext_g21_shwtp_expansion.py` — 21 tests.

## 2. Selected slice (justified from G16 readiness)

`RAW-INTAKE → T100 → T106 → T108 → DIST-P108` (5 executable scopes):

| Scope | Fidelity | Status | Source |
|---|---|---|---|
| RAW-INTAKE | logical_only | scenario_assumed | G16 LATER_CANDIDATE |
| T100 | logical_only | scenario_assumed | G16 LATER_CANDIDATE |
| T106 | logical_only | accepted | G13B runtime |
| T108 | first_order | accepted | G13 runtime |
| DIST-P108 | logical_only | scenario_assumed | G16 NEXT_SLICE_CANDIDATE |

T110 is NOT used (blocked pending evidence). Only T106→T108 is PIM-authoritative
(REL-SHW-F01); the other three links are G18 `VF_SCENARIO_ASSUMED_TOPOLOGY`.

## 3. Required semantics coverage

| Requirement | Proof |
|---|---|
| >=4 executable scopes | 5 scopes, spans intake + treatment + distribution |
| assumed vs authoritative topology | 3 overlay edges (assumed) + 1 F01 binding (authoritative) |
| fidelity/status explicit | `PlantSliceScope.fidelity/status` |
| deterministic multi-window | identical slices produce identical outcomes + tank state |
| no same-window feed-through | T106 window-2 output = T100 window-1 value (not window-2) |
| no mutable cross-scope state | detached frozen transfer payloads only |
| CompositionGraph != execution order | no execution-order/coupling-policy field on graph |
| no authority broadening | `NOT_AUTHORIZED` flags unchanged |
| T106/T108 reused unchanged | standalone runtimes step identically |

## 4. Preserved / unchanged

TIPA ASSY behavior; G20/G19/G18/G14/G15; reference connectivity graph; T106/T108
standalone runtimes; PIM pins. No gateway routing, no MQTT/Kafka/REST, no T110
runtime, no whole-plant/site-faithful claim, no G4 redesign.

## 5. Test evidence

- `tests/test_vnext_g21_shwtp_expansion.py` — 21 tests PASS.
- Complete canonical vNext baseline (see report `VF-vNEXT-G21.md`).
