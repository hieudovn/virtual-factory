from pathlib import Path

from virtual_factory.main import run_simulation


def test_run_simulation_runs_three_steps_without_error() -> None:
    """The CLI run helper should execute the MVP config and return telemetry frames."""
    frames = run_simulation(
        config_path=Path("configs/plants/continuous_mvp_01.yaml"),
        steps=3,
        dt_s=1.0,
        quiet=True,
    )

    assert len(frames) == 3
    assert all(frame for frame in frames)


def test_run_simulation_exports_no_internal_truth(tmp_path) -> None:
    """Normal CLI export should include publishable telemetry only."""
    csv_path = tmp_path / "telemetry.csv"
    jsonl_path = tmp_path / "telemetry.jsonl"

    frames = run_simulation(
        config_path=Path("configs/plants/continuous_mvp_01.yaml"),
        steps=3,
        dt_s=1.0,
        csv_output=csv_path,
        jsonl_output=jsonl_path,
        quiet=True,
    )
    exported_names = {signal.name for frame in frames for signal in frame}

    assert "T102_LEVEL_TRUE" not in exported_names
    assert "T102_LEVEL_TRUE" not in csv_path.read_text(encoding="utf-8")
    assert "T102_LEVEL_TRUE" not in jsonl_path.read_text(encoding="utf-8")
