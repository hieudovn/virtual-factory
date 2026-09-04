# SA REVIEW INBOX

Task: VF-vNEXT-G4-C02
Status: READY FOR SA REVIEW (C02: producer coordination interval [before, target]; execution-time registered-vs-current scope_path identity)
Parent: Implementation phase (umbrella #39 VF-vNEXT-ARCH CLOSED; only authorized implementation gate)
Prerequisite: G3 PASS / COMPLETE at 8edb9f4cce0410ea2f0b15e6e1eb1607c4fdc5e7 (#48 CLOSED)

Gate type:
Accelerated implementation gate — Implement Composition Graph + Coordinator + Typed Boundary Ports (G4), correction C02

Architecture baseline:
ARCH-01..06 accepted; G3 base 8edb9f4cce0410ea2f0b15e6e1eb1607c4fdc5e7
Production base SHA: canonical main @ f5261c8 (inspected; not merged)

Implemented (new package src/virtual_factory/composition/):
- ports.py: typed boundary ports — PortRef (owner scope + port id), BoundaryPort
  (direction in/out; category material/utility/information/coordination;
  optional unit/descriptor), PortRegistry, check_port_compatibility (fail-closed
  direction/category/unit/descriptor rules).
- graph.py: CompositionGraph + CompositionBinding — directed declared bindings
  over G1 identity; CYCLES ALLOWED (no DAG); deterministic enumeration;
  dangling/duplicate edge id/duplicate logical binding/cross-workspace fail
  closed; fan-out deterministic; disconnected nodes allowed.
- transfer.py: BoundaryTransfer — detached/immutable staged exchange value;
  deep-frozen JSON-compatible payload (no callable/runtime-object reference);
  workspace identity fail-closed.
- participant.py: ExecutableParticipant protocol (mechanism-neutral:
  scope_path/current_time_s/advance_to/commit_transfers; no one-engine-per-scope,
  no identical dt/scheduler).
- coordinator.py: Coordinator + WindowOutcome — deterministic
  validate -> advance -> stage -> validate transfers -> commit -> finalize;
  fail-closed failure semantics WITHOUT false rollback claims.

Frozen invariants preserved:
- Containment tree separate from composition graph; cycles allowed.
- Coordinator is a composition service, not a domain engine (owns no domain truth).
- Exchange only via declared typed boundary ports; no direct cross-scope state
  mutation; staged transfer detached/immutable.
- Deterministic ordering independent of declaration/registration order (sorted by
  structural identity).
- Container-only scope cannot be registered as executable participant.
- No PIM canonical identity fabricated; no false rollback claim.
- No AssyLineRuntime rewrite; no G5+.

Self-audit (5 invariant matrices, evidence 06): identity/authority; port
compatibility; graph/order; time/window; mutation/isolation — each audited with
positive/negative tests; no same-class defect left; no new architecture decision
required.

C01 corrections applied (coordinator authority, evidence 09):
- C01-1 producer ownership fail-closed: transfer staged by scope X must have
  source.owner_scope == X; source-scope mismatch fails before commit.
- C01-2 window authority: staged transfer must carry exactly the active
  window_id; simulation_time_s finite (NaN/Inf rejected) and <= target boundary;
  coordinator rejects NaN/Inf target.
- C01-3 multi-producer is a declared-graph error: CompositionGraph rejects
  implicit many-to-one input at build time (not only emitted transfers); fan-out
  remains allowed.
- C01-4 endpoint scope resolution: every bound endpoint owner scope resolves in
  the G1 Workspace before advance; nonexistent scope fails pre-advance.
- C01-5 participant time contract: coordinator verifies current_time_s
  numeric/finite/>=0, fails if local time ahead of boundary before advance, and
  requires exact boundary landing after a successful advance_to (already-at-
  boundary remains valid no-op).
- Adversarial self-audit with broken participants + stale transfers covers all 5
  matrices (source ownership, window, time, graph multi-producer, scope
  resolution).

C02 corrections applied (authority-triangle completion, evidence 10):
- C02-1 producer coordination interval: every staged transfer time must satisfy
  before <= simulation_time_s <= target_time_s for the emitting participant
  (equality allowed; no epsilon/tolerance invented; no global timestep); a stale
  transfer below the producer's lower bound fails the window before commit.
- C02-2 execution-time participant identity: before advancing each participant,
  run_window re-reads participant.scope_path; it must still be a StructuralPath
  and exactly equal the registered scope key (drift / invalid type / foreign
  scope fails closed before that participant advances). No silent re-key or
  re-register mid-window.
- Full authority triangle enforced: registered scope key == current
  participant.scope_path == transfer.source.owner_scope; plus participant
  pre-window time <= transfer time <= target boundary; active window_id ==
  transfer.window_id.

Test / regression results:
- New G4 tests: 53 passed (incl. C01 + C02).
- G1 workspace: 32 passed.
- G2 provenance: 36 passed.
- G3 Observation/Event/Alarm (+ M5 + alarm_manager): 328 passed.
- Core graph/port/runtime: 21 passed.
- Discrete runtime/scheduler: 279 passed.
- ASSY regression oracle: 354 passed.
- Continuous/compressor baseline: 61 passed.
- Full repository suite: 1846 passed (0 failures).
- Compile check PASS (no configured ruff/mypy/black in repo).

Deferred (NOT implemented): G5 ASSY federation, G6 UI, G7 run-control/UI/API,
replay/restart policy, G8, G9 semantic binding, G10 SH-WTP runtime, final
material/energy schemas, numerical coupling solver, historian/database,
real-plant control, frontend changes, AssyLineRuntime rewrite, legacy WTP
mini-engine migration/deletion.

STOP conditions: none triggered.

G5 started: NO

Report:
.ai-harness/sa-review/reports/VF-vNEXT-G4.md

Evidence:
.ai-harness/sa-review/evidence/VF-vNEXT-G4/ (10 files: 01…10; 09 = C01 corrections + adversarial self-audit; 10 = C02 corrections)





