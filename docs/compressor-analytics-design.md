# Virtual Factory — Compressor Station Analytics Design Proposal

> **Status:** Draft for Review. Do not implement until approved.
> **Date:** 2026-06-24
> **Context:** Approved Option B (graph-based boundary topology). Core modules built in prior sessions.

---

## 0. Current State Inventory

Before proposing new work, here is what already exists and is tested (167 tests):

### ✅ Already Built

| Layer | Module | What It Does |
|-------|--------|-------------|
| **Fault Lifecycle** | `faults/` | `FaultEngine`, `FaultInstance`, 6 severity curves, symptom propagation (additive/multiplicative/replacement), maintenance actions, recovery profiles (instant/linear/exponential) |
| **Fault Library** | `configs/faults/` | 10 compressor faults + 5 pump faults in YAML, with symptoms, growth rates, recovery actions |
| **Operating States** | `operating_states/` | `OperatingStateMachine`, 11 states, condition-based transitions, entry/exit callbacks, state history |
| **Benchmark** | `benchmark/` | `BenchmarkManager`, `BenchmarkLabels`, `BenchmarkPackage`, Parquet/JSONL export, manifest |
| **Maintenance Events** | `maintenance/` | `EventGenerator`, 7 event types (alarm, log, inspection, WO, repair, downtime, spare) |
| **Sensor Quality** | `sensor_quality/` | `SensorQualityModel`, 8 degradation modes (noise, bias, drift, flatline, intermittent, comm loss, cal offset, rate mismatch) |
| **Asset Hierarchy** | `equipment/asset_hierarchy.py` | Tree-structured `AssetNode` with parent-child, tag aggregation, metadata export |
| **Compressor Train** | `equipment/compressor_train.py` | 52 tags, polytropic compression, motor/bearing/lube/cooling/seal/anti-surge subsystems, reads from boundary source, writes to boundary sink |
| **Boundary** | `equipment/boundary.py` | `BoundaryEquipment` (source/sink), gas composition, MW, cp/cv calculation |
| **Analytics Runtime** | `analytics/` | `AnalyticsRuntime` — ties fault engine + state machines + maintenance + benchmark into one orchestrator |
| **Config** | `configs/plants/` | `compressor_train_benchmark_01.yaml` with GAS_SOURCE, COMP01, GAS_SINK, 26 sensors, 7 alarms, connections |

### ❌ Not Yet Integrated

These modules exist but are **not wired into** the compressor train simulation loop:

1. `FaultEngine` runs standalone in tests; not called from `CompressorTrain.process_step()`
2. `OperatingStateMachine` runs standalone; not attached to `CompressorTrain`
3. `BenchmarkManager` runs standalone; not recording per-timestep during simulation
4. `SensorQualityModel` exists but sensors don't use it
5. `AnalyticsRuntime` exists but `SimulationEngine` doesn't invoke it

**The primary goal of this phase is integration — wiring existing modules into the simulation loop, not building them from scratch.**

---

## 1. Operating State Model

### 1.1 Current State

`OperatingStateMachine` already has 11 states matching the requirement (plus `RECOVERY` is missing). Missing state:

- `recovery` — equipment returning to normal after maintenance

### 1.2 Recommended Changes

**Add `RECOVERY` state:**
```python
RECOVERY = "recovery"  # Returning to normal after maintenance
```

**State-specific tag behavior table:**

| State | suction_p | discharge_p | flow | vibration | temp | Valid for Training? |
|-------|-----------|-------------|------|-----------|------|-------------------|
| STOPPED | ambient | ambient | 0 | 0 | ambient | ❌ (no dynamics) |
| STARTUP | rising | rising | ramp up | transient | rising | ❌ (transient) |
| RAMP_UP | rising | rising | increasing | transient | rising | ❌ (transient) |
| STEADY_RUNNING | design | design | rated | nominal | nominal | ✅ YES |
| LOW_LOAD | design | low PR | <50% | low | low | ✅ (partial) |
| HIGH_LOAD | design | high PR | >100% | elevated | elevated | ✅ (partial) |
| RECYCLE_MODE | design | mid | recycled | elevated | elevated | ✅ |
| NEAR_SURGE | design | high | <min | fluctuating | rising | ❌ (abnormal) |
| SHUTDOWN | falling | falling | ramp down | transient | falling | ❌ (transient) |
| TRIP | ambient | ambient | 0 | 0 | ambient | ❌ (fault) |
| MAINTENANCE | ambient | ambient | 0 | 0 | ambient | ❌ (offline) |
| RECOVERY | rising | rising | ramp up | settling | settling | ❌ (transient) |

**Benchmark label per state:** `operating_state` field in `BenchmarkLabels` records current state. Analytics models should filter training data to `STEADY_RUNNING`, `LOW_LOAD`, `HIGH_LOAD`, `RECYCLE_MODE` only.

### 1.3 Integration Design

`CompressorTrain` should own its `OperatingStateMachine`. On `process_step()`:

```
1. Read current truth values
2. Build truth_dict for state machine evaluation
3. Call sm.step(truth_dict, dt_s)
4. If state changed, log state transition event
5. Write current state to benchmark labels (via callback)
```

State transitions driven by compressor conditions:

```
STOPPED    → STARTUP        : COMP01.running == True
STARTUP    → RAMP_UP        : time_in_state > 5s AND flow > 0
RAMP_UP    → STEADY_RUNNING : time_in_state > 30s
STEADY    → LOW_LOAD        : flow < 50% rated
STEADY    → HIGH_LOAD       : flow > 100% rated
STEADY    → RECYCLE_MODE    : recycle_valve.position > 20%
STEADY    → NEAR_SURGE      : surge_margin < 0.10
NEAR_SURGE → STEADY         : surge_margin > 0.15
STEADY    → SHUTDOWN        : running == False
TRIP      → STOPPED         : time_in_state > 60s (auto-reset)
SHUTDOWN  → STOPPED         : speed_rpm == 0
MAINTENANCE → RECOVERY      : maintenance complete
RECOVERY  → STEADY_RUNNING  : flow > 80% rated AND vibration < threshold
```

---

## 2. Demand / Backpressure Profile

### 2.1 Current State

`GAS_SINK` has a single static `backpressure_kpa` parameter. No dynamic behavior.

### 2.2 Design Decision

**Recommendation: Extend `boundary_v1` with `demand_profile` parameter, NOT a new model type.**

Boundary sink already owns `backpressure_kpa`. Adding a demand profile makes it time-aware:

```yaml
# In compressor_train_benchmark_01.yaml
equipment:
  - id: GAS_SINK
    model_type: boundary_v1
    parameters:
      boundary_type: sink
      pressure_kpa: 280.0          # base backpressure
      demand_profile:
        type: daily_shift           # constant | step | daily_shift | random
        base_flow_m3_s: 1.5         # nominal demand
        fluctuation_pct: 10         # ±10% random noise
        schedule:                   # for daily_shift type
          - { hour: 0,  factor: 0.7 }   # night low
          - { hour: 6,  factor: 1.0 }   # morning normal
          - { hour: 14, factor: 1.2 }   # afternoon high
          - { hour: 22, factor: 0.8 }   # evening
```

**Implementation:** `BoundaryEquipment.process_step()` evaluates the demand profile each tick, updates `backpressure_kpa` and `available_flow_m3_s` accordingly. The compressor reads these dynamically.

**Why not Scenario Manager:** Scenarios are for discrete event injection. Demand profiles are continuous time-varying behavior — belongs in the equipment model.

### 2.3 Profile Types

| Type | Behavior | Use Case |
|------|----------|----------|
| `constant` | Fixed backpressure, no variation | Baseline |
| `step` | Backpressure changes at scheduled times | Load change testing |
| `daily_shift` | Hourly factor × base value | Realistic plant operation |
| `random` | Gaussian noise around base | Robustness testing |

---

## 3. Compressor Process Topology Evolution

### 3.1 Current Topology

```
GAS_SOURCE → COMP01 → GAS_SINK
```

`COMP01` is a monolithic `CompressorTrain` containing all sub-systems internally.

### 3.2 Target Topology (Phase 3)

```
GAS_SOURCE
  → INLET_SCRUBBER (liquid knockout, DP measurement)
  → COMPRESSOR (polytropic compression)
  → AFTERCOOLER (heat removal, ΔT measurement)
  → DISCHARGE_SEPARATOR (condensate knockout)
  → DISCHARGE_HEADER (backpressure, check valve)
```

### 3.3 Staged Implementation

**Phase 3a: Split COMP01 into sub-equipment (internal only)**

Keep `CompressorTrain` as facade. Internally delegate physics to sub-models. Each sub-model is a standalone `BaseEquipment` subclass:

```
CompressorTrain (facade)
  ├── InletScrubber    → DP, level, drain
  ├── CompressorCore   → polytropic physics (moved from CompressorTrain)
  ├── Aftercooler      → heat transfer, approach temp
  ├── DischargeSep     → level, condensate
  ├── DriverMotor      → already modeled
  ├── LubeOilSystem    → already modeled
  └── SealGasSystem    → already modeled
```

Connections are internal to the train, not in the plant config.

**Phase 3b: Expose sub-equipment to plant graph (later)**

Make each sub-system a top-level equipment in the plant config with explicit connections. This enables:
- Independent sensor placement per sub-system
- Sub-system-level fault injection
- Per-component health index

### 3.4 What NOT to do yet

- Do not split the compressor train config into 7 separate YAML equipment entries yet
- Do not add individual sub-system model types to the registry yet
- Keep the single `compressor_train_v1` facade for now

---

## 4. Fault Lifecycle Engine Integration

### 4.1 Current State

`FaultEngine` is fully built and tested. `FaultLibrary` has 10 compressor faults in YAML. Neither is connected to the simulation loop.

### 4.2 Integration Design

**The fault engine should be owned by `SimulationEngine` (or `AnalyticsRuntime`), not individual equipment.**

Each simulation step:

```
1. FaultEngine.step(state, current_time_s)
   - Applies scheduled fault injections
   - Advances severity for each active fault
   - Propagates symptoms to RuntimeState truth variables
   - Logs fault events

2. process_dynamics / process_step (equipment physics)
   - Equipment reads truth variables (now modified by fault symptoms)
   - Equipment does NOT need to know about faults

3. BenchmarkManager records fault state
   - Active fault IDs, severities, health index, RUL
```

**Key principle:** Equipment models should not import `FaultEngine`. Faults modify truth variables; equipment reads truth variables. This keeps equipment models clean and fault logic centralized.

### 4.3 Compressor Fault Types (Already Defined)

All 9 requested fault types already exist in `configs/faults/compressor_faults.yaml`:

| Fault ID | Symptoms |
|----------|----------|
| `bearing_wear` | vibration_de +4-8 mm/s, bearing_temp +15-25°C, shaft_displacement +60μm |
| `filter_fouling` | lube_oil.filter_dp +80 kPa, flow -30%, temp +10°C |
| `aftercooler_fouling` | cooling.delta_t -50%, discharge_temp +30°C |
| `oil_pressure_loss` | lube_oil.pressure -50%, flow -40%, bearing_temp +15°C |
| `cooling_degradation` | cooling.flow -40%, discharge_temp +15°C, lube_oil.temp +12°C |
| `recycle_valve_stiction` | valve.position stutters, flow -15%, surge_margin -30% |
| `seal_leakage` | seal_gas.flow +200%, vent_pressure +15 kPa |
| `sensor_drift` | discharge_pressure +8% multiplicative drift |
| `surge_risk` | flow -40%, surge_margin -70%, axial vibration +10 mm/s |

### 4.4 What needs to be built

Only integration code — connecting `FaultEngine` to the simulation loop. All fault models exist.

---

## 5. Ground Truth / Benchmark Export

### 5.1 Current State

`BenchmarkManager`, `BenchmarkLabels`, `BenchmarkPackage`, and `BenchmarkExporter` are built and tested. They produce:

```
telemetry.parquet          — published industrial signals
asset_metadata.yaml        — equipment hierarchy
operating_states.parquet   — state per equipment per timestep
alarm_events.parquet       — alarm history
maintenance_events.parquet — maintenance records
fault_timeline.parquet     — fault activity over time
benchmark_labels.parquet   — hidden ground truth
manifest.json              — dataset inventory
```

### 5.2 Separation of Telemetry vs Ground Truth

This is already implemented via `BenchmarkMode`:

| Mode | Telemetry Published? | Ground Truth Exported? |
|------|---------------------|----------------------|
| `INDUSTRIAL` | ✅ (industrial signals only) | ❌ |
| `BENCHMARK` | ✅ (industrial signals only) | ✅ (separate file) |
| `HIDDEN` | ✅ (industrial signals only) | ✅ (stored, not exportable) |

**Ground truth NEVER appears in industrial telemetry.** It is a separate export path (`benchmark_labels.parquet`). The `OutputPolicy` enforcement already blocks `internal_truth` category from all protocol gateways.

### 5.3 Benchmark Labels (Already Defined)

`BenchmarkLabels` already has all requested fields:

```
timestamp_s              — simulation time
equipment_id             — asset identifier
operating_state          — from state machine
active_faults            — list of active fault IDs
fault_severities         — {fault_id: severity} map
fault_start_times        — {fault_id: start_time} map
health_index             — 1.0 = healthy, 0.0 = failed
remaining_useful_life_s  — simulated RUL (linear degradation model)
failure_probability      — max severity across all faults
expected_anomaly         — True if any fault severity > 0.1
expected_diagnosis       — most severe fault ID (or "healthy")
expected_severity_label  — incipient/developing/degraded/critical/failed
```

### 5.4 What needs to be built

Integration: call `BenchmarkManager.record_from_engine()` each simulation step from within `SimulationEngine` or `AnalyticsRuntime`.

---

## 6. Sensor & Data Quality Model

### 6.1 Current State

`SensorQualityModel` supports 8 degradation modes via `SensorQualityProfile`. The `BaseSensor.sample()` method already handles noise, bias, delay, drift, stuck, and quality flags.

### 6.2 Gap Analysis

| Degradation | Already in BaseSensor? | In SensorQualityModel? | Gap |
|-------------|----------------------|----------------------|-----|
| Noise | ✅ `noise_std` | ✅ `NOISE_INCREASE` | None |
| Bias | ✅ `sensor_bias` | ✅ `BIAS_SHIFT` | None |
| Drift | ✅ `sensor_drift` | ✅ `DRIFT` | None |
| Delay | ✅ `delay_s` | ❌ | Scenario-level |
| Flatline | ✅ (via STUCK quality) | ✅ `FLATLINE` | None |
| Missing data | ❌ | ✅ `INTERMITTENT` | Not in BaseSensor |
| Comm loss | ❌ | ✅ `COMM_LOSS` | Not in BaseSensor |
| Calibration offset | ❌ | ✅ `CALIBRATION_OFFSET` | Not in BaseSensor |
| Sample rate mismatch | ❌ | ✅ `SAMPLE_RATE_MISMATCH` | Not in BaseSensor |
| Timestamp jitter | ❌ | ❌ | Not implemented |

### 6.3 Design Decision: Sensor-Level vs Scenario-Level

| Behavior | Where | Rationale |
|----------|-------|-----------|
| Noise, Bias, Drift, Delay | **Sensor config** (parameters) | Inherent sensor characteristics |
| Flatline, Intermittent, Comm Loss | **Scenario** (timed injection) | Discrete failure events |
| Calibration Offset | **Sensor config** (initial) + **Scenario** (change) | Initial + drift |
| Sample Rate Mismatch | **Sensor config** | Design characteristic |
| Timestamp Jitter | **Sensor config** (new parameter) | System behavior |

### 6.4 Recommended Changes

1. **Add `SensorQualityModel` to `BaseSensor`**: Each sensor instantiates its own quality model. `sample()` routes the raw value through `quality_model.apply()` before writing the signal.

2. **Add new `BaseSensor` parameters**:
   - `sample_rate_hz` — actual sampling rate (for mismatch)
   - `timestamp_jitter_s` — max random jitter on timestamp

3. **Scenario-driven quality changes**: New scenario action `set_sensor_profile` adds a `SensorQualityProfile` to a sensor's quality model.

---

## 7. Configuration Design

### 7.1 Schema Extensions (Backward Compatible)

All new fields are optional with defaults. No existing configs break.

```yaml
# configs/plants/compressor_train_benchmark_01.yaml (extended)

plant:
  id: compressor_train_benchmark_01
  # ... existing fields ...

  # NEW: Analytics configuration
  analytics:
    mode: benchmark              # industrial | benchmark | hidden
    operating_states: true       # enable state tracking
    fault_library: configs/faults/compressor_faults.yaml
    benchmark_output:
      directory: output/benchmark
      formats: [parquet, jsonl]
      include_labels: true

# NEW: Operating state definitions per equipment
operating_states:
  COMP01:
    initial: stopped
    data_valid_states: [steady_running, low_load, high_load, recycle_mode]
    transitions:
      - { from: stopped, to: startup, condition: "COMP01.running == true" }
      - { from: startup, to: ramp_up, condition: "COMP01.flow_m3_s > 0.05" }
      - { from: ramp_up, to: steady_running, condition: "state_time_s > 30" }
      # ... more transitions ...

# NEW: Fault schedule (alternative to scenario-based injection)
fault_schedule:
  - fault_id: bearing_wear
    equipment_id: COMP01
    start_time_s: 3600
    initial_severity: 0.0
  - fault_id: cooling_degradation
    equipment_id: COMP01
    start_time_s: 7200
    initial_severity: 0.0
```

### 7.2 GAS_SINK Demand Profile (in boundary parameters)

```yaml
equipment:
  - id: GAS_SINK
    model_type: boundary_v1
    parameters:
      boundary_type: sink
      pressure_kpa: 280.0
      # NEW: demand profile
      demand_profile:
        type: daily_shift
        base_flow_m3_s: 1.5
        fluctuation_pct: 10
        schedule:
          - { hour: 0, factor: 0.7 }
          - { hour: 6, factor: 1.0 }
          - { hour: 14, factor: 1.2 }
          - { hour: 22, factor: 0.8 }
```

### 7.3 Sensor Quality Extensions

```yaml
sensors:
  - id: PT102
    model_type: pressure_transmitter_v1
    measures: COMP01.discharge_pressure_kpa
    output_signal: COMP01_DISCHARGE_PRESSURE
    parameters:
      sample_time_s: 1.0
      noise_std: 0.5
      resolution: 0.1
      # NEW fields
      sample_rate_hz: 1.0
      timestamp_jitter_s: 0.05
      calibration_offset: 0.0
```

### 7.4 Backward Compatibility

All existing `continuous_mvp_01.yaml` configs load without changes. New fields use `default_factory` or `None` defaults in Pydantic schema.

---

## 8. Validation Plan

### 8.1 Existing Tests (Keep Passing)

- 89 core tests (MVP, PID, MQTT, OPC UA, API, scenarios)
- 78 analytics tests (fault engine, states, sensor quality, maintenance, benchmark, hierarchy, compressor train)
- **Total: 167 tests**

### 8.2 New Tests Required

| Test Category | Count | What It Validates |
|---------------|-------|-------------------|
| `test_compressor_states` | ~10 | All 12 state transitions fire correctly based on truth conditions |
| `test_demand_profile` | ~8 | Each profile type (constant, step, daily, random) produces correct backpressure |
| `test_fault_integration` | ~10 | Fault engine connected to compressor; symptoms affect telemetry; recovery works |
| `test_benchmark_integration` | ~8 | Labels recorded each step; benchmark mode exports; industrial mode hides |
| `test_sensor_quality_integration` | ~6 | Quality model applied in sample(); profiles activate/deactivate |
| `test_output_policy` | ~4 | Ground truth blocked from industrial telemetry; benchmark labels in separate file |
| `test_mvp_regression` | existing | Tank-transfer MVP still runs unchanged |
| `test_config_validation` | ~6 | New schema fields validate; old configs still load |

**Total new tests: ~52 → Total: ~219**

### 8.3 Smoke Test

```python
# End-to-end: 2-hour compressor run with bearing_wear fault
python tests/demo_compressor_analytics.py
# Expected: 7200 steps, operating states logged, fault severity grows,
# benchmark_labels.parquet exported, health_index decreases
```

---

## 9. Implementation Phases

### Phase 1: Operating State + Demand Profile (2-3 days)

**Files affected:**
- `equipment/compressor_train.py` — own state machine, state-aware process_step
- `equipment/boundary.py` — demand profile evaluation in process_step
- `operating_states/state_machine.py` — add RECOVERY state
- `configs/plants/compressor_train_benchmark_01.yaml` — state transitions, demand profile
- `configs/scenarios/` — demand change scenarios
- `tests/test_compressor_states.py` — new
- `tests/test_demand_profile.py` — new

**Design decisions:**
- State machine owned by CompressorTrain (not AnalyticsRuntime)
- Demand profile in BoundaryEquipment (not new model type)
- State transitions configurable in YAML, defaults in Python

**Risks:**
- State transitions may conflict with fault-induced behavior (near_surge during bearing_wear)
- Low

**Acceptance criteria:**
- Compressor transitions through full state lifecycle in simulation
- Demand profile changes backpressure over time
- State labels appear in benchmark export
- MVP tank-transfer still works unchanged

**What NOT to implement yet:**
- Fault integration
- Sub-equipment splitting
- New UI for compressor states

---

### Phase 2: Fault Lifecycle + Benchmark Labels (2-3 days)

**Files affected:**
- `core/simulation_engine.py` — integrate FaultEngine.step() in main loop
- `equipment/compressor_train.py` — read fault-modified truth (no changes needed)
- `benchmark/benchmark_manager.py` — record_from_engine each step
- `faults/fault_engine.py` — symptom propagation integration
- `configs/scenarios/compressor_benchmark_scenarios.yaml` — update fault injection actions
- `tests/test_fault_integration.py` — new
- `tests/test_benchmark_integration.py` — new

**Design decisions:**
- FaultEngine owned by SimulationEngine (not equipment)
- Symptoms modify RuntimeState truth → equipment reads truth
- Benchmark recording in engine step, not in equipment

**Risks:**
- Symptom accumulation across steps may cause unrealistic values
- Mitigation: severity curves already bounded to [0,1]

**Acceptance criteria:**
- Injecting bearing_wear increases vibration over time in telemetry
- Health index decreases as severity grows
- benchmark_labels.parquet contains per-timestep fault data
- Recovery after maintenance restores health
- Industrial telemetry NEVER contains ground truth labels

---

### Phase 3: Topology Expansion (3-4 days)

**Files affected:**
- `equipment/compressor_train.py` — refactor into facade with sub-models
- `equipment/inlet_scrubber.py` — new
- `equipment/compressor_core.py` — new (extract from CompressorTrain)
- `equipment/aftercooler.py` — new (extract from HeatExchanger)
- `equipment/discharge_separator.py` — new (extract from Separator)
- `configs/model_types/` — new model types
- `configs/plants/compressor_train_benchmark_01.yaml` — optional split config
- `tests/test_compressor_topology.py` — new

**Design decisions:**
- Phase 3a: internal delegation (CompressorTrain facade)
- Phase 3b: expose to plant graph (later, not now)
- Sub-models reuse existing physics (polytropic, LMTD, separation)

**Risks:**
- Medium — refactoring CompressorTrain internals
- Must preserve 52-tag output

**What NOT to implement:**
- Phase 3b (external graph)
- Per-component config YAML files
- Individual health indices per sub-component

---

### Phase 4: Sensor/Data Quality Integration (1-2 days)

**Files affected:**
- `instrumentation/base_sensor.py` — integrate SensorQualityModel
- `sensor_quality/quality_model.py` — timestamp jitter
- `configs/plants/` — sensor quality parameters

**Design decisions:**
- Quality model per sensor instance
- Profiles activated via scenario actions
- Timestamp jitter as sensor parameter

**Risks:**
- Low — SensorQualityModel already tested

---

### Phase 5: Analytics Benchmark Dataset Export (1-2 days)

**Files affected:**
- `benchmark/export_utils.py` — already built, may need minor tweaks
- `analytics/__init__.py` — integrate with SimulationEngine
- `main.py` — CLI flags for benchmark mode
- `tests/test_benchmark_export.py` — extended

**Design decisions:**
- `--benchmark` flag on CLI
- `--benchmark-dir` for output path
- `--format parquet|jsonl`

**Risks:**
- Low — export already tested standalone

---

## 10. Open Questions for Human Review

1. **State machine ownership:** Should `CompressorTrain` own its state machine, or should `SimulationEngine` manage all state machines centrally? Recommendation: CompressorTrain owns it (equipment knows its own states).

2. **FaultEngine location:** Should it be in `SimulationEngine` or `AnalyticsRuntime`? Recommendation: `AnalyticsRuntime` (separation of concerns — core engine does physics, analytics runtime does faults/states/benchmark).

3. **Demand profile complexity:** Is `daily_shift` with hourly factors sufficient, or do we need sub-hour granularity? Recommendation: start with hourly, add minute-level later.

4. **Sub-equipment splitting (Phase 3b):** Should individual sub-components (inlet scrubber, aftercooler) be visible in the plant graph as separate nodes, or stay internal to CompressorTrain? Recommendation: stay internal until Phase 3b.

5. **Timestamp jitter:** Do analytics models actually need realistic timestamp jitter, or is clean 1-second spacing sufficient for benchmark generation? Recommendation: add as optional parameter, default off.

6. **RUL model:** Current RUL is simple linear (10000s × (1 - max_severity)). Should we implement Weibull or exponential degradation for more realistic RUL? Recommendation: linear for Phase 1, Weibull option later.

7. **Config schema:** Should the new `analytics`, `operating_states`, `fault_schedule` fields be in the plant config YAML, or in a separate analytics config file? Recommendation: in plant config (single source of truth).

---

## Appendix A: What Already Exists vs What's Needed

| Feature | Status | Action Needed |
|---------|--------|---------------|
| Fault lifecycle engine | ✅ Built | Integrate into simulation loop |
| Fault library (10 compressor) | ✅ YAML | Load at engine init |
| Operating state machine (11 states) | ✅ Built | Add RECOVERY, attach to CompressorTrain |
| Benchmark labels | ✅ Built | Call record_from_engine each step |
| Benchmark export (Parquet/JSONL) | ✅ Built | Wire to end-of-simulation |
| Maintenance events | ✅ Built | Generate based on fault triggers |
| Sensor quality (8 modes) | ✅ Built | Integrate into BaseSensor.sample() |
| Asset hierarchy | ✅ Built | Already used by CompressorTrain |
| Analytics runtime | ✅ Built | Wire to SimulationEngine |
| Demand profile | ❌ Not built | Add to BoundaryEquipment |
| Timestamp jitter | ❌ Not built | Add to BaseSensor |
| Inlet scrubber sub-model | ❌ Not built | Phase 3 |
| Compressor core sub-model | ❌ Not built | Phase 3 (extract from train) |
| Aftercooler sub-model | ❌ Not built | Phase 3 |
| Discharge separator sub-model | ❌ Not built | Phase 3 |

## Appendix B: Integration Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                   SimulationEngine                       │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐ │
│  │ Core Physics │  │ Sensor       │  │ Protocol       │ │
│  │ (process_    │  │ Sampling     │  │ Gateways       │ │
│  │  dynamics +  │  │ (BaseSensor  │  │ (MQTT, OPC UA, │ │
│  │  process_step│  │  + Quality)  │  │  Sparkplug)    │ │
│  └──────┬───────┘  └──────┬───────┘  └───────┬────────┘ │
│         │                 │                   │          │
│         ▼                 ▼                   ▼          │
│  ┌──────────────────────────────────────────────────┐   │
│  │              RuntimeState (truth)                │   │
│  │  COMP01.vibration_de_mm_s: 2.3 + fault_effect   │   │
│  │  GAS_SOURCE.pressure_kpa: 101.3                 │   │
│  └──────────────────────────────────────────────────┘   │
│                         │                               │
│         ┌───────────────┼───────────────┐              │
│         ▼               ▼               ▼              │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │ Fault    │  │ Operating    │  │ Benchmark        │ │
│  │ Engine   │  │ State Mach.  │  │ Manager          │ │
│  │          │  │              │  │                  │ │
│  │ severity │  │ current      │  │ per-timestep     │ │
│  │ symptoms │  │ state        │  │ labels           │ │
│  └────┬─────┘  └──────┬───────┘  └────────┬─────────┘ │
│       │               │                   │           │
│       ▼               ▼                   ▼           │
│  ┌──────────────────────────────────────────────────┐   │
│  │        AnalyticsRuntime (orchestrator)           │   │
│  │  event_generator  maintenance_records            │   │
│  │  fault_timeline   benchmark_labels               │   │
│  └──────────────────────┬───────────────────────────┘   │
└─────────────────────────┼───────────────────────────────┘
                          │
                          ▼
              ┌─────────────────────┐
              │  Benchmark Package  │
              │  .parquet / .jsonl  │
              │  .yaml / manifest   │
              └─────────────────────┘
```
