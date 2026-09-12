# VF-ARCH-05 · Evidence 03 — Decision C: Runtime reuse boundary

## 1. Decision statement

**`AssyLineRuntime` domain behavior is frozen unchanged. Migration may
introduce host/context adapters AROUND it, never changes INSIDE it. Any domain
change requires a separately authorized domain decision.**

## 2. Must remain unchanged inside `AssyLineRuntime` (reuse as-is)

| Concern | Frozen behavior | Evidence |
|---|---|---|
| Route | 12 conveyor positions `PRE-ASSY, AP01..AP11` | `conveyor.py` `ConveyorConfig.positions` |
| Feed | `produce_sso2_wip`, `produce_rso2_wip` | `line_runtime.py` |
| AP04 JOIN | requires both SSO2+RSO2 parents; `GenealogyRecord(join_station="AP04", relationship_type="assembly_join")` | `line_runtime.py::_execute_ap04_join`, `genealogy.py` |
| Quality stations | AP06 TEST→retest, AP08 VISION→reinspect, AP11 FINAL_QC | `line_runtime.py::_QUALITY_STATION_MAP` |
| failed_final | max attempts exhausted → `QualityStatus.FAILED_FINAL` (terminal, idempotent) | `line_runtime.py::_apply_quality_decision` |
| Finished-good | `WipLifecycle.RELEASED` | `wip.py`, `line_runtime.py::_execute_release_disposition` |
| Deterministic timing | `TimingResolver(seed=...)` isolated RNG; AUTO-TIME-01B reset restores stream | `line_runtime.py`, `auto_timing.py` |
| Station contracts | `Capabilities` / `CompletionMode` / `StationCommand` capability-driven dispatch | `station_contracts.py` |

## 3. Reuse / wrap / adapt matrix

| Component | Disposition | What may change (later) |
|---|---|---|
| `AssyLineRuntime` | **reuse as-is** | nothing inside; wrapped by a scope-host adapter |
| `conveyor`, `genealogy`, `quality`, `quality_records`, `auto_timing`, `upstream`, `carrier`, `wip`, `station_contracts` | **reuse as-is** | nothing |
| `sub_line_identity` | **reuse as-is** | consumed as ARCH-01 structural identity source |
| `mes_adapter`, `assy_mes_bridge`, `observation_bridge` | **reuse as-is** | projection contracts unchanged |
| `AssyDemoComposition` | **wrap/host** — reference for future federation | later: generic composition seam replaces demo feed/step policy; same `AssyLineRuntime` underneath |
| `DemoController` | **adapt composition/context only** | later: becomes a scope run facade over the generic seam |
| `demo_snapshot`, `projection`, `scene`, `topology` | **generalize later** | may become platform projection primitives |
| `tipa.py::build_tipa_topology` | **legacy/demo-only** | not migrated; superseded by `AssyLineRuntime` |

## 4. Adapter boundary (allowed vs forbidden)

**Allowed (later implementation):** introduce a host/context adapter that
provides scope identity, run boundary, and command routing to an
`AssyLineRuntime` instance — without altering the runtime's domain methods.

**Forbidden (without separate authorization):**

- forking `AssyLineRuntime` into standalone vs federated variants;
- changing route order, AP04 join parents, AP06/AP08/AP11 semantics;
- changing genealogy/quality/timing determinism;
- changing `WipLifecycle` terminal semantics;
- changing MES/observation/event fact schemas.

## 5. Conclusion

- Same domain logic in both hosts: **already true** (single `AssyLineRuntime`
  class; standalone `demo_assy.py` and six-sub-line `AssyDemoComposition` both
  instantiate it).
- The only acceptable migration shape is **wrap/adapt around a frozen core**,
  never a fork.

**Decision C is explicit.**
