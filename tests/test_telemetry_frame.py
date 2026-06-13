from pathlib import Path

from virtual_factory.core.config_loader import load_plant_config
from virtual_factory.core.simulation_engine import SimulationEngine
from virtual_factory.telemetry.telemetry_frame import build_publishable_frame


def test_publishable_frame_contains_allowed_industrial_signals() -> None:
    """Telemetry frames should contain configured publishable signals only."""
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    engine = SimulationEngine(config)
    snapshot = engine.step()

    frame = build_publishable_frame(
        config,
        engine.state,
        engine.assembly.output_policy,
        timestamp_s=0.0,
    )
    names = {item.name for item in frame}

    assert {"LT102_LEVEL", "FT101_FLOW", "PT101_PRESSURE", "LIC102_OUT", "V101_OPENING_FEEDBACK"} <= names
    assert {
        "T102_LOW_LEVEL_ALARM",
        "T102_HIGH_LEVEL_ALARM",
        "P101_NO_FLOW_ALARM",
        "V101_POSITION_DEVIATION_ALARM",
        "LT102_BAD_QUALITY_ALARM",
    } <= names
    assert "T102_LEVEL_TRUE" not in names
    assert all(item.category != "internal_truth" for item in frame)
    assert {item.name for item in snapshot["telemetry_latest"]} == names
