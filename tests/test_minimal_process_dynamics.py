from pathlib import Path

import pytest

from virtual_factory.core.config_loader import load_plant_config
from virtual_factory.core.simulation_engine import SimulationEngine
from virtual_factory.equipment.process_dynamics import update_continuous_process


def test_minimal_process_dynamics_updates_flow_pressure_and_level() -> None:
    """The MVP process should react physically to valve opening over time."""
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    engine = SimulationEngine(config, dt_s=1.0)
    engine.initialize()
    initial_level = float(engine.state.get_truth("T102.level_true"))

    for _ in range(5):
        snapshot = engine.step()

    assert "V101.outlet.flow_true" in snapshot["truth"]
    assert "P101.discharge_pressure_true" in snapshot["truth"]
    assert snapshot["truth"]["T102.level_true"] != initial_level


def test_valve_opening_controls_flow() -> None:
    """A fully closed valve should produce lower flow than a fully open valve."""
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    engine = SimulationEngine(config, dt_s=1.0)
    engine.initialize()

    engine.state.set_truth("V101.opening_actual", 0.0)
    update_continuous_process(config, engine.state, dt_s=1.0)
    closed_flow = float(engine.state.get_truth("V101.outlet.flow_true"))

    engine.state.set_truth("V101.opening_actual", 100.0)
    update_continuous_process(config, engine.state, dt_s=1.0)
    open_flow = float(engine.state.get_truth("V101.outlet.flow_true"))

    assert closed_flow == pytest.approx(0.0)
    assert open_flow > closed_flow


def test_flow_and_pressure_transmitters_measure_updated_truth() -> None:
    """FT101 and PT101 should sample the post-dynamics physical truth values."""
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    engine = SimulationEngine(config, dt_s=1.0)
    snapshot = engine.step()

    assert engine.state.get_signal_numeric("FT101_FLOW") == pytest.approx(
        snapshot["truth"]["V101.outlet.flow_true"],
        abs=0.0001,
    )
    assert engine.state.get_signal_numeric("PT101_PRESSURE") == pytest.approx(
        snapshot["truth"]["P101.discharge_pressure_true"],
        abs=0.01,
    )
