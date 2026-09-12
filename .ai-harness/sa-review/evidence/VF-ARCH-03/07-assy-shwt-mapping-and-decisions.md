# 07 — ASSY / SH WTP Mappings, STOP Assessment & Decisions (Issue #42 §K)

## 7.1 ASSY conceptual mapping (no runtime rewrite)

The contracts apply to ASSY without rewriting `AssyLineRuntime`:

- **Observations/events:** stations, WIP, quality decisions, genealogy, and
  lifecycle facts project into observations/events via the existing observation
  seam (`observation_bridge`, `projection.EventView`, `scene.EventMarkerView`,
  `MESEventType`).
- **Alarms:** any quality/attention event remains an **Event specialization**
  (`AlarmEvent(MaintenanceEvent)` precedent), never a parallel store.
- **Capabilities:** station `Capabilities` flags are execution/domain
  capabilities; ASSY-specific behaviors (e.g. AP06 retest, AP04 join) remain
  domain features — **no workspace-name hard-coded routing** (capability-driven
  dispatch already in place).
- **Readiness:** ASSY scope readiness aggregates sub-line scope readiness +
  station capability states + scenario config.

## 7.2 SH WTP conceptual mapping (no invented plant truth)

Conceptual only; do **not** invent site topology or site-verified semantics:

- **Observations:** continuous-process/equipment observations
  (level/flow/pressure/quality signals) → observation seam.
- **Alarms/events:** threshold/alarm events from signal state (like
  `AlarmConfig`), as Event specializations.
- **Capabilities:** continuous/domain capabilities (e.g. `continuous.balance`)
  + water-quality domain features (e.g. `shw.water_quality`) — illustrative.
- **Readiness:** aggregated from capability states + PIM semantic-binding
  compatibility (SH WTP `semantic_binding.mode: required` → fail-closed) +
  `runtime.engine` + fidelity ceiling (`logical_only` baseline).

## 7.3 STOP-condition assessment

| Stop condition | Assessment |
|---|---|
| Competing accepted observation/event authority conflicts with target pipeline | NOT triggered — existing `observation/` + `telemetry/` seams align with `Runtime State → Observation → Projection`. |
| Alarm cannot be an Event specialization without breaking semantics | NOT triggered — `AlarmEvent(MaintenanceEvent)` already models Alarm ⊂ Event; `AlarmConfig` derives alarms from signals. |
| Capability/readiness requires a breaking Owner/SA decision | NOT triggered — capability flags + PH00/PIM readiness already frozen; aggregation is additive. |
| Provenance/evidence separation conflicts with PIM/VF contracts | NOT triggered — PH00 §10 provenance + PIM evidence policy are already distinct axes. |
| Requires choosing ARCH-04 UI architecture prematurely | NOT triggered — only data-authority relationship frozen; UI layout deferred. |
| Requires fabricating site truth / source mapping / readiness | NOT triggered — synthetic provenance vocabulary + PIM evidence statuses suffice; nothing fabricated. |

**Conclusion: no STOP condition triggered.**

## 7.4 Frozen decisions (ARCH-03)

1. `Runtime State → Observation → Monitoring / Live Series / Export / Integration`
   — Runtime State is the only mutable truth; Observation is immutable/downstream;
   projections cache/index but never mutate truth.
2. `Runtime Activity → Event → Alarm` — **Alarm ⊂ Event**; Alarm List and Event
   Timeline are projections over the event model.
3. Live Series (bounded current-run) ≠ Historian (durable, outside baseline);
   Run Result = finalized summary, not a warehouse.
4. Capability namespaces: platform / execution-domain / workspace-feature —
   separated; no workspace-name hard-coding.
5. Capability states: `available` / `not_applicable` / `not_ready` /
   `restricted` / `error/degraded` (with error vs degraded as operational
   substates of the combined class).
6. Workspace/scope readiness = deterministic categorical aggregation of
   capability + binding + runtime + child-scope states; never a competing
   evaluator; never hides blockers; no arbitrary health score.
7. Provenance ≠ Evidence: VF owns provenance (`origin_kind=simulation`,
   synthetic vocabulary); PIM/external owns evidence (`SourceMapped`,
   `SiteVerified`, …); VF never upgrades evidence, never relabels synthetic as
   measured/site truth.
8. Monitoring and Context Inspector share the same observation/event facts,
   differing only by interaction perspective (data authority, not two stores).
9. Preserved: ARCH-01 structural identity; ARCH-02 runtime composition/isolation;
   PIM semantic authority; `AssyLineRuntime` not rewritten.

## 7.5 Explicit non-decisions (deferred to ARCH-04+ / implementation gates)

1. Production Observation/Event/Alarm classes or DB schemas.
2. Production capability registry classes.
3. Dashboard/widget implementation.
4. UI navigation/layout (ARCH-04).
5. Historian/storage engine.
6. Alarm workflow/notification engine.
7. TIPA/ASSY migration implementation.
8. SH WTP runtime/domain models.
9. Semantic loader/binding implementation.
10. Provenance persistence implementation.
11. Real plant-control/acknowledgement authority.
12. Advanced RBAC.
13. Frontend framework migration.
