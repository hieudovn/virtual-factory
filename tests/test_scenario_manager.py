from pathlib import Path

import pytest

from virtual_factory.core.config_loader import load_plant_config
from virtual_factory.core.simulation_engine import SimulationEngine
from virtual_factory.core.schema import ScenarioActionConfig, ScenarioConfig
from virtual_factory.scenarios.scenario_manager import ScenarioManager


def test_set_truth_action_fires_once() -> None:
    """set_truth should update runtime truth once when due."""
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    engine = SimulationEngine(config)
    engine.initialize()
    manager = ScenarioManager(
        ScenarioConfig(
            id="pump_stop_test",
            actions=[ScenarioActionConfig(at_s=1.0, type="set_truth", target="P101.running", value=False)],
        )
    )

    assert manager.apply_due_actions(engine.state, config, 0.0) == []
    fired = manager.apply_due_actions(engine.state, config, 1.0)
    fired_again = manager.apply_due_actions(engine.state, config, 2.0)

    assert len(fired) == 1
    assert fired_again == []
    assert engine.state.get_truth("P101.running") is False


def test_set_parameter_action_modifies_tank_outlet_demand() -> None:
    """set_parameter should modify equipment parameters in the runtime config."""
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    manager = ScenarioManager(
        ScenarioConfig(
            id="demand_test",
            actions=[
                ScenarioActionConfig(
                    at_s=0.0,
                    type="set_parameter",
                    target="equipment.T102.outlet_demand_m3_s",
                    value=0.01,
                )
            ],
        )
    )

    manager.apply_due_actions(SimulationEngine(config).state, config, 0.0)
    t102 = next(item for item in config.equipment if item.id == "T102")

    assert t102.parameters["outlet_demand_m3_s"] == 0.01


def test_valve_stuck_keeps_feedback_at_stuck_value() -> None:
    """valve_stuck should prevent the actuator from following controller command."""
    scenario = ScenarioConfig(
        id="valve_stuck_test",
        actions=[ScenarioActionConfig(at_s=0.0, type="valve_stuck", target="V101", value=25.0)],
    )
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    engine = SimulationEngine(config, scenario=scenario)
    engine.initialize()

    snapshot = engine.step()

    assert snapshot["truth"]["V101.opening_actual"] == pytest.approx(25.0)
    assert engine.state.get_signal_numeric("V101_OPENING_FEEDBACK") == pytest.approx(25.0)


def test_sensor_bias_changes_measured_signal() -> None:
    """set_sensor_bias should alter measured sensor output through BaseSensor."""
    scenario = ScenarioConfig(
        id="sensor_bias_test",
        actions=[ScenarioActionConfig(at_s=0.0, type="set_sensor_bias", target="LT102", value=0.5)],
    )
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    engine = SimulationEngine(config, scenario=scenario)
    engine.initialize()
    engine.state.set_truth("T102.level_true", 1.0)

    snapshot = engine.step()

    assert engine.state.get_signal_numeric("LT102_LEVEL") == pytest.approx(
        snapshot["truth"]["T102.level_true"] + 0.5,
        abs=0.01,
    )
