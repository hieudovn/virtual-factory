# SA REVIEW INBOX

Task: VF-vNEXT-G3-C01
Status: READY FOR SA REVIEW (C01: Observation/Event run-identity coherence fail-closed; initial-active alarm assert history)
Parent: Implementation phase (umbrella #39 VF-vNEXT-ARCH CLOSED; only authorized implementation gate)
Prerequisite: G2 PASS / COMPLETE at fec6fe4127634fcf31e1c90ce23dd9a7457ebda5 (#47 CLOSED)
Reviewed head: 910317f4bd66877aeda6ae264f7ed9cc1860845f

Gate type:
Accelerated implementation gate — Align Observation / Event / Alarm Production Contracts (G3), correction C01

Architecture baseline:
ARCH-01..06 accepted; G2 base fec6fe4127634fcf31e1c90ce23dd9a7457ebda5
Production base SHA: canonical main @ f5261c8 (inspected; not merged)

Implemented:
- telemetry/event_fact.py (new): dependency-light typed immutable platform
  EventFact (event_id/type/category, occurrence time, source/severity/status,
  deep-frozen payload, G1 workspace/scope + G2 provenance only when explicit)
  + AlarmEventFact(EventFact) — Alarm specialization/category (category=ALARM).
- telemetry/event_store.py (adapted): append-only typed EventFact store (typed
  append, deterministic append order, read-only events tuple, no
  mutation/deletion; no historian).
- telemetry/alarm_manager.py (additive): evaluate()/SignalValue/AlarmState
  unchanged; emits immutable AlarmEventFacts (assert/clear); AlarmState = mutable
  DERIVED projection, never mutates facts.
- observation/alignment.py (new): non-fabricating G1/G2 context seam
  (ObservationStructuralContext + carry_structural_context); legacy envelope
  unchanged when no context.
- Runtime state stays the sole mutable truth; observation/event objects are
  downstream facts only; no PIM canonical/evidence fabricated.

C01 corrections applied:
- C01-1 run-identity coherence (fail-closed): context.run_id must equal
  ObservationEnvelope.run_id; provenance.run_id must equal envelope.run_id (all
  three agree when both present); pre-existing reserved vf.* keys conflict fails
  closed (never silently overwritten); EventFact explicit run_id/scope_path must
  agree with an accompanying ProvenanceV2.
- C01-2 alarm history: first-observed INACTIVE = baseline (no fact); first-
  observed ACTIVE emits an assert AlarmEventFact (no orphan clear); first active
  then clear => [assert, clear]; stable active/inactive emits no duplicate
  facts. SignalValue/thresholds/AlarmState preserved.

Test / regression results:
- New G3 tests: 44 passed (incl. C01 negatives/positives).
- Existing observation package (M5-S01..S05): 244 passed.
- Telemetry/alarm/event group: 27 passed.
- G2 provenance: 36 passed.
- G1 workspace: 32 passed.
- ASSY regression oracle: 354 passed (clean re-run).
- Continuous/compressor baseline: 61 passed.
- Full repository suite: 1759 passed (0 failures).
- Compile check PASS (no configured ruff/mypy/black in repo).

Pre-existing ASSY id()-flake (test_demo_composition.py::TestReset::
test_reset_creates_fresh_runtimes, same family as test_reset_creates_fresh_
configs) documented separately; passes when the file runs alone; oracle re-run
clean.

Deferred (NOT implemented): capability/readiness, G4 coordinator/ports,
G5 ASSY federation, G6 UI, G7 run-control/replay, G8, G9 semantic binding,
G10 SH WTP runtime, historian/database, alarm workflow/notification,
real-plant acknowledgement authority.

STOP conditions: none triggered.

G4 started: NO

Report:
.ai-harness/sa-review/reports/VF-vNEXT-G3.md

Evidence:
.ai-harness/sa-review/evidence/VF-vNEXT-G3/ (8 files: 01…08; 08 = C01)





