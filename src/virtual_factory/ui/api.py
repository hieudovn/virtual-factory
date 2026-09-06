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
    # G6 — Shared hierarchical UI context (read-only, additive)
    # Projection of the accepted G1 Workspace/StructuralPath authority only.
    # No run-control/replay/orchestration semantics.
    # ═══════════════════════════════════════════════════
    from fastapi.responses import JSONResponse as _JSONResponse

    def _tipa_structural_workspace():
        from virtual_factory.federation import build_tipa_workspace

        return build_tipa_workspace()

    @app.get("/api/ui/hierarchy")
    def ui_hierarchy(workspace: str = Query("TIPA")):
        from virtual_factory.ui import hierarchy as ui_hierarchy_mod

        if workspace != "TIPA":
            return _JSONResponse(
                status_code=404,
                content={
                    "detail": (
                        f"unknown workspace {workspace!r} for structural "
                        f"hierarchy; supported: TIPA"
                    )
                },
            )
        return ui_hierarchy_mod.workspace_to_dict(
            _tipa_structural_workspace()
        )

    @app.get("/api/ui/context")
    def ui_context(
        workspace: str = Query("TIPA"),
        path: str | None = Query(None),
        object_id: str | None = Query(None),
    ):
        from virtual_factory.ui import hierarchy as ui_hierarchy_mod

        if workspace != "TIPA":
            return _JSONResponse(
                status_code=404,
                content={
                    "detail": (
                        f"unknown workspace {workspace!r} for structural "
                        f"context; supported: TIPA"
                    )
                },
            )
        try:
            scope_path = (
                ui_hierarchy_mod.parse_path(path) if path else None
            )
            return ui_hierarchy_mod.structural_context(
                _tipa_structural_workspace(),
                scope_path=scope_path,
                object_id=object_id,
            )
        except ui_hierarchy_mod.UiHierarchyError as exc:
            return _JSONResponse(
                status_code=400,
                content={"detail": str(exc)},
            )

    @app.get("/api/ui/context/continuous")
    def ui_context_continuous():
        """Truthful ROOT-ONLY context for the continuous dashboard.

        The continuous runtime has no authoritative multi-level G1 hierarchy;
        do not invent plant structure. The shared primitives may render only
        the workspace root.
        """
        from virtual_factory.ui import hierarchy as ui_hierarchy_mod

        plant_id = (service.status().get("plant_id") or "continuous")
        return ui_hierarchy_mod.root_only_context(plant_id)

    # ═══════════════════════════════════════════════
    # G7 — Hierarchical Scenario / Run Control (additive vNext seam)
    # One platform-level run authority PER WORKSPACE; domain runtimes stay
    # authoritative. TIPA and continuous are independent workspace authorities
    # (no cross-workspace mutation, no platform-global active run singleton).
    # Legacy /step /start /stop /reset remain compatibility surfaces (not
    # repointed). The ``workspace`` discriminator follows the existing G6
    # ``?workspace=`` query-param convention (default: TIPA).
    # ═══════════════════════════════════════════════
    _run_control: dict = {}

    def _get_run_control_service(workspace: str = "TIPA"):
        """Return the run-control authority for a workspace, or None.

        ``workspace`` is a platform workspace discriminator (``TIPA`` or
        ``continuous``); each value owns an independent RunLifecycleService
        (independent active run, history and bridge state). Unknown names fail
        closed (caller returns 404).
        """
        if workspace in _run_control:
            return _run_control[workspace]

        if workspace == "TIPA":
            from virtual_factory.federation import (
                TipaAssyFederation,
                build_tipa_workspace,
            )
            from virtual_factory.runcontrol import (
                AssyExecutionBridge,
                RunLifecycleService,
            )

            ws = build_tipa_workspace()

            def bridge_factory():
                assy_config = os.environ.get(
                    "TIPA_ASSY_CONFIG",
                    str(Path(__file__).resolve().parent.parent.parent.parent
                        / "configs" / "plants" / "tipa_assy_demo.yaml"),
                )
                federation = TipaAssyFederation(config_path=assy_config)
                federation.initialize()
                return AssyExecutionBridge(federation)

            _run_control[workspace] = RunLifecycleService(ws, bridge_factory)
        elif workspace == "continuous":
            from virtual_factory.runcontrol import (
                ContinuousExecutionBridge,
                RunLifecycleService,
                build_continuous_workspace,
            )

            ws = build_continuous_workspace()

            def bridge_factory():
                # Attempt-bound (C01): a NEW attempt builds a fresh execution
                # context on the SAME accepted continuous RuntimeService seam
                # (no engine rewrite, no second runtime instance).
                return ContinuousExecutionBridge(
                    service, participant_id=ws.workspace_id
                )

            _run_control[workspace] = RunLifecycleService(ws, bridge_factory)
        else:
            return None

        return _run_control[workspace]

    def _vnext_service(workspace: str):
        svc = _get_run_control_service(workspace)
        if svc is None:
            return None, _JSONResponse(
                status_code=404,
                content={"detail": f"unknown workspace {workspace!r}"},
            )
        return svc, None

    @app.post("/vnext/runs", status_code=201)
    def vnext_create_run(body: dict, workspace: str = Query("TIPA")):
        from virtual_factory.runcontrol import (
            RunLifecycleError,
            TargetResolutionError,
        )

        service, unknown = _vnext_service(workspace)
        if service is None:
            return unknown

        target_path = body.get("target_path", "")
        if not target_path:
            return _JSONResponse(
                status_code=400, content={"detail": "target_path is required"}
            )
        try:
            record = service.create_run(
                target_path,
                scenario_id=body.get("scenario_id"),
                model_id=body.get("model_id"),
                profile=body.get("profile"),
                random_seed=body.get("random_seed"),
            )
            return record.to_dict()
        except (TargetResolutionError, ValueError) as exc:
            return _JSONResponse(status_code=400, content={"detail": str(exc)})
        except RunLifecycleError as exc:
            return _JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.get("/vnext/runs/current")
    def vnext_current_run(workspace: str = Query("TIPA")):
        service, unknown = _vnext_service(workspace)
        if service is None:
            return unknown
        record = service.current()
        if record is None:
            return _JSONResponse(
                status_code=404, content={"detail": "no active run"}
            )
        return record.to_dict()

    @app.get("/vnext/runs/{run_id}")
    def vnext_get_run(run_id: str, workspace: str = Query("TIPA")):
        service, unknown = _vnext_service(workspace)
        if service is None:
            return unknown
        if not service.has_run(run_id):
            return _JSONResponse(
                status_code=404,
                content={"detail": f"unknown/stale run_id {run_id!r}"},
            )
        return service.status(run_id)

    def _vnext_mutate(
        run_id: str,
        operation: str,
        workspace: str = "TIPA",
        body: dict | None = None,
    ):
        service, unknown = _vnext_service(workspace)
        if service is None:
            return unknown
        if not service.has_run(run_id):
            return _JSONResponse(
                status_code=404,
                content={"detail": f"unknown/stale run_id {run_id!r}"},
            )
        from virtual_factory.runcontrol import (
            ReplayUnavailableError,
            RunLifecycleError,
        )

        try:
            if operation == "start":
                return service.start(run_id).to_dict()
            if operation == "step":
                return service.step(run_id).to_dict()
            if operation == "pause":
                return service.pause(run_id).to_dict()
            if operation == "resume":
                return service.resume(run_id).to_dict()
            if operation == "stop":
                return service.stop(run_id).to_dict()
            if operation == "reset":
                return service.reset(run_id).to_dict()
            if operation == "restart":
                return service.restart(run_id).to_dict()
            if operation == "replay":
                return service.replay(run_id).to_dict()
        except ReplayUnavailableError as exc:
            return _JSONResponse(status_code=409, content={"detail": str(exc)})
        except RunLifecycleError as exc:
            return _JSONResponse(status_code=409, content={"detail": str(exc)})
        return _JSONResponse(
            status_code=400, content={"detail": f"unknown operation {operation!r}"}
        )

    @app.post("/vnext/runs/{run_id}/start")
    def vnext_start(run_id: str, workspace: str = Query("TIPA")):
        return _vnext_mutate(run_id, "start", workspace)

    @app.post("/vnext/runs/{run_id}/step")
    def vnext_step(run_id: str, workspace: str = Query("TIPA")):
        return _vnext_mutate(run_id, "step", workspace)

    @app.post("/vnext/runs/{run_id}/pause")
    def vnext_pause(run_id: str, workspace: str = Query("TIPA")):
        return _vnext_mutate(run_id, "pause", workspace)

    @app.post("/vnext/runs/{run_id}/resume")
    def vnext_resume(run_id: str, workspace: str = Query("TIPA")):
        return _vnext_mutate(run_id, "resume", workspace)

    @app.post("/vnext/runs/{run_id}/stop")
    def vnext_stop(run_id: str, workspace: str = Query("TIPA")):
        return _vnext_mutate(run_id, "stop", workspace)

    @app.post("/vnext/runs/{run_id}/reset")
    def vnext_reset(run_id: str, workspace: str = Query("TIPA")):
        return _vnext_mutate(run_id, "reset", workspace)

    @app.post("/vnext/runs/{run_id}/restart")
    def vnext_restart(run_id: str, workspace: str = Query("TIPA")):
        return _vnext_mutate(run_id, "restart", workspace)

    @app.post("/vnext/runs/{run_id}/replay")
    def vnext_replay(run_id: str, workspace: str = Query("TIPA")):
        return _vnext_mutate(run_id, "replay", workspace)

    return app
