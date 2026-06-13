from pathlib import Path

import pytest

from virtual_factory.core.config_loader import load_plant_config
from virtual_factory.core.simulation_engine import SimulationEngine


def test_minimal_closed_loop_signal_flow() -> None:
    """Truth should flow through sensor, controller, and actuator in one step."""
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    engine = SimulationEngine(config)
    engine.initialize()
    engine.state.set_truth("T102.level_true", 1.0)

    snapshot = engine.step()

    assert engine.state.get_signal_numeric("LT102_LEVEL") == pytest.approx(
        snapshot["truth"]["T102.level_true"],
        abs=0.01,
    )
    assert "LIC102_OUT" in snapshot["signals"]
    assert "V101_OPENING_FEEDBACK" in snapshot["signals"]
    assert snapshot["truth"]["V101.opening_actual"] == engine.state.get_signal_numeric("V101_OPENING_FEEDBACK")
    assert snapshot["truth"]["V101.opening_actual"] > 0.0


def test_closed_loop_updates_tank_level_over_repeated_steps() -> None:
    """Minimal process dynamics should make destination tank level move."""
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    engine = SimulationEngine(config, dt_s=1.0)
    engine.initialize()
    initial_level = float(engine.state.get_truth("T102.level_true"))

    for _ in range(5):
        snapshot = engine.step()

    assert snapshot["truth"]["T102.level_true"] != initial_level
