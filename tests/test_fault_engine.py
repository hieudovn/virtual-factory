"""Tests for the Fault Lifecycle Engine and fault models."""

import pytest

from virtual_factory.faults.fault_models import (
    FaultConfig,
    FaultInstance,
    FaultLibrary,
    FaultSeverity,
    FaultSymptom,
    MaintenanceAction,
    RecoveryProfile,
    SEVERITY_CURVES,
)
from virtual_factory.faults.fault_engine import FaultEngine, FaultScheduler
from virtual_factory.core.runtime_state import RuntimeState


class TestFaultSeverity:
    def test_severity_labels(self):
        inst = FaultInstance(
            fault_config=FaultConfig(
                fault_id="test", category="test",
                display_name="Test Fault", severity_curve="linear",
                growth_rate=0.01,
            ),
            equipment_id="EQ01",
            start_time_s=0.0,
            initial_severity=0.0,
        )
        assert inst.severity_label == FaultSeverity.NONE

        inst._current_severity = 0.05
        assert inst.severity_label == FaultSeverity.INCIPIENT

        inst._current_severity = 0.3
        assert inst.severity_label == FaultSeverity.DEVELOPING

        inst._current_severity = 0.6
        assert inst.severity_label == FaultSeverity.DEGRADED

        inst._current_severity = 0.85
        assert inst.severity_label == FaultSeverity.CRITICAL

        inst._current_severity = 0.98
        assert inst.severity_label == FaultSeverity.FAILED


class TestSeverityCurves:
    def test_linear(self):
        curve = SEVERITY_CURVES["linear"]
        assert curve(0.0) == 0.0
        assert curve(0.5) == 0.5
        assert curve(1.0) == 1.0

    def test_exponential(self):
        curve = SEVERITY_CURVES["exponential"]
        assert curve(0.0) == 0.0
        assert curve(1.0) == pytest.approx(1.0 - 2 ** (-3), rel=0.01)

    def test_sigmoid(self):
        curve = SEVERITY_CURVES["sigmoid"]
        assert curve(0.0) < 0.04  # 1/(1+2^5) ≈ 0.03
        assert 0.4 < curve(0.5) < 0.6
        assert curve(1.0) > 0.96  # 1/(1+2^-5) ≈ 0.97

    def test_step(self):
        curve = SEVERITY_CURVES["step"]
        assert curve(0.0) == 0.0
        assert curve(0.5) == 0.0
        assert curve(0.8) == 1.0
        assert curve(1.0) == 1.0


class TestFaultProgression:
    def test_linear_progression(self):
        config = FaultConfig(
            fault_id="test", category="test",
            display_name="Test", severity_curve="linear",
            growth_rate=0.01,
        )
        instance = FaultInstance(
            fault_config=config,
            equipment_id="EQ01",
            start_time_s=0.0,
            initial_severity=0.0,
        )

        # After 50 steps at 1s each, t=50, normalized t=0.5, linear=0.5
        for _ in range(50):
            instance.advance(1.0)
        assert instance.severity == pytest.approx(0.5, rel=0.05)

        # After 100 steps, t=100, normalized=1.0, linear=1.0
        for _ in range(50):
            instance.advance(1.0)
        assert instance.severity == pytest.approx(1.0, rel=0.01)

    def test_progression_with_initial_severity(self):
        config = FaultConfig(
            fault_id="test", category="test",
            display_name="Test", severity_curve="linear",
            growth_rate=0.01,
        )
        instance = FaultInstance(
            fault_config=config,
            equipment_id="EQ01",
            start_time_s=0.0,
            initial_severity=0.2,
        )
        assert instance.severity == 0.2

    def test_recovery_instant(self):
        config = FaultConfig(
            fault_id="test", category="test",
            display_name="Test", severity_curve="linear",
            growth_rate=0.01,
            maintenance_actions=[
                MaintenanceAction(
                    action_id="fix", action_type="repair",
                    recovery=RecoveryProfile(method="instant", residual_severity=0.0),
                )
            ],
        )
        instance = FaultInstance(
            fault_config=config,
            equipment_id="EQ01",
            start_time_s=0.0,
            initial_severity=0.5,
        )
        instance.start_recovery(config.maintenance_actions[0])
        instance.advance(1.0)
        assert instance.severity == 0.0
        assert not instance.active

    def test_recovery_linear(self):
        config = FaultConfig(
            fault_id="test", category="test",
            display_name="Test", severity_curve="linear",
            growth_rate=0.01,
            maintenance_actions=[
                MaintenanceAction(
                    action_id="fix", action_type="repair",
                    recovery=RecoveryProfile(method="linear", duration_s=100.0, residual_severity=0.1),
                )
            ],
        )
        instance = FaultInstance(
            fault_config=config,
            equipment_id="EQ01",
            start_time_s=0.0,
            initial_severity=1.0,
        )
        instance.start_recovery(config.maintenance_actions[0])
        # Halfway through recovery
        for _ in range(50):
            instance.advance(1.0)
        # severity should be between 0.4 and 0.65 (linear from 1.0 to 0.1)
        assert 0.4 < instance.severity < 0.65

    def test_symptom_propagation(self):
        config = FaultConfig(
            fault_id="test", category="test",
            display_name="Test", severity_curve="linear",
            growth_rate=0.01,
            symptoms=[
                FaultSymptom(variable="EQ01.vib", effect_type="additive", magnitude=10.0),
            ],
        )
        instance = FaultInstance(
            fault_config=config,
            equipment_id="EQ01",
            start_time_s=0.0,
            initial_severity=0.5,
        )
        val = instance.get_symptom_value(config.symptoms[0], current_time_s=0.0)
        assert val == pytest.approx(5.0, rel=0.01)  # 0.5 * 10


class TestFaultLibrary:
    def test_register_and_get(self):
        lib = FaultLibrary()
        config = FaultConfig(fault_id="test", category="cat1", display_name="Test")
        lib.register(config)
        assert lib.get("test") is config
        assert "test" in lib
        assert len(lib) == 1

    def test_list_by_category(self):
        lib = FaultLibrary()
        lib.register(FaultConfig(fault_id="f1", category="compressor", display_name="F1"))
        lib.register(FaultConfig(fault_id="f2", category="compressor", display_name="F2"))
        lib.register(FaultConfig(fault_id="f3", category="pump", display_name="F3"))

        assert len(lib.list_by_category("compressor")) == 2
        assert len(lib.list_by_category("pump")) == 1
        assert len(lib.list_by_category("fan")) == 0
        assert lib.categories() == ["compressor", "pump"]


class TestFaultEngine:
    def test_inject_and_step(self):
        lib = FaultLibrary()
        lib.register(FaultConfig(
            fault_id="bearing_wear", category="compressor",
            display_name="Bearing Wear", severity_curve="linear",
            growth_rate=0.01,
            symptoms=[
                FaultSymptom(variable="COMP01.vibration_de_mm_s", effect_type="additive", magnitude=10.0),
            ],
        ))
        engine = FaultEngine(library=lib)
        state = RuntimeState()
        state.set_truth("COMP01.vibration_de_mm_s", 2.0)

        instance = engine.inject_fault("bearing_wear", "COMP01", 0.0, 0.0)
        assert instance is not None

        # Run several steps
        for _ in range(20):
            engine.step(state, 0.0)

        active = engine.get_active_faults("COMP01")
        assert len(active) == 1
        assert active[0].severity > 0.1

    def test_scheduled_fault(self):
        lib = FaultLibrary()
        lib.register(FaultConfig(
            fault_id="test", category="test",
            display_name="Test", severity_curve="linear",
            growth_rate=0.01,
        ))
        engine = FaultEngine(library=lib)
        engine.schedule_fault(FaultScheduler("test", "EQ01", 10.0))
        state = RuntimeState()

        # Before schedule time
        engine.step(state, 5.0)
        assert len(engine.get_active_faults()) == 0

        # After schedule time
        engine.step(state, 15.0)
        assert len(engine.get_active_faults()) == 1

    def test_health_index(self):
        lib = FaultLibrary()
        lib.register(FaultConfig(
            fault_id="f1", category="test",
            display_name="F1", severity_curve="linear",
            growth_rate=0.01,
        ))
        engine = FaultEngine(library=lib)
        engine.inject_fault("f1", "EQ01", 0.0, 0.3)
        health = engine.get_health_index("EQ01")
        assert health == pytest.approx(0.7, rel=0.01)

    def test_health_index_no_faults(self):
        lib = FaultLibrary()
        engine = FaultEngine(library=lib)
        assert engine.get_health_index("EQ01") == 1.0

    def test_apply_maintenance(self):
        lib = FaultLibrary()
        action = MaintenanceAction(
            action_id="fix", action_type="repair",
            recovery=RecoveryProfile(method="instant", residual_severity=0.0),
        )
        lib.register(FaultConfig(
            fault_id="test", category="test",
            display_name="Test", severity_curve="linear",
            growth_rate=0.01,
            maintenance_actions=[action],
        ))
        engine = FaultEngine(library=lib)
        engine.inject_fault("test", "EQ01", 0.0, 0.8)

        result = engine.apply_maintenance("test", "EQ01", action, 0.0)
        assert result is True

    def test_apply_maintenance_nonexistent(self):
        lib = FaultLibrary()
        engine = FaultEngine(library=lib)
        result = engine.apply_maintenance("nonexistent", "EQ01",
                                          MaintenanceAction(action_id="x", action_type="repair"), 0.0)
        assert result is False
