"""Tests for the Compressor Train equipment model."""

import pytest

from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.core.schema import EquipmentConfig
from virtual_factory.equipment.compressor_train import CompressorTrain


@pytest.fixture
def compressor_config() -> EquipmentConfig:
    return EquipmentConfig(
        id="COMP01",
        model_type="compressor_train_v1",
        display_name="Compressor Train A",
        parameters={
            "rated_power_kw": 500.0,
            "rated_flow_m3_s": 2.0,
            "rated_pressure_ratio": 3.0,
            "polytropic_efficiency": 0.82,
        },
    )


class TestCompressorTrain:
    def test_initialize_state(self, compressor_config):
        train = CompressorTrain(config=compressor_config)
        state = RuntimeState()
        train.initialize_state(state)

        # Check core values exist
        assert state.get_truth("COMP01.running") is False
        assert state.get_truth("COMP01.suction_pressure_kpa") == 101.325
        assert state.get_truth("COMP01.flow_m3_s") == 0.0

        # Check motor values
        assert state.get_truth("COMP01.motor.current_a") == 0.0
        assert state.get_truth("COMP01.motor.bearing_de_temp_c") == 25.0

        # Check lube oil
        assert state.get_truth("COMP01.lube_oil.pressure_kpa") == 0.0
        assert state.get_truth("COMP01.lube_oil.level_pct") == 100.0

        # Check cooling
        assert state.get_truth("COMP01.cooling.supply_temp_c") == 25.0

        # Check health
        assert state.get_truth("COMP01.health_index") == 1.0

    def test_process_step_running(self, compressor_config):
        train = CompressorTrain(config=compressor_config)
        state = RuntimeState()
        train.initialize_state(state)

        # Start the compressor
        state.set_truth("COMP01.running", True)
        state.set_truth("COMP01.flow_m3_s", 1.5)  # 75% of rated 2.0
        state.set_truth("COMP01.suction_pressure_kpa", 101.325)
        state.set_truth("COMP01.suction_temperature_c", 25.0)

        train.process_step(state, dt_s=1.0)

        # Should compute discharge pressure > suction
        discharge_p = state.get_truth("COMP01.discharge_pressure_kpa")
        assert discharge_p > 101.325

        # Should have positive power
        power = state.get_truth("COMP01.power_consumed_kw")
        assert power > 0

        # Motor should have current
        current = state.get_truth("COMP01.motor.current_a")
        assert current > 0

        # Speed should be nominal
        speed = state.get_truth("COMP01.speed_rpm")
        assert speed > 0

        # Surge margin should be > 0
        surge = state.get_truth("COMP01.surge_margin")
        assert surge > 0

    def test_process_step_stopped(self, compressor_config):
        train = CompressorTrain(config=compressor_config)
        state = RuntimeState()
        train.initialize_state(state)

        # First run to set some values
        state.set_truth("COMP01.running", True)
        state.set_truth("COMP01.flow_m3_s", 1.5)
        train.process_step(state, dt_s=1.0)

        # Now stop
        state.set_truth("COMP01.running", False)
        train.process_step(state, dt_s=1.0)

        # Dynamic values should be zeroed
        assert state.get_truth("COMP01.speed_rpm") == 0.0
        assert state.get_truth("COMP01.motor.current_a") == 0.0
        assert state.get_truth("COMP01.motor.power_kw") == 0.0
        assert state.get_truth("COMP01.vibration_de_mm_s") == 0.0

    def test_operating_hours_accumulation(self, compressor_config):
        train = CompressorTrain(config=compressor_config)
        state = RuntimeState()
        train.initialize_state(state)
        state.set_truth("COMP01.running", True)
        state.set_truth("COMP01.flow_m3_s", 1.5)

        # Run for 3600 seconds
        for _ in range(3600):
            train.process_step(state, dt_s=1.0)

        hours = state.get_truth("COMP01.operating_hours")
        assert hours == pytest.approx(1.0, rel=0.1)  # Float accumulation tolerance

    def test_get_tag_names(self, compressor_config):
        train = CompressorTrain(config=compressor_config)
        tags = train.get_tag_names()
        # Phase 1: 50+ tags
        assert len(tags) >= 50
        assert "COMP01.running" in tags
        assert "COMP01.suction_pressure_kpa" in tags
        assert "COMP01.motor.current_a" in tags
        assert "COMP01.lube_oil.pressure_kpa" in tags
        assert "COMP01.cooling.supply_temp_c" in tags
        assert "COMP01.seal_gas.flow_nm3_h" in tags
        assert "COMP01.health_index" in tags

    def test_surge_margin_computation(self, compressor_config):
        train = CompressorTrain(config=compressor_config)
        state = RuntimeState()
        train.initialize_state(state)
        state.set_truth("COMP01.running", True)
        state.set_truth("COMP01.flow_m3_s", 0.2)  # Low flow
        state.set_truth("COMP01.suction_pressure_kpa", 101.325)
        state.set_truth("COMP01.suction_temperature_c", 25.0)

        train.process_step(state, dt_s=1.0)

        surge = state.get_truth("COMP01.surge_margin")
        # At low flow, surge margin should be reduced
        assert surge < 0.5

    def test_full_flow(self, compressor_config):
        train = CompressorTrain(config=compressor_config)
        state = RuntimeState()
        train.initialize_state(state)
        state.set_truth("COMP01.running", True)
        state.set_truth("COMP01.flow_m3_s", 2.0)  # Rated flow
        state.set_truth("COMP01.suction_pressure_kpa", 101.325)
        state.set_truth("COMP01.suction_temperature_c", 25.0)

        train.process_step(state, dt_s=1.0)

        # At rated flow, pressure ratio should be near 1.0
        pr = state.get_truth("COMP01.pressure_ratio")
        assert pr < 1.1

        # Power should be near rated
        power = state.get_truth("COMP01.power_consumed_kw")
        assert power > 400  # Near 500 kW rated
