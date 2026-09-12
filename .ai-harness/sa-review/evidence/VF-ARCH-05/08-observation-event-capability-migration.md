# VF-ARCH-05 · Evidence 08 — Decision H: Observation / Event / Capability migration

## 1. Decision statement

**Existing ASSY projections map onto ARCH-03 contracts without changing runtime
truth and without creating duplicate stores. Station-level `Capabilities` are
NOT automatically promoted into a global platform capability registry; exact
implementation remains later.**

## 2. Projection mapping (runtime truth untouched)

| ASSY projection | ARCH-03 contract | Mapping rule |
|---|---|---|
| `observation_bridge.py` observation points | Observation (immutable, downstream) | ASSY observations become Observation facts; delivery stays idempotent `(run_id, source_event_id)` |
| `line_runtime.py` emitted events (`LINE_ENTRY`, `AP04_JOIN`, `QUALITY_*`, `OPERATION_TERMINAL`) | Event (immutable fact) | map to ARCH-03 event stream; no second store |
| `assy_mes_bridge.py` MES facts (quality/checklist/measurement/LINE_OUT) | Monitoring/Live-Series projection | projection over the same facts; `evidence_source="DEMO_SYNTHETIC"` preserved as VF synthetic provenance (never relabeled site truth) |
| `demo_assy_mes/*` MES demo | Monitoring (MES projection) | projection; not an independent store |
| `station_contracts.Capabilities` | Capability state | scoped to the sub-line/stations that declare them; capability-driven dispatch stays local |

## 3. Authority boundaries (ARCH-03 preserved)

- Runtime truth = `AssyLineRuntime` only. Projections cache/index but never
  mutate.
- Event Timeline + Alarm List + MES panels are projections; ack/clear lifecycle
  never rewrites the historical fact.
- VF provenance = `origin_kind=simulation` + synthetic vocabulary
  (`DEMO_SYNTHETIC`); PIM/external owns evidence; VF never upgrades evidence.

## 4. Capability promotion guard

- Station-level `Capabilities` (e.g., a station supports a checklist/measurement)
  remain **domain capabilities declared by their owner scope**.
- They are NOT promoted into a global platform capability registry in this gate;
  if/when a platform capability namespace is needed, it must come from the
  declared provider (ARCH-03 C01 authority), not be auto-collected from
  `station_contracts`.

## 5. Non-conflation

- MES/event/observation semantics are not silently changed (Issue #44).
- No duplicate store is created between `assy_mes_bridge.py` and a future
  platform Observation/Event layer: the mapping is one-way projection, with the
  platform layer as the downstream consumer of the same facts.

**Decision H is explicit; ARCH-03 contracts respected.**
