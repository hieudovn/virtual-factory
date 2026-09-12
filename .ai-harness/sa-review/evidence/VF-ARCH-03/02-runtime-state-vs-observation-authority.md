# 02 — Runtime State vs Observation: Authority Boundary (Issue #42 §A, §B)

## 2.1 Source-of-truth matrix

| Concept | Authority | Mutability | Notes |
|---|---|---|---|
| **Runtime State** | Executable scope runtime (`RuntimeState`, ASSY domain state, `DiscreteRunState`) | Mutable (only via its own runtime semantics) | The authoritative mutable simulation truth. |
| **Observation** | Emitted as an immutable fact/projection **from** runtime truth | Immutable / append-style | `ObservationEnvelope` is frozen; never mutated back into truth. |
| **Live Series / rolling buffer** | Bounded projection cache (`RingBufferTelemetryStore`) | Append/evict bounded | Current-run rolling observations; not truth, not historian. |
| **Monitoring projection** | Consumer (view/UI/service) | Read-only view | Scope/area-centric view over observations/events. |
| **Export / Integration projection** | Gateway/protocol projection | Read-only publish | Publishes policy-allowed observations; never writes truth. |
| **Run Result summary** | Finalized run projection | Immutable summary | Run/scenario identity, final state, selected KPIs, event/alarm summary, provenance. |

## 2.2 Frozen rules (Runtime State → Observation)

1. **Runtime State is the only authoritative mutable truth** inside an
   executable scope.
2. **Observation is downstream** — an immutable/append-style fact or projection
   emitted from runtime truth. It is never a parallel mutable runtime state.
3. **Projections may cache/index** (e.g. live series, event store) but **may not
   silently mutate runtime truth**.
4. **Monitoring ≠ result storage**: monitoring views are projections; durable
   retention is not their authority.
5. **Live series ≠ historian**: VF baseline live series is a bounded
   current-run buffer; durable historian retention belongs to PlantOS / PI /
   Canary / Data Platform or a future explicit capability (see evidence 06).

## 2.3 Observation identity / context (conceptual minimum)

An observation conceptually carries enough to distinguish its origin, without
conflating with PIM canonical identity or `outputs.namespace`:

| Field | Meaning |
|---|---|
| workspace structural identity | `workspace_id` (VF structural identity) |
| scope identity / path | `scope_id` / hierarchical scope path |
| object / runtime identity | object id or runtime-local key (where applicable) |
| run identity / attempt identity | `run_id` (+ attempt identity after a restart) |
| scenario context | `scenario_id` (where applicable) |
| simulation time / coordination point | `simulation_time_s` / coordination point |
| origin / provenance category | `origin_kind = simulation`; synthetic provenance vocabulary |
| semantic binding reference | PIM semantic binding metadata **where available** (read-only) |

Repo evidence: `ObservationEnvelope` already carries `run_id`, `model_id`,
`source_event_id`, `source_path`, `simulation_time_s`, subject/context,
correlation/causation; PH00 §10 adds `workspace_id`, `scenario_id`,
`runtime_signal_id` vs `canonical_signal_id`, `origin_kind`, `data_status`.

These are **VF structural/provenance fields**, distinct from PIM canonical
semantic identity and `outputs.namespace` (ARCH-01 identity invariants).
