# VF-vNEXT-G3 — Align Observation / Event / Alarm Production Contracts

| Field | Value |
|---|---|
| Task ID | `VF-vNEXT-G3` (GitHub Issue #48) + C01 |
| Program | Implementation phase (G3; only authorized implementation gate) |
| G2 base (required) | `fec6fe4127634fcf31e1c90ce23dd9a7457ebda5` |
| Branch | `feature/vf-vnext-g3` |
| Production base (`origin/main`) | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` |
| G4+ started | **NO** |

## 1. Objective

Implement the smallest production alignment so that
`Runtime Truth -> immutable Observation/Event facts -> projections` holds and
`Alarm ⊂ Event`, without duplicate mutable truth, without monitoring/UI as
authority, and without capability/readiness, coordinator/ports, UI, semantic
binding, run-control, historian, or alarm-workflow work. Reuse the G2 provenance
seam (no second provenance model). Preserve existing Observation and AlarmManager
backward compatibility.

## 2. Implementation (production)

- `telemetry/event_fact.py` (NEW) — dependency-light typed immutable platform
  `EventFact` (stable event_id, event_type/category, occurrence simulation time,
  source/severity/status occurrence classification, deep-frozen payload, G1
  workspace/scope + G2 provenance carried only when explicit, with provenance
  run/workspace/scope coherence fail-closed C01-1) and
  `AlarmEventFact(EventFact)` — the Alarm specialization/category (`category =
  ALARM`, alarm_id/alarm_kind/transition/threshold/message metadata beside the
  shared event identity).
- `telemetry/event_store.py` (ADAPT) — from mutable `list[dict]` skeleton to
  append-only typed `EventFact` store: `append()` validates `EventFact`,
  deterministic append-order reads, read-only `events` tuple snapshot, no
  mutation/deletion workflow, no historian/database.
- `telemetry/alarm_manager.py` (ADAPT, additive) — `evaluate()` signature/return/
  `industrial_event` output and `AlarmState` content unchanged; emits immutable
  `AlarmEventFact`s under the C01-2 contract (first INACTIVE = baseline; first
  ACTIVE emits `assert`; active↔inactive transitions emit assert/clear; stable
  states emit no duplicates); `AlarmState` remains a mutable DERIVED projection
  that never mutates facts.
- `observation/alignment.py` (NEW) — non-fabricating G1/G2 context seam:
  `ObservationStructuralContext` + `carry_structural_context()`; run-identity
  coherence fail-closed (context/provenance run_id must equal envelope run_id)
  and reserved `vf.*` key conflict fail-closed (C01-1); legacy flows with no
  context return the same envelope unchanged; existing
  `ObservationEnvelope`/`ObservationService` untouched.

No forbidden file modified. `AssyLineRuntime`, discrete, maintenance, core,
existing observation modules, provenance, workspace untouched.

## 3. Key decisions (evidence 01–05)

- **Reuse, don't rewrite:** `ObservationEnvelope`/`ObservationService` and G2
  `ProvenanceV2` are reused unchanged; alignment is additive.
- **Alarm ⊂ Event:** `AlarmEventFact` is a subtype of `EventFact` with
  `category=ALARM`; every emitted alarm fact IS an Event fact. Mutable current
  alarm condition/state (`AlarmState`) is explicitly a derived projection, never
  historical authority.
- **Append-style typed storage:** EventStore stores typed immutable facts;
  arbitrary dict mutation is rejected; no delete/mutation workflow in G3.
- **Non-fabrication:** G1/G2 identity and PIM canonical identity are never
  invented; provenance is reused, not duplicated.
- **Runtime is the sole mutable truth:** alarm outputs remain runtime
  `industrial_event` signals; Observation/Event objects are downstream facts.
- **C01-1 identity coherence:** carried `context.run_id` / `provenance.run_id`
  must equal the observation `envelope.run_id`; `EventFact` explicit run/scope
  must agree with an accompanying `ProvenanceV2`; conflicting pre-existing
  reserved `vf.*` keys fail closed (never silently overwritten).
- **C01-2 alarm history:** first-observed ACTIVE emits an `assert` fact (no
  orphan `clear`); first-observed INACTIVE is a baseline; stable states emit no
  duplicate facts.

## 4. Test / regression results (evidence 06)

| Suite | Result |
|---|---|
| New G3 tests | **44 passed** (incl. C01) |
| Existing observation package (M5-S01..S05) | **244 passed** |
| Telemetry/alarm/event group | **27 passed** |
| G2 provenance | **36 passed** |
| G1 workspace | **32 passed** |
| ASSY regression oracle | **354 passed** (clean re-run) |
| Continuous/compressor baseline | **61 passed** |
| Full repository suite | **1759 passed** (0 failures) |
| Compile check | PASS (no configured ruff/mypy/black) |

Pre-existing ASSY `id()`-flake (`test_demo_composition.py::TestReset::
test_reset_creates_fresh_runtimes`, same family as `..._fresh_configs`)
documented separately; passes when the file runs alone; oracle re-run clean
(evidence 06 §3).

## 5. STOP-condition assessment (evidence 07 §1)

None triggered.

## 6. Non-decisions / deferred (evidence 07 §2)

Capability/readiness, G4 coordinator/ports, G5 ASSY federation, G6 UI, G7
run-control, G8, G9 PIM binding, G10 SH-WTP runtime, historian/database,
alarm workflow/notification, real-plant acknowledgement authority — all deferred
/ not implemented.

## 7. Acceptance (Issue #48 criteria)

| Criterion | Result |
|---|---|
| Existing observation pipeline compatible + aligned (non-fabricating G1/G2 seam) | PASS |
| One typed immutable Event fact model | PASS |
| Alarm as Event specialization/category | PASS |
| Mutable alarm condition/state is derived projection only | PASS |
| Event storage append-style typed facts, not mutable dict authority | PASS |
| Existing alarm/telemetry behavior compatible | PASS |
| Runtime state remains sole mutable execution truth | PASS |
| No historian/workflow/capability/G4+ present | PASS |
| Mandatory regressions pass (anomalies honestly evidenced) | PASS (44+244+27+36+32+354+61+full 1759) |
| Branch/head pushed and working tree clean | PASS (after push) |

## 8. Evidence

`.ai-harness/sa-review/evidence/VF-vNEXT-G3/` — 8 files (01…08; 08 = C01
corrections).

## 9. Final status

```text
VF-vNEXT-G3-C01 — READY FOR SA REVIEW
```

PM does not self-certify COMPLETE/CLOSED. G4 is NOT started.
