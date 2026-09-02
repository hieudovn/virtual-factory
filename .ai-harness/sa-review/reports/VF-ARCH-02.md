# VF-ARCH-02 — Freeze runtime composition contract

| Field | Value |
|---|---|
| Task ID | `VF-ARCH-02` (GitHub Issue #41) |
| Parent | Issue #39 `VF-vNEXT-ARCH` (umbrella architecture program) |
| Prerequisite | ARCH-01 / Issue #40 CLOSED by SA as `completed` |
| Repository | `hieudovn/virtual-factory` |
| Gate type | Architecture / design gate — documentation & evidence only (no production implementation) |
| Architecture baseline | ARCH-01 package @ `feature/vf-arch-01` `41903e186e96a05726483e4a17b9ac2d9cd56655` |
| Production baseline | canonical `main` lineage (`f5261c8…`; unchanged) |
| Production code changed | **NO** (only `.ai-harness/`) |
| ARCH-03 started | **NO** |

## 1. Objective

Freeze the minimum runtime-composition contract to coordinate multiple
executable Simulation Scopes safely and deterministically **without turning the
coordinator into a second domain engine** (God Engine).

## 2. Repo-first discovery (evidence 01)

Verified seams at the ARCH-01 baseline:

- `AssyDemoComposition.step_all()` — `COMMON_DEMO_CLOCK`, six isolated
  `AssyLineRuntime` contexts, **no equal-sim-time assertion**, fault-exclusion,
  `reset()/snapshot()`. Demo orchestration, not plant synchronization truth.
- `AssyLineRuntime` — single source of domain truth (not rewritten).
- `discrete/` — full lifecycle `CREATED→…→FAILED`, `DiscreteRunController/Service`,
  deterministic event scheduler.
- `core/` — `SimulationEngineProtocol` + `TimeManager` fixed-step tick +
  `RuntimeAssembly` + `PlantGraph` + `Port`.
- `scenarios/` — `ScenarioManager.apply_due_actions`.

## 3. Frozen decisions (summary; detail in evidence 02–07)

1. **Ownership** (evidence 02): workspace host, executable scope runtime,
   container-only scope, coordinator, domain engine, run context, scenario
   context — non-overlapping may/may-not-mutate.
2. **Run lifecycle** (evidence 03): validate → create → start → step/pause/resume
   → stop → reset; replay distinct from reset. One workspace run owns child run
   contexts.
3. **Time & synchronization** (evidence 04): composition time vs scope-local
   time vs sync boundary vs internal cadence vs wall-clock. **Invariant:
   synchronized composition does NOT require identical timestep/scheduler.**
4. **Determinism** (evidence 04): stable ordering key; explicit inputs/seed;
   no dict/set/hash/time-of-day ordering; replay ≠ snapshot restore.
5. **Coordinator** (evidence 05): owns composition only; anti-responsibilities
   fixed (no AP/WIP/quality, physics, recipe, control logic, PIM, monitoring).
6. **Boundaries** (evidence 05): material / utility-energy / information-observation /
   coordination-event categories; structural identity (not PIM canonical);
   boundary exchange is the only cross-scope data path; direct mutation forbidden.
7. **Hybrid archetypes** (evidence 06): C+C, D+D, C+D, Batch+C compose without a
   shared engine.
8. **ASSY mapping** (evidence 06): six executable sub-line scopes over existing
   `AssyLineRuntime`; demo policy ≠ plant truth.
9. **PH00 `runtime.engine`** (evidence 07): compatibility/default/profile
   descriptor; not one-engine-per-workspace; no schema change.

## 4. STOP-condition assessment

None triggered (evidence 07 §7.2): composition does not require rewriting
`AssyLineRuntime`; hybrid composition needs no forced global engine; no breaking
contract conflict; `runtime.engine` reconciled without schema change; determinism
is mechanism-agnostic; boundaries use structural identity; ARCH-03 concerns
deferred.

**Conclusion: no STOP condition triggered.**

## 5. Acceptance

| Criterion | Result |
|---|---|
| Runtime ownership explicit and non-overlapping | PASS (02) |
| Executable vs container-only consistent with ARCH-01 | PASS (02/03/05) |
| Common run lifecycle explicit | PASS (03) |
| Parent/child run relationship explicit | PASS (03) |
| Time/sync allows different mechanisms/cadences | PASS (04) |
| Deterministic ordering/replay contract explicit | PASS (04) |
| Coordinator responsibilities and anti-responsibilities explicit | PASS (05) |
| Inter-scope boundary categories and mutation authority explicit | PASS (05) |
| Hybrid archetype composition maps without one forced engine | PASS (06) |
| ASSY maps without runtime rewrite or demo-policy overclaim | PASS (06) |
| PH00 `runtime.engine` reconciled safely | PASS (07) |
| Later-gate concerns deferred | PASS (07 §7.4) |
| No production code changed | PASS (only `.ai-harness/`) |

## 6. Evidence

`.ai-harness/sa-review/evidence/VF-ARCH-02/` — 7 files (01…07).

## 7. Final status

```text
VF-ARCH-02 — READY FOR SA REVIEW
```

PM does not self-certify COMPLETE/CLOSED. ARCH-03 is NOT started; all
implementation non-decisions remain deferred.
