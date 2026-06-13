from pathlib import Path

from virtual_factory.main import run_simulation


def test_run_simulation_with_scenario_keeps_frames_publishable() -> None:
    """Scenario execution should not add internal truth to telemetry frames."""
    frames = run_simulation(
        config_path=Path("configs/plants/continuous_mvp_01.yaml"),
        scenario_path=Path("configs/scenarios/demand_change.yaml"),
        steps=3,
        quiet=True,
    )

    assert frames
    assert all(signal.category != "internal_truth" for frame in frames for signal in frame)
    assert "T102_LEVEL_TRUE" not in {signal.name for frame in frames for signal in frame}
