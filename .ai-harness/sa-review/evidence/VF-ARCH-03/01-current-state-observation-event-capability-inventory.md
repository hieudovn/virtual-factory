# 01 — Current-State Observation / Event / Capability / Readiness Evidence Inventory

Repo-first discovery against ARCH-02 accepted head `40454487`. Each finding is
classified: **runtime truth / observation-projection seam / event-alarm seam /
capability-readiness seam / UI-demo-only / legacy-reference**.

## 1.1 Runtime truth (authoritative mutable simulation truth)

| File | Content | Class |
|---|---|---|
| `src/virtual_factory/core/runtime_state.py` `RuntimeState` | `truth` (internal physical truth), `signals`, `commands`, `diagnostics`, `streams` — the mutable execution truth of one runtime assembly. | **Runtime truth** |
| `src/virtual_factory/assembly/line_runtime.py` | ASSY domain state (WIP lifecycle, conveyor, stations, genealogy, quality) — the ASSY runtime truth. | **Runtime truth** |
| `src/virtual_factory/discrete/state.py` `DiscreteRunState` | Engine-owned lifecycle state (`run_id`, `simulation_time_s`, events, stop/failure). | **Runtime truth** |

## 1.2 Observation seam (immutable projection/fact from runtime truth)

| File | Content | Class |
|---|---|---|
| `src/virtual_factory/observation/envelope.py` | `ObservationType` (EVENT/MEASUREMENT/STATE/HUMAN_ENTRY); `ObservationEnvelope` **frozen/immutable** dataclass; deterministic idempotency key (`run_id`+`source_event_id`+`point_id`+`schema_version`). | **Observation-projection seam** |
| `src/virtual_factory/observation/point.py` | `ObservationPoint`, `TriggerKind` (ON_EVENT/PERIODIC/ON_CHANGE/MANUAL), `TriggerPolicy`, `FieldPolicy` — declaration layer. | Observation seam |
| `src/virtual_factory/observation/service.py` | `ObservationService` evaluates points against `RealityInput` (run/model/source identity, `simulation_time_s`, category, subject, context, correlation/causation) → 0..N envelopes. "Does NOT route to consumers or projections." | Observation seam |
| `src/virtual_factory/observation/{router,projection,identity}.py`, `projections/{iiot,mes}.py` | Routing + consumer projections (IIoT, MES). | Observation seam |

## 1.3 Telemetry / projection seams

| File | Content | Class |
|---|---|---|
| `src/virtual_factory/telemetry/telemetry_frame.py` | `build_publishable_frame` — policy-allowed `SignalValue`s for publication. | Observation/projection seam |
| `src/virtual_factory/telemetry/output_policy.py` | `OutputPolicy` — `internal_truth` never publishable; category gating. | Projection policy |
| `src/virtual_factory/telemetry/ring_buffer.py` | `RingBufferTelemetryStore` — **bounded** (`maxlen=3600`) current-run frames = live series (NOT historian). | Live-series seam |
| `src/virtual_factory/telemetry/event_store.py` | `EventStore` — in-memory event list (skeleton). | Event seam |
| `src/virtual_factory/telemetry/alarm_manager.py` | `AlarmManager` + `AlarmState` — evaluates `AlarmConfig` from measured/industrial signals → alarm samples (a projection of signals, not a parallel store). | Event-alarm seam |

## 1.4 Event / alarm model

| File | Content | Class |
|---|---|---|
| `src/virtual_factory/discrete/events.py` | `ScheduledEvent` — immutable frozen event record (pure data). | Event seam |
| `src/virtual_factory/discrete/trace.py` | `EventTraceEntry` — event trace record. | Event seam |
| `src/virtual_factory/maintenance/event_generator.py` | `EventType` (ALARM, OPERATOR_LOG, INSPECTION, WORK_ORDER, …); `MaintenanceEvent`; **`AlarmEvent(MaintenanceEvent)`** (subclass, `event_type=ALARM`) — direct repo precedent for **Alarm ⊂ Event**. | Event-alarm seam |
| `src/virtual_factory/core/schema.py` `AlarmConfig` | Alarm configured from a measured/industrial `source_signal` (validated link) — alarms are derived from signals, not independent truth. | Event-alarm seam |
| `src/virtual_factory/assembly/projection.py` `EventView`, `scene.py` `EventMarkerView` | Event view/marker projections. | UI projection |

## 1.5 Capability / readiness seam

| File | Content | Class |
|---|---|---|
| `src/virtual_factory/assembly/station_contracts.py` `Capabilities` | Station capability flags (execution/checklist/measurement/quality_decision/exception/identity_transformation/final_disposition); capability-driven dispatch ("never from a hard-coded `if AP03 / if AP06` branch table"). | Capability seam |
| `src/virtual_factory/assembly/line_runtime.py` (C01-01) | Capability-driven dispatch; command-aware gating. | Capability seam |
| PH00 evidence `06-workspace-contract-proposal.md` | Workspace readiness inputs: `semantic_binding.mode`, `compatibility.status`, `runtime.engine`, `fidelity_ceiling`. | Readiness seam |
| PIM `vf_readiness` profile (`SHW-PIM-VF-EXPORT-v0.1`) | `fidelity_readiness` (NotReady/LogicalOnly/FirstOrderReady/ParameterizedReady/CalibratedReady); required/optional/missing parameters + gaps. | Readiness seam (PIM-side) |

## 1.6 Provenance / evidence

| File | Content | Class |
|---|---|---|
| PH00 evidence `10-output-provenance-contract.md` | Output provenance envelope: `workspace_id`, `run_id`, `scenario_id`, `step`, `simulation_time_s`, `runtime_signal_id` (VF key) vs `canonical_signal_id` (PIM), `origin_kind=simulation`, `fidelity`, `data_status=synthetic|simulated_ground_truth`, `semantic_contract_version/sha`, `evidence_note`. | Provenance seam |
| `observation/envelope.py` idempotency key | `run_id` + `source_event_id` + `point_id` + `schema_version`. | Provenance seam |
| PIM `plant_config/evidence_policy.yaml` | Evidence statuses (`DocumentConfirmed/PatternInferred/IndustryExpected/Expected/SourceMapped/SiteVerified/Rejected`); promotion `Expected → SourceMapped → SiteVerified`. | Evidence (PIM authority) |

## 1.7 UI / demo-only state (NOT platform authority)

| File | Content | Class |
|---|---|---|
| `src/virtual_factory/ui/static/app.js` | Hard-coded `ALARM_SIGNALS` list; `APP.telemetry`/`APP.alarms` Maps (client-side projection state); polling + reset clears. | UI-demo-only |
| `src/virtual_factory/ui/static/editor.js` | `ALARM_COLOURS`, `alarms` Map (editor view projection). | UI-demo-only |
| `src/virtual_factory/ui/api.py` | `/alarms`, `/telemetry/latest`, `/reset` endpoints. | UI-demo-only |

## 1.8 Summary — seams vs truth

| Seam | Authoritative truth? |
|---|---|
| `RuntimeState` / ASSY domain state / `DiscreteRunState` | **Yes** — mutable execution truth. |
| `ObservationEnvelope` | **No** — immutable projection/fact. |
| Telemetry frame / live series / alarm samples / event store | **No** — projections/caches (bounded, append-style). |
| UI maps / demo snapshots | **No** — client-side projection state. |
| PIM evidence status | **Semantic authority** (PIM), distinct from VF provenance. |
