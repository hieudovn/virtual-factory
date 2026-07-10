# Prompt for Coder — VF-2 ST07: Simulation Loop & Frame Builder

> **Parent:** VF-2 PIM-native Simulation Runtime  
> **Task:** VF2-ST07 — Simulation Loop & Frame Builder  
> **Prerequisite:** ST01-ST06 completed  
> **This is the orchestrator** — ties all previous modules into a working simulator

---

## Context

ST07 is the **integration point** — it combines package loader, validator, registries, topology, behavior engine, and scenario engine into a single `step()` call that produces measurement frames. This is where VF-2 becomes a working simulator.

---

## What You're Building

### `simulation_loop.py` — Orchestrator

```python
from simulators.vf2.models import VF2Package
from simulators.vf2.object_registry import ObjectRegistry
from simulators.vf2.signal_registry import SignalRegistry
from simulators.vf2.topology_engine import TopologyEngine
from simulators.vf2.behavior_engine import BehaviorEngine
from simulators.vf2.scenario_engine import ScenarioEngine

@dataclass
class Measurement:
    timestamp: str
    signal_id: str
    value: float | bool
    quality: str
    source: str

@dataclass  
class SimulationState:
    time_s: float = 0.0
    step_count: int = 0
    signal_values: dict[str, float] = field(default_factory=dict)
    latest_measurements: list[Measurement] = field(default_factory=list)

class Vf2SimulationLoop:
    """
    Orchestrates one simulation tick.
    
    Flow per tick:
    1. BehaviorEngine.step(dt) → raw signal values
    2. TopologyEngine resolves dependent signals (topological order)
    3. ScenarioEngine.step(dt) → apply scenario overrides (with transition)
    4. FrameBuilder.build() → collect all signals into Measurement list
    """
    
    def __init__(self, pkg: VF2Package, config: Vf2Config | None = None):
        self.pkg = pkg
        self.config = config or Vf2Config()
        
        # Build all sub-systems
        self.obj_reg = ObjectRegistry(pkg)
        self.sig_reg = SignalRegistry(pkg)
        self.topology = TopologyEngine(pkg, self.obj_reg, self.sig_reg)
        self.behavior = BehaviorEngine(self.sig_reg)
        self.scenario = ScenarioEngine(pkg, self.config.transition_s)
        
        # Build topology graph once
        self.graph = self.topology.build()
        
        self.state = SimulationState()
        self.rng = random.Random(42)
    
    def step(self, dt_s: float = 1.0) -> list[Measurement]:
        """Execute one full simulation tick."""
        self.state.time_s += dt_s
        self.state.step_count += 1
        
        # Phase 1: Behavior engine generates raw values
        raw_values = self.behavior.step(dt_s, self.state.signal_values)
        self.state.signal_values.update(raw_values)
        
        # Phase 2: Resolve dependent signals in topological order
        for sig_id in self.graph.eval_order:
            sig = self.sig_reg.get(sig_id)
            if sig and sig_id in raw_values:
                continue  # Already computed
            # Dependent signals resolved via behavior engine
            behavior = self.sig_reg.get_default_behavior(sig) if sig else {}
            if behavior.get("type") == "dependent":
                val = self.behavior.step_one(sig_id, dt_s, behavior, self.state.signal_values)
                self.state.signal_values[sig_id] = val
        
        # Phase 3: Apply scenario overrides
        scenario_overrides = self.scenario.step(dt_s)
        for sid, val in scenario_overrides.items():
            self.state.signal_values[sid] = val
        
        # Phase 4: Build measurement frame
        frame = self._build_frame()
        self.state.latest_measurements = frame
        return frame
    
    def _build_frame(self) -> list[Measurement]:
        """Collect all signal values into Measurement objects."""
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        
        frame = []
        for sig_id in self.sig_reg.all_signal_ids:
            val = self.state.signal_values.get(sig_id, 0.0)
            sig = self.sig_reg.get(sig_id)
            
            # Determine quality
            quality = "GOOD"
            if sig and sig.behavior.signal_type.value == "alarm":
                quality = "GOOD"  # Alarms are GOOD when false
            
            frame.append(Measurement(
                timestamp=ts,
                signal_id=sig_id,
                value=val,
                quality=quality,
                source=self.config.source,
            ))
        return frame
    
    def run(self, steps: int, dt_s: float = 1.0) -> list[list[Measurement]]:
        """Run N steps, return all frames."""
        return [self.step(dt_s) for _ in range(steps)]
    
    def activate_scenario(self, scenario_id: str) -> dict:
        return self.scenario.activate(scenario_id)
```

### `frame_builder.py` — Standalone frame builder (optional, can be in simulation_loop)

```python
# FrameBuilder can be a standalone class or integrated in SimulationLoop.
# The key method is _build_frame() which iterates all registered signals
# and wraps them in Measurement objects with timestamp + quality.
```

### `tests/test_simulation_loop.py`

```python
from pathlib import Path
from simulators.vf2.package_loader import load_package
from simulators.vf2.simulation_loop import Vf2SimulationLoop

GOLDEN = Path(__file__).resolve().parent.parent / "examples" / "sample_pim_package.json"

class TestSimulationLoop:
    
    def test_step_produces_frame(self):
        pkg = load_package(GOLDEN)
        loop = Vf2SimulationLoop(pkg)
        frame = loop.step(1.0)
        assert len(frame) == 4  # 4 signals in golden fixture
        for m in frame:
            assert m.signal_id  # not empty
            assert m.timestamp  # ISO 8601
            assert m.source == "vf2-sim-01"
    
    def test_run_60_steps(self):
        pkg = load_package(GOLDEN)
        loop = Vf2SimulationLoop(pkg)
        frames = loop.run(60, 1.0)
        assert len(frames) == 60
        for frame in frames:
            assert len(frame) == 4
    
    def test_signal_values_change_over_time(self):
        pkg = load_package(GOLDEN)
        loop = Vf2SimulationLoop(pkg)
        f1 = loop.step(1.0)
        f2 = loop.step(1.0)
        # At least one signal should change (random_walk on measurements)
        changes = 0
        for m1, m2 in zip(f1, f2):
            if m1.value != m2.value:
                changes += 1
        assert changes > 0
    
    def test_scenario_applies_overrides(self):
        pkg = load_package(GOLDEN)
        loop = Vf2SimulationLoop(pkg)
        # Run a few normal steps
        loop.run(10, 1.0)
        # Activate pump trip
        loop.activate_scenario("SCN-PUMP-TRIP-002")
        # Run through transition
        loop.run(35, 1.0)
        # Check affected signals are 0
        frame = loop.step(1.0)
        ft101 = [m for m in frame if "FT_101" in m.signal_id]
        if ft101:
            assert ft101[0].value == 0.0
    
    def test_state_accumulates(self):
        pkg = load_package(GOLDEN)
        loop = Vf2SimulationLoop(pkg)
        loop.run(10, 1.0)
        assert loop.state.step_count == 10
        assert loop.state.time_s == 10.0
```

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC-1 | `step()` returns list of 4 Measurements (golden fixture) |
| AC-2 | `run(60)` returns 60 frames |
| AC-3 | Signal values change over time (random_walk active) |
| AC-4 | Scenario activation changes affected signal values to 0 |
| AC-5 | `state.step_count` accumulates correctly |
| AC-6 | Every Measurement has timestamp + signal_id + value + quality + source |
| AC-7 | All tests pass + VF-1 OK |
