"""Tests for sensor delay buffer, drift, and stuck-fault."""

from pathlib import Path

from virtual_factory.core.config_loader import load_plant_config
from virtual_factory.core.simulation_engine import SimulationEngine


def test_sensor_delay_buffers_signal() -> None:
    """With delay_s = 2, output is delayed by 2 steps:
    - Step 1: truth=1.0, buffer=[1.0], output oldest=1.0
    - Step 2: truth=2.0, buffer=[1.0, 2.0], output oldest=1.0
    - Step 3: truth=3.0, buffer=[2.0, 3.0], output oldest=2.0
    - Step 4: truth=4.0, buffer=[3.0, 4.0], output oldest=3.0
    """
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    engine = SimulationEngine(config, dt_s=1.0)
    engine.initialize()

    lt102 = engine.assembly.sensors["LT102"]
    # Override delay for this test
    lt102.parameters["delay_s"] = 2.0
    lt102._delay_buffer = __import__("collections").deque(maxlen=2)

    # Step 1: truth = 1.0, buffer=[1.0] → oldest = 1.0
    engine.state.set_truth("T102.level_true", 1.0)
    lt102.sample(engine.state, timestamp_s=0.0, signal_config=config.signals["LT102_LEVEL"])
    assert engine.state.get_signal_numeric("LT102_LEVEL") == 1.0

    # Step 2: truth = 2.0, buffer=[1.0, 2.0] → oldest = 1.0
    engine.state.set_truth("T102.level_true", 2.0)
    lt102.sample(engine.state, timestamp_s=1.0, signal_config=config.signals["LT102_LEVEL"])
    assert engine.state.get_signal_numeric("LT102_LEVEL") == 1.0

    # Step 3: truth = 3.0, buffer=[2.0, 3.0] → oldest = 2.0
    engine.state.set_truth("T102.level_true", 3.0)
    lt102.sample(engine.state, timestamp_s=2.0, signal_config=config.signals["LT102_LEVEL"])
    assert engine.state.get_signal_numeric("LT102_LEVEL") == 2.0

    # Step 4: truth = 4.0, buffer=[3.0, 4.0] → oldest = 3.0
    engine.state.set_truth("T102.level_true", 4.0)
    lt102.sample(engine.state, timestamp_s=3.0, signal_config=config.signals["LT102_LEVEL"])
    assert engine.state.get_signal_numeric("LT102_LEVEL") == 3.0


def test_sensor_stuck_returns_last_good_value() -> None:
    """When sensor quality is STUCK, the output should freeze at the last good value."""
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    engine = SimulationEngine(config, dt_s=1.0)
    engine.initialize()

    lt102 = engine.assembly.sensors["LT102"]

    # Normal sample
    engine.state.set_truth("T102.level_true", 2.5)
    lt102.sample(engine.state, timestamp_s=0.0, signal_config=config.signals["LT102_LEVEL"])
    assert engine.state.get_signal_numeric("LT102_LEVEL") == 2.5

    # Set stuck
    engine.state.diagnostics["sensor_quality.LT102"] = "STUCK"
    engine.state.set_truth("T102.level_true", 5.0)
    lt102.sample(engine.state, timestamp_s=1.0, signal_config=config.signals["LT102_LEVEL"])
    assert engine.state.get_signal_numeric("LT102_LEVEL") == 2.5  # frozen


def test_sensor_drift_accumulates_over_time() -> None:
    """Drift should increase the sensor output each sample."""
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    engine = SimulationEngine(config, dt_s=1.0)
    engine.initialize()

    lt102 = engine.assembly.sensors["LT102"]
    lt102.parameters["drift_scale"] = 0.1
    lt102._drift_acc = 0.0

    # Drift accumulates: 0.1 per step
    engine.state.set_truth("T102.level_true", 1.0)
    lt102.sample(engine.state, timestamp_s=0.0, signal_config=config.signals["LT102_LEVEL"])
    v1 = engine.state.get_signal_numeric("LT102_LEVEL")
    assert v1 == 1.1  # truth(1.0) + drift(0.1)

    lt102.sample(engine.state, timestamp_s=1.0, signal_config=config.signals["LT102_LEVEL"])
    v2 = engine.state.get_signal_numeric("LT102_LEVEL")
    assert v2 == 1.2  # truth(1.0) + drift(0.1+0.1)


def test_delay_reset_on_new_sensor_instance() -> None:
    """Each sensor instance should have its own independent delay buffer."""
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    engine = SimulationEngine(config, dt_s=1.0)
    engine.initialize()

    ft101 = engine.assembly.sensors["FT101"]
    ft101.parameters["delay_s"] = 1.0
    ft101._delay_buffer = __import__("collections").deque(maxlen=1)

    engine.state.set_truth("V101.outlet.flow_true", 0.012)
    ft101.sample(engine.state, timestamp_s=0.0, signal_config=config.signals["FT101_FLOW"])

    assert engine.state.get_signal_numeric("FT101_FLOW") == 0.012
