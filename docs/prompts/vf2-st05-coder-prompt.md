# Prompt for Coder — VF-2 ST05: Behavior Engine & Transform Evaluator

> **Parent:** VF-2 PIM-native Simulation Runtime  
> **Task:** VF2-ST05 — Behavior Engine & Transform Evaluator  
> **Prerequisite:** ST01-ST04 completed (loader, validator, registries, topology working)

---

## Context

The behavior engine generates signal values each tick. Unlike VF-1's WTP-specific stage formulas, VF-2's behavior engine is generic — it reads signal metadata from the SignalRegistry and applies the appropriate pattern.

Per SA C2: PIM provides metadata (signal_type, initial_value), VF-2 owns the behavior generation.

---

## What You're Building

### 1. `behavior_engine.py` — Pattern-based signal generators

```python
import random
from simulators.vf2.signal_registry import SignalRegistry
from simulators.vf2.models import VF2SimulationSignal

class BehaviorState:
    """Per-signal mutable state carried across ticks."""
    def __init__(self, signal_id: str):
        self.signal_id = signal_id
        self.current_value: float = 0.0
        self.phase: float = 0.0          # For sine
        self.accumulated_drift: float = 0.0  # For degradation
        self.rw_position: float = 0.0    # For random_walk

class BehaviorEngine:
    """
    Generates signal values for each tick.
    
    Uses SignalRegistry.get_default_behavior() to determine
    which pattern to apply for each signal.
    
    Supported patterns in MVP:
    - constant: Fixed value
    - random_walk: Random walk with bounds + mean reversion
    - sine: Oscillating with phase accumulator
    - degradation: Slow linear drift
    - dependent: Expression-based (from transform_evaluator)
    """
    
    def __init__(self, sig_reg: SignalRegistry, rng: random.Random | None = None):
        self.sig_reg = sig_reg
        self.rng = rng or random.Random(42)
        self._state: dict[str, BehaviorState] = {}  # Per-signal state
    
    def step(self, dt_s: float, signal_values: dict[str, float]) -> dict[str, float]:
        """
        Generate values for all signals for one tick.
        
        Args:
            dt_s: Tick duration in seconds
            signal_values: Current values of all signals (for dependent resolution)
        
        Returns:
            {signal_id: new_value} for all signals
        """
        ...
    
    def step_one(self, signal_id: str, dt_s: float, 
                 behavior: dict, signal_values: dict[str, float]) -> float:
        """Generate one signal value based on its behavior config."""
        btype = behavior.get("type", "constant")
        
        if btype == "constant":
            return self._constant(behavior)
        elif btype == "random_walk":
            return self._random_walk(signal_id, behavior, dt_s)
        elif btype == "sine":
            return self._sine(signal_id, behavior, dt_s)
        elif btype == "degradation":
            return self._degradation(signal_id, behavior, dt_s)
        elif btype == "dependent":
            return self._dependent(behavior, signal_values)
        else:
            return behavior.get("value", behavior.get("baseline", 0.0))
    
    def _constant(self, behavior: dict) -> float:
        return behavior.get("value", 0.0)
    
    def _random_walk(self, signal_id: str, behavior: dict, dt_s: float) -> float:
        state = self._get_state(signal_id)
        baseline = behavior.get("baseline", 0.0)
        noise_std = behavior.get("noise_std", 0.02)
        bounds_min = behavior.get("bounds_min", -1e9)
        bounds_max = behavior.get("bounds_max", 1e9)
        
        # Random walk step
        step = self.rng.gauss(0, noise_std * (dt_s ** 0.5))
        # Mean reversion toward baseline (gentle pull)
        reversion = 0.01 * (baseline - state.rw_position) * dt_s
        state.rw_position += step + reversion
        state.rw_position = clamp(state.rw_position, bounds_min, bounds_max)
        return state.rw_position
    
    def _sine(self, signal_id: str, behavior: dict, dt_s: float) -> float:
        state = self._get_state(signal_id)
        baseline = behavior.get("baseline", 0.0)
        amplitude = behavior.get("amplitude", 1.0)
        freq = behavior.get("frequency_hz", 0.1)
        noise_std = behavior.get("noise_std", 0.0)
        
        import math
        state.phase += 2 * math.pi * freq * dt_s
        value = baseline + amplitude * math.sin(state.phase)
        value += self.rng.gauss(0, noise_std)
        return value
    
    def _degradation(self, signal_id: str, behavior: dict, dt_s: float) -> float:
        state = self._get_state(signal_id)
        baseline = behavior.get("baseline", 0.0)
        drift_rate = behavior.get("drift_rate_per_s", 0.0)
        noise_std = behavior.get("noise_std", 0.0)
        
        state.accumulated_drift += drift_rate * dt_s
        value = baseline + state.accumulated_drift
        value += self.rng.gauss(0, noise_std)
        return value
    
    def _dependent(self, behavior: dict, signal_values: dict[str, float]) -> float:
        from .transform_evaluator import evaluate_transform
        transform = behavior.get("transform", "input")
        depends_on = behavior.get("depends_on", [])
        
        # Build namespace: map upstream signal IDs to their current values
        namespace = {sid: signal_values.get(sid, 0.0) for sid in depends_on}
        if depends_on:
            namespace["input"] = signal_values.get(depends_on[0], 0.0)
        
        return evaluate_transform(transform, namespace, self.rng)
```

### 2. `transform_evaluator.py` — Safe expression evaluator

```python
import math
import random

# Whitelist of allowed functions
_SAFE_FUNCTIONS = {
    "abs": abs,
    "max": max,
    "min": min,
    "round": round,
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "log": math.log,
    "exp": math.exp,
    "pi": math.pi,
    "e": math.e,
}

def evaluate_transform(expr: str, namespace: dict[str, float], 
                       rng: random.Random) -> float:
    """
    Safely evaluate a transform expression.
    
    Allowed:
    - Variables from namespace
    - Basic math: +, -, *, /, **, (, )
    - Whitelist functions: abs, max, min, sqrt, sin, cos, log, exp
    - noise(mean, std) → Gaussian random
    - clamp(x, lo, hi) → bound to range
    
    Forbidden:
    - __builtins__, __import__, exec, eval, open, etc.
    
    Args:
        expr: Expression string, e.g. "input * 120.0 + noise(0, 2.0)"
        namespace: Variable values, e.g. {"input": 1.0, "RUN_STATUS": 1.0}
        rng: Random generator for noise()
    
    Returns:
        Evaluated float value
    """
    # Build safe namespace
    local_ns = dict(namespace)
    local_ns.update(_SAFE_FUNCTIONS)
    local_ns["noise"] = lambda m, s: rng.gauss(m, s)
    local_ns["clamp"] = lambda x, lo, hi: max(lo, min(x, hi))
    
    # Use eval with restricted builtins
    result = eval(expr, {"__builtins__": {}}, local_ns)
    return float(result)
```

### 3. `tests/test_behavior_engine.py`

```python
import random
from simulators.vf2.behavior_engine import BehaviorEngine, BehaviorState

class TestBehaviorEngine:
    
    def test_constant(self):
        engine = BehaviorEngine(None, random.Random(42))
        val = engine.step_one("test", 1.0, {"type": "constant", "value": 42.0}, {})
        assert val == 42.0
    
    def test_random_walk_stays_in_bounds(self):
        engine = BehaviorEngine(None, random.Random(42))
        behavior = {"type": "random_walk", "baseline": 50.0, "noise_std": 1.0,
                    "bounds_min": 40.0, "bounds_max": 60.0}
        values = [engine.step_one("rw", 1.0, behavior, {}) for _ in range(1000)]
        assert all(40.0 <= v <= 60.0 for v in values)
    
    def test_sine_oscillates(self):
        engine = BehaviorEngine(None, random.Random(42))
        behavior = {"type": "sine", "baseline": 50.0, "amplitude": 10.0,
                    "frequency_hz": 1.0, "noise_std": 0.0}
        values = [engine.step_one("s", 0.01, behavior, {}) for _ in range(100)]
        # Should oscillate
        assert min(values) < 50.0 and max(values) > 50.0
    
    def test_degradation_drifts(self):
        engine = BehaviorEngine(None, random.Random(42))
        behavior = {"type": "degradation", "baseline": 100.0, "drift_rate_per_s": 1.0, "noise_std": 0.0}
        v1 = engine.step_one("d", 10.0, behavior, {})
        v2 = engine.step_one("d", 10.0, behavior, {})
        assert v2 > v1  # Should be drifting up
    
    def test_dependent_simple(self):
        engine = BehaviorEngine(None, random.Random(42))
        behavior = {"type": "dependent", "depends_on": ["STATUS"],
                    "transform": "input * 120.0"}
        val = engine.step_one("dep", 1.0, behavior, {"STATUS": 1.0})
        assert val == 120.0
    
    def test_step_generates_all_signals(self):
        """Integration: step() should produce values for all signals."""
        from simulators.vf2.package_loader import load_package
        from simulators.vf2.signal_registry import SignalRegistry
        from pathlib import Path
        
        GOLDEN = Path(__file__).resolve().parent.parent / "examples" / "sample_pim_package.json"
        pkg = load_package(GOLDEN)
        sig_reg = SignalRegistry(pkg)
        engine = BehaviorEngine(sig_reg, random.Random(42))
        
        values = engine.step(1.0, {})
        assert len(values) == sig_reg.signal_count
        assert all(isinstance(v, (int, float)) for v in values.values())
```

### 4. `tests/test_transform_evaluator.py`

```python
from simulators.vf2.transform_evaluator import evaluate_transform
import random

class TestTransformEvaluator:
    
    def test_simple_input(self):
        rng = random.Random(42)
        val = evaluate_transform("input * 2.0", {"input": 5.0}, rng)
        assert val == 10.0
    
    def test_clamp(self):
        rng = random.Random(42)
        assert evaluate_transform("clamp(5, 0, 10)", {}, rng) == 5.0
        assert evaluate_transform("clamp(15, 0, 10)", {}, rng) == 10.0
        assert evaluate_transform("clamp(-5, 0, 10)", {}, rng) == 0.0
    
    def test_noise_within_range(self):
        rng = random.Random(42)
        values = [evaluate_transform("noise(50, 5)", {}, rng) for _ in range(100)]
        assert all(30 <= v <= 70 for v in values)  # Within 4σ
    
    def test_math_functions(self):
        rng = random.Random(42)
        assert evaluate_transform("abs(-5)", {}, rng) == 5.0
        assert evaluate_transform("max(3, 7)", {}, rng) == 7.0
        assert evaluate_transform("sqrt(16)", {}, rng) == 4.0
    
    def test_rejects_dangerous_code(self):
        rng = random.Random(42)
        with pytest.raises(Exception):
            evaluate_transform("__import__('os').system('ls')", {}, rng)
    
    def test_multi_variable(self):
        rng = random.Random(42)
        ns = {"A": 10.0, "B": 3.0}
        assert evaluate_transform("A + B * 2", ns, rng) == 16.0
```

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC-1 | `constant` returns fixed value across ticks |
| AC-2 | `random_walk` stays within bounds over 1000 steps |
| AC-3 | `sine` oscillates around baseline |
| AC-4 | `degradation` accumulates drift correctly |
| AC-5 | `dependent` evaluates transform from upstream values |
| AC-6 | `transform_evaluator` supports `clamp`, `noise`, `abs`, `max`, `min`, `sqrt` |
| AC-7 | `transform_evaluator` rejects `__import__`, `open`, `exec` |
| AC-8 | `step()` generates values for ALL signals in golden fixture |
| AC-9 | All tests pass + VF-1 OK |
