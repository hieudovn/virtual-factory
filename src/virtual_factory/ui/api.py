"""FastAPI monitoring API for Virtual Factory telemetry."""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from virtual_factory.ui.runtime_service import RuntimeService


def create_app(
    config_path: str | Path = "configs/plants/continuous_mvp_01.yaml",
    scenario_path: str | Path | None = None,
    dt_s: float = 1.0,
    mqtt_host: str | None = None,
    mqtt_port: int = 1883,
    mqtt_topic_prefix: str = "virtual-factory/demo/continuous_mvp_01",
    mqtt_client_id: str | None = None,
    mqtt_connect_retries: int = 20,
    mqtt_connect_delay: float = 1.0,
    auto_start: bool = False,
):
    """Create a FastAPI app backed by one RuntimeService instance."""
    from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    service = RuntimeService(
        config_path=config_path,
        scenario_path=scenario_path,
        dt_s=dt_s,
        mqtt_host=mqtt_host,
        mqtt_port=mqtt_port,
        mqtt_topic_prefix=mqtt_topic_prefix,
        mqtt_client_id=mqtt_client_id,
        mqtt_connect_retries=mqtt_connect_retries,
        mqtt_connect_delay=mqtt_connect_delay,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if auto_start:
            service.start_loop()
        try:
            yield
        finally:
            await service.stop_loop()
            service.disconnect_mqtt()

    app = FastAPI(title="Virtual Factory Monitoring API", version="0.1.0", lifespan=lifespan)
    static_dir = Path(__file__).resolve().parent / "static"

    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    def dashboard() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/status")
    def status() -> dict:
        return service.status()

    @app.get("/telemetry/latest")
    def telemetry_latest() -> list[dict]:
        telemetry = service.latest_telemetry()
        return telemetry or service.step_once()

    @app.get("/telemetry/history")
    def telemetry_history(limit: int = Query(default=100, ge=0, le=3600)) -> list[dict]:
        return service.telemetry_history(limit=limit)

    @app.get("/alarms")
    def alarms() -> list[dict]:
        if not service.latest_telemetry():
            service.step_once()
        return service.latest_alarms()

    @app.post("/step")
    def step() -> list[dict]:
        return service.step_once()

    @app.post("/run-steps")
    def run_steps(n: int = Query(default=10, ge=0, le=10000)) -> list[dict]:
        return service.run_steps(n)

    @app.post("/start")
    async def start() -> dict:
        service.start_loop()
        return service.status()

    @app.post("/stop")
    async def stop() -> dict:
        await service.stop_loop()
        return service.status()

    @app.websocket("/ws/telemetry")
    async def websocket_telemetry(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            while True:
                if service.is_running:
                    telemetry = service.latest_telemetry() or service.step_once()
                else:
                    telemetry = service.step_once()
                await websocket.send_json(telemetry)
                await asyncio.sleep(1.0)
        except WebSocketDisconnect:
            return

    return app
