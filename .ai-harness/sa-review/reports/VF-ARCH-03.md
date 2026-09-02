# VF-ARCH-03 — Freeze observation, event/alarm, capability and readiness contracts

| Field | Value |
|---|---|
| Task ID | `VF-ARCH-03` (GitHub Issue #42) |
| Parent | Issue #39 `VF-vNEXT-ARCH` (umbrella architecture program) |
| Prerequisite | ARCH-02 / Issue #41 CLOSED by SA as `completed` |
| Repository | `hieudovn/virtual-factory` |
| Gate type | Architecture / design gate — documentation & evidence only (no production implementation) |
| Architecture baseline | ARCH-01 @ `41903e18…` + ARCH-02 @ `40454487…` |
| Production baseline | canonical `main` lineage (`f5261c8…`; unchanged) |
| Production code changed | **NO** (only `.ai-harness/`) |
| ARCH-04 started | **NO** |

## 1. Objective

Freeze the contracts between runtime truth and product/UI projections:

```
Runtime State → Observation → Monitoring / Live Series / Export / Integration
Runtime Activity → Event → Alarm
```

plus the minimum capability/readiness model. Prevent four drifts: UI/telemetry
becoming a second truth; Event/Alarm duplicate stores; capability God Registry /
workspace-name hard-coding; workspace readiness becoming a competing evaluator.

## 2. Repo-first discovery (evidence 01)

Verified seams: `RuntimeState` (mutable truth), `observation/` (immutable
`ObservationEnvelope` + idempotency key), `telemetry/` (`RingBufferTelemetryStore`
bounded live series, `AlarmManager`, `EventStore`), `discrete/events.py`
(immutable `ScheduledEvent`), `maintenance/event_generator.py`
(`AlarmEvent(MaintenanceEvent)` = **Alarm ⊂ Event** precedent),
`station_contracts.Capabilities` (capability-driven dispatch), PH00 §06/§10
(readiness + output provenance), PIM `evidence_policy.yaml` (evidence statuses).

## 3. Frozen decisions (evidence 02–07)

1. **Runtime State** = only mutable truth; **Observation** = immutable/downstream;
   projections cache/index but never mutate truth.
2. **Alarm ⊂ Event**; Event Timeline and Alarm List are projections over the
   event model; alarm lifecycle never mutates the historical event fact.
3. **Live Series** (bounded current-run) ≠ **Historian** (durable, outside
   baseline); **Run Result** = finalized summary, not a warehouse.
4. **Capability namespaces**: platform / execution-domain / workspace-feature —
   separated; never hard-coded by workspace name.
5. **Capability states**: `available` / `not_applicable` / `not_ready` /
   `restricted` / `error/degraded` (error vs degraded = operational substates).
6. **Readiness** = deterministic categorical aggregation of capability + binding
   + runtime + child-scope states; never a competing evaluator; never hides
   blockers; no arbitrary health score.
7. **Provenance ≠ Evidence**: VF owns provenance (`origin_kind=simulation`,
   synthetic vocabulary); PIM/external owns evidence; VF never upgrades evidence,
   never relabels synthetic as measured/site truth.
8. **Monitoring and Context Inspector** share the same observation/event facts,
   differing only by interaction perspective.

## 4. Conceptual mappings (evidence 07)

- **ASSY:** stations/WIP/quality/genealogy → observations/events; quality alarms
  = event specializations; station capabilities = domain capabilities;
  capability-driven dispatch (no workspace-name routing).
- **SH WTP:** continuous/equipment observations, water-quality domain
  capabilities, threshold alarms, aggregated readiness — conceptual only; no
  invented site topology/site-verified semantics.

## 5. STOP-condition assessment

None triggered (evidence 07 §7.3): existing observation/telemetry seams align
with the target pipeline; Alarm ⊂ Event already holds; capability/readiness is
additive aggregation; provenance/evidence are already separate; ARCH-04 UI not
needed; nothing fabricated.

**Conclusion: no STOP condition triggered.**

## 6. Acceptance

| Criterion | Result |
|---|---|
| Source-of-truth boundaries explicit and non-overlapping | PASS (02) |
| Observation clearly downstream of runtime truth | PASS (02) |
| Event/Alarm relationship explicit | PASS (03) |
| Monitoring/live-series/run-result/historian boundaries explicit | PASS (06) |
| Capability namespaces avoid workspace-name hard-coding | PASS (04) |
| Capability state semantics explicit | PASS (04) |
| Readiness aggregation deterministic, no hidden blockers | PASS (05) |
| Provenance and evidence explicitly separated | PASS (06) |
| ASSY and SH WTP map conceptually without rewrite/invention | PASS (07) |
| Later UI/implementation concerns deferred | PASS (07 §7.5) |
| No production code changed | PASS (only `.ai-harness/`) |

## 7. Evidence

`.ai-harness/sa-review/evidence/VF-ARCH-03/` — 7 files (01…07).

## 8. Final status

```text
VF-ARCH-03 — READY FOR SA REVIEW
```

PM does not self-certify COMPLETE/CLOSED. ARCH-04 is NOT started; all
implementation non-decisions remain deferred.
