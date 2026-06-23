"""Tests: Compressor Train Operating State Transitions."""
import pytest

from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.core.schema import EquipmentConfig
from virtual_factory.equipment.compressor_train import CompressorTrain
from virtual_factory.operating_states.state_machine import OperatingState


@pytest.fixture
def train_and_state():
    config = EquipmentConfig(
        id="COMP01", model_type="compressor_train_v1",
        display_name="Test Train",
        parameters={
            "rated_power_kw": 500.0, "rated_flow_m3_s": 2.0,
            "rated_pressure_ratio": 3.0, "polytropic_efficiency": 0.82,
            "source_equipment_id": "SRC", "sink_equipment_id": "SNK",
        },
    )
    train = CompressorTrain(config=config)
    state = RuntimeState()
    # Set up boundary source/sink
    state.set_truth("SRC.pressure_kpa", 101.325)
    state.set_truth("SRC.temperature_c", 25.0)
    state.set_truth("SRC.molecular_weight_kg_kmol", 28.97)
    state.set_truth("SRC.specific_heat_ratio", 1.4)
    state.set_truth("SRC.available_flow_m3_s", 5.0)
    state.set_truth("SNK.backpressure_kpa", 280.0)
    train.initialize_state(state)
    return train, state


class TestCompressorStates:
    def test_initial_state_is_stopped(self, train_and_state):
        train, state = train_and_state
        assert train.operating_state == OperatingState.STOPPED

    def test_stopped_to_startup(self, train_and_state):
        train, state = train_and_state
        state.set_truth("COMP01.running", True)
        train.process_step(state, dt_s=1.0)
        assert train.operating_state == OperatingState.STARTUP

    def test_startup_to_ramp_up(self, train_and_state):
        train, state = train_and_state
        state.set_truth("COMP01.running", True)
        # Run enough steps to establish flow and pass startup duration
        for _ in range(10):
            train.process_step(state, dt_s=1.0)
        assert train.operating_state in (OperatingState.RAMP_UP, OperatingState.STEADY_RUNNING)

    def test_ramp_up_to_steady(self, train_and_state):
        train, state = train_and_state
        state.set_truth("COMP01.running", True)
        for _ in range(50):
            train.process_step(state, dt_s=1.0)
        assert train.operating_state == OperatingState.STEADY_RUNNING

    def test_steady_to_shutdown(self, train_and_state):
        train, state = train_and_state
        state.set_truth("COMP01.running", True)
        for _ in range(50):
            train.process_step(state, dt_s=1.0)
        assert train.operating_state == OperatingState.STEADY_RUNNING

        state.set_truth("COMP01.running", False)
        train.process_step(state, dt_s=1.0)
        assert train.operating_state == OperatingState.SHUTDOWN

    def test_shutdown_to_stopped(self, train_and_state):
        train, state = train_and_state
        state.set_truth("COMP01.running", True)
        for _ in range(50):
            train.process_step(state, dt_s=1.0)
        state.set_truth("COMP01.running", False)
        train.process_step(state, dt_s=1.0)
        assert train.operating_state == OperatingState.SHUTDOWN

        # Wait for cooldown (10s)
        for _ in range(15):
            train.process_step(state, dt_s=1.0)
        assert train.operating_state == OperatingState.STOPPED

    def test_near_surge_triggered_by_low_flow(self, train_and_state):
        train, state = train_and_state
        state.set_truth("COMP01.running", True)
        for _ in range(50):
            train.process_step(state, dt_s=1.0)
        assert train.operating_state == OperatingState.STEADY_RUNNING

        # Set flow to 0.75 m3/s → frac=0.375 → surge ≈ 0.063 (< 0.10, > 0.02)
        state.set_truth("COMP01.flow_m3_s", 0.75)
        train.process_step(state, dt_s=1.0)
        assert train.operating_state == OperatingState.NEAR_SURGE

    def test_near_surge_recovery(self, train_and_state):
        train, state = train_and_state
        state.set_truth("COMP01.running", True)
        for _ in range(50):
            train.process_step(state, dt_s=1.0)
        # Trigger near surge with low flow
        state.set_truth("COMP01.flow_m3_s", 0.75)
        train.process_step(state, dt_s=1.0)
        assert train.operating_state == OperatingState.NEAR_SURGE

        # Recover by restoring normal flow → surge_margin recovers
        state.set_truth("COMP01.flow_m3_s", 1.5)
        train.process_step(state, dt_s=1.0)
        assert train.operating_state == OperatingState.STEADY_RUNNING

    def test_emergency_trip(self, train_and_state):
        train, state = train_and_state
        state.set_truth("COMP01.running", True)
        for _ in range(50):
            train.process_step(state, dt_s=1.0)
        assert train.operating_state == OperatingState.STEADY_RUNNING

        # Set very low flow → frac=0.15 → surge=0.0 < 0.02 → TRIP
        state.set_truth("COMP01.flow_m3_s", 0.3)
        train.process_step(state, dt_s=1.0)
        assert train.operating_state == OperatingState.TRIP

    def test_maintenance_and_recovery(self, train_and_state):
        train, state = train_and_state
        state.set_truth("COMP01.running", True)
        for _ in range(50):
            train.process_step(state, dt_s=1.0)
        state.set_truth("COMP01.running", False)
        for _ in range(15):
            train.process_step(state, dt_s=1.0)
        assert train.operating_state == OperatingState.STOPPED

        # Enter maintenance
        state.set_truth("COMP01.maintenance_active", True)
        train.process_step(state, dt_s=1.0)
        assert train.operating_state == OperatingState.MAINTENANCE

        # Exit maintenance → recovery
        state.set_truth("COMP01.maintenance_active", False)
        train.process_step(state, dt_s=1.0)
        assert train.operating_state == OperatingState.RECOVERY

    def test_valid_training_data_flag(self, train_and_state):
        train, state = train_and_state
        # Stopped = not valid
        assert not train.is_valid_training_data

        state.set_truth("COMP01.running", True)
        for _ in range(50):
            train.process_step(state, dt_s=1.0)
        # Steady running = valid
        assert train.is_valid_training_data

    def test_operating_state_in_truth(self, train_and_state):
        train, state = train_and_state
        state.set_truth("COMP01.running", True)
        for _ in range(50):
            train.process_step(state, dt_s=1.0)
        assert state.get_truth("COMP01.operating_state") == "steady_running"
        assert state.get_truth("COMP01.valid_training_data") is True
