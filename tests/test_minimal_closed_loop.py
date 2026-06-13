from pathlib import Path

from virtual_factory.core.config_loader import load_plant_config
from virtual_factory.core.simulation_engine import SimulationEngine


def test_minimal_closed_loop_signal_flow() -> None:
    """Truth should flow through sensor, controller, and actuator in one step."""
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    engine = SimulationEngine(config)
    engine.initialize()
    engine.state.set_truth("T102.level_true", 1.0)

    snapshot = engine.step()

    assert snapshot["signals"]["LT102_LEVEL"] == 1.0
    assert "LIC102_OUT" in snapshot["signals"]
    assert "V101_OPENING_FEEDBACK" in snapshot["signals"]
    assert snapshot["truth"]["V101.opening_actual"] == snapshot["signals"]["V101_OPENING_FEEDBACK"]
    assert snapshot["truth"]["V101.opening_actual"] > 0.0
