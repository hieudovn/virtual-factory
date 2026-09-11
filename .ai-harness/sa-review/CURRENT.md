# SA REVIEW INBOX

Task: VF-vNEXT-R1
Status: READY FOR SA REVIEW (Canonical TIPA Same-Session Production Semantics)
Parent: TIPA ASSY recovery sequence R1..R4 (R0 / Issue #78 CLOSED — architecture frozen)
Prerequisite: G26 accepted at ed217c8; Issue #79 (R1) current and the ONLY authorized gate

Gate type:
IMPLEMENTATION gate — runtime/domain-run semantics only, per Issue #79 and the R0
recovery architecture. The selected canonical vNext TIPA RuntimeSession now runs
the already-accepted six-sub-line ASSY production semantics instead of advancing
six empty clocks. NO rich UI migration (R2), NO Observation/MES reintegration
(R3), NO SH-WTP/gateway work.

Base:
Technical base (branch point) = ed217c867dff048ee3774d139e53b8cfb1130251 (G26 head)
Production base SHA: canonical main @ f5261c8 (inspected; not merged; not rebased)

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
  reset.
- src/virtual_factory/runcontrol/session.py: session scenario_id is resolved to a
  pinned immutable ASSY run profile and the profile id is pinned in the run
  context.
- src/virtual_factory/assembly/demo_composition.py: the legacy accepted demo now
  DELEGATES its scenario mapping, config transforms, feed preparation and step
  driver to the same shared helpers (no two diverging implementations), keeping
  its public API/behaviour.
- tests/test_vnext_r1_production_semantics.py (NEW, 39 tests)
- .ai-harness/sa-review/evidence/VF-vNEXT-R1/
