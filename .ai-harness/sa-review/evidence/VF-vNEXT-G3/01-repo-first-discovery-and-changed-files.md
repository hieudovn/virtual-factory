# VF-vNEXT-G3 · Evidence 01 — Repo-first discovery + changed files

## 1. Issue scope (Issue #48)

Align Observation / Event / Alarm production contracts with ARCH-03: runtime
state = sole mutable truth; Observation = immutable downstream fact; typed
immutable Event fact; Alarm ⊂ Event; AlarmState = derived projection; EventStore
= append-style typed facts; Observation compatible + non-fabricating G1/G2
context seam; reuse G2 provenance; no capability/readiness, coordinator/ports,
ASSY federation, UI, run-control, semantic binding, historian, alarm-workflow,
or AssyLineRuntime rewrite.

## 2. Repo-first discovery (actual accepted G2 head)

- `src/virtual_factory/observation/` — substantial, consumer-neutral:
  `ObservationEnvelope` (frozen, deeply protected context/payload via
  MappingProxyType, idempotency), `ObservationService` builds immutable
  envelopes from `RealityInput`, point/policy/router/projections/identity.
  Decision: do NOT rewrite; only add a small additive seam module.
- `src/virtual_factory/telemetry/event_store.py` — mutable `list[dict]` skeleton
  with `append(dict)`. Zero importers in src/tests. Decision: adapt to
  append-only typed immutable `EventFact` store (Issue #48 E).
- `src/virtual_factory/telemetry/alarm_manager.py` — `AlarmManager` evaluates
  configured `AlarmConfig` → writes `industrial_event` `SignalValue` into
  runtime state and keeps a mutable `AlarmState` (id, active, severity, message,
  last_value, timestamp_s). Imported by `core/runtime_factory.py`,
  `core/simulation_engine.py`, `ui/runtime_service.py`. Decision: additive
  immutable alarm Event-fact emission on transitions; keep `evaluate()`
  signature/return and `AlarmState` semantics.
- `src/virtual_factory/provenance/` (G2 accepted) — `ProvenanceV2`,
  `RunContextV2` etc. reused additively; no second provenance model.
- Precedent for Alarm ⊂ Event: `maintenance/event_generator.py`
  `AlarmEvent(MaintenanceEvent)` (ARCH-03 §3.2). G3 Event model is a separate,
  dependency-light platform fact (not a redesign of discrete/maintenance
  events).

## 3. Reuse / adapt / new / defer classification

| Item | Class | Reason |
|---|---|---|
| `ObservationEnvelope`/`ObservationService` | REUSE (unchanged) | consumer-neutral, heavily tested; do not rewrite (Issue A) |
| `provenance.ProvenanceV2` | REUSE (read-only) | G2 seam, no second model |
| `EventStore` | ADAPT | skeleton → typed append-only store |
| `AlarmManager`/`AlarmState` | ADAPT (additive) | emit alarm Event facts; AlarmState stays derived projection; signal output unchanged |
| `telemetry/event_fact.py` | NEW | typed immutable platform Event fact + Alarm specialization |
| `observation/alignment.py` | NEW | non-fabricating G1/G2 context carry seam |
| capability/readiness, coordinator, UI, run-control, binding, historian, workflow | DEFER | G4+ / explicitly out of scope |

## 4. Changed files (13)

Production:
- `src/virtual_factory/telemetry/event_fact.py` (new)
- `src/virtual_factory/telemetry/event_store.py` (adapted)
- `src/virtual_factory/telemetry/alarm_manager.py` (additive)
- `src/virtual_factory/observation/alignment.py` (new)

Tests (new):
- `tests/test_event_fact.py`
- `tests/test_event_store.py`
- `tests/test_alarm_event_facts.py`
- `tests/test_observation_alignment.py`

Harness:
- `.ai-harness/tasks/VF-vNEXT-G3.json`
- `.ai-harness/sa-review/CURRENT.md`
- `.ai-harness/sa-review/reports/VF-vNEXT-G3.md`
- `.ai-harness/sa-review/evidence/VF-vNEXT-G3/` (01…07)

No forbidden domain file changed (observation existing files, discrete,
assembly, core, ui, integration, maintenance, provenance, workspace, telemetry
frame/init untouched).
