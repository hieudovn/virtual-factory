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

    _assy_experience_note = (
        "R2: /assy-demo is the rich projection of the SAME canonical TIPA "
        "RuntimeSession used by /workspaces (one run authority). No legacy "
        "DemoController/AssyDemoComposition is instantiated on this path."
    )

    def _get_assy_experience():
        from virtual_factory.ui.assy_experience import CanonicalAssyExperience

        return CanonicalAssyExperience(_get_workspace_monitor())

    def _deferred_response(feature: str, reason: str, *, mutation: bool = True):
        """Explicit deferred-unavailable (fail closed; never legacy runtime)."""
        from fastapi.responses import JSONResponse
        from virtual_factory.ui.assy_experience import DeferredUnavailable

        exc = DeferredUnavailable(feature, reason)
        return JSONResponse(
            status_code=409 if mutation else 503,
            content={
                "status": "deferred",
                "feature": exc.feature,
                "deferred_to": exc.gate,
                "reason": exc.reason,
                "authority": "canonical_tipa_runtime_session",
                "legacy_runtime_authority": False,
            },
        )

    def _experience_error_response(exc: Exception):
        from fastapi.responses import JSONResponse
        from virtual_factory.ui.assy_experience import (
            AssyExperienceError,
            SessionNotStarted,
        )

        if isinstance(exc, SessionNotStarted):
            return JSONResponse(
                status_code=409,
                content={
                    "status": "session_not_started",
                    "detail": str(exc),
                    "authority": "canonical_tipa_runtime_session",
                },
            )
        if isinstance(exc, AssyExperienceError):
            return JSONResponse(
                status_code=404, content={"detail": str(exc), "status": "error"}
            )
        raise exc

    @app.get("/assy-demo")
    def assy_demo_page() -> FileResponse:
        return FileResponse(static_dir / "assy_demo.html")

    @app.get("/assy-demo/static/{filename}")
    def assy_demo_static(filename: str) -> FileResponse:
        return FileResponse(static_dir / filename)

    @app.post("/assy-demo/reset")
    def assy_demo_reset(body: dict | None = None) -> dict:
        """In-context reset of the SELECTED canonical TIPA session (R1-C01).

        Scenario/profile is pinned run input (R1): a request for a DIFFERENT
        scenario is deferred (no legacy mutate-then-reset semantics).
        """
        experience = _get_assy_experience()
        requested = (body or {}).get("scenario")
        if requested:
            effective = experience.session_identity().get("scenario_id", "")
            profile = experience.session_identity().get("run_profile") or {}
            if requested not in (effective, profile.get("scenario")):
                return _deferred_response(
                    "scenario_change",
                    "scenario/profile is pinned run input; changing it needs a "
                    "new canonical session (R4), not a legacy reset",
                )
        try:
            return experience.reset()
        except Exception as exc:
            return _experience_error_response(exc)

    @app.post("/assy-demo/step")
    def assy_demo_step() -> dict:
        """Advance the SELECTED canonical TIPA session (one boundary)."""
        experience = _get_assy_experience()
        try:
            return experience.step()
        except Exception as exc:
            return _experience_error_response(exc)

    @app.get("/assy-demo/observations")
    def assy_demo_observations() -> dict:
        """R3: observation/MES output is not rewired yet (fail closed)."""
        return _deferred_response(
            "observations",
            "observation/MES reintegration is R3; the legacy runtime is not "
            "allowed to serve it",
            mutation=False,
        )

    @app.post("/assy-demo/snapshot")
    def assy_demo_snapshot() -> dict:
        experience = _get_assy_experience()
        try:
            return experience.snapshot()
        except Exception as exc:
            return _experience_error_response(exc)

    # ═══════════════════════════════════════════════════
    # VF-DM-DEMO-ASSY-MES-02 — MES contract bridge endpoints
    # ═══════════════════════════════════════════════════

    @app.post("/assy-demo/jam")
    def assy_demo_jam(body: dict | None = None) -> dict:
        """R4: AP05 fault/OEE workflow needs legacy authority (fail closed)."""
        return _deferred_response(
            "jam",
            "AP05 fault/OEE workflow is not bindable to the canonical session "
            "without new architecture (R4)",
        )

    @app.post("/assy-demo/recover")
    def assy_demo_recover(body: dict | None = None) -> dict:
        """R4: AP05 fault recovery needs legacy authority (fail closed)."""
        return _deferred_response(
            "recover",
            "AP05 fault recovery is not bindable to the canonical session "
            "without new architecture (R4)",
        )

    @app.post("/assy-demo/run-to-terminal")
    def assy_demo_run_to_terminal() -> dict:
        """R4: legacy run-to-terminal/OEE driver is deferred (fail closed)."""
        return _deferred_response(
            "run_to_terminal",
            "legacy run-to-terminal/OEE driving is not part of the canonical "
            "session contract (R4)",
        )

    @app.get("/assy-demo/mes-messages")
    def assy_demo_mes_messages() -> dict:
        """R3: MES contract output is not rewired yet (fail closed)."""
        return _deferred_response(
            "mes_messages",
            "MES/output reintegration is R3; the legacy runtime is not allowed "
            "to serve it",
            mutation=False,
        )

    @app.get("/assy-demo/mes-trace")
    def assy_demo_mes_trace() -> dict:
        """R3: MES bridge delivery trace is not rewired yet (fail closed)."""
        return _deferred_response(
            "mes_trace",
            "MES/output reintegration is R3; the legacy runtime is not allowed "
            "to serve it",
            mutation=False,
        )

    @app.get("/assy-demo/version")
    def assy_demo_version() -> dict:
        """Exact source SHA + active additive MES contract version (read-only)."""
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
            "authority": "canonical_tipa_runtime_session",
        }

    # ═══════════════════════════════════════════════════
    # OPS-03 — Station Interaction / Inspector Binding
    # ═══════════════════════════════════════════════════

    @app.post("/assy-demo/operation-command")
    def assy_demo_operation_command(body: dict) -> dict:
        """OPS-03 thin same-session binding: the canonical runtime decides."""
        from fastapi.responses import JSONResponse
        from virtual_factory.assembly.line_runtime import AssyLineError
        station_id = body.get("station_id", "")
        wip_id = body.get("wip_id", "")
        command = body.get("command", "")
        payload = body.get("payload")
        if not station_id or not wip_id or not command:
            return JSONResponse(
                status_code=400,
                content={"detail": "station_id, wip_id and command are required"},
            )
        experience = _get_assy_experience()
        try:
            return experience.operation_command(
                body.get("sub_line_id", ""), station_id, wip_id, command, payload
            )
        except AssyLineError as exc:
            return JSONResponse(
                status_code=409,
                content={"detail": str(exc), "status": "error"},
            )
        except Exception as exc:
            return _experience_error_response(exc)

    @app.post("/assy-demo/station-action")
    def assy_demo_station_action(body: dict) -> dict:
        """OPS-03/OPS-04 thin same-session binding: runtime decides."""
        from fastapi.responses import JSONResponse
        from virtual_factory.assembly.line_runtime import AssyLineError
        station_id = body.get("station_id", "")
        wip_id = body.get("wip_id", "")
        action = body.get("action", "")
        if not station_id or not wip_id or not action:
            return JSONResponse(
                status_code=400,
                content={"detail": "station_id, wip_id and action are required"},
            )
        experience = _get_assy_experience()
        try:
            return experience.station_action(
                body.get("sub_line_id", ""), station_id, wip_id, action
            )
        except AssyLineError as exc:
            return JSONResponse(
                status_code=409,
                content={"detail": str(exc), "status": "error"},
            )
        except Exception as exc:
            return _experience_error_response(exc)

    @app.post("/assy-demo/run-mode")
    def assy_demo_run_mode(body: dict) -> dict:
        """Thin same-session binding: effective run mode on the six canonical lines."""
        from fastapi.responses import JSONResponse
        from virtual_factory.assembly.station_contracts import CompletionMode
        from virtual_factory.ui.assy_experience import SessionNotStarted
        mode = body.get("mode", "")
        experience = _get_assy_experience()
        try:
            return experience.set_run_mode(mode)
        except SessionNotStarted as exc:
            return _experience_error_response(exc)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"detail": f"Invalid run mode: {mode!r}"},
            )
        except Exception as exc:
            return _experience_error_response(exc)

    @app.post("/assy-demo/select")
    def assy_demo_select(body: dict) -> dict:
        """Select the presentation sub-line of the canonical session.

        R2: presentation context only — never resets/reconstructs/forks any
        runtime and never changes the parent run identity.
        """
        from fastapi.responses import JSONResponse
        sub_line_id = body.get("sub_line_id", "")
        if not sub_line_id:
            return JSONResponse(
                status_code=400,
                content={"detail": "sub_line_id is required"},
            )
        experience = _get_assy_experience()
        try:
            return experience.select(sub_line_id)
        except Exception as exc:
            return _experience_error_response(exc)

    # ── Frame A / Frame B projection endpoints (canonical session) ──
    @app.get("/assy-demo/overview")
    def assy_demo_overview() -> dict:
        experience = _get_assy_experience()
        try:
            return experience.overview()
        except Exception as exc:
            return _experience_error_response(exc)

    @app.get("/assy-demo/sub-lines")
    def assy_demo_sub_lines() -> list[dict]:
        experience = _get_assy_experience()
        return experience.overview()["sub_lines"]

    @app.get("/assy-demo/sub-line/{sub_line_id}")
    def assy_demo_sub_line_detail(sub_line_id: str) -> dict:
        experience = _get_assy_experience()
        try:
            return experience.detail(sub_line_id)
        except Exception as exc:
            return _experience_error_response(exc)

    @app.get("/assy-demo/identity")
    def assy_demo_identity() -> dict:
        """Canonical session/run/scenario/profile identity for the rich UI."""
        experience = _get_assy_experience()
        payload = experience.identity()
        payload["note"] = _assy_experience_note
        return payload

    # ═══════════════════════════════════════════════════
    # G6 — Shared hierarchical UI context (read-only, additive)
    # Projection of the accepted G1 Workspace/StructuralPath authority only.
    # No run-control/replay/orchestration semantics.
    # ═══════════════════════════════════════════════════
    from fastapi.responses import JSONResponse as _JSONResponse

    def _tipa_structural_workspace():
        from virtual_factory.federation import build_tipa_workspace

        return build_tipa_workspace()

    def _continuous_structural_workspace():
        from virtual_factory.runcontrol import build_continuous_workspace

        return build_continuous_workspace()

    def _structural_workspace(workspace: str):
        """Resolve a workspace discriminator to its G1 Workspace (or None)."""
        if workspace == "TIPA":
            return _tipa_structural_workspace()
        if workspace == "continuous":
            return _continuous_structural_workspace()
        return None

    @app.get("/api/ui/hierarchy")
    def ui_hierarchy(workspace: str = Query("TIPA")):
        from virtual_factory.ui import hierarchy as ui_hierarchy_mod

        ws = _structural_workspace(workspace)
        if ws is None:
            return _JSONResponse(
                status_code=404,
                content={
                    "detail": (
                        f"unknown workspace {workspace!r} for structural "
                        f"hierarchy; supported: TIPA, continuous"
                    )
                },
            )
        return ui_hierarchy_mod.workspace_to_dict(ws)

    @app.get("/api/ui/context")
    def ui_context(
        workspace: str = Query("TIPA"),
        path: str | None = Query(None),
        object_id: str | None = Query(None),
    ):
        from virtual_factory.ui import hierarchy as ui_hierarchy_mod

        ws = _structural_workspace(workspace)
        if ws is None:
            return _JSONResponse(
                status_code=404,
                content={
                    "detail": (
                        f"unknown workspace {workspace!r} for structural "
                        f"context; supported: TIPA, continuous"
                    )
                },
            )
        try:
            scope_path = (
                ui_hierarchy_mod.parse_path(path) if path else None
            )
            return ui_hierarchy_mod.structural_context(
                ws,
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
                process_scope_path,
            )

            ws = build_continuous_workspace()

            def bridge_factory():
                # Attempt isolation (C03): a NEW run attempt owns a FRESH
                # RuntimeService built from the SAME accepted config/runtime
                # construction inputs. It never shares the legacy dashboard's
                # service and never reuses another attempt's runtime object.
                attempt_runtime = RuntimeService(
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
                return ContinuousExecutionBridge(
                    attempt_runtime,
                    participant_id=process_scope_path().as_string(),
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

    # ═══════════════════════════════════════════════
    # G24 — Multi-Workspace UI Switching + Monitoring Shell
    # Additive observer/controller seam over the G23 WorkspaceRuntimeRegistry
    # + G22 RuntimeSession. The shell page (`/workspaces`) lists the accepted
    # workspaces (selector), selects a workspace, shows a read-only monitor
    # view, and lets shared run controls act on the selected workspace session
    # only. SH-WTP assumed topology/fidelity is never presented as site truth.
    # No gateway routing / export / MES-PIM change here.
    # ═══════════════════════════════════════════════
    _workspace_monitor: dict = {"instance": None}

    def _get_workspace_monitor():
        if _workspace_monitor["instance"] is None:
            from virtual_factory.ui.workspace_monitor import WorkspaceMonitor

            tipa_config = os.environ.get(
                "TIPA_ASSY_CONFIG",
                str(
                    Path(__file__).resolve().parent.parent.parent.parent
                    / "configs" / "plants" / "tipa_assy_demo.yaml"
                ),
            )
            _workspace_monitor["instance"] = WorkspaceMonitor(
                tipa_config_path=tipa_config
            )
        return _workspace_monitor["instance"]

    @app.get("/workspaces", include_in_schema=False)
    def workspaces_page() -> FileResponse:
        """G24 multi-workspace shell page (HTML/CSS/JS)."""
        return FileResponse(static_dir / "workspace_shell.html")

    @app.get("/static/workspace_shell.js", include_in_schema=False)
    def workspace_shell_js_direct() -> FileResponse:
        return FileResponse(
            static_dir / "workspace_shell.js", media_type="application/javascript"
        )

    @app.get("/static/workspace_shell.css", include_in_schema=False)
    def workspace_shell_css_direct() -> FileResponse:
        return FileResponse(static_dir / "workspace_shell.css", media_type="text/css")

    @app.get("/vnext/workspaces")
    def vnext_workspaces():
        """Registry-backed selector source (deterministic, orchestration only)."""
        monitor = _get_workspace_monitor()
        return monitor.workspace_list()

    @app.get("/vnext/workspaces/{workspace_id}/view")
    def vnext_workspace_view(workspace_id: str):
        monitor = _get_workspace_monitor()
        try:
            return monitor.view(workspace_id)
        except Exception as exc:
            return _JSONResponse(
                status_code=404,
                content={"detail": f"unknown workspace {workspace_id!r}: {exc}"},
            )

    @app.post("/vnext/workspaces/select")
    def vnext_workspace_select(body: dict):
        monitor = _get_workspace_monitor()
        workspace_id = (body or {}).get("workspace_id", "")
        if not workspace_id:
            return _JSONResponse(
                status_code=400, content={"detail": "workspace_id is required"}
            )
        try:
            return monitor.select(workspace_id)
        except Exception as exc:
            return _JSONResponse(
                status_code=404,
                content={"detail": f"unknown workspace {workspace_id!r}: {exc}"},
            )

    @app.post("/vnext/workspaces/{workspace_id}/control")
    def vnext_workspace_control(workspace_id: str, body: dict):
        monitor = _get_workspace_monitor()
        action = (body or {}).get("action", "")
        if not action:
            return _JSONResponse(
                status_code=400, content={"detail": "action is required"}
            )
        try:
            return monitor.control(workspace_id, action)
        except Exception as exc:
            return _JSONResponse(
                status_code=400,
                content={"detail": f"workspace {workspace_id!r}: {exc}"},
            )

    return app
