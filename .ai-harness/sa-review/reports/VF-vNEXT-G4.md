# VF-vNEXT-G4 — Implement Composition Graph + Coordinator + Typed Boundary Ports

| Field | Value |
|---|---|
| Task ID | `VF-vNEXT-G4` (GitHub Issue #49) + C01 + C02 |
| Program | Implementation phase (G4; only authorized implementation gate) |
| G3 base (required) | `8edb9f4cce0410ea2f0b15e6e1eb1607c4fdc5e7` |
| Branch | `feature/vf-vnext-g4` |
| Production base (`origin/main`) | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` |
| G5+ started | **NO** |

## 1. Objective

Implement the smallest reusable production foundation for hierarchical scopes +
connectivity graph + executable participants + typed boundary exchange +
deterministic coordinator, preserving the frozen rule that the Coordinator is a
composition service, not a domain simulation engine. Independent executable
scopes with different mechanisms/cadences participate deterministically without
direct cross-scope state mutation.

## 2. Implementation (production — new `composition/` package)

- `ports.py` — typed boundary ports: `PortRef` (owner scope + port id),
  `BoundaryPort` (direction in/out, category material/utility/information/
  coordination, optional unit/descriptor), `PortRegistry`,
  `check_port_compatibility` (fail-closed direction/category/unit/descriptor).
- `graph.py` — `CompositionGraph` + `CompositionBinding`: directed declared
  bindings over G1 identity; cycles allowed; deterministic enumeration;
  dangling/duplicate/cross-workspace endpoints fail closed.
- `transfer.py` — `BoundaryTransfer`: detached/immutable staged exchange value;
  deep-frozen JSON-compatible payload; workspace identity fail-closed.
- `participant.py` — `ExecutableParticipant` protocol (mechanism-neutral:
  scope_path, current_time_s, advance_to, commit_transfers).
- `coordinator.py` — `Coordinator` + `WindowOutcome`: deterministic
  validate/advance/stage/validate/commit/finalize; fail-closed failure semantics
  without false rollback. C01 enforcement: the emitting participant is the
  authoritative producer (source-scope mismatch fails); staged transfers must
  carry exactly the active window and a finite time within the boundary;
  graph-level multi-producer ambiguity rejected; bound endpoint scopes resolved
  in the G1 Workspace pre-advance; participant current_time verified before/after
  advance (must land exactly on the boundary). C02 enforcement: every staged
  transfer time must fall inside the emitting participant's coordination
  interval [before, target_time_s] (equality allowed; no epsilon; no global
  timestep); and the registered structural identity is re-verified against
  `participant.scope_path` immediately before advance (drift or invalid type
  fails closed).

No forbidden file modified; `workspace`, `provenance`, `observation`, `telemetry`,
`discrete`, `assembly`, `core`, `ui`, `integration` untouched.

## 3. Architecture / reuse classification (evidence 01)

G1 identity reused (graph endpoints); G2 identity referenced (transfer run/
workspace id); G3 untouched; `core/ports.py`, `core/plant_graph.py`,
`core/engine_contract.py`, `assembly/demo_composition.py`, `discrete/clock.py`
are legacy-references (not collapsed, not rewritten). New generic composition
seam is distinct from PlantGraph.

## 4. Deterministic-order strategy

- Graph bindings sorted by `(source, target, edge_id)`; nodes by canonical
  endpoint string.
- Participants resolved by structural scope path (sorted), independent of
  registration order.
- Staged transfers committed by target scope path then transfer id.
- Port registry ordered by canonical ref.

## 5. Invariant matrices (evidence 06)

Five matrices audited with positive/negative tests: identity/authority; port
compatibility; graph/order; time/window; mutation/isolation. No same-class defect
left unaddressed; no new architecture/schema decision required.

## 6. Test / regression results (evidence 07)

| Suite | Result |
|---|---|
| New G4 tests | **53 passed** (incl. C01 + C02) |
| G1 workspace | **32 passed** |
| G2 provenance | **36 passed** |
| G3 Observation/Event/Alarm (+ M5 + alarm) | **328 passed** |
| Core graph/port/runtime | **21 passed** |
| Discrete runtime/scheduler | **279 passed** |
| ASSY regression oracle | **354 passed** |
| Continuous/compressor baseline | **61 passed** |
| Full repository suite | **1846 passed** (0 failures) |
| Compile check | PASS (no configured ruff/mypy/black) |

## 7. STOP-condition assessment (evidence 08)

None triggered.

## 8. Acceptance (Issue #49 criteria)

| Criterion | Result |
|---|---|
| Generic cross-scope composition graph, distinct from containment | PASS |
| Graph cycles supported safely at staged exchange boundaries | PASS |
| Typed directional boundary ports with fail-closed compatibility | PASS |
| Transfer values detached/immutable (no mutable child state exposed) | PASS |
| Mechanism-neutral executable participant seam | PASS |
| Deterministic validate/advance/stage/validate/commit sequencing | PASS |
| Different internal participant cadences supported | PASS |
| Container-only scopes own no runtime participant | PASS |
| No direct cross-scope mutation path | PASS |
| Failure semantics explicit and honest about lack of rollback | PASS |
| Invariant matrices / self-audit complete | PASS |
| Regressions pass (anomalies honestly evidenced) | PASS (53+32+36+328+21+279+354+61+full 1846) |
| Branch/head pushed and working tree clean | PASS (after push) |

## 9. Evidence

`.ai-harness/sa-review/evidence/VF-vNEXT-G4/` — 10 files (01…10; 09 = C01
corrections + adversarial self-audit; 10 = C02 corrections).

## 10. Final status

```text
VF-vNEXT-G4-C02 — READY FOR SA REVIEW
```

PM does not self-certify COMPLETE/CLOSED. G5 is NOT started.
