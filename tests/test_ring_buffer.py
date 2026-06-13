from pathlib import Path

from virtual_factory.core.config_loader import load_plant_config
from virtual_factory.core.simulation_engine import SimulationEngine
from virtual_factory.telemetry.ring_buffer import RingBufferTelemetryStore
from virtual_factory.telemetry.signal_value import SignalValue


def test_ring_buffer_store_latest_frame() -> None:
    """The telemetry ring buffer should retain the latest frame."""
    store = RingBufferTelemetryStore(maxlen=2)
    frame = [
        SignalValue(
            name="LT102_LEVEL",
            value=1.0,
            unit="m",
            category="industrial_signal",
            timestamp_s=0.0,
        )
    ]

    store.append_frame(frame)

    assert store.latest() == frame
    assert store.all() == [frame]


def test_engine_step_appends_publishable_telemetry_without_internal_truth() -> None:
    """After a step, latest telemetry should exist and exclude internal truth."""
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    engine = SimulationEngine(config)
    engine.step()

    latest = engine.assembly.telemetry_store.latest()

    assert latest
    assert "T102_LEVEL_TRUE" not in {item.name for item in latest}
    assert all(item.category != "internal_truth" for item in latest)
