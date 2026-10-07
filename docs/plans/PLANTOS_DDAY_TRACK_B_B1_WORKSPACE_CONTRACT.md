# PlantOS D-Day Track B — B1 Bottled Water Workspace Contract

**Status:** READY FOR SA REVIEW  
**Date:** 2026-10-03  
**Scope:** Contract/skeleton only — no broad runtime implementation.

## 1. Decision

The Bottled Water Factory is a new workspace on the existing Virtual Factory foundation. It is not a new simulator foundation and does not authorize a new engine.

Existing TIPA ASSY capability is reused as foundation/reference for discrete line mechanics, runtime control, observation/event delivery, telemetry, protocol gateways and 2D renderer mechanics.

TIPA-specific station identities, manual workflows, icons and animation skins must not leak into the Bottled Water workspace.

## 2. D-Day fidelity

The D-Day goal is a believable operational factory, not a complete digital twin.

- Full factory: aggregate/basic simulation.
- Filling & Packaging: detailed-basic discrete simulation + 2D animation.
- Capper: deterministic hero abnormal asset.
- Non-target areas: only enough changing raw facts for production, performance-context, quality, energy, material/process and operations views.
- Case packing/palletizing may be aggregate-cycle based.
- Inspection may combine fill/cap/label checks where useful.
- No deep MES, batch/recipe, scheduling or manual workflow fidelity.

## 3. Target topology

Target line:

Blower/Infeed -> Rinser -> Filler -> Capper -> Inspection -> Labeler -> Case Packer -> Palletizer

Machine-readable authority for B1 is configs/workspaces/bottled-water-dday/topology.yaml.

## 4. Automation-first interaction policy

Normal production is automated. Allowed manual controls only:

- Start
- Stop
- Pause
- Resume
- Declare Downtime Code
- Declare Failure Code

Downtime/failure classification enriches an event that already exists. It does not cause the simulated failure.

Explicitly excluded: checklist confirmation, manual quality disposition, manual release, manual retry and manual rework decision.

## 5. Raw-fact boundary

VF publishes raw operational facts and events. PlantOS owns calculated KPI semantics.

VF MUST NOT be the canonical producer of OEE, Availability, Performance, Quality %, energy/unit, utilization or generic health score.

Hidden scenario truth such as injected degradation factor or internal phase timer is not industrial telemetry and must not be published.

## 6. Visualization boundary

Reuse existing 2D renderer mechanics where practical: viewport/pan/zoom, animation clock, station selection, popup/inspector, state highlighting, unit movement mechanism and data binding.

Do not reuse the TIPA ASSY visual skin. Bottled Water requires dedicated machine and bottle visual assets.

## 7. Primary integration contract

Primary D-Day integration: MQTT JSON.

Conceptual topic shape:

virtual-factory/bottled-water-dday/{kind}/{asset_id}/{signal_or_event}

REST/WebSocket/CSV/JSONL remain verification/debug paths. OPC UA remains an optional output.

## 8. Sample telemetry

```json
{
  "workspace_id": "bottled-water-dday",
  "asset_id": "BW-FP-CAP01",
  "signal_id": "motor_current",
  "value": 8.7,
  "unit": "A",
  "timestamp_s": 412.0,
  "quality": "GOOD",
  "provenance": "SIMULATED_RAW",
  "scenario_id": "BW-CAP-DEG-01"
}
```

Sample downtime event:

```json
{
  "workspace_id": "bottled-water-dday",
  "event_type": "DOWNTIME_START",
  "asset_id": "BW-FP-CAP01",
  "reason_code": "CAP_DRIVE_DEGRADATION",
  "planned": false,
  "scenario_id": "BW-CAP-DEG-01",
  "simulation_time_s": 420.0,
  "provenance": "SIMULATED_RAW"
}
```

## 9. Deployment target after simulation completion

VF and PlantOS will be deployed on the same VPS, but remain separate services/containers.

Preferred deployment shape:

```text
VPS
├── PlantOS container/service
├── Virtual Factory container/service
├── MQTT broker
└── shared private Docker network
```

The integration should use service DNS/private networking rather than hard-coded public VPS addresses. No production credential, host IP or fixed port is frozen in B1.

Deployment is a later bounded slice after simulation and local integration proof.

## 10. Implementation sequence

1. B1 — Workspace contract & skeleton — this slice.
2. B2 — Hero line runtime reuse — wire Bottled Water target line onto existing discrete foundation; no engine fork.
3. B3 — Bottled Water 2D skin — reuse renderer mechanics, dedicated skin.
4. B4 — Full-factory aggregate simulation — Water Treatment, Utilities, preparation, warehouse/dispatch.
5. B5 — Capper deterministic abnormal scenario.
6. B6 — PlantOS local integration proof.
7. B7 — VPS deployment/integrated D-Day verification — co-located services, MQTT/private network, startup/restart/health/evidence.

## 11. B1 gate

B1 is complete only when SA confirms:

- workspace identity is stable;
- no new engine/foundation is introduced;
- topology IDs are acceptable;
- signal/event dictionary is acceptable;
- manual interaction is limited as frozen;
- KPI boundary is preserved;
- visual skin boundary is preserved;
- deployment assumptions do not hard-code environment-specific values.

No B2 broad runtime coding is authorized until this gate is reviewed.