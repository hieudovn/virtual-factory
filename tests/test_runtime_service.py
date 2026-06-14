import asyncio
from pathlib import Path

from virtual_factory.ui import runtime_service
from virtual_factory.ui.runtime_service import RuntimeService


def test_runtime_service_status_includes_running_and_mqtt_flags() -> None:
    service = RuntimeService(config_path=Path("configs/plants/continuous_mvp_01.yaml"))

    status = service.status()

    assert status["running"] is False
    assert status["mqtt_enabled"] is False
    assert status["mqtt_connected"] is False
    assert "truth" not in status


def test_runtime_service_mqtt_publishes_latest_publishable_frame(monkeypatch) -> None:
    gateways = []

    class FakeGateway:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs
            self.connected = False
            self.published_frames = []
            gateways.append(self)

        def connect(self, **kwargs) -> None:
            self.connect_kwargs = kwargs
            self.connected = True

        def disconnect(self) -> None:
            self.connected = False

        def publish_frame(self, frame) -> None:
            self.published_frames.append(list(frame))

    monkeypatch.setattr(runtime_service, "MqttGateway", FakeGateway)
    service = RuntimeService(
        config_path=Path("configs/plants/continuous_mvp_01.yaml"),
        mqtt_host="localhost",
        mqtt_connect_retries=3,
        mqtt_connect_delay=0.0,
    )

    records = service.step_once()

    assert records
    assert service.status()["mqtt_enabled"] is True
    assert service.status()["mqtt_connected"] is True
    assert gateways[0].connect_kwargs["retries"] == 3
    assert len(gateways[0].published_frames) == 1
    assert all(signal.category != "internal_truth" for signal in gateways[0].published_frames[0])


def test_runtime_service_start_and_stop_loop() -> None:
    async def run_loop() -> None:
        service = RuntimeService(config_path=Path("configs/plants/continuous_mvp_01.yaml"), dt_s=0.01)

        service.start_loop()
        await asyncio.sleep(0.03)
        assert service.is_running is True
        assert service.latest_telemetry()

        await service.stop_loop()
        assert service.is_running is False

    asyncio.run(run_loop())
