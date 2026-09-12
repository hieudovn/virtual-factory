# VF-vNEXT-G4 · Evidence 05 — Coordinator

`src/virtual_factory/composition/coordinator.py`.

## API

```python
class Coordinator:
    def __init__(self, workspace: Workspace, graph: CompositionGraph)
    def register(self, participant: ExecutableParticipant) -> None
    def run_window(self, window_id, target_time_s) -> WindowOutcome

@dataclass(frozen=True, slots=True)
class WindowOutcome:
    window_id; target_time_s
    participants: tuple[str, ...]   # deterministic scope-path order
    committed: tuple[str, ...]      # deterministic transfer-id order
    status: "completed" | "failed"
    failure: str | None
```

## Frozen phase semantics

`validate -> advance participants -> stage outputs -> validate transfers ->
commit inputs -> finalize window outcome`.

- Participants resolved deterministically (sorted by scope path), independent of
  registration order.
- Graph/port bindings validated BEFORE execution (invalid binding detected
  pre-advance).
- Each participant `advance_to(target)` in order, staging declared outbound
  transfers; duplicate transfer id fails.
- All staged transfers validated before ANY commit: workspace matches graph;
  binding (edge id + endpoints) declared; port compatibility (direction/category/
  unit/descriptor); both endpoint scopes registered; baseline input at most one
  producer (implicit many-to-one merge rejected).
- Commit grouped by target scope path then transfer id; a commit failure stops
  further commits.
- Cycles are safe: all participants fully advance to the boundary (staging
  detached values) before any commit — no recursive execution through graph
  edges, no consumer sees another scope's partially-advanced mutable state.

## Coordinator MUST NOT own (verified by scope, not implemented)

AP/WIP/quality/genealogy, pump/tank/process physics, recipe/phase rules, domain
control logic, PIM semantics, alarm/monitoring truth, UI state. The coordinator
only calls the participant surface (`scope_path`, `advance_to`,
`commit_transfers`).

## Failure semantics (fail closed, honest)

- invalid graph/binding -> fails before window execution;
- participant advance failure -> stops the window before later exchange/commit;
- transfer validation failure -> prevents boundary commit;
- commit failure -> marks failure and stops further commits;
- NO transactional rollback of already-advanced child runtime state is claimed
  (no snapshot/checkpoint restore).

## Proofs (`tests/test_composition_coordinator.py`)

deterministic registration-order independence; cyclic staged exchange; different
cadences reach one boundary; container-only and dangling-scope registration
rejected; backward time fails; advance failure stops before exchange; undeclared
exchange rejected; multi-producer input rejected; commit failure stops commits
without rollback; no direct cross-scope mutation via payload; already-at-boundary
no-op; later-participant failure does not roll back earlier participants.
