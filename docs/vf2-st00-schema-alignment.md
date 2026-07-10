# VF2-ST00 — Schema Alignment & Golden Package Freeze

> **Status:** COMPLETED  
> **Date:** 2026-07-10  
> **SA Review:** APPROVED WITH CORRECTIVE NOTES (see roadmap §C1-C5)

---

## 1. Golden Fixture

The actual PIM PH04-generated package for the Reference Pump Station has been imported as the golden fixture:

```
simulators/vf2/examples/sample_pim_package.json
```

**Source:** `plant-intelligence-model/examples/vf2-packages/pumping-station.json`  
**PIM version:** PIM-PH04-v0.1  
**Schema version:** 1.0  
**VF-2 loader MUST use this exact structure for MVP.**

---

## 2. PIM Package Summary

| Aspect | Value |
|--------|-------|
| `package_id` | `VF2-PKG-UNIT-REF-PUMP-STATION-01` |
| `package_type` | `vf2_simulation_package` |
| `schema_version` | `1.0` |
| **Objects** | 8 (2 pumps, 4 valves, 2 motors) |
| **Signals** | 4 (flow, pressure, level, vibration) |
| **Topology** | 3 process_edges, 0 electrical_edges |
| **Scenarios** | 6 (2 pump_trip, 4 valve_fault) |
| **Validation Rules** | 9 rules |

### Object types present

| Type | Count | IDs |
|------|-------|-----|
| `centrifugal_pump` | 2 | VF2-REF-PMP-101A (duty), VF2-REF-PMP-101B (standby) |
| `electric_motor` | 2 | VF2-REF-PMP-MTR-101A, VF2-REF-PMP-MTR-101B |
| `gate_valve` | 2 | VF2-REF-PMP-VLV-101A, VF2-REF-PMP-VLV-101B |
| `check_valve` | 2 | VF2-REF-PMP-VLV-102A, VF2-REF-PMP-VLV-102B |

### Signals present

| Signal ID | Type | Unit | Asset | Direction |
|-----------|------|------|-------|-----------|
| `VF2.PUMP_STATION_01.FT_101.DISCHARGE_FLOW_TRANSMITTER` | measurement | m³/h | ASSET-REF-PMP-101A | VF2_INPUT |
| `VF2.PUMP_STATION_01.PT_101.DISCHARGE_PRESSURE_TRANSMITTER` | measurement | bar | ASSET-REF-PMP-101A | VF2_INPUT |
| `VF2.PUMP_STATION_01.LT_101.SUCTION_LEVEL_TRANSMITTER` | measurement | m | UNIT-REF-PUMP-STATION-01 | VF2_INPUT |
| `VF2.PUMP_STATION_01.VB_101.PUMP_A_VIBRATION_SENSOR` | measurement | mm/s | ASSET-REF-PMP-101A | VF2_INPUT |

### Scenarios present

| ID | Type | Affected Signals |
|----|------|-----------------|
| `SCN-PUMP-TRIP-002` | pump_trip | FT_101 (flow→0), PT_101 (pressure→0), VB_101 (vibration→0) |
| `SCN-PUMP-TRIP-005` | pump_trip | (B pump — no signals mapped yet) |
| `SCN-PUMP-VLV-001` | valve_fault | (check valve A — no signals mapped) |
| `SCN-PUMP-VLV-003` | valve_fault | (gate valve A — no signals mapped) |
| `SCN-PUMP-VLV-004` | valve_fault | (gate valve B — no signals mapped) |
| `SCN-PUMP-VLV-006` | valve_fault | (check valve B — no signals mapped) |

---

## 3. Schema Compatibility: Roadmap vs Actual PIM

### 3.1 Fields that MATCH

| Roadmap Field | PIM Field | Status |
|--------------|-----------|--------|
| `package_id` | `package_id` | ✅ Exact match |
| `source_model.system` | `source_model.system = "PIM"` | ✅ Exact match |
| `source_model.unit_id` | `source_model.unit_id` | ✅ Exact match |
| `objects[].simulation_object_id` | `objects[].simulation_object_id` | ✅ Exact match (VF2- prefix) |
| `objects[].canonical_id` | `objects[].canonical_id` | ✅ Exact match |
| `objects[].object_type` | `objects[].object_type` | ✅ Exact match |
| `signals[].simulation_signal_id` | `signals[].simulation_signal_id` | ✅ Exact match (VF2. prefix) |
| `signals[].data_type` | `signals[].data_type` | ✅ Match (float64) |
| `signals[].engineering_unit` | `signals[].engineering_unit` | ✅ Match |
| `topology.process_edges` | `topology.process_edges` | ✅ Match |
| `scenarios[].scenario_id` | `scenarios[].scenario_id` | ✅ Exact match |
| `scenarios[].scenario_type` | `scenarios[].scenario_type` | ✅ Match (pump_trip, valve_fault) |
| `validation_rules` | `validation_rules` | ✅ Match |

### 3.2 Fields that DIFFER

| Roadmap Field | PIM Field | Difference | Action |
|--------------|-----------|------------|--------|
| `package_version` (roadmap) | `package_type` (PIM) | Roadmap used `package_version`; PIM uses `package_type: "vf2_simulation_package"` + `schema_version: "1.0"` | **Use PIM fields** |
| `source_object_id` (roadmap) | `canonical_asset_id` (PIM) | Roadmap put `source_object_id` on signal; PIM puts `canonical_asset_id` + `canonical_instrument_id` | **Use PIM fields** |
| `signal_role` (roadmap: MV/DV/PV/KPI) | `direction` + `behavior.signal_type` (PIM) | Roadmap had `signal_role` for taxonomy; PIM uses `direction: VF2_INPUT/VF2_OUTPUT` + `behavior.signal_type: measurement/status/alarm/setpoint/feedback` | **Use PIM taxonomy** |
| `min_value/max_value/default_value` (roadmap) | `behavior.initial_value` (PIM) | Roadmap had explicit min/max/default; PIM has only `initial_value` | **Use PIM; VF-2 infers bounds** |
| `behavior.type` + `depends_on` + `transform` (roadmap) | `behavior.signal_type` + `update_rate_ms` + `initial_value` (PIM) | Roadmap envisioned executable behaviors; PIM provides metadata only | **VF-2 assigns default behaviors** |
| `effects` (roadmap: executable overrides) | `expected_effects` (PIM: human-readable) | Roadmap had `effects` as signal overrides; PIM has `expected_effects` as descriptions + `affected_simulation_signal_ids` | **VF-2 maps expected_effects → runtime templates** |
| `expected_impact_path` (roadmap: object IDs) | `affected_simulation_object_ids` + `impact_path_source` + `impact_path_length` (PIM) | Roadmap had a single path; PIM has richer structure | **Use PIM fields** |

### 3.3 Fields PIM has that Roadmap didn't anticipate

| PIM Field | Description | VF-2 Action |
|-----------|-------------|------------|
| `objects[].ports[]` | Port definitions with direction, connected_to, relationship_id | **VF-2 topology engine uses ports for dependency resolution** |
| `objects[].source` | Provenance: `{generated_from, model_version, canonical_id}` | **VF-2 validator checks source.model_version compatibility** |
| `objects[].status` | Operational status: active/standby/out_of_service | **VF-2 uses for initial state** |
| `topology.electrical_edges` | Electrical topology (empty in MVP) | **Accept, handle empty** |
| `scenarios[].affected_simulation_signal_ids` | Explicit list of affected signals | **VF-2 scenario engine reads this directly** |
| `scenarios[].expected_effects[].expected_change` | Human-readable expected effect | **Used for validation messages, not runtime** |
| `scenarios[].impact_path_source` | Source of impact analysis | **VF-2 logs for provenance** |
| `signals[].direction` | VF2_INPUT / VF2_OUTPUT | **Key for signal taxonomy in VF-2** |

---

## 4. Boundary Endpoint Handling

The PIM package contains topology edges referencing `VF2-UNIT-REF-PUMP-STATION-01` (the unit boundary) and `VF2-REF-PMP-DISCH-001` (discharge header). These are NOT in the `objects[]` array because PIM doesn't export unit-level boundary objects.

**VF-2 policy (per SA C3):**

```
compatibility mode (MVP default):
  - Topology edges referencing objects NOT in objects[] → accept as boundary reference
  - Log warning: "Boundary endpoint: {id} not in objects[] — treated as external"
  - Do NOT fail validation

strict mode (future):
  - Reject unresolved endpoints
```

---

## 5. Behavior Strategy (per SA C2)

PIM currently provides signal **metadata** (`behavior.signal_type`, `update_rate_ms`, `initial_value`) — not executable behaviors.

**VF-2 must generate default behaviors based on signal metadata:**

| PIM `signal_type` | VF-2 Default Behavior | Rationale |
|-------------------|----------------------|-----------|
| `measurement` | `random_walk` around `initial_value` with small noise | Instruments fluctuate naturally |
| `status` | `constant` at `initial_value` | Discrete state changes via scenario only |
| `alarm` | `constant` at `false` | Alarms activate via scenario or threshold |
| `setpoint` | `constant` at `initial_value` | Setpoints change via operator/API |
| `feedback` | `dependent` on associated status signal | Valve position follows valve command |

**Enriched package** (`examples/sample_pim_package_enriched.json`) can add explicit `behavior.type`, `depends_on`, `transform` for testing the full behavior engine. But the golden fixture test MUST pass with default behaviors only.

---

## 6. Scenario Strategy (per SA C4)

PIM scenarios have `expected_effects` (human-readable) + `affected_simulation_signal_ids` (machine-readable).

**VF-2 maps to runtime:**

```
For scenario SCN-PUMP-TRIP-002:
  affected_simulation_signal_ids = [
    "VF2.PUMP_STATION_01.FT_101.DISCHARGE_FLOW_TRANSMITTER",
    "VF2.PUMP_STATION_01.PT_101.DISCHARGE_PRESSURE_TRANSMITTER",
    "VF2.PUMP_STATION_01.VB_101.PUMP_A_VIBRATION_SENSOR"
  ]
  expected_effects → template "pump_trip" → overrides:
    FT_101.flow     → value: 0.0
    PT_101.pressure → value: 0.0
    VB_101.vibration → value: 0.0
```

**For scenarios without `affected_simulation_signal_ids` (valve faults):**
- Apply default valve_fault template to the trigger object
- Log warning: "No affected signals specified; applying template defaults"

---

## 7. VF-2 Loader Supported Fields (MVP)

Based on this analysis, the VF-2 package loader SHALL support these fields:

### Top-level
- `package_id` ✅
- `package_type` ✅
- `schema_version` ✅ (must be "1.0")

### source_model
- `system` ✅
- `model_version` ✅
- `generated_at` ✅
- `unit_id` ✅
- `unit_name` ✅

### objects[]
- `simulation_object_id` ✅
- `canonical_id` ✅
- `object_type` ✅
- `name` ✅
- `unit_id` ✅
- `status` ✅
- `ports[]` ✅ (port_id, direction, connected_to_canonical_id, relation_type)
- `parameters` ✅ (dict[str, float])
- `source` ✅

### signals[]
- `simulation_signal_id` ✅
- `canonical_instrument_id` ✅
- `canonical_asset_id` ✅
- `name` ✅
- `data_type` ✅
- `engineering_unit` ✅
- `direction` ✅
- `behavior.signal_type` ✅
- `behavior.update_rate_ms` ✅
- `behavior.initial_value` ✅

### topology
- `process_edges[]` ✅ (from, to, relation_type, relationship_id)
- `electrical_edges[]` ✅ (may be empty)

### scenarios[]
- `scenario_id` ✅
- `scenario_type` ✅
- `trigger_simulation_object_id` ✅
- `affected_simulation_object_ids[]` ✅
- `affected_simulation_signal_ids[]` ✅
- `expected_effects[]` ✅ (signal_id, expected_change)
- `impact_path_source` ✅
- `impact_path_length` ✅

### validation_rules[]
- `rule_id` ✅
- `rule_name` ✅
- `severity` ✅
- `applies_to` ✅

---

## 8. VF-2 Package Schema Version Compatibility

```python
SUPPORTED_SCHEMA_VERSIONS = ["1.0"]

def check_schema_compatibility(package: dict) -> bool:
    version = package.get("schema_version", "unknown")
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        raise ValueError(
            f"Unsupported schema version: {version}. "
            f"VF-2 supports: {SUPPORTED_SCHEMA_VERSIONS}"
        )
    return True
```

---

## 9. ST00 Acceptance Checklist

- [x] Golden fixture imported from PIM (`examples/sample_pim_package.json`)
- [x] Schema differences documented (this file)
- [x] Boundary endpoint policy defined (compatibility mode for MVP)
- [x] Default behavior strategy defined
- [x] Scenario mapping strategy defined (expected_effects → runtime templates)
- [x] Supported fields list finalized
- [x] VF-2 directory structure created (`simulators/vf2/`)
- [ ] `__init__.py` created (done)
- [ ] VF-1 regression barrier confirmed (no files modified)

---

## 10. Next Steps

After SA reviews this ST00 note:

1. **Create `examples/sample_pim_package_enriched.json`** — enriched with explicit behaviors for testing
2. **Release Coder prompt for ST01** — Package Loader & Schema Models
3. **Coder implements `package_loader.py`** against golden fixture first
