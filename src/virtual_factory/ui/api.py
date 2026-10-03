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
    # VF-DM-DEMO-ASSY-MES-01 — TIPA ASSY Customer Demo Scenario v1
    # Minimal control surface: reset / start / pause / step / jam / recover.
    # ═══════════════════════════════════════════════════

    _demo_controller: dict = {"instance": None}

    def _get_demo_controller():
        if _demo_controller["instance"] is None:
            from virtual_factory.assembly.demo_assy_mes.controller import DemoController
            from virtual_factory.assembly.demo_assy_mes.runner import DemoRunner
            _demo_controller["instance"] = DemoController(DemoRunner())
        return _demo_controller["instance"]

    @app.get("/demo-assy-mes", include_in_schema=False)
    def demo_asssy_page() -> FileResponse:
        """Customer-facing TIPA ASSY demo page (VF-DM-DEMO-ASSY-MES-01-C02)."""
        return FileResponse(static_dir / "demo_assy_mes.html")

    @app.post("/demo-assy-mes/reset")
    def demo_reset() -> dict:
        return _get_demo_controller().reset()

    @app.post("/demo-assy-mes/start")
    def demo_start() -> dict:
        return _get_demo_controller().start()

    @app.post("/demo-assy-mes/pause")
    def demo_pause() -> dict:
        return _get_demo_controller().pause()

    @app.post("/demo-assy-mes/step")
    def demo_step() -> dict:
        return _get_demo_controller().step()

    @app.post("/demo-assy-mes/jam")
    def demo_jam() -> dict:
        return _get_demo_controller().trigger_jam()

    @app.post("/demo-assy-mes/recover")
    def demo_recover() -> dict:
        return _get_demo_controller().recover()

    @app.get("/demo-assy-mes/snapshot")
    def demo_snapshot() -> dict:
        return _get_demo_controller().snapshot()

    @app.get("/demo-assy-mes/messages")
    def demo_messages() -> list[dict]:
        return _get_demo_controller().messages()
    # M6-S04 — TIPA ASSY Demo Endpoints
    # ═══════════════════════════════════════════════════

    _assy_controller: dict = {"instance": None}

    def _get_assy_controller():
        if _assy_controller["instance"] is None:
            from virtual_factory.assembly.demo_controller import DemoController
            from virtual_factory.assembly.observation_bridge import (
                build_assy_observation_pipeline,
            )
            from virtual_factory.assembly.assy_mes_bridge import (
                build_assy_mes_pipeline,
            )
            assy_config = os.environ.get(
                "TIPA_ASSY_CONFIG",
                str(Path(__file__).resolve().parent.parent.parent.parent / "configs" / "plants" / "tipa_assy_demo.yaml")
            )
            ctrl = DemoController(config_path=assy_config)
            ctrl.initialize()
            # M6-INT-01: attach the downstream observation pipeline (read-only).
            pipeline = build_assy_observation_pipeline()
            ctrl.attach_observation_bridge(pipeline.bridge)
            # VF-DM-DEMO-ASSY-MES-02: attach the six-sub-line MES contract bridge.
            mes_pipeline = build_assy_mes_pipeline()
            ctrl.attach_mes_bridge(mes_pipeline.bridge)
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

    @app.get("/assy-demo/observations")
    def assy_demo_observations() -> dict:
        """M6-INT-01: ordered P0 outbound observation trace (read-only)."""
        ctrl = _get_assy_controller()
        trace = ctrl.outbound_trace
        return {"count": len(trace), "observations": trace}

    @app.post("/assy-demo/snapshot")
    def assy_demo_snapshot() -> dict:
        ctrl = _get_assy_controller()
        return ctrl.snapshot().to_dict()

    # ═══════════════════════════════════════════════════
    # VF-DM-DEMO-ASSY-MES-02 — MES contract bridge endpoints
    # ═══════════════════════════════════════════════════

    @app.post("/assy-demo/jam")
    def assy_demo_jam(body: dict | None = None) -> dict:
        """Deterministic AP05_JAM on the exception target sub-line."""
        ctrl = _get_assy_controller()
        sub_line_id = (body or {}).get("sub_line_id") or None
        return ctrl.trigger_jam(sub_line_id).to_dict()

    @app.post("/assy-demo/recover")
    def assy_demo_recover(body: dict | None = None) -> dict:
        """Resolve the AP05_JAM after the deterministic 120 s downtime."""
        ctrl = _get_assy_controller()
        sub_line_id = (body or {}).get("sub_line_id") or None
        return ctrl.recover(sub_line_id).to_dict()

    @app.post("/assy-demo/run-to-terminal")
    def assy_demo_run_to_terminal() -> dict:
        """Run the demo until the exception target sub-line is terminal, then
        emit per-sub-line OEE summaries."""
        ctrl = _get_assy_controller()
        return ctrl.run_to_terminal().to_dict()

    @app.get("/assy-demo/mes-messages")
    def assy_demo_mes_messages() -> dict:
        """VF-DM-DEMO-ASSY-MES-02: delivered MES-compatible messages."""
        ctrl = _get_assy_controller()
        msgs = ctrl.mes_messages
        return {"count": len(msgs), "messages": msgs}

    @app.get("/assy-demo/mes-trace")
    def assy_demo_mes_trace() -> dict:
        """VF-DM-DEMO-ASSY-MES-02: ordered MES bridge delivery trace."""
        ctrl = _get_assy_controller()
        trace = ctrl.mes_outbound_trace
        return {"count": len(trace), "observations": trace}

    @app.get("/assy-demo/version")
    def assy_demo_version() -> dict:
        """VF-DM-DEMO-ASSY-MES-02/03: exact source SHA recorded/exposed and the
        active additive MES contract version."""
        import subprocess
        from virtual_factory.assembly.assy_mes_bridge import CONTRACT_VERSION
        sha = os.environ.get("VF_SOURCE_SHA", "")
        if not sha:
            try:
                repo = Path(__file__).resolve().parent.parent.parent.parent
                sha = subprocess.run(
                    ["git", "-C", str(repo), "rev-parse", "HEAD"],
                    capture_output=True, text=True, timeout=5,
                ).stdout.strip()
            except Exception:
                sha = ""
        return {
            "source_sha": sha,
            "contract_version": CONTRACT_VERSION,
            "runtime": "assy-demo",
        }

    # ═══════════════════════════════════════════════════
    # OPS-03 — Station Interaction / Inspector Binding
    # ═══════════════════════════════════════════════════

    @app.post("/assy-demo/operation-command")
    def assy_demo_operation_command(body: dict) -> dict:
        """Submit an operation command. Runtime decides; snapshot is truth."""
        from fastapi.responses import JSONResponse
        from virtual_factory.assembly.line_runtime import AssyLineError
        ctrl = _get_assy_controller()
        station_id = body.get("station_id", "")
        wip_id = body.get("wip_id", "")
        command = body.get("command", "")
        payload = body.get("payload")
        if not station_id or not wip_id or not command:
            return JSONResponse(
                status_code=400,
                content={"detail": "station_id, wip_id and command are required"},
            )
        try:
            snap = ctrl.submit_operation_command(station_id, wip_id, command, payload)
        except AssyLineError as exc:
            return JSONResponse(
                status_code=409,
                content={"detail": str(exc), "status": "error"},
            )
        return snap.to_dict()

    @app.post("/assy-demo/station-action")
    def assy_demo_station_action(body: dict) -> dict:
        """Submit an exception station action (HOLD). Runtime decides."""
        from fastapi.responses import JSONResponse
        from virtual_factory.assembly.line_runtime import AssyLineError
        ctrl = _get_assy_controller()
        station_id = body.get("station_id", "")
        wip_id = body.get("wip_id", "")
        action = body.get("action", "")
        if not station_id or not wip_id or not action:
            return JSONResponse(
                status_code=400,
                content={"detail": "station_id, wip_id and action are required"},
            )
        try:
            snap = ctrl.submit_station_action(station_id, wip_id, action)
        except AssyLineError as exc:
            return JSONResponse(
                status_code=409,
                content={"detail": str(exc), "status": "error"},
            )
        return snap.to_dict()

    @app.post("/assy-demo/run-mode")
    def assy_demo_run_mode(body: dict) -> dict:
        """Set global run mode (MANUAL/AUTO/ASSISTED) for the demo contexts."""
        from fastapi.responses import JSONResponse
        from virtual_factory.assembly.station_contracts import CompletionMode
        ctrl = _get_assy_controller()
        mode = body.get("mode", "")
        try:
            parsed = CompletionMode(mode)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"detail": f"Invalid run mode: {mode!r}"},
            )
        return ctrl.set_run_mode(parsed).to_dict()

    @app.post("/assy-demo/select")
    def assy_demo_select(body: dict) -> dict:
        """Select the active sub-line context for step/command endpoints.

        Additive M6-S04B binding: the detail view can render any sub-line, but
        step/command endpoints operate on the selected context. This exposes the
        existing DemoController.select_sub_line surface so operators can target
        a specific sub-line in MANUAL E2E.
        """
        from fastapi.responses import JSONResponse
        ctrl = _get_assy_controller()
        sub_line_id = body.get("sub_line_id", "")
        if not sub_line_id:
            return JSONResponse(
                status_code=400,
                content={"detail": "sub_line_id is required"},
            )
        try:
            ctrl.select_sub_line(sub_line_id)
        except ValueError as exc:
            return JSONResponse(
                status_code=404,
                content={"detail": str(exc)},
            )
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

    # ═══════════════════════════════════════════════════
    # DDAY-B3 — Bottled Water 2D target-line skin
    #
    # Binds the dedicated Bottled Water skin to the B2 generic single-line
    # runtime. The projection below is raw operational facts only: no KPI is
    # calculated here and no hidden scenario truth is exposed.
    # ═══════════════════════════════════════════════════

    _bw_controller: dict = {"instance": None}

    def _bw_config_path() -> str:
        """Resolve the Bottled Water workspace config (env override supported)."""
        default = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "configs" / "workspaces" / "bottled-water-dday" / "line.yaml"
        )
        return os.environ.get("BOTTLED_WATER_CONFIG", str(default))

    def _get_bw_controller():
        if _bw_controller["instance"] is None:
            from virtual_factory.assembly.demo_controller import DemoController
            ctrl = DemoController(config_path=_bw_config_path())
            ctrl.initialize()
            if not ctrl.is_generic_line:
                raise RuntimeError(
                    "Bottled Water workspace requires a generic single-line "
                    "configuration"
                )
            _bw_controller["instance"] = ctrl
        return _bw_controller["instance"]

    def _bw_projection(ctrl, limit: int = 60) -> dict:
        """Domain-neutral outward projection of the B2 generic line runtime.

        Reads only public runtime surfaces. Counts and states are raw facts.
        """
        line = ctrl.line
        facts = ctrl.line_facts()
        checkpoints = [
            station_id
            for station_id, contract in line.station_contracts.items()
            if contract.capabilities.quality_decision
        ]

        stations = []
        for sequence, entry in enumerate(facts["positions"]):
            station_id = entry["position_id"]
            stations.append({
                "sequence": sequence,
                "station_id": station_id,
                "unit_id": entry["unit_id"],
                "unit_type": entry["unit_type"],
                "product_code": entry["product_code"],
                "unit_status": entry["manufacturing_status"],
                "is_occupied": entry["is_occupied"],
                "is_quality_checkpoint": station_id in checkpoints,
                "last_disposition": line.last_quality_disposition(station_id),
            })

        events = [
            {
                "event_type": event.event_type,
                "station_id": event.position,
                "unit_id": event.wip_id,
                "detail": event.detail,
                "simulation_time_s": event.simulation_time_s,
                "dwell_number": event.dwell_number,
            }
            for event in line.trace[-limit:]
        ]

        return {
            "workspace_id": "bottled-water-dday",
            "plant_id": facts["plant_id"],
            "line_id": facts["line_id"],
            "line_label": facts["line_label"],
            "run_state": facts["run_state"],
            "operating_state": facts["operating_state"],
            "simulation_time_s": facts["simulation_time_s"],
            "dwell_number": facts["dwell_number"],
            "nominal_dwell_s": facts["nominal_dwell_s"],
            "unit_type": facts["unit_type"],
            "product_code": facts["product_code"],
            "route": facts["route"],
            "stations": stations,
            "counts": {
                "total": facts["total_count"],
                "good": facts["good_count"],
                "reject": facts["reject_count"],
            },
            "units_on_line": facts["units_on_line"],
            "quality_checkpoints": checkpoints,
            "last_reject": next(
                (e["unit_id"] for e in reversed(events)
                 if e["event_type"] == "REJECT"), ""),
            "recent_events": events,
        }

    @app.get("/bottled-water-demo/state")
    def bottled_water_state(
        limit: int = Query(default=60, ge=0, le=200),
    ) -> dict:
        """Raw line facts for the Bottled Water skin (no KPI calculation).

        `limit` bounds the event window. A full production cycle emits roughly
        20–30 events, so the default window covers more than one cycle and the
        skin never misses a cycle's events between polls.
        """
        return _bw_projection(_get_bw_controller(), limit=limit)

    @app.get("/bottled-water-demo/static/{filename}", include_in_schema=False)
    def bottled_water_static(filename: str) -> FileResponse:
        return FileResponse(static_dir / filename)

    @app.get("/bottled-water-demo", include_in_schema=False)
    def bottled_water_page() -> FileResponse:
        return FileResponse(static_dir / "bottled_water_demo.html")

    @app.get("/bottled-water-demo/unit/{unit_id}")
    def bottled_water_unit(unit_id: str) -> dict:
        """Context for one unit at a selected point (selection is read-only)."""
        from fastapi.responses import JSONResponse
        ctrl = _get_bw_controller()
        line = ctrl.line
        unit = line.get_wip(unit_id)
        if unit is None:
            return JSONResponse(
                status_code=404,
                content={"detail": f"Unit not found: {unit_id!r}"},
            )
        history = line.get_quality_history(unit_id)
        return {
            "unit_id": unit.wip_id,
            "unit_type": unit.unit_type,
            "product_code": unit.product_code,
            "unit_sequence": unit.unit_sequence,
            "unit_status": unit.lifecycle.value,
            "current_station_id": unit.current_position,
            "stations_completed": unit.station_count,
            "rejected": unit.rejected,
            "counted_good": unit.counted_good,
            "quality_status": line.get_current_quality_status(unit_id).value,
            "quality_records": [
                {
                    "record_id": record.record_id,
                    "station_id": record.station_id,
                    "check_type": record.check_type.value,
                    "disposition": record.disposition,
                    "attempt_number": record.attempt_number,
                    "simulation_time_s": record.simulation_time_s,
                    "reason_code": record.reason_code,
                }
                for record in (history.records if history else ())
            ],
        }

    # Controls: exactly the operator set allowed by the B3 contract.
    @app.post("/bottled-water-demo/start")
    def bottled_water_start() -> dict:
        ctrl = _get_bw_controller()
        ctrl.start()
        return _bw_projection(ctrl)

    @app.post("/bottled-water-demo/pause")
    def bottled_water_pause() -> dict:
        ctrl = _get_bw_controller()
        ctrl.pause()
        return _bw_projection(ctrl)

    @app.post("/bottled-water-demo/resume")
    def bottled_water_resume() -> dict:
        ctrl = _get_bw_controller()
        ctrl.resume()
        return _bw_projection(ctrl)

    @app.post("/bottled-water-demo/stop")
    def bottled_water_stop() -> dict:
        ctrl = _get_bw_controller()
        ctrl.stop()
        return _bw_projection(ctrl)

    @app.post("/bottled-water-demo/reset")
    def bottled_water_reset() -> dict:
        """RESET rebuilds the line and returns it to its known initial state."""
        ctrl = _get_bw_controller()
        ctrl.reset()
        return _bw_projection(ctrl)

    @app.post("/bottled-water-demo/advance")
    def bottled_water_advance() -> dict:
        """Animation-clock tick: one deterministic production cycle.

        Not an operator control — the skin's presentation clock calls this while
        the line is RUNNING. The runtime itself refuses to advance unless the
        run state is RUNNING, so operator semantics are preserved.
        """
        ctrl = _get_bw_controller()
        ctrl.advance()
        return _bw_projection(ctrl)

    return app

