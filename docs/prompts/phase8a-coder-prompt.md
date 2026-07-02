# Prompt for Coder — Implement Virtual Factory WTP Simulator (Phase 8A)

You are the **Coder** for the Virtual Factory WTP Simulator. Your job is to implement the simulator based on the approved PM & Designer plans.

---

## Required Reading (in order)

Before writing ANY code, read these files in the Virtual Factory repo:

```text
docs/wtp-simulator-design.md       ← PM plan: architecture, API, file structure, task breakdown
docs/wtp-simulation-model.md       ← Designer spec: ALL formulas, signal taxonomy, stage equations
examples/contracts/wtp-demo-01.contract.yaml  ← THE contract (from PlantOS repo, read-only)
```

---

## What You're Building

A **standalone Python WTP process simulator** that:

1. **Reads** the PlantOS Integration Contract (`wtp-demo-01.contract.yaml`)
2. **Parses** all 92 signals with their metadata
3. **Simulates** the WTP process using physics/chemistry formulas (from `wtp-simulation-model.md`)
4. **Allows operator control** of 12 Manipulated Variables via HTTP API
5. **Generates** realistic telemetry at 1-second intervals
6. **Publishes** measurements to PlantOS via `POST /api/v1/measurements/ingest`
7. **Supports** 8 scenarios defined in the contract

---

## Architecture Rules (Non-Negotiable)

1. **Standalone** — do NOT integrate with the main VF engine. This is a separate simulator under `simulators/wtp/`.
2. **Contract-driven** — read the contract file; do NOT hardcode signal lists.
3. **Formulas from Designer spec** — use the exact formulas in `docs/wtp-simulation-model.md`. Do NOT invent your own.
4. **MV→PV→KPI flow** — Manipulated Variables + Disturbances drive Process Variables, which compute KPIs.
5. **No OPC UA, No MQTT** — only HTTP POST to PlantOS ingestion endpoint.
6. **All timestamps in UTC** — ISO 8601 format.
7. **Quality field** — "GOOD" for normal, "UNCERTAIN" near bounds (±10%), "BAD" out of bounds.

---

## File Structure to Create

```
simulators/wtp/
├── __init__.py
├── main.py                          # CLI entry point + main simulator loop
├── models.py                        # All dataclasses: SignalConfig, BehaviorConfig, MVConfig, etc.
├── contract_parser.py               # Read & parse wtp-demo-01.contract.yaml
├── config.py                        # Read wtp_config.yaml (PlantOS URL, interval, etc.)
├── signal_registry.py               # Signal taxonomy: classifies 92 signals as MV/DV/PV/KPI
├── disturbance_engine.py            # 7 DV generators (random_walk + sine with bounds)
├── actuator_engine.py               # 12 MV actuators (SP → actual with slew rate + accuracy)
├── clarification_engine.py          # Stage 3: coagulation/flocculation/sedimentation physics
├── filtration_engine.py             # Stage 4: filter DP accumulation + efficiency + backwash
├── disinfection_engine.py           # Stage 5: chlorine chemistry (free/total/combined)
├── energy_engine.py                 # Stage 8: pump power curves, total power, specific energy
├── kpi_engine.py                    # Stage 8: cost, quality index, traceability scores
├── simulation_loop.py               # 8-stage step() orchestrator
├── scenario_manager.py              # 8 scenarios with smooth transitions
├── ingest_client.py                 # HTTP POST to PlantOS + retry + buffer
├── api_server.py                    # FastAPI: status, control MV, override DV, switch scenario
├── wtp_config.yaml                  # Default configuration file
├── scenarios/                       # 8 scenario YAML files (with MV/DV overrides)
│   ├── normal_operation.yaml
│   ├── raw_water_contamination.yaml
│   ├── algae_bloom.yaml
│   ├── filter_breakthrough.yaml
│   ├── chlorine_underdosing.yaml
│   ├── chemical_overdosing.yaml
│   ├── filter_clogging_energy_impact.yaml
│   └── hsp_trip.yaml
├── tests/
│   ├── __init__.py
│   ├── test_contract_parser.py
│   ├── test_signal_registry.py
│   ├── test_disturbance_engine.py
│   ├── test_actuator_engine.py
│   ├── test_clarification_engine.py
│   ├── test_filtration_engine.py
│   ├── test_disinfection_engine.py
│   ├── test_simulation_loop.py
│   ├── test_scenario_manager.py
│   └── test_ingest_client.py
└── requirements.txt                 # pyyaml, httpx, fastapi, uvicorn
```

---

## Implementation Order (Follow EXACTLY)

### Phase 1: Foundation (Day 1-2)

#### Task 1.1 — Create directory structure + requirements.txt

```text
simulators/wtp/requirements.txt:
pyyaml>=6.0
httpx>=0.27
fastapi>=0.110
uvicorn[standard]>=0.27
```

#### Task 1.2 — `models.py` — All data classes

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

class SignalType(Enum):
    MV = "manipulated_variable"     # operator can control
    DV = "disturbance_variable"     # external, uncontrollable
    PV = "process_variable"         # physical result
    KPI = "key_performance_indicator"  # derived from PVs

@dataclass
class SignalMeta:
    signal_id: str
    signal_name: str
    display_name: str
    asset_id: str
    area_id: str
    signal_type: SignalType
    data_type: str          # float | bool | int | string
    engineering_unit: str
    default_value: float
    min_value: float
    max_value: float
    depends_on: list[str] = field(default_factory=list)  # upstream signal_ids

@dataclass 
class MVConfig:
    signal_id: str
    default_sp: float      # default setpoint
    min_sp: float
    max_sp: float
    slew_rate: float       # max change per second
    accuracy_pct: float    # steady-state error %

@dataclass
class DVConfig:
    signal_id: str
    pattern: str           # "random_walk" | "sine"
    baseline: float
    amplitude: float
    noise_std: float
    bounds_min: float
    bounds_max: float
    frequency_hz: float = 0.001  # for sine

@dataclass
class Measurement:
    timestamp: str         # ISO 8601 UTC
    signal_id: str
    value: float | bool | int
    quality: str           # "GOOD" | "UNCERTAIN" | "BAD"
    source: str            # "wtp-sim-01"

@dataclass
class SimulationState:
    time_s: float = 0.0
    step_count: int = 0
    mv_values: dict[str, float] = field(default_factory=dict)     # actual MV values
    dv_values: dict[str, float] = field(default_factory=dict)     # current DV values
    pv_values: dict[str, float] = field(default_factory=dict)     # computed PV values
    kpi_values: dict[str, float | bool] = field(default_factory=dict)
    dv_state: dict[str, dict] = field(default_factory=dict)       # internal DV state (phase, position)
    mv_actuator_state: dict[str, float] = field(default_factory=dict)  # actuator current position
    filter_dp_101_accum: float = 20.0
    filter_dp_102_accum: float = 15.0
    backwash_101_remaining: float = 0.0
    backwash_102_remaining: float = 0.0
    total_energy_kwh: float = 0.0
    total_water_m3: float = 0.0
    total_waste_m3: float = 0.0
    compliance_frames: int = 0
    total_frames: int = 0
```

#### Task 1.3 — `config.py` — Configuration loader

```yaml
# simulators/wtp/wtp_config.yaml
simulator:
  name: "wtp-sim-01"
  source: "wtp-sim-01"
  interval_s: 1.0
  max_frames_buffer: 3600
  auto_start: true

plantos:
  base_url: "http://localhost:8000"
  ingest_endpoint: "/api/v1/measurements/ingest"
  retry:
    max_retries: 5
    base_delay_s: 1.0
    max_delay_s: 30.0
    backoff_multiplier: 2.0

scenario:
  default: "normal_operation"
  transition_s: 30.0

api:
  host: "0.0.0.0"
  port: 8100

logging:
  level: "INFO"
```

Load with PyYAML, validate required fields.

#### Task 1.4 — `contract_parser.py` — Parse the contract file

```python
def parse_contract(contract_path: str) -> dict:
    """
    Parse wtp-demo-01.contract.yaml.
    
    Returns:
    {
        "plant": {...},
        "areas": [...],
        "assets": [...],
        "signals": [
            {
                "signal_id": "RWP-101.flow_rate",
                "asset_id": "RWP-101",
                "signal_name": "flow_rate",
                "display_name": "RWP-101 Flow Rate",
                "signal_type": "measurement",   # from contract
                "data_type": "float",
                "engineering_unit": "m3/h",
                "status": "active"
            },
            ...
        ],
        "behaviors": {
            "RWP-101.flow_rate": {
                "pattern": "sine",
                "mid": 450.0,
                "amplitude": 35.0,
                "noise": 5.0,
                "signal_id": "RWP-101.flow_rate"
            },
            ...
        },
        "scenarios": [...],   # from extensions.monitoring.scenarios
        "opcua_bindings": [...]
    }
    """
```

**Important**: The contract has NO signal taxonomy (MV/PV/DV/KPI). Your parser reads it as-is. The taxonomy mapping happens in `signal_registry.py`.

---

### Phase 2: Signal Taxonomy + Generators (Day 2-3)

#### Task 2.1 — `signal_registry.py` — Classify all 92 signals

```python
class SignalRegistry:
    """
    Maps each of the 92 signal_ids to its simulation role.
    
    Uses an explicit mapping table based on the Designer spec
    (docs/wtp-simulation-model.md, Section 4).
    """
    
    # Copy the EXACT tables from the Designer spec:
    # - 7 DV signals with their ranges
    # - 12 MV signals with their setpoint ranges and slew rates
    # - 43 PV signals with their dependencies
    # - 30 KPI signals with their derivation formulas
    
    MV_CONFIGS: dict[str, MVConfig] = {
        "COAG-PUMP-101.flow_rate": MVConfig(
            signal_id="COAG-PUMP-101.flow_rate",
            default_sp=12.0, min_sp=5.0, max_sp=25.0,
            slew_rate=2.0, accuracy_pct=2.0
        ),
        # ... ALL 12 MVs from the spec table
    }
    
    DV_CONFIGS: dict[str, DVConfig] = {
        "RAW-WATER-QUALITY-STATION-101.raw_turbidity": DVConfig(
            signal_id="RAW-WATER-QUALITY-STATION-101.raw_turbidity",
            pattern="random_walk", baseline=45.0, amplitude=15.0,
            noise_std=2.0, bounds_min=10.0, bounds_max=120.0
        ),
        # ... ALL 7 DVs from the spec table
    }
    
    def get_signal_type(self, signal_id: str) -> SignalType:
        """Returns MV, DV, PV, or KPI for a signal."""
    
    def get_mv_config(self, signal_id: str) -> MVConfig:
        """Returns actuator configuration for an MV."""
    
    def get_dv_config(self, signal_id: str) -> DVConfig:
        """Returns disturbance configuration for a DV."""
```

#### Task 2.2 — `disturbance_engine.py` — 7 DV generators

```python
class DisturbanceEngine:
    """
    Generates values for 7 Disturbance Variables.
    
    Each DV has:
    - A pattern (random_walk or sine)
    - Baseline, amplitude, noise_std
    - Bounds [min, max]
    - Internal state (current value, phase for sine)
    
    random_walk: value[t] = clamp(value[t-1] + step*N(0,1), min, max)
        with gentle mean-reversion toward baseline
    
    sine: value = baseline + amplitude * sin(2π * freq * t) + noise*N(0,1)
    """
    
    def __init__(self, dv_configs: dict[str, DVConfig]):
        ...
    
    def step(self, dt_s: float, rng: random.Random) -> dict[str, float]:
        """Advance all DVs by dt_s seconds. Returns {signal_id: value}."""
    
    def override(self, signal_id: str, value: float) -> None:
        """Force a DV to a specific value (for scenario injection)."""
    
    def release_override(self, signal_id: str) -> None:
        """Release override, resume normal DV generation."""
```

#### Task 2.3 — `actuator_engine.py` — 12 MV actuators

```python
class ActuatorEngine:
    """
    Manages 12 Manipulated Variables.
    
    Each MV has an Actuator that:
    - Accepts a new setpoint (SP)
    - Moves toward SP at the configured slew rate
    - Has steady-state accuracy error (±accuracy_pct%)
    - Returns the actual value (MV) each tick
    
    SP → [slew rate limit] → [accuracy error] → MV actual
    """
    
    def __init__(self, mv_configs: dict[str, MVConfig]):
        # Create one Actuator per MV, initialized at default_sp
        ...
    
    def set_setpoint(self, signal_id: str, sp: float) -> None:
        """Operator sets a new setpoint for an MV."""
    
    def step(self, dt_s: float, rng: random.Random) -> dict[str, float]:
        """Advance all actuators by dt_s. Returns {signal_id: actual_value}."""
    
    def get_status(self) -> dict:
        """Return current SP and actual for all 12 MVs."""
```

---

### Phase 3: Process Engines (Day 3-4)

#### Task 3.1 — `clarification_engine.py`

**CRITICAL**: This is the heart of WTP simulation. Copy formulas EXACTLY from Designer spec.

```python
def compute_stage3_clarification(
    raw_turbidity: float,
    raw_ph: float,
    coag_dose_rate: float,       # mg/L (from MV1 via chemical conversion)
    ph_pump_flow: float,         # L/min (from MV3)
    mixer_speed: float,          # RPM (from MV8)
    flocculator_speed: float,    # RPM (from MV9)
    rng: random.Random
) -> dict:
    """
    Compute coagulation/flocculation/sedimentation.
    
    Returns: {
        "settled_turbidity": float,  # NTU
        "settled_ph": float,          # pH
        "floc_size_index": float,
        "clarifier_efficiency_index": float,
        "streaming_current": float,    # mV
    }
    """
    # coag_dose_norm = coag_dose_rate / 25.0
    # mixing_norm = mixer_speed / 300.0
    # floc_norm = flocculator_speed / 40.0
    # efficiency_max = 0.85
    # efficiency = efficiency_max * coag_dose_norm * mixing_norm * floc_norm 
    #            * min(1.0, 50.0/raw_turbidity)
    # settled_turbidity = raw_turbidity * (1.0 - efficiency) + gauss(0, 0.3)
    # settled_ph = raw_ph - 0.15*coag_dose_norm + 0.05*(ph_pump_flow/5.0) + gauss(0, 0.02)
    # floc_size_index = 3.5 * coag_dose_norm * floc_norm + gauss(0, 0.1)
    # clarifier_efficiency = efficiency / 0.85
    # streaming_current = -5.0 + 0.3*(coag_dose_rate - 25) + gauss(0, 0.2)
    ...
```

#### Task 3.2 — `filtration_engine.py`

```python
def compute_stage4_filtration(
    settled_turbidity: float,
    settled_ph: float,
    algae_index: float,
    filter_101_effluent_flow: float,
    filter_102_effluent_flow: float,
    filter_101_dp_accum: float,     # mutable, updated in-place
    filter_102_dp_accum: float,     # mutable, updated in-place
    backwash_101_remaining: float,  # mutable
    backwash_102_remaining: float,  # mutable
    dt_s: float,
    rng: random.Random
) -> dict:
    """
    Compute multimedia filtration.
    
    Filter DP accumulates over time:
      d(DP)/dt = 0.02 + 0.01*(settled_turb/8.0) + 0.01*(algae/3.0)  [kPa/s]
    
    When DP > 80 kPa → backwash_remaining = 300 (5 min)
    During backwash → DP frozen
    After backwash → DP reset to 20 kPa
    
    filter_efficiency = 0.96 - 0.06*((dp - 20)/60) + gauss(0, 0.005)
    filtered_turbidity = settled_turbidity * (1 - efficiency) + gauss(0, 0.02)
    filtered_ph = settled_ph + gauss(0, 0.05)
    
    Returns all filter PVs.
    """
    ...
```

#### Task 3.3 — `disinfection_engine.py`

```python
def compute_stage5_disinfection(
    chlorine_pump_flow: float,     # L/min (from MV2)
    raw_ammonia: float,            # mg/L (DV5)
    algae_index: float,            # (DV6)
    contact_time: float,           # min
    rng: random.Random
) -> dict:
    """
    Compute chlorine disinfection chemistry.
    
    cl_dose_rate = chlorine_pump_flow * 0.375  # L/min → mg/L
    cl_demand_nh3 = raw_ammonia * 5.0
    cl_demand_org = algae_index * 0.3
    total_chlorine = cl_dose_rate + gauss(0, 0.05)
    combined_cl = min(cl_demand_nh3 + cl_demand_org, total_chlorine)
    free_chlorine = max(0.0, total_chlorine - combined_cl) + gauss(0, 0.02)
    orp = 450 + 250*(free_chlorine/0.8) + gauss(0, 5)
    
    Returns: {free_chlorine, total_chlorine, orp, cl_dose_rate, ...}
    """
    ...
```

#### Task 3.4 — `energy_engine.py`

```python
def compute_energy(
    rwp101_flow: float, rwp102_flow: float,
    hsp101_flow: float, hsp102_flow: float,
    manifold_pressure: float,
    outlet_pressure: float,
    total_flow: float,
    rng: random.Random
) -> dict:
    """
    Compute pump power curves and total energy.
    
    rwp101_power = 45*(rwp101_flow/450)*(manifold_pressure/250) + gauss(0, 1)
    rwp102_power = (same formula with rwp102_flow)
    hsp101_power = 110*(hsp101_flow/320)*(outlet_pressure/380) + gauss(0, 1)
    hsp102_power = (same formula with hsp102_flow)
    
    total_power = rwp_powers + hsp_powers + 50 (aux load)
    spec_energy = total_power / max(0.1, total_flow)
    
    Returns all power + energy PVs and KPIs.
    """
    ...
```

#### Task 3.5 — `kpi_engine.py`

```python
def compute_all_kpis(
    pv_values: dict[str, float],
    dv_values: dict[str, float],
    mv_values: dict[str, float],
    state: SimulationState,
    rng: random.Random
) -> dict:
    """
    Compute all 30 KPI signals from current PV/DV/MV values.
    
    Includes:
    - chemical_cost_per_m3 = coag_dose_rate*30 + cl_dose_rate*50
    - energy_cost_per_m3 = spec_energy * 2500
    - cost_per_m3 = energy_cost + chemical_cost + 1500
    - outlet_quality_index (weighted composite)
    - outlet_compliance_status (3 checks: turbidity ≤ 1.0, free_cl ≥ 0.2, pH in [6.5, 8.5])
    - outlet_quality_risk_score (weighted: raw_impact 40%, chem_abnorm 30%, energy 20%, compliance 10%)
    - probable_root_cause_code (1xx/2xx/3xx/4xx/5xx/6xx based on highest risk contributor)
    - compliance_rate_today = compliance_frames / total_frames * 100
    - water_production_today = cumulative outlet_flow
    - treatment_yield = 100 - waste/total_intake*100
    
    Copy ALL formulas from Section 3 Stage 8 + Section 4.4 in wtp-simulation-model.md.
    """
    ...
```

---

### Phase 4: Simulation Loop (Day 4)

#### Task 4.1 — `simulation_loop.py` — 8-stage orchestrator

```python
class WtpSimulationLoop:
    """
    Orchestrates one simulation tick through all 8 stages.
    
    Execution order (follow EXACTLY):
    
    STAGE 1: INTAKE
      - Update 7 DVs (disturbance_engine.step)
      - Update 2 pump MVs (actuator_engine.step for RWP-101, RWP-102)
      - Compute: screen_dp, manifold_pressure, motor_currents, motor_powers
    
    STAGE 2: CHEMICAL DOSING
      - Update chemical MVs (COAG-PUMP, CHLORINE-PUMP, PH-PUMP)
      - Compute: coag_dose_rate, cl_dose_rate, streaming_current
      - Compute: tank_levels, chemical_cost_per_m3
    
    STAGE 3: CLARIFICATION  ← MOST IMPORTANT
      - Update mixer/flocculator MVs
      - Call clarification_engine.compute_stage3()
      → settled_turbidity, settled_ph, floc_size_index, clarifier_efficiency
    
    STAGE 4: FILTRATION
      - Call filtration_engine.compute_stage4()
      → filter_dp (accumulates), filtered_turbidity, filtered_ph
    
    STAGE 5: DISINFECTION
      - Call disinfection_engine.compute_stage5()
      → free_chlorine, total_chlorine, orp, cl_dose_rate
    
    STAGE 6: CLEAR WATER
      - clear_water_turbidity = filtered_turbidity * 0.95
      - CWT.quality_index = composite
      - CWT.level (flow balance)
    
    STAGE 7: DISTRIBUTION
      - Update HSP MVs
      - Compute: discharge_pressure, outlet_pressure, outlet_flow
      - Compute: motor_currents, motor_powers, winding_temps
      - outlet_turbidity ≈ clear_water_turbidity
      - outlet_free_cl ≈ free_chlorine * 0.9
      - outlet_ph ≈ filtered_ph
    
    STAGE 8: KPI + TRACEABILITY
      - Call energy_engine.compute_energy()
      - Call kpi_engine.compute_all_kpis()
      → All KPIs, traceability scores, compliance
    
    Collect all 92 signal values → build Measurement list
    
    Accumulate state:
      - total_energy_kwh += total_power * dt_s / 3600
      - total_water_m3 += outlet_flow * dt_s / 3600
      - compliance_frames += outlet_compliance ? 1 : 0
      - total_frames += 1
    """
    
    def __init__(self, contract_parsed: dict, config: dict):
        ...
    
    def step(self, dt_s: float = 1.0) -> list[Measurement]:
        """
        Execute one full simulation tick.
        Returns list of 92 Measurement objects ready for ingestion.
        """
        ...
    
    def get_all_values(self) -> dict[str, float]:
        """Return current value for all 92 signals."""
        ...
```

---

### Phase 5: API + Ingestion (Day 4-5)

#### Task 5.1 — `ingest_client.py`

```python
class IngestClient:
    """
    HTTP client for PlantOS measurement ingestion.
    
    Features:
    - POST to {base_url}/api/v1/measurements/ingest
    - Payload: {"measurements": [{timestamp, signal_id, value, quality, source}, ...]}
    - Retry with exponential backoff: 1s, 2s, 4s, 8s, 16s (max 5 retries)
    - Jitter: ±20% on backoff times
    - Local ring buffer: if PlantOS is down, buffer up to 3600 frames
    - Auto-replay buffered frames when connection restores
    - Connection status: "connected" | "retrying" | "buffering" | "failed"
    """
    
    def __init__(self, base_url: str, endpoint: str, max_retries: int = 5, ...):
        ...
    
    def post_measurements(self, measurements: list[Measurement]) -> bool:
        """Post a frame of measurements. Returns True if successful."""
        ...
    
    def get_status(self) -> dict:
        """Return ingestion status (connected, buffered_count, errors)."""
        ...
```

#### Task 5.2 — `api_server.py`

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

class SetpointRequest(BaseModel):
    value: float

class DisturbanceOverride(BaseModel):
    value: float
    override: bool = True

def create_app(sim_loop: WtpSimulationLoop, ingest_client: IngestClient, 
               scenario_manager, config: dict) -> FastAPI:
    """
    Create FastAPI app with endpoints:
    
    GET  /health
      → {"status": "ok", "simulator": "wtp-sim-01"}
    
    GET  /status
      → Full simulator status including:
        - plant_id, current_scenario, uptime_s
        - total_frames, total_measurements
        - ingestion_status, ingestion_errors
        - All 12 MV SP + actual values
    
    GET  /api/v1/control
      → List all 12 MVs with current SP and actual value
      → {"manipulated_variables": {signal_id: {sp, actual, unit, range}, ...}}
    
    POST /api/v1/control/{signal_id}
      → Set new setpoint for an MV
      → Body: {"value": 18.0}
      → Response: {"signal_id": "...", "old_sp": 12.0, "new_sp": 18.0, "status": "accepted"}
      → 422 if signal_id is not an MV
      → 422 if value out of range
    
    GET  /api/v1/disturbances
      → List all 7 DVs with current values and overrides
    
    POST /api/v1/disturbances/{signal_id}
      → Override a DV value (for scenario injection)
      → Body: {"value": 95.0, "override": true}
    
    DELETE /api/v1/disturbances/{signal_id}
      → Release DV override
    
    GET  /api/v1/scenarios
      → List all 8 scenarios with descriptions
    
    GET  /api/v1/scenarios/current
      → Current active scenario
    
    POST /api/v1/scenarios/{scenario_id}
      → Switch to scenario, smooth transition over transition_s seconds
      → Response includes transition info
    
    GET  /api/v1/telemetry/latest
      → Latest 92 signal values
    
    GET  /api/v1/telemetry/signal/{signal_id}
      → Latest value for one specific signal
    """
    ...
```

#### Task 5.3 — `scenario_manager.py`

```python
class ScenarioManager:
    """
    Manages 8 operational scenarios.
    
    Each scenario is a YAML file under simulators/wtp/scenarios/
    containing MV and DV overrides.
    
    Smooth transition:
    - When switching, identify which MVs/DVs change
    - Linearly interpolate from old value to new value over transition_s seconds
    - After transition completes, use new values directly
    """
    
    def __init__(self, default_scenario: str, transition_s: float):
        ...
    
    def switch_scenario(self, scenario_id: str) -> dict:
        """Initiate smooth transition to a new scenario."""
        ...
    
    def step(self, dt_s: float, actuator_engine, disturbance_engine) -> bool:
        """
        Advance transition if active. Apply interpolated values.
        Returns True if transition is complete.
        """
        ...
    
    def get_current(self) -> str:
        """Return current active scenario ID."""
```

#### Task 5.4 — `main.py` — CLI entry point

```python
"""
WTP Simulator CLI.

Usage:
  python -m simulators.wtp.main \
    --contract path/to/wtp-demo-01.contract.yaml \
    --config simulators/wtp/wtp_config.yaml

  python -m simulators.wtp.main \
    --contract ... \
    --scenario raw_water_contamination \
    --steps 3600 \
    --api-only   # Run API server only, no auto-simulation
"""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True, help="Path to contract YAML")
    parser.add_argument("--config", default="simulators/wtp/wtp_config.yaml")
    parser.add_argument("--scenario", default=None, help="Override default scenario")
    parser.add_argument("--steps", type=int, default=0, help="Run N steps then exit (0 = infinite)")
    parser.add_argument("--api-only", action="store_true", help="Start API only")
    parser.add_argument("--csv-output", default=None, help="Optional CSV output path")
    args = parser.parse_args()
    
    # 1. Load config
    # 2. Parse contract
    # 3. Create SignalRegistry
    # 4. Create DisturbanceEngine, ActuatorEngine
    # 5. Create WtpSimulationLoop
    # 6. Create ScenarioManager
    # 7. Create IngestClient
    # 8. Create FastAPI app
    # 9. Start simulation loop in background thread
    # 10. Start uvicorn server
    ...
```

---

### Phase 6: Scenario Files (Day 5)

#### Task 6.1 — Create 8 scenario YAML files

Each scenario file has this structure:

```yaml
# simulators/wtp/scenarios/raw_water_contamination.yaml
scenario_id: raw_water_contamination
name: "Raw Water Contamination Event"
description: >
  Raw turbidity, COD, and ammonia increase sharply.
  Impact propagates through treatment chain.

# Override MV setpoints
mv_overrides:
  # Optional: change coagulant dose to compensate
  COAG-PUMP-101.flow_rate:
    sp: 18.0  # increase to fight contamination

# Override DV values (inject the contamination)
dv_overrides:
  RAW-WATER-QUALITY-STATION-101.raw_turbidity:
    baseline: 85.0
    amplitude: 25.0
    bounds_max: 150.0
    override: true
  
  RAW-WATER-QUALITY-STATION-101.raw_ammonia:
    baseline: 1.5
    amplitude: 0.5
    override: true
  
  RAW-WATER-QUALITY-STATION-101.raw_conductivity:
    baseline: 550.0
    override: true
```

Create all 8 files following the parameter tables from the Designer spec (Section 4, `wtp-simulation-model.md`). Each scenario has proper MV and DV overrides that produce visibly different behavior.

---

### Phase 7: Tests (Day 5-6)

#### Task 7.1 — Unit tests for each engine

Each test file should:
1. Create the engine with known inputs
2. Call the compute function
3. Assert outputs are within expected ranges
4. Test edge cases (zero flow, max dose, etc.)

Example: `test_clarification_engine.py`
```python
def test_normal_operation():
    result = compute_stage3_clarification(
        raw_turbidity=45.0, raw_ph=7.15,
        coag_dose_rate=25.0, ph_pump_flow=5.0,
        mixer_speed=300, flocculator_speed=40,
        rng=random.Random(42)
    )
    # At optimal settings: ~85% turbidity removal
    # 45 * 0.15 ≈ 6.75 NTU (with noise ~0.3)
    assert 5.0 <= result["settled_turbidity"] <= 8.5
    assert 6.8 <= result["settled_ph"] <= 7.3
    assert 2.5 <= result["floc_size_index"] <= 4.5

def test_low_coagulant_dose():
    result = compute_stage3_clarification(
        raw_turbidity=45.0, raw_ph=7.15,
        coag_dose_rate=8.0,  # LOW dose
        ph_pump_flow=5.0, mixer_speed=300, flocculator_speed=40,
        rng=random.Random(42)
    )
    # Low dose → poor removal
    assert result["settled_turbidity"] > 15.0  # much worse

def test_high_raw_turbidity():
    result = compute_stage3_clarification(
        raw_turbidity=100.0,  # VERY turbid
        raw_ph=7.15,
        coag_dose_rate=25.0, ph_pump_flow=5.0,
        mixer_speed=300, flocculator_speed=40,
        rng=random.Random(42)
    )
    # Harder to treat → lower efficiency
    assert result["settled_turbidity"] > 10.0  # still high after treatment
```

#### Task 7.2 — Integration tests

- `test_simulation_loop.py` — run 100 steps, verify all 92 signals have values
- `test_scenario_manager.py` — switch scenarios, verify MV/DV values change smoothly
- `test_ingest_client.py` — mock PlantOS server, verify POST payload format

---

## Key Numbers to Memorize

| Constant | Value | Where Used |
|----------|-------|-----------|
| Coagulant conversion | ×2.08 | L/min → mg/L |
| Chlorine conversion | ×0.375 | L/min → mg/L |
| Coagulation max efficiency | 0.85 (85%) | Stage 3 |
| Filtration base efficiency | 0.96 (96%) | Stage 4 |
| Filter DP accumulation | 0.02 kPa/s base | Stage 4 |
| Backwash trigger | DP > 80 kPa | Stage 4 |
| Backwash duration | 300 seconds | Stage 4 |
| Backwash DP reset | 20 kPa | Stage 4 |
| NH3 chlorine demand | ×5.0 | Stage 5 |
| Algae chlorine demand | ×0.3 | Stage 5 |
| Free Cl → outlet decay | ×0.9 | Stage 7 |
| Turbidity → COD factor | ×0.3 | Stage 8 |
| Turbidity → TOC factor | ×0.06 | Stage 8 |
| Energy cost rate | 2500 VND/kWh | Stage 8 |
| Coagulant cost | 30 VND per mg/L dose | Stage 8 |
| Chlorine cost | 50 VND per mg/L dose | Stage 8 |
| Fixed operating cost | 1500 VND/m³ | Stage 8 |
| Auxiliary power | 50 kW constant | Stage 8 |

---

## Acceptance Criteria

The WTP Simulator is DONE when:

1. ✅ Runs `python -m simulators.wtp.main --contract ...` without errors
2. ✅ Parses the contract and extracts all 92 signal definitions
3. ✅ Classifies all 92 signals as MV/DV/PV/KPI correctly
4. ✅ DVs generate realistic values within specified ranges
5. ✅ MVs can be changed via API and actual values follow with slew rate
6. ✅ Clarification engine: settled_turbidity ≈ raw_turbidity × (1-efficiency) 
7. ✅ Filtration engine: DP accumulates, backwash triggers at 80 kPa
8. ✅ Disinfection engine: free_chlorine = dosage - NH3 demand
9. ✅ All 92 signal values are generated each tick
10. ✅ Measurements posted to PlantOS in correct format
11. ✅ GET /api/v1/control returns all 12 MVs
12. ✅ POST /api/v1/control/COAG-PUMP-101.flow_rate {"value": 18.0} changes the dose
13. ✅ All 8 scenarios load and produce visibly different behavior
14. ✅ Scenario transitions are smooth (30s interpolation)
15. ✅ Ingestion retries when PlantOS is down
16. ✅ At least 5 scenarios demonstrate visible impact on outlet quality + cost KPIs
17. ✅ All unit tests pass (coverage ≥ 80% for engine modules)

---

## Reference: Quick signal mapping

```
DV1 = RAW-WATER-QUALITY-STATION-101.raw_turbidity (random_walk, 10-120 NTU)
DV2 = RAW-WATER-QUALITY-STATION-101.raw_ph (random_walk, 6.5-9.0)
DV3 = RAW-WATER-QUALITY-STATION-101.raw_conductivity
DV4 = RAW-WATER-QUALITY-STATION-101.raw_temperature (sine, seasonal)
DV5 = RAW-WATER-QUALITY-STATION-101.raw_ammonia
DV6 = RAW-WATER-QUALITY-STATION-101.raw_algae_index
DV7 = INTAKE-STRUCTURE-101.raw_water_level (sine, seasonal)

MV1 = COAG-PUMP-101.flow_rate (SP:12, range:5-25 L/min, slew:2)
MV2 = CHLORINE-PUMP-101.flow_rate (SP:8, range:2-18 L/min, slew:1)
MV3 = PH-PUMP-101.flow_rate (SP:5, range:1-12 L/min, slew:1)
MV4 = RWP-101.flow_rate (SP:450, range:200-550 m³/h, slew:50)
MV5 = RWP-102.flow_rate (SP:440, range:0-500 m³/h, slew:50)
MV6 = HSP-101.flow_rate (SP:320, range:100-400 m³/h, slew:50)
MV7 = HSP-102.flow_rate (SP:320, range:0-450 m³/h, slew:50)
MV8 = FLASH-MIXER-101.mixer_speed (SP:300, range:150-500 RPM, slew:50)
MV9 = FLOCCULATOR-101.flocculator_speed (SP:40, range:10-80 RPM, slew:10)
MV10 = SCREEN-101.running_status (SP:ON, bool)
MV11 = CLARIFIER-SCRAPER-101.running_status (SP:ON, bool)
MV12 = SLUDGE-PUMP-101.running_status (SP:OFF intermittent, bool)
```

---

**Start coding. Follow the implementation order. Read the Designer spec formulas before writing each engine. Ask if any formula is unclear.**
