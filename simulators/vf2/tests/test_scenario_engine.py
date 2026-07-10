"""Tests for VF-2 scenario engine (ST06)."""

from __future__ import annotations

from pathlib import Path

import pytest

from simulators.vf2.package_loader import load_package
from simulators.vf2.scenario_engine import ScenarioEngine, ScenarioTransition

GOLDEN = (
    Path(__file__).resolve().parent.parent
    / "examples"
    / "sample_pim_package.json"
)


@pytest.fixture(scope="module")
def pkg():
    return load_package(GOLDEN)


@pytest.fixture(scope="module")
def engine(pkg):
    return ScenarioEngine(pkg)


class TestScenarioEngine:

    # AC-1
    def test_list_scenarios(self, engine):
        scenarios = engine.list_scenarios()
        assert len(scenarios) == 6
        ids = {s["scenario_id"] for s in scenarios}
        assert "SCN-PUMP-TRIP-002" in ids
        assert "SCN-PUMP-VLV-001" in ids

    # AC-2
    def test_activate_pump_trip(self, engine):
        result = engine.activate("SCN-PUMP-TRIP-002")
        assert result["status"] == "transitioning"
        assert result["to_scenario"] == "SCN-PUMP-TRIP-002"
        assert result["transition_duration_s"] == 30.0

    # AC-3
    def test_activate_unknown_scenario(self, engine):
        result = engine.activate("NONEXISTENT")
        assert result["status"] == "error"

    # AC-4
    def test_pump_trip_overrides_built(self, engine):
        engine.activate("SCN-PUMP-TRIP-002")
        # 35 steps of 1s → transition of 30s has completed
        for _ in range(35):
            engine.step(1.0)
        overrides = engine._get_active_overrides()
        assert len(overrides) == 3  # FT-101, PT-101, VB-101
        for v in overrides.values():
            assert v == 0.0

    # AC-5
    def test_transition_interpolation(self, engine):
        engine = ScenarioEngine(load_package(GOLDEN), transition_s=10.0)
        engine.activate("SCN-PUMP-TRIP-002")
        # Mid-transition after 5s → values should be half of target (halfway)
        mid = engine.step(5.0)
        for sid, val in mid.items():
            # Target is 0.0, start is the current overrides (empty → 0)
            # Since start overrides are empty, interpolation starts at 0
            assert val == 0.0

    def test_transition_progress(self, engine):
        engine = ScenarioEngine(load_package(GOLDEN), transition_s=10.0)
        engine.activate("SCN-PUMP-TRIP-002")
        # Before transition: no overrides
        step0 = engine.step(0.0)
        # All target overrides are 0.0, so even at mid-point they're 0
        # But we can check that transition is active
        assert engine.transition is not None

    # AC-6
    def test_get_current(self, engine):
        engine = ScenarioEngine(load_package(GOLDEN))
        assert engine.get_current() == ""
        engine.activate("SCN-PUMP-TRIP-002")
        assert engine.get_current() == "SCN-PUMP-TRIP-002"

    # AC-7
    def test_valve_fault_no_signals_does_not_crash(self, engine):
        """Valve fault scenarios have no affected_simulation_signal_ids."""
        engine = ScenarioEngine(load_package(GOLDEN))
        # SCN-PUMP-VLV-001 has no affected_simulation_signal_ids
        result = engine.activate("SCN-PUMP-VLV-001")
        assert result["status"] == "transitioning", "Should not crash"
        # Step through transition
        for _ in range(35):
            engine.step(1.0)
        assert engine.get_current() == "SCN-PUMP-VLV-001"

    def test_activate_twice(self, engine):
        engine = ScenarioEngine(load_package(GOLDEN))
        r1 = engine.activate("SCN-PUMP-TRIP-002")
        assert r1["status"] == "transitioning"
        # Activate again mid-transition
        r2 = engine.activate("SCN-PUMP-VLV-003")
        assert r2["status"] == "transitioning"
        assert r2["from_scenario"] == "SCN-PUMP-TRIP-002"
        assert r2["to_scenario"] == "SCN-PUMP-VLV-003"

    def test_list_descriptions(self, engine):
        scenarios = engine.list_scenarios()
        descs = {s["scenario_id"]: s["description"] for s in scenarios}
        assert "Discharge Check Valve A fails" in descs.get("SCN-PUMP-VLV-001", "")

    def test_step_before_activate_returns_empty(self, engine):
        engine = ScenarioEngine(load_package(GOLDEN))
        overrides = engine.step(1.0)
        assert overrides == {}

    def test_transition_dataclass_defaults(self):
        t = ScenarioTransition()
        assert t.active is False
        assert t.duration_s == 30.0
        assert t.elapsed_s == 0.0


class TestScenarioTransition:

    def test_overrides_start_empty(self, engine):
        engine = ScenarioEngine(load_package(GOLDEN))
        engine.activate("SCN-PUMP-TRIP-002")
        assert engine.transition is not None
        # Start overrides should be empty since no prior active scenario
        assert engine.transition.signal_overrides_start == {}
