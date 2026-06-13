from pathlib import Path

import virtual_factory.main as main_module
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


def test_run_simulation_can_publish_to_fake_mqtt(monkeypatch) -> None:
    """The CLI helper should publish frames when MQTT options are provided."""
    gateways = []

    class FakeGateway:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs
            self.frames = []
            self.connected = False
            self.disconnected = False
            gateways.append(self)

        def connect(self) -> None:
            self.connected = True

        def publish_frame(self, frame) -> None:
            self.frames.append(frame)

        def disconnect(self) -> None:
            self.disconnected = True

    monkeypatch.setattr(main_module, "MqttGateway", FakeGateway)

    frames = run_simulation(
        config_path=Path("configs/plants/continuous_mvp_01.yaml"),
        steps=2,
        mqtt_host="localhost",
        quiet=True,
    )

    assert len(frames) == 2
    assert gateways[0].connected is True
    assert gateways[0].disconnected is True
    assert len(gateways[0].frames) == 2
    assert gateways[0].kwargs["host"] == "localhost"


def test_run_simulation_show_alarms_keeps_frames_publishable() -> None:
    """The show_alarms option should not add internal truth to frames."""
    frames = run_simulation(
        config_path=Path("configs/plants/continuous_mvp_01.yaml"),
        steps=2,
        show_alarms=True,
        quiet=True,
    )
    names = {signal.name for frame in frames for signal in frame}

    assert "T102_LOW_LEVEL_ALARM" in names
    assert "T102_LEVEL_TRUE" not in names
