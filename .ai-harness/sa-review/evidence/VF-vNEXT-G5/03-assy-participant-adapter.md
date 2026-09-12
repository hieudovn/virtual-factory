# VF-vNEXT-G5 · Evidence 03 — ASSY runtime participant adapter (Issue #50 B)

`src/virtual_factory/federation/assy_participant.py` — `AssySubLineAdapter`

A G4 `ExecutableParticipant` adapter around ONE existing `AssyLineRuntime`
instance. `AssyLineRuntime` internals are NOT modified; the class is not
subclassed/retyped.

Contract:
- owns a fixed G1 sub-line `StructuralPath` (`scope_path`);
- `current_time_s` delegates to `runtime.simulation_time_s`;
- advancement uses ONLY existing public ASSY runtime operations, in the same
  order as the ASSY regression-oracle driver: `execute_dwell()` then
  `index_line()` when `conveyor.state == READY_TO_INDEX` (`natural_step`);
- no duplicate WIP/conveyor/quality/genealogy truth — all domain state stays in
  the wrapped runtime (`runtime` property exposes the single source of truth);
- no one-engine-per-scope abstraction beyond the wrapped runtime;
- no direct cross-scope state access; `commit_transfers` fails closed on any
  inbound (ASSY sub-lines exchange nothing at G5 boundaries).

Natural-boundary rule (no hidden rewrite): `advance_to(target)` loops natural
steps while `runtime.simulation_time_s < target`; a natural step that lands
ABOVE the target raises `ParticipantError` ("natural ASSY boundary … overshoots
… not reachable without fractional dwell/time rewrite"); success is reported
only on an EXACT landing. Backward targets are rejected. The G4 coordinator
therefore fails the window (never fabricates time) for any boundary that is not
a legitimately reachable natural ASSY boundary.

Proven by tests:
- `TestAdapterTimeAndBoundary.test_adapter_current_time_delegates_to_runtime`
  (time delegation);
- `test_unreachable_fractional_boundary_fails_closed` (target 60 vs nominal 120
  → window failed, no commit, no fractional dwell);
- `test_adapter_rejects_backward_target` (coordinator "ahead of boundary");
- `TestAssyContainerOnly` (non-StructuralPath rejected; container scope cannot
  register — existing G4 rule);
- `TestFederationHost.test_adapter_conforms_to_g4_participant_protocol`
  (runtime-checkable protocol conformance).
