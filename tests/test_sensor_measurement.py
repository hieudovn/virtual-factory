from pathlib import Path

from virtual_factory.core.config_loader import load_plant_config
from virtual_factory.core.simulation_engine import SimulationEngine
from virtual_factory.telemetry.signal_value import SignalValue


def test_level_transmitter_samples_truth_with_resolution_and_quality() -> None:
    """LT102 should produce a rounded GOOD SignalValue at the provided timestamp."""
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    engine = SimulationEngine(config)
    engine.initialize()
    engine.state.set_truth("T102.level_true", 1.234)

    sensor = engine.assembly.sensors["LT102"]
    sensor.sample(
        engine.state,
        timestamp_s=7.0,
        signal_config=config.signals[sensor.output_signal],
    )
    signal = engine.state.get_signal_value("LT102_LEVEL")

    assert isinstance(signal, SignalValue)
    assert signal.value == 1.23
    assert signal.quality == "GOOD"
    assert signal.timestamp_s == 7.0
    assert signal.unit == "m"
