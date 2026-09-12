# VF-vNEXT-G2 · Evidence 07 — Known limitations (deferred) + STOP assessment

## 1. Known limitations explicitly deferred

| Deferred item | Gate |
|---|---|
| Observation/Event/Alarm semantic alignment | G3 |
| Composition Graph / Coordinator / Typed Ports | G4 |
| ASSY federation migration | G5 |
| Hierarchical UI | G6 |
| Scenario/run control commands + replay orchestration (G2 carries lineage metadata only) | G7 |
| Regression baseline program | G8 |
| PIM semantic binding / canonical-id resolver / artifact validation (semantic pins are opaque in G2) | G9 |
| SH WTP runtime / domain models | G10 |
| Attaching `ProvenancedFrame` to MQTT/OPC UA publishers (protocol schema change) | later (no breaking schema authorized) |
| `outputs.namespace` consumption by protocol/export layers | later |

## 2. STOP-condition assessment (Issue #47)

| STOP condition | Assessment |
|---|---|
| Generic runtime context requires changing G1 structural identity semantics | **Not triggered** — `scope_path` reuses G1 `StructuralPath`; no G1 change |
| Two run-context models cannot be reconciled without breaking decision | **Not triggered** — thin adapter; `discrete.RunContext` untouched and converts losslessly |
| Provenance threading requires redefining Observation/Event/Alarm (G3) | **Not triggered** — threading is additive at the telemetry frame; observation untouched |
| Solution requires coordinator/ports (G4) | **Not triggered** — no coordinator/ports needed |
| Semantic pins require PIM binding/validation (G9) | **Not triggered** — pins are opaque, immutable, serialized; no validation |
| Protocol propagation requires a breaking external schema | **Not triggered** — protocol seams (SignalValue) unchanged; propagation deferred |
| Preserving ASSY/discrete requires domain runtime rewrite | **Not triggered** — `AssyLineRuntime`/discrete untouched; 354 + discrete tests pass |
| Provenance fields must fabricate PIM identity or relabel simulation as plant measurement | **Not triggered** — no canonical field exists; `origin_kind=simulation` enforced |
| Scope expands into G3+ | **Not triggered** — only context/provenance/namespace + additive telemetry seam |

**Conclusion: no STOP condition triggered.**

## 3. Notes

- One generic mechanism-neutral seam (`RunContextV2` + `ProvenanceV2`) now exists
  as the single platform authority; `discrete.RunContext` adapts into it (no
  duplicate authority).
- `engine_kind` is NOT promoted to a universal engine authority (carried as the
  informational `profile` only). ARCH-06 C01 preserved.
