# 06 — Provenance vs Evidence, Series Boundaries, Monitoring/Context-Inspector (Issue #42 §H, §I, §J)

## 6.1 Provenance ≠ Evidence (frozen separation)

| Axis | Meaning | Owner | Examples |
|---|---|---|---|
| **Provenance** | origin/run/scope/scenario/model context of runtime output | **VF** | `workspace_id`, scope path/id, `run_id`/attempt id, `scenario_id`, model/version, `origin_kind = simulation`, synthetic origin vocabulary |
| **Evidence / trust** | basis for semantic/site trust | **PIM / external semantic authority** | `SourceMapped`, `SiteVerified`, `missing`, `assumed`, `pending mapping` |

Rules:

1. VF may **attach/reference** evidence metadata supplied by semantic
   authorities (PIM), read-only.
2. VF must **not upgrade evidence maturity by itself** (no `assumed → SourceMapped`
   promotion by VF).
3. **Simulated/synthetic output must never be relabeled as measured / site
   ground truth.** VF output carries `origin_kind = simulation`,
   `data_status = synthetic | simulated_ground_truth` (PH00 §10/B6).

Repo evidence: PH00 §10 output-provenance envelope (VF provenance fields +
`canonical_signal_id` consumed read-only); PIM `evidence_policy.yaml`
(evidence statuses + `Expected → SourceMapped → SiteVerified` promotion owned by
PIM).

## 6.2 Live series vs Historian vs Run Result

| Concept | Boundary |
|---|---|
| **Live Series** | Bounded **current-run rolling observations** (`RingBufferTelemetryStore`, maxlen). NOT durable. |
| **Historian** | Durable retention/query capability **outside VF baseline** (PlantOS / PI / Canary / Data Platform) unless explicitly added later. |
| **Run Result** | Finalized run summary/projection: run/scenario identity, final state, selected KPIs, event/alarm summary, provenance. NOT a full historian/warehouse. |

No retention policies or database schema are designed here.

## 6.3 Monitoring vs Context Inspector — shared data authority

Both are **projections over the same observation/event facts**; neither owns
runtime truth:

| Consumer | Perspective |
|---|---|
| **Context Inspector** | Object-centric consumer of observations/events (drill into one object/scope). |
| **Monitoring** | Scope/area-centric consumer of the same facts (live series + alarms). |

- Drill-down references the **same structural/run context** (scope path, object
  id, run id) rather than duplicating state.
- No UI layout/components are designed in ARCH-03 (deferred to ARCH-04).
