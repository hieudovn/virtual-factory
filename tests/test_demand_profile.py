"""Tests: Demand Profile on Boundary Sink."""
import pytest

from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.core.schema import EquipmentConfig
from virtual_factory.equipment.boundary import BoundaryEquipment


@pytest.fixture
def sink_with_profile(profile_params):
    config = EquipmentConfig(
        id="GAS_SINK", model_type="boundary_v1",
        display_name="Test Sink",
        parameters={
            "boundary_type": "sink",
            "pressure_kpa": 280.0,
            "demand_profile": profile_params,
        },
    )
    eq = BoundaryEquipment(config=config)
    state = RuntimeState()
    eq.initialize_state(state)
    return eq, state


class TestDemandProfile:
    def test_constant_no_change(self):
        config = EquipmentConfig(
            id="GAS_SINK", model_type="boundary_v1",
            display_name="Test Sink",
            parameters={
                "boundary_type": "sink",
                "pressure_kpa": 280.0,
                "demand_profile": {"type": "constant"},
            },
        )
        eq = BoundaryEquipment(config=config)
        state = RuntimeState()
        eq.initialize_state(state)
        bp_before = state.get_truth("GAS_SINK.backpressure_kpa")
        eq.process_step(state, dt_s=1.0)
        assert state.get_truth("GAS_SINK.backpressure_kpa") == bp_before

    def test_step_profile(self):
        config = EquipmentConfig(
            id="GAS_SINK", model_type="boundary_v1",
            display_name="Test Sink",
            parameters={
                "boundary_type": "sink",
                "pressure_kpa": 280.0,
                "demand_profile": {
                    "type": "step",
                    "schedule": [
                        {"at_s": 0, "factor": 1.0},
                        {"at_s": 100, "factor": 0.8},
                        {"at_s": 200, "factor": 1.2},
                    ],
                },
            },
        )
        eq = BoundaryEquipment(config=config)
        state = RuntimeState()
        eq.initialize_state(state)

        # Before step change
        for _ in range(50):
            eq.process_step(state, dt_s=1.0)
        assert state.get_truth("GAS_SINK.backpressure_kpa") == 280.0

        # After first step
        for _ in range(60):
            eq.process_step(state, dt_s=1.0)
        assert state.get_truth("GAS_SINK.backpressure_kpa") == pytest.approx(224.0, abs=1)

        # After second step
        for _ in range(100):
            eq.process_step(state, dt_s=1.0)
        assert state.get_truth("GAS_SINK.backpressure_kpa") == pytest.approx(336.0, abs=1)

    def test_daily_shift_profile(self):
        config = EquipmentConfig(
            id="GAS_SINK", model_type="boundary_v1",
            display_name="Test Sink",
            parameters={
                "boundary_type": "sink",
                "pressure_kpa": 200.0,
                "demand_profile": {
                    "type": "daily_shift",
                    "base_flow_m3_s": 1.5,
                    "fluctuation_pct": 10,
                    "schedule": [
                        {"hour": 0, "factor": 0.5},
                        {"hour": 12, "factor": 1.0},
                    ],
                },
            },
        )
        eq = BoundaryEquipment(config=config)
        state = RuntimeState()
        eq.initialize_state(state)

        # t=0: factor 0.5
        eq.process_step(state, dt_s=1.0)
        assert state.get_truth("GAS_SINK.backpressure_kpa") == 100.0  # 200 * 0.5

        # Simulate 12 hours
        for _ in range(int(12 * 3600)):
            eq.process_step(state, dt_s=1.0)
        # At hour 12, factor should be 1.0
        assert state.get_truth("GAS_SINK.backpressure_kpa") == pytest.approx(200.0, abs=1)

    def test_random_profile(self):
        config = EquipmentConfig(
            id="GAS_SINK", model_type="boundary_v1",
            display_name="Test Sink",
            parameters={
                "boundary_type": "sink",
                "pressure_kpa": 100.0,
                "demand_profile": {
                    "type": "random",
                    "fluctuation_pct": 5.0,
                },
            },
        )
        eq = BoundaryEquipment(config=config)
        state = RuntimeState()
        eq.initialize_state(state)

        values = []
        for _ in range(100):
            eq.process_step(state, dt_s=1.0)
            values.append(state.get_truth("GAS_SINK.backpressure_kpa"))

        # Should vary around 100 with some noise
        mean = sum(values) / len(values)
        assert 95 < mean < 105  # close to base
        assert len(set(round(v, 1) for v in values)) > 3  # some variation

    def test_source_boundary_unchanged(self):
        """Source boundaries ignore demand profile."""
        config = EquipmentConfig(
            id="GAS_SOURCE", model_type="boundary_v1",
            display_name="Test Source",
            parameters={
                "boundary_type": "source",
                "pressure_kpa": 101.325,
                "demand_profile": {"type": "random", "fluctuation_pct": 50},
            },
        )
        eq = BoundaryEquipment(config=config)
        state = RuntimeState()
        eq.initialize_state(state)
        bp = state.get_truth("GAS_SOURCE.pressure_kpa")
        eq.process_step(state, dt_s=1.0)
        assert state.get_truth("GAS_SOURCE.pressure_kpa") == bp  # unchanged

    def test_no_profile_no_change(self):
        """Sink without demand_profile stays constant."""
        config = EquipmentConfig(
            id="GAS_SINK", model_type="boundary_v1",
            display_name="Test Sink",
            parameters={"boundary_type": "sink", "pressure_kpa": 280.0},
        )
        eq = BoundaryEquipment(config=config)
        state = RuntimeState()
        eq.initialize_state(state)
        bp = state.get_truth("GAS_SINK.backpressure_kpa")
        for _ in range(10):
            eq.process_step(state, dt_s=1.0)
        assert state.get_truth("GAS_SINK.backpressure_kpa") == bp
