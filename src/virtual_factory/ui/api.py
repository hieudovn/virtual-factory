"""FastAPI monitoring API for Virtual Factory telemetry."""

import asyncio
import os
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
    opcua_endpoint: str | None = None,
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
        opcua_endpoint=opcua_endpoint,
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

    # Direct-serve app.js to bypass any StaticFiles caching
    @app.get("/static/app.js", include_in_schema=False)
    def app_js_direct() -> FileResponse:
        return FileResponse(static_dir / "app.js", media_type="application/javascript")

    @app.get("/static/editor.js", include_in_schema=False)
    def editor_js_direct() -> FileResponse:
        return FileResponse(static_dir / "editor.js", media_type="application/javascript")

    @app.get("/static/icons.js", include_in_schema=False)
    def icons_js_direct() -> FileResponse:
        return FileResponse(static_dir / "icons.js", media_type="application/javascript")

    @app.get("/static/widgets.js", include_in_schema=False)
    def widgets_js_direct() -> FileResponse:
        return FileResponse(static_dir / "widgets.js", media_type="application/javascript")

    @app.get("/static/settings.js", include_in_schema=False)
    def settings_js_direct() -> FileResponse:
        return FileResponse(static_dir / "settings.js", media_type="application/javascript")

    @app.get("/static/builder.js", include_in_schema=False)
    def builder_js_direct() -> FileResponse:
        return FileResponse(static_dir / "builder.js", media_type="application/javascript")

    @app.get("/static/assy_demo.js", include_in_schema=False)
    def assy_js_direct() -> FileResponse:
        return FileResponse(static_dir / "assy_demo.js", media_type="application/javascript")

    @app.get("/static/assy_demo.css", include_in_schema=False)
    def assy_css_direct() -> FileResponse:
        return FileResponse(static_dir / "assy_demo.css", media_type="text/css")

    @app.get("/")
    def dashboard() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "static_dir": str(static_dir.resolve())}

    @app.get("/status")
    def status() -> dict:
        return service.status()

    @app.get("/telemetry/latest")
    def telemetry_latest() -> list[dict]:
        telemetry = service.latest_telemetry()
        if telemetry:
            return telemetry
        # Step once to get initial state
        return service.step_once()

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

    @app.post("/reset")
    async def reset() -> dict:
        """Reinitialize the simulation to initial state at t=0."""
        await service.stop_loop()
        service.reset()
        # Ensure time is at 0
        service.engine.time_manager.current_time_s = 0.0
        return service.status()

    @app.websocket("/ws/telemetry")
    async def websocket_telemetry(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            while True:
                if service.is_running:
                    telemetry = service.step_once()
                else:
                    # Don't auto-step when stopped — serve latest snapshot
                    telemetry = service.latest_telemetry() or []
                await websocket.send_json(telemetry)
                await asyncio.sleep(1.0)
        except WebSocketDisconnect:
            return

    @app.get("/api/plant-graph")
    def plant_graph() -> dict:
        return service.plant_graph()

    @app.get("/api/model-types")
    def model_types() -> list[dict]:
        return service.model_types()

    @app.patch("/api/pid/{controller_id}")
    def update_pid(controller_id: str, body: dict) -> dict:
        """Update PID controller parameters (kp, ki, kd, setpoint)."""
        result = service.update_pid(controller_id, body)
        return result

    @app.post("/api/fault")
    def inject_fault(body: dict) -> dict:
        """Inject a fault into the running simulation."""
        result = service.inject_fault(body.get("type"), body.get("value"))
        return result

    @app.get("/api/opcua/status")
    def opcua_status() -> dict:
        """Return OPC UA gateway status."""
        return service.opcua_status()

    @app.post("/api/ai/generate")
    def ai_generate(body: dict) -> dict:
        """Generate plant config YAML from natural language description."""
        from virtual_factory.ai.generator import generate_config
        description = body.get("description", "")
        if not description:
            return {"error": "No description provided"}
        try:
            yaml_str = generate_config(description, backend="template")
            return {"yaml": yaml_str}
        except Exception as e:
            return {"error": str(e)}

    @app.post("/api/ai/parse")
    def ai_parse(body: dict) -> dict:
        """Parse P&ID shorthand text into plant config YAML."""
        from virtual_factory.ai.pid_parser import parse_pid_shorthand
        import yaml
        text = body.get("text", "")
        if not text:
            return {"error": "No text provided"}
        try:
            config = parse_pid_shorthand(text)
            yaml_str = yaml.dump(config.model_dump(mode="json"), default_flow_style=False, allow_unicode=True)
            return {"yaml": yaml_str}
        except Exception as e:
            return {"error": str(e)}

    @app.get("/api/config/current")
    def config_current() -> dict:
        """Return the currently loaded plant config and available configs."""
        return service.current_config_info()

    @app.post("/api/config/switch")
    async def config_switch(body: dict) -> dict:
        """Switch to a different plant configuration at runtime and persist it."""
        config_path = body.get("config_path", "")
        if not config_path:
            return {"status": "error", "message": "No config_path provided"}
        from pathlib import Path
        if not Path(config_path).exists():
            return {"status": "error", "message": f"Config file not found: {config_path}"}
        from virtual_factory.core.state_persistence import set_last_config
        set_last_config(config_path)
        result = await service.reload_config(config_path)
        return {"status": "ok", "config": config_path, **result}

    # ═══════════════════════════════════════════════════
    # M6-S04 — TIPA ASSY Demo Endpoints
    # ═══════════════════════════════════════════════════

    _assy_controller: dict = {"instance": None}

    def _get_assy_controller():
        if _assy_controller["instance"] is None:
            from virtual_factory.assembly.demo_controller import DemoController
            assy_config = os.environ.get(
                "TIPA_ASSY_CONFIG",
                str(Path(__file__).resolve().parent.parent.parent.parent / "configs" / "plants" / "tipa_assy_demo.yaml")
            )
            ctrl = DemoController(config_path=assy_config)
            ctrl.initialize()
            _assy_controller["instance"] = ctrl
        return _assy_controller["instance"]

    @app.get("/assy-demo")
    def assy_demo_page() -> FileResponse:
        return FileResponse(static_dir / "assy_demo.html")

    @app.get("/assy-demo/static/{filename}")
    def assy_demo_static(filename: str) -> FileResponse:
        return FileResponse(static_dir / filename)

    @app.post("/assy-demo/reset")
    def assy_demo_reset(body: dict | None = None) -> dict:
        ctrl = _get_assy_controller()
        scenario = (body or {}).get("scenario", "HAPPY_PATH")
        from virtual_factory.assembly.demo_controller import DemoScenario
        ctrl.set_scenario(DemoScenario(scenario))
        snap = ctrl.reset()
        return snap.to_dict()

    @app.post("/assy-demo/step")
    def assy_demo_step() -> dict:
        ctrl = _get_assy_controller()
        snap = ctrl.step()
        return snap.to_dict()

    @app.post("/assy-demo/snapshot")
    def assy_demo_snapshot() -> dict:
        ctrl = _get_assy_controller()
        return ctrl.snapshot().to_dict()

    # ═══════════════════════════════════════════════════
    # M6-S04B-I03 — Additive S04B Overview / Detail Endpoints
    # ═══════════════════════════════════════════════════

    _enable_s04b = os.environ.get("VF_ENABLE_S04B_OVERVIEW", "0") == "1"

    if _enable_s04b:
        @app.get("/assy-demo/overview")
        def assy_demo_overview() -> dict:
            ctrl = _get_assy_controller()
            return ctrl.overview().to_dict()

        @app.get("/assy-demo/sub-lines")
        def assy_demo_sub_lines() -> list[dict]:
            ctrl = _get_assy_controller()
            ov = ctrl.overview()
            return [s.to_dict() for s in ov.sub_lines]

        @app.get("/assy-demo/sub-line/{sub_line_id}")
        def assy_demo_sub_line_detail(sub_line_id: str) -> dict:
            from virtual_factory.assembly.demo_controller import DemoController
            ctrl = _get_assy_controller()
            try:
                snap = ctrl.detail_for(sub_line_id)
                return snap.to_dict()
            except ValueError:
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=404,
                    content={"detail": f"Sub-line not found: {sub_line_id!r}"},
                )

    return app
