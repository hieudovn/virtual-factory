# VF-vNEXT-G12B — SH-WTP PIM Reference Connectivity Materialization — Evidence

Gate: `VF-vNEXT-G12B` · PIM reference connectivity materialization (no PIM change, no runtime).

## 1. Pinned PIM evidence (repo-first)

| Pin | Value |
| --- | --- |
| Repo | `hieudovn/plant-intelligence-model` |
| Main SHA | `ec7f1266d4a19e5201b689874a2a7a75a022fc5c` |
| Package | `SHW-PIM-VF-EXPORT-v0.1` `v0.1` (`SHW-PH03-v0.1`) |
| Semantic identity SHA | `f23f3c4614f50a1a2e3805f7e887433feb934915` |
| Artifact hash SHA | `ea3361a4aca9d25927a4a76c792f3af184e1aabb` |
| Compatibility | `compatible_with_constraints` |
| Runtime authorization | `NOT_AUTHORIZED` |
| Model fixture | `examples/song-hong-wtp/model_fixture/model.yaml` (sha256 `e9c6703f…`) |

## 2. Selected slice (repo-first inspection)

Exactly the F01-F07 process/connectivity relationships from `model.yaml`:

| id | raw type | source -> target | status |
| --- | --- | --- | --- |
| REL-SHW-F01 | FLOWS_TO | PROC-SHW-L1-T106-OUT-FLOW -> PROC-SHW-L1-T108-IN-FLOW | DocumentConfirmed |
| REL-SHW-F02 | DISCHARGES_TO | PROC-SHW-L1-T106-WASH-OUT -> PROC-SHW-WASH-T110-RECOVERY-RETURN | PatternInferred (REL-006 WARNING) |
| REL-SHW-F03 | CONNECTED_TO | PROC-SHW-WASH-T110-RECOVERY-RETURN -> PROC-SHW-L1-T106-OUT-FLOW | PatternInferred (REL-006 WARNING) |
| REL-SHW-F04 | FLOWS_TO | PROC-SHW-RAW-TO-T100 -> PROC-SHW-T100-TO-L1 | DocumentConfirmed |
| REL-SHW-F05 | FLOWS_TO | PROC-SHW-T100-TO-L1 -> PROC-SHW-L1-TO-DIST | DocumentConfirmed |
| REL-SHW-F06 | FLOWS_TO | PROC-SHW-L1-SLUDGE-OUT -> PROC-SHW-SLUDGE-T201-IN | PatternInferred |
| REL-SHW-F07 | FLOWS_TO | PROC-SHW-CHEM-DOSING-LINE -> PROC-SHW-T100-TO-L1 | PatternInferred |

## 3. Materialization rules honored

- Endpoints are `ReferenceEndpoint(authority="hieudovn/plant-intelligence-model",
  entity_id=<canonical id>, entity_kind="ProcessConnection")` — PIM declares every
  flow-path entity with `entity_type/category: ProcessConnection`. No StructuralPath,
  no Scope, no PROC-* -> Unit mapping, no runtime owner.
- Raw relation types preserved verbatim; no six-class reclassification; F06/F07
  remain `FLOWS_TO` (no name-based sludge/chemical inference).
- F02/F03 carry the PIM "known-but-unconstrained (REL-006 WARNING)" gap verbatim.
- Every edge `runtime_effect = none`; no BoundaryPort/G4/coordinator/run-control.

## 4. Implementation

- `src/virtual_factory/shwtp/connectivity.py` — frozen source pins, frozen
  `PimReferenceRelation` slice (F01-F07), `build_shwtp_reference_graph()` (G12A
  `ReferenceConnectivityGraph`), `source_pins()`, and
  `ShwtpReferenceConnectivity.serialize()` (pins + selected ids + graph).
- Exposed from `virtual_factory.shwtp` (`build_shwtp_reference_connectivity`, …).

## 5. Test evidence

- `tests/test_vnext_g12b_shwtp.py` — 19 tests PASS.
- Full suite: 2077 passed (2058 prior + 19 new).
- Complete canonical vNext baseline + checks: see report `VF-vNEXT-G12B.md`.

## 6. Unchanged

PIM; G11 containment (28 scopes); generic G12A connectivity module; G4 composition;
run-control; semantic binding; runtime authorization (`NOT_AUTHORIZED` /
`PENDING_LATER_PIM_REVIEW`); no G13.
