# Prompt for Coder — VF-2 ST06: Scenario Engine

> **Parent:** VF-2 PIM-native Simulation Runtime  
> **Task:** VF2-ST06 — Scenario Engine  
> **Prerequisite:** ST01-ST05 completed  
> **SA Note C4:** Map PIM `expected_effects` → VF-2 runtime templates

---

## Context

The scenario engine activates fault scenarios. Per SA C4, PIM scenarios have `expected_effects` (human-readable) + `affected_simulation_signal_ids` (machine-readable). VF-2 maps these to runtime signal overrides.

---

## What You're Building

### `scenario_engine.py`

```python
from simulators.vf2.models import VF2Package, VF2Scenario

@dataclass
class ScenarioTransition:
    """Smooth transition between scenarios."""
    active: bool = False
    from_scenario: str = ""
    to_scenario: str = ""
    duration_s: float = 30.0
    elapsed_s: float = 0.0
    signal_overrides_start: dict[str, float] = field(default_factory=dict)
    signal_overrides_target: dict[str, float] = field(default_factory=dict)

class ScenarioEngine:
    """
    Activates fault scenarios with signal overrides.
    
    Scenario types supported:
    - pump_trip: Flow→0, pressure→0, vibration→0
    - valve_fault: Flow→0 or restricted (no signals mapped in MVP → default template)
    - feeder_trip: Power→0 for downstream equipment
    
    Smooth transition: linear interpolation over transition_s seconds.
    """
    
    def __init__(self, pkg: VF2Package, transition_s: float = 30.0):
        self.scenarios: dict[str, VF2Scenario] = {
            s.scenario_id: s for s in pkg.scenarios
        }
        self.active_scenario: VF2Scenario | None = None
        self.transition: ScenarioTransition | None = None
        self.transition_duration_s = transition_s
    
    def activate(self, scenario_id: str) -> dict:
        """Activate a scenario. Returns status."""
        if scenario_id not in self.scenarios:
            return {"status": "error", "message": f"Scenario '{scenario_id}' not found"}
        
        scn = self.scenarios[scenario_id]
        old = self.active_scenario.scenario_id if self.active_scenario else "none"
        self.active_scenario = scn
        
        # Build overrides from affected_simulation_signal_ids + scenario type template
        overrides = self._build_overrides(scn)
        
        self.transition = ScenarioTransition(
            active=True,
            from_scenario=old,
            to_scenario=scenario_id,
            duration_s=self.transition_duration_s,
            signal_overrides_target=overrides,
        )
        
        return {
            "status": "transitioning",
            "from_scenario": old,
            "to_scenario": scenario_id,
            "transition_duration_s": self.transition_duration_s,
        }
    
    def step(self, dt_s: float) -> dict[str, float]:
        """
        Advance transition by dt_s.
        Returns current signal overrides (interpolated if transitioning).
        """
        if self.transition is None or not self.transition.active:
            return self._get_active_overrides()
        
        self.transition.elapsed_s += dt_s
        progress = min(1.0, self.transition.elapsed_s / self.transition.duration_s)
        
        # Linear interpolation
        overrides = {}
        for sid, target in self.transition.signal_overrides_target.items():
            start = self.transition.signal_overrides_start.get(sid, target)
            overrides[sid] = start + (target - start) * progress
        
        if progress >= 1.0:
            self.transition.active = False
            self.transition.signal_overrides_start = dict(self.transition.signal_overrides_target)
        
        return overrides
    
    def _build_overrides(self, scn: VF2Scenario) -> dict[str, float]:
        """
        Map scenario type + affected signals to runtime overrides.
        
        pump_trip template:
          - All affected measurement signals → 0.0
        
        valve_fault template (default when no affected signals):
          - All signals on trigger object → 0.0 (flow blocked)
          - Log warning: "No affected signals specified; applying template defaults"
        """
        overrides = {}
        affected = scn.affected_simulation_signal_ids
        
        if scn.scenario_type == "pump_trip":
            for sid in affected:
                overrides[sid] = 0.0
        
        elif scn.scenario_type == "valve_fault":
            for sid in affected:
                overrides[sid] = 0.0
            if not affected:
                # Default: block all signals on trigger object
                pass  # Handled by simulation loop via topology
        
        return overrides
    
    def _get_active_overrides(self) -> dict[str, float]:
        """Get final overrides (after transition complete)."""
        if self.transition and not self.transition.active:
            return dict(self.transition.signal_overrides_target)
        return {}
    
    def get_current(self) -> str:
        return self.active_scenario.scenario_id if self.active_scenario else ""
    
    def list_scenarios(self) -> list[dict]:
        return [{"scenario_id": s.scenario_id, "scenario_type": s.scenario_type,
                 "description": s.description} for s in self.scenarios.values()]
```

### `tests/test_scenario_engine.py`

```python
class TestScenarioEngine:
    
    def test_list_scenarios(self):
        pkg = load_package(GOLDEN)
        engine = ScenarioEngine(pkg)
        scenarios = engine.list_scenarios()
        assert len(scenarios) == 6
    
    def test_activate_pump_trip(self):
        pkg = load_package(GOLDEN)
        engine = ScenarioEngine(pkg)
        result = engine.activate("SCN-PUMP-TRIP-002")
        assert result["status"] == "transitioning"
        assert result["to_scenario"] == "SCN-PUMP-TRIP-002"
    
    def test_activate_unknown_scenario(self):
        pkg = load_package(GOLDEN)
        engine = ScenarioEngine(pkg)
        result = engine.activate("NONEXISTENT")
        assert result["status"] == "error"
    
    def test_pump_trip_overrides_built(self):
        pkg = load_package(GOLDEN)
        engine = ScenarioEngine(pkg)
        engine.activate("SCN-PUMP-TRIP-002")
        # After full transition, all affected signals should be 0
        for _ in range(35):  # 35 steps of 1s, transition is 30s
            engine.step(1.0)
        overrides = engine._get_active_overrides()
        assert len(overrides) == 3  # FT-101, PT-101, VB-101
        for v in overrides.values():
            assert v == 0.0
    
    def test_transition_interpolation(self):
        pkg = load_package(GOLDEN)
        engine = ScenarioEngine(pkg, transition_s=10.0)
        engine.activate("SCN-PUMP-TRIP-002")
        # Mid-transition: values should be between start (current) and target (0)
        mid = engine.step(5.0)
        assert 0.0 < mid.get(list(mid.keys())[0], 0) < max(1.0, ...)  # interpolating
    
    def test_get_current(self):
        pkg = load_package(GOLDEN)
        engine = ScenarioEngine(pkg)
        assert engine.get_current() == ""
        engine.activate("SCN-PUMP-TRIP-002")
        assert engine.get_current() == "SCN-PUMP-TRIP-002"
    
    def test_valve_fault_no_signals_does_not_crash(self):
        pkg = load_package(GOLDEN)
        engine = ScenarioEngine(pkg)
        # Valve fault scenarios have no affected_simulation_signal_ids
        result = engine.activate("SCN-PUMP-VLV-001")
        assert result["status"] == "transitioning"  # Should not crash
```

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC-1 | `list_scenarios()` returns 6 scenarios from golden fixture |
| AC-2 | `activate("SCN-PUMP-TRIP-002")` transitions to pump_trip |
| AC-3 | Unknown scenario → `{"status": "error"}` |
| AC-4 | After full transition, affected signals override to 0.0 |
| AC-5 | Transition interpolates smoothly over duration |
| AC-6 | `get_current()` returns active scenario ID |
| AC-7 | Valve fault without affected signals doesn't crash |
| AC-8 | All tests pass + VF-1 OK |
