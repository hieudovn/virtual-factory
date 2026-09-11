# SA REVIEW INBOX

Task: VF-vNEXT-R1-C01
Status: READY FOR SA REVIEW (R1 correction — reset clears ASSY domain hold/freeze state)
Parent: TIPA ASSY recovery sequence R1..R4 (R0 / Issue #78 CLOSED — architecture frozen)
Prerequisite: R1 accepted-for-review head 77ab1de; this correction is the ONLY authorized work

Gate type:
IMPLEMENTATION gate — runtime/domain-run semantics only, per Issue #79 and the R0
recovery architecture. The selected canonical vNext TIPA RuntimeSession now runs
the already-accepted six-sub-line ASSY production semantics instead of advancing
six empty clocks. NO rich UI migration (R2), NO Observation/MES reintegration
(R3), NO SH-WTP/gateway work.

Base:
Technical base (branch point) = 77ab1def956d9b3d5aefd7304413dedd77206597 (R1 head)
Production base SHA: canonical main @ f5261c8 (inspected; not merged; not rebased)

Correction (VF-vNEXT-R1-C01):
AssyExecutionBridge.reset(...) now clears the ASSY domain hold/freeze state of
the scopes it resets (capability-scoped: a full session reset clears every domain
hold), so a canonical TIPA session reset returns all six sub-lines to the fresh
profile baseline and the next coordination window includes all six again. The
frozen G22 same-run-id reset semantics are unchanged (same run identity, same
runtime objects, time back to 0, profile-consistent domain state, no lifecycle
change). No generic G22 lifecycle change, no R2/R3/SH-WTP/gateway work.
Evidence: .ai-harness/sa-review/evidence/VF-vNEXT-R1-C01/hold-reset.json
Proof: advance -> hold ASSY-SL03 -> 2 advances (frozen at t=120 while the other
five reach t=360) -> RuntimeSession.reset() -> held_sub_line_ids == () with the
same run id and the same six runtime objects at the fresh baseline
(t=0, dwell=0, wip=7, rso2=7, motors=0) -> next advance has 6/6 participants and
all six progress together (t=600, motor 1 each after 5 advances).

Implemented (implementation only; no new architecture proposed):
- src/virtual_factory/assembly/assy_run_profile.py (NEW): immutable AssyRunProfile
  run INPUT (profile id/version, session scenario, effective per-line scenario,
  deterministic exception target, initial SSO2/RSO2 inventory, continuous feed
  settings, provenance=simulation_synthetic_profile_input) + shared pure helpers
  (scenario quality transforms, target resolution) + shared AssySubLineRunState
  holder + the shared production driver step_prepared_line().
- src/virtual_factory/federation/assy_host.py: initialize(run_profile=...) applies
  the profile per sub-line BEFORE runtime construction (own config transform, own
  run state, own adapter) and reset_sub_line() re-prepares deterministically; the
  plain initialize() contract (six unseeded runtimes, no demo policy) is unchanged.
- src/virtual_factory/federation/assy_participant.py: prepared mode executes the
  accepted production driver through the shared helper; unprepared mode keeps the
  frozen G5 structural step (standalone/federated parity unchanged).
- src/virtual_factory/runcontrol/assy_bridge.py: ASSY-domain hold/freeze seam
  (held sub-lines are excluded from the coordination window) + profile-consistent
  reset; **R1-C01: reset also clears the scope's domain hold/freeze state**.
- src/virtual_factory/runcontrol/session.py: session scenario_id is resolved to a
  pinned immutable ASSY run profile and the profile id is pinned in the run
  context.
- src/virtual_factory/assembly/demo_composition.py: the legacy accepted demo now
  DELEGATES its scenario mapping, config transforms, feed preparation and step
  driver to the same shared helpers (no two diverging implementations), keeping
  its public API/behaviour.
- tests/test_vnext_r1_production_semantics.py (NEW, 40 tests: 39 R1 + 1 R1-C01
  hold/freeze-reset regression test)
- .ai-harness/sa-review/evidence/VF-vNEXT-R1-C01/
