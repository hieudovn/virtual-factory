# Prompt for Coder — VF-2 ST03: Dynamic Object & Signal Registry

> **Parent:** VF-2 PIM-native Simulation Runtime  
> **Task:** VF2-ST03 — Dynamic Object / Signal Registry  
> **Prerequisite:** ST01 + ST02 completed (loader + validator working)  
> **Critical Rule:** NO hardcoded signal IDs. Registry is fully dynamic, loaded from package.

---

## Context

This is the **architectural heart** of VF-2. Unlike VF-1 which has 92 hardcoded signal IDs in `signal_registry.py`, VF-2's registries are built dynamically from the PIM package at load time. This is what makes VF-2 "PIM-native" — it doesn't know about any specific plant, pump, or signal until the package tells it.

---

## What You're Building

### 1. `object_registry.py` — Queryable object store

```python
from simulators.vf2.models import VF2Package, VF2SimulationObject

class ObjectRegistry:
    """
    Dynamic registry of VF-2 simulation objects, built from a package.
    
    Provides lookup by:
    - simulation_object_id
    - object_type (filter)
    - canonical_id (PIM back-reference)
    - unit_id
    """
    
    def __init__(self, pkg: VF2Package):
        self._by_id: dict[str, VF2SimulationObject] = {}
        for obj in pkg.objects:
            self._by_id[obj.simulation_object_id] = obj
    
    def get(self, simulation_object_id: str) -> VF2SimulationObject | None:
        """Get an object by its simulation_object_id, or None."""
        ...
    
    def get_by_canonical(self, canonical_id: str) -> VF2SimulationObject | None:
        """Get an object by its PIM canonical_id."""
        ...
    
    def filter_by_type(self, object_type: str) -> list[VF2SimulationObject]:
        """Return all objects of a given type."""
        ...
    
    def filter_by_unit(self, unit_id: str) -> list[VF2SimulationObject]:
        """Return all objects in a given unit."""
        ...
    
    @property
    def all_objects(self) -> list[VF2SimulationObject]:
        ...
    
    @property
    def object_count(self) -> int:
        ...
    
    @property
    def object_ids(self) -> list[str]:
        """All simulation_object_ids."""
        ...
    
    @property
    def object_types(self) -> set[str]:
        """Distinct object types present in the package."""
        ...
```

### 2. `signal_registry.py` — Queryable signal store + classification

```python
from simulators.vf2.models import VF2Package, VF2SimulationSignal, VF2SignalDirection, VF2SignalType

class SignalRegistry:
    """
    Dynamic registry of VF-2 simulation signals, built from a package.
    
    NO hardcoded signal IDs. EVERYTHING comes from the package.
    
    Provides:
    - Lookup by simulation_signal_id
    - Filter by direction (VF2_INPUT / VF2_OUTPUT)
    - Filter by signal_type (measurement / status / alarm / setpoint / feedback)
    - Filter by canonical_asset_id (parent object)
    - Default behavior assignment (signal_type → behavior template)
    """
    
    def __init__(self, pkg: VF2Package):
        self._by_id: dict[str, VF2SimulationSignal] = {}
        for sig in pkg.signals:
            self._by_id[sig.simulation_signal_id] = sig
    
    # --- Basic lookup ---
    def get(self, signal_id: str) -> VF2SimulationSignal | None: ...
    
    @property
    def all_signal_ids(self) -> list[str]: ...
    
    @property
    def signal_count(self) -> int: ...
    
    # --- Filter by PIM fields ---
    def filter_by_direction(self, direction: VF2SignalDirection) -> list[VF2SimulationSignal]: ...
    
    def filter_by_signal_type(self, signal_type: VF2SignalType) -> list[VF2SimulationSignal]: ...
    
    def filter_by_asset(self, canonical_asset_id: str) -> list[VF2SimulationSignal]: ...
    
    def filter_by_instrument(self, canonical_instrument_id: str) -> list[VF2SimulationSignal]: ...
    
    # --- Default behavior assignment (per SA C2) ---
    def get_default_behavior(self, signal: VF2SimulationSignal) -> dict:
        """
        Return a default behavior template based on the PIM signal_type.
        
        measurement → {"type": "random_walk", "baseline": initial_value, "noise_std": 0.02}
        status      → {"type": "constant", "value": initial_value}
        alarm       → {"type": "constant", "value": False}
        setpoint    → {"type": "constant", "value": initial_value}
        feedback    → {"type": "dependent", "depends_on": inferred, "transform": "input"}
        """
        ...
    
    # --- Signal grouping ---
    @property
    def input_signals(self) -> list[VF2SimulationSignal]: ...
    
    @property
    def output_signals(self) -> list[VF2SimulationSignal]: ...
    
    @property
    def measurement_signals(self) -> list[VF2SimulationSignal]: ...
    
    @property
    def status_signals(self) -> list[VF2SimulationSignal]: ...
```

### 3. `tests/test_object_registry.py`

```python
import pytest
from pathlib import Path
from simulators.vf2.package_loader import load_package
from simulators.vf2.object_registry import ObjectRegistry

GOLDEN = Path(__file__).resolve().parent.parent / "examples" / "sample_pim_package.json"

class TestObjectRegistry:
    
    def test_from_package(self):
        pkg = load_package(GOLDEN)
        reg = ObjectRegistry(pkg)
        assert reg.object_count == 8
    
    def test_get_existing(self):
        pkg = load_package(GOLDEN)
        reg = ObjectRegistry(pkg)
        obj = reg.get("VF2-REF-PMP-101A")
        assert obj is not None
        assert obj.object_type == "centrifugal_pump"
        assert obj.name == "Main Pump A (duty)"
    
    def test_get_nonexistent(self):
        pkg = load_package(GOLDEN)
        reg = ObjectRegistry(pkg)
        assert reg.get("VF2-NONEXISTENT") is None
    
    def test_filter_by_type(self):
        pkg = load_package(GOLDEN)
        reg = ObjectRegistry(pkg)
        pumps = reg.filter_by_type("centrifugal_pump")
        assert len(pumps) == 2
        motors = reg.filter_by_type("electric_motor")
        assert len(motors) == 2
        valves = reg.filter_by_type("gate_valve")
        assert len(valves) == 2
    
    def test_get_by_canonical(self):
        pkg = load_package(GOLDEN)
        reg = ObjectRegistry(pkg)
        obj = reg.get_by_canonical("ASSET-REF-PMP-101A")
        assert obj is not None
        assert obj.simulation_object_id == "VF2-REF-PMP-101A"
    
    def test_object_ids(self):
        pkg = load_package(GOLDEN)
        reg = ObjectRegistry(pkg)
        ids = reg.object_ids
        assert "VF2-REF-PMP-101A" in ids
        assert "VF2-REF-PMP-MTR-101A" in ids
    
    def test_object_types(self):
        pkg = load_package(GOLDEN)
        reg = ObjectRegistry(pkg)
        types = reg.object_types
        assert "centrifugal_pump" in types
        assert "electric_motor" in types
```

### 4. `tests/test_dynamic_signal_registry.py`

```python
class TestSignalRegistry:
    
    def test_from_package(self):
        pkg = load_package(GOLDEN)
        reg = SignalRegistry(pkg)
        assert reg.signal_count == 4
    
    def test_get_existing(self):
        pkg = load_package(GOLDEN)
        reg = SignalRegistry(pkg)
        sig = reg.get("VF2.PUMP_STATION_01.FT_101.DISCHARGE_FLOW_TRANSMITTER")
        assert sig is not None
        assert sig.data_type == "float64"
        assert sig.engineering_unit == "m3/h"
    
    def test_get_nonexistent(self):
        pkg = load_package(GOLDEN)
        reg = SignalRegistry(pkg)
        assert reg.get("NONEXISTENT.SIGNAL") is None
    
    def test_all_signal_ids(self):
        pkg = load_package(GOLDEN)
        reg = SignalRegistry(pkg)
        ids = reg.all_signal_ids
        assert len(ids) == 4
        assert all(id.startswith("VF2.") for id in ids)
    
    def test_filter_by_direction(self):
        pkg = load_package(GOLDEN)
        reg = SignalRegistry(pkg)
        inputs = reg.filter_by_direction(VF2SignalDirection.VF2_INPUT)
        assert len(inputs) == 4  # All 4 are VF2_INPUT in golden fixture
    
    def test_filter_by_signal_type(self):
        pkg = load_package(GOLDEN)
        reg = SignalRegistry(pkg)
        measurements = reg.filter_by_signal_type(VF2SignalType.MEASUREMENT)
        assert len(measurements) == 4
    
    def test_filter_by_asset(self):
        pkg = load_package(GOLDEN)
        reg = SignalRegistry(pkg)
        sigs = reg.filter_by_asset("ASSET-REF-PMP-101A")
        assert len(sigs) == 3  # FT-101, PT-101, VB-101
    
    def test_default_behavior_measurement(self):
        pkg = load_package(GOLDEN)
        reg = SignalRegistry(pkg)
        sig = reg.get("VF2.PUMP_STATION_01.FT_101.DISCHARGE_FLOW_TRANSMITTER")
        behavior = reg.get_default_behavior(sig)
        assert behavior["type"] == "random_walk"
        assert "baseline" in behavior
    
    def test_default_behavior_status(self):
        # Create a signal with status type
        from simulators.vf2.models import VF2SimulationSignal, VF2SignalBehavior
        sig = VF2SimulationSignal(
            simulation_signal_id="VF2.TEST.STATUS_SIG",
            canonical_asset_id="ASSET-REF-PMP-101A",
            name="Test Status",
            direction=VF2SignalDirection.VF2_OUTPUT,
            behavior=VF2SignalBehavior(signal_type=VF2SignalType.STATUS, initial_value=True)
        )
        reg = SignalRegistry.__new__(SignalRegistry)
        reg._by_id = {sig.simulation_signal_id: sig}
        behavior = reg.get_default_behavior(sig)
        assert behavior["type"] == "constant"
        assert behavior["value"] == True
    
    def test_no_hardcoded_signals(self):
        """VF-2 MUST NOT have hardcoded signal IDs."""
        pkg = load_package(GOLDEN)
        reg = SignalRegistry(pkg)
        # The registry only knows what's in the package
        assert reg.signal_count == len(pkg.signals)
```

### 5. Accept/reject `tests/test_signal_registry_hardcoded.py` (NEGATIVE TEST)

```python
def test_no_hardcoded_dv_configs():
    """VF-2 SignalRegistry must NOT have class-level DV_CONFIGS."""
    from simulators.vf2.signal_registry import SignalRegistry
    assert not hasattr(SignalRegistry, 'DV_CONFIGS'), \
        "VF-2 must not have hardcoded DV_CONFIGS — use package data"

def test_no_hardcoded_mv_configs():
    """VF-2 SignalRegistry must NOT have class-level MV_CONFIGS."""
    from simulators.vf2.signal_registry import SignalRegistry
    assert not hasattr(SignalRegistry, 'MV_CONFIGS'), \
        "VF-2 must not have hardcoded MV_CONFIGS — use package data"

def test_no_hardcoded_pv_signals():
    """VF-2 SignalRegistry must NOT have class-level PV_SIGNALS."""
    from simulators.vf2.signal_registry import SignalRegistry
    assert not hasattr(SignalRegistry, 'PV_SIGNALS'), \
        "VF-2 must not have hardcoded PV_SIGNALS — use package data"
```

---

## Files to Create

| File | Content |
|------|---------|
| `simulators/vf2/object_registry.py` | `ObjectRegistry` class |
| `simulators/vf2/signal_registry.py` | `SignalRegistry` class with default behavior assignment |
| `simulators/vf2/tests/test_object_registry.py` | ~8 tests |
| `simulators/vf2/tests/test_dynamic_signal_registry.py` | ~12 tests (including negative tests for no hardcoding) |

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC-1 | `ObjectRegistry(pkg).object_count == len(pkg.objects)` |
| AC-2 | `ObjectRegistry(pkg).get("VF2-REF-PMP-101A")` returns correct pump object |
| AC-3 | `ObjectRegistry(pkg).filter_by_type("centrifugal_pump")` returns 2 pumps |
| AC-4 | `SignalRegistry(pkg).signal_count == len(pkg.signals)` |
| AC-5 | `SignalRegistry(pkg).get("VF2.PUMP_STATION_01.FT_101...")` returns correct signal |
| AC-6 | `SignalRegistry(pkg).filter_by_asset("ASSET-REF-PMP-101A")` returns 3 signals |
| AC-7 | `get_default_behavior(measurement)` returns `random_walk` |
| AC-8 | `get_default_behavior(status)` returns `constant` |
| AC-9 | NO hardcoded class-level constants (`DV_CONFIGS`, `MV_CONFIGS`, `PV_SIGNALS`, `KPI_SIGNALS`) |
| AC-10 | All tests pass + VF-1 regression OK |
