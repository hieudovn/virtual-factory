"""FastAPI monitoring API for Virtual Factory telemetry."""

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════
# VF-vNEXT-R5 — Single Simulation System Consolidation (legacy authority removal)
#
# The active product path must create simulation state ONLY through the canonical
# Workspace / RuntimeSession seam (/workspaces, /vnext/workspaces/*, /assy-demo/*).
# The legacy simulation authorities were DE-AUTHORIZED here:
#   1. the eager root-dashboard ``RuntimeService`` (experimental MVP-01 surface),
#   2. the legacy G7 run-control service family (``/vnext/runs*``),
#   3. the legacy ``/demo-assy-mes`` ``DemoController`` runtime path.
# They remain reachable only as FAIL-CLOSED deprecated aliases: any request that
# touches them returns HTTP 410 and constructs ZERO runtime/engine/controller
# state. The reusable kernel/library classes are NOT deleted (classification in
# the VF-vNEXT-R5 report); nothing here constructs them.
# ═══════════════════════════════════════════════════════════════════════════
LEGACY_AUTHORITY_REMOVED_CODE = "VF_LEGACY_AUTHORITY_DEAUTHORIZED"

#: The legacy surfaces removed from the active product path in VF-vNEXT-R5.
DEAUTHORIZED_LEGACY_SURFACES: tuple[str, ...] = (
    "root_dashboard_runtime_service",
    "legacy_g7_run_control",
    "legacy_demo_assy_mes",
)

#: Canonical product paths that replace the removed authorities.
CANONICAL_PRODUCT_PATHS: tuple[str, ...] = (
    "/workspaces",
    "/vnext/workspaces",
    "/vnext/workspaces/{workspace_id}/view",
    "/assy-demo",
)


def legacy_deprecation_payload(surface: str) -> dict:
    """Machine-readable fail-closed payload for a de-authorized legacy route."""
    return {
        "error": "legacy_runtime_authority_deauthorized",
        "code": LEGACY_AUTHORITY_REMOVED_CODE,
        "surface": surface,
        "detail": (
            "This legacy simulation authority was de-authorized in VF-vNEXT-R5 and "
            "constructs no runtime state. Use the canonical product paths instead."
        ),
        "canonical_paths": list(CANONICAL_PRODUCT_PATHS),
        "legacy_runtime_authority": False,
    }


class LegacyRuntimeAuthorityDeauthorized(RuntimeError):
    """A de-authorized legacy simulation authority was touched (VF-vNEXT-R5)."""

    def __init__(self, surface: str) -> None:
        self.surface = surface
        RuntimeError.__init__(
            self,
            f"legacy runtime authority {surface!r} is de-authorized "
            f"(VF-vNEXT-R5); canonical product paths: "
            f"{', '.join(CANONICAL_PRODUCT_PATHS)}",
        )


class DeauthorizedRuntimeAuthority:
    """Fail-closed placeholder standing in for a removed runtime authority.

    Attribute access ALWAYS raises, so a provider that returned this object can
    never construct, step or reset simulation state.
    """

    __slots__ = ("_surface",)

    def __init__(self, surface: str) -> None:
        object.__setattr__(self, "_surface", surface)

    def __getattr__(self, name: str):
        raise LegacyRuntimeAuthorityDeauthorized(object.__getattribute__(self, "_surface"))

    def __repr__(self) -> str:  # pragma: no cover - diagnostic only
        return f"<deauthorized legacy authority {object.__getattribute__(self, '_surface')!r}>"


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
    """Create the Virtual Factory FastAPI app for one process.

    VF-vNEXT-R5: the app is a CANONICAL product shell host, not a simulation
    authority — it constructs no runtime state (no RuntimeService, engine,
    controller or session). ``GET /`` is the canonical entrypoint and redirects
    to the workspace shell (``/workspaces``). The accepted ``config_path`` /
    ``scenario_path`` / ``dt_s`` / ``mqtt_*`` / ``opcua_endpoint`` / ``auto_start``
    arguments are retained for call-site compatibility with the de-authorized
    experimental continuous dashboard and create no authority.
    """
    from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
    from fastapi.responses import FileResponse, RedirectResponse
    from fastapi.staticfiles import StaticFiles

    # VF-vNEXT-R5: NO RuntimeService (and no engine/runtime object) is created
    # here any more. The construction inputs are retained for call-site
    # compatibility with the de-authorized experimental continuous dashboard and
    # create no authority: ``service`` is a fail-closed placeholder.
    service = DeauthorizedRuntimeAuthority("root_dashboard_runtime_service")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # The experimental continuous loop authority was removed in VF-vNEXT-R5:
        # the app starts no simulation loop and therefore starts no runtime state.
        # ``auto_start`` is accepted for call-site compatibility only; it must not
        # be referenced here (a bare ``del`` would make it a local name and break
        # startup with UnboundLocalError — caught by the R5 server smoke).
        yield

    app = FastAPI(title="Virtual Factory Monitoring API", version="0.1.0", lifespan=lifespan)
    static_dir = Path(__file__).resolve().parent / "static"

    @app.exception_handler(LegacyRuntimeAuthorityDeauthorized)
    def _legacy_authority_removed(_request, exc: LegacyRuntimeAuthorityDeauthorized):
        """HTTP 410 for every de-authorized legacy simulation authority."""
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=410, content=legacy_deprecation_payload(exc.surface)
        )

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

    @app.get("/", include_in_schema=False)
    def dashboard() -> RedirectResponse:
        """Canonical VF entrypoint: redirect the bare root to the workspace shell.

        VF-vNEXT-R5-C01: the root used to serve the EXPERIMENTAL continuous
        dashboard (``index.html``), which was backed by the removed eager
        RuntimeService authority. The root is now the canonical entrypoint into
        the canonical product surface (Workspace Shell); the legacy dashboard and
        its static assets stay in the repo as reference-only and are no longer
        served. Resolving this route constructs ZERO runtime state.
        """
        return RedirectResponse(url="/workspaces", status_code=307)

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
        """Switch to a different plant configuration at runtime and persist it.

        VF-vNEXT-R5: de-authorized — the root-dashboard runtime authority was
        removed, so there is no live continuous configuration to switch. Fails
        closed BEFORE any body validation (deterministic 410, no construction).
        """
        raise LegacyRuntimeAuthorityDeauthorized("root_dashboard_runtime_service")

    # ═══════════════════════════════════════════════════
    # VF-DM-DEMO-ASSY-MES-01 — TIPA ASSY Customer Demo Scenario v1
    # Minimal control surface: reset / start / pause / step / jam / recover.
    # ═══════════════════════════════════════════════════

    def _get_demo_controller():
        """VF-vNEXT-R5: the active legacy DemoController runtime path is removed.

        No request may construct a ``DemoController``/``DemoRunner``/legacy
        composition. The module and its classes stay available as
        reference/test-only code (nothing is deleted); this provider fails closed.
        """
        raise LegacyRuntimeAuthorityDeauthorized("legacy_demo_assy_mes")

    @app.get("/demo-assy-mes", include_in_schema=False)
    def demo_asssy_page():
        """Legacy TIPA ASSY demo page: de-authorized fail-closed alias (R5).

        The legacy customer-demo page was backed by the removed DemoController
        runtime path; the static asset stays in the repo as reference but the
        route never serves an active legacy runtime surface again.
        """
        raise LegacyRuntimeAuthorityDeauthorized("legacy_demo_assy_mes")

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
        "DemoController/AssyDemoComposition is instantiated on this path. "
        "R3: observation/MES output (observations | mes-messages | mes-trace) "
        "is a READ-ONLY downstream projection of that same session."
    )

    def _get_assy_experience():
        from virtual_factory.ui.assy_experience import CanonicalAssyExperience

        return CanonicalAssyExperience(_get_workspace_monitor())

    _assy_output: dict = {"instance": None}

    def _get_assy_output():
        """R3 canonical same-session output projection (memoized, read-only)."""
        from virtual_factory.ui.assy_output import CanonicalAssyOutput

        if _assy_output["instance"] is None:
            _assy_output["instance"] = CanonicalAssyOutput(_get_assy_experience())
        return _assy_output["instance"]

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
        try:
            from virtual_factory.ui.assy_output import (
                CanonicalOutputError,
                OutputMutationError,
            )
        except Exception:  # pragma: no cover - import guard
            CanonicalOutputError = OutputMutationError = ()  # type: ignore
        if isinstance(exc, OutputMutationError):
            return JSONResponse(
                status_code=409,
                content={
                    "status": "output_mutation_blocked",
                    "detail": str(exc),
                    "authority": "canonical_tipa_runtime_session",
                    "legacy_runtime_authority": False,
                },
            )
        if isinstance(exc, CanonicalOutputError):
            return JSONResponse(
                status_code=409,
                content={
                    "status": "output_unavailable",
                    "detail": str(exc),
                    "authority": "canonical_tipa_runtime_session",
                    "legacy_runtime_authority": False,
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
            identity = experience.session_identity()
            profile = identity.get("run_profile") or {}
            if requested not in (
                identity.get("scenario_id", ""),
                profile.get("scenario"),
            ):
                # R4: a different scenario is a FRESH canonical run, never an
                # in-place mutation of the active run's pinned identity.
                try:
                    result = experience.select_scenario(requested)
                except Exception as exc:
                    return _experience_error_response(exc)
                result["legacy_runtime_authority"] = False
                return result
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
        """R3: canonical same-session P0 observation facts (READ-ONLY).

        Re-enabled by R3: no longer a deferred 503. Polls the canonical
        projection only — it never creates or steps a simulation runtime.
        """
        try:
            return _get_assy_output().observations()
        except Exception as exc:
            return _experience_error_response(exc)

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
        """R4: canonical AP05 jam on ONE selected sub-line (same session)."""
        experience = _get_assy_experience()
        payload = body or {}
        sub_line_id = payload.get("sub_line_id") or None
        try:
            result = experience.jam(sub_line_id)
        except Exception as exc:
            return _experience_error_response(exc)
        result["legacy_runtime_authority"] = False
        return result

    @app.post("/assy-demo/recover")
    def assy_demo_recover(body: dict | None = None) -> dict:
        """R4: canonical AP05 recovery on the same sub-line (fail closed)."""
        experience = _get_assy_experience()
        payload = body or {}
        sub_line_id = payload.get("sub_line_id") or None
        try:
            result = experience.recover(sub_line_id)
        except Exception as exc:
            return _experience_error_response(exc)
        result["legacy_runtime_authority"] = False
        return result

    @app.post("/assy-demo/run-to-terminal")
    def assy_demo_run_to_terminal(body: dict | None = None) -> dict:
        """R4: bounded canonical run-to-terminal over the SAME session."""
        experience = _get_assy_experience()
        max_windows = (body or {}).get("max_windows", 32)
        try:
            result = experience.run_to_terminal(max_windows)
        except Exception as exc:
            return _experience_error_response(exc)
        result["legacy_runtime_authority"] = False
        return result

    @app.get("/assy-demo/oee")
    def assy_demo_oee() -> dict:
        """R4: READ-ONLY OEE/final summary from canonical facts (idempotent)."""
        try:
            return _get_assy_output().oee_summary()
        except Exception as exc:
            return _experience_error_response(exc)

    @app.post("/assy-demo/scenario")
    def assy_demo_scenario(body: dict) -> dict:
        """R4: scenario selection = FRESH canonical run (no in-place mutation)."""
        experience = _get_assy_experience()
        scenario_id = (body or {}).get("scenario_id")
        if not scenario_id:
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=400,
                content={
                    "detail": "scenario_id is required",
                    "status": "error",
                },
            )
        try:
            result = experience.select_scenario(scenario_id)
        except Exception as exc:
            return _experience_error_response(exc)
        result["legacy_runtime_authority"] = False
        return result

    @app.get("/assy-demo/mes-messages")
    def assy_demo_mes_messages() -> dict:
        """R3: canonical same-session MES messages (READ-ONLY)."""
        try:
            return _get_assy_output().mes_messages()
        except Exception as exc:
            return _experience_error_response(exc)

    @app.get("/assy-demo/mes-trace")
    def assy_demo_mes_trace() -> dict:
        """R3: canonical same-session MES delivery trace (READ-ONLY)."""
        try:
            return _get_assy_output().mes_trace()
        except Exception as exc:
            return _experience_error_response(exc)

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
    # G7 — legacy run-control family: DE-AUTHORIZED (VF-vNEXT-R5).
    #
    # The legacy family kept its OWN RunLifecycleService authority per workspace
    # (``TIPA`` = a duplicate authority over an UNPREPARED federation, and
    # ``continuous`` = a second continuous authority owning an extra
    # RuntimeService per attempt). Both discriminators are removed from the
    # active product path: the canonical TIPA authority is /vnext/workspaces/TIPA/*
    # plus /assy-demo/*, and no continuous workspace is registered.
    #
    # The route decorators are kept so callers receive an explicit fail-closed
    # deprecation (HTTP 410) instead of an ambiguous 404, and so the removal is
    # auditable. NOTHING below constructs a lifecycle service or runtime.
    # ═══════════════════════════════════════════════

    def _get_run_control_service(workspace: str = "TIPA"):
        """Fail closed: the legacy G7 run-control authority no longer exists."""
        raise LegacyRuntimeAuthorityDeauthorized("legacy_g7_run_control")

    # ═══════════════════════════════════════════════
    # Legacy G7 route surface (deprecated aliases only)
    # One platform-level run authority PER WORKSPACE; domain runtimes stay
    # authoritative. TIPA and continuous are independent workspace authorities
    # (no cross-workspace mutation, no platform-global active run singleton).
    # Legacy /step /start /stop /reset remain compatibility surfaces (not
    # repointed). The ``workspace`` discriminator follows the existing G6
    # ``?workspace=`` query-param convention (default: TIPA).
    # ═══════════════════════════════════════════════

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

    @app.post("/vnext/workspaces/{workspace_id}/new-run")
    def vnext_workspace_new_run(workspace_id: str, body: dict):
        """VF-vNEXT-R5 (audit I1): start a FRESH canonical run from the shell.

        The shell's scenario / new-run control uses the SAME canonical seam as
        the rich ASSY page (``WorkspaceMonitor.new_run`` -> the shared
        ``build_tipa_scenario_run_factory``), so there is exactly ONE run-id
        authority and every new run is pinned to its own immutable run context
        (no cross-run profile contamination).
        """
        monitor = _get_workspace_monitor()
        if not monitor.has(workspace_id):
            return _JSONResponse(
                status_code=404, content={"detail": f"unknown workspace {workspace_id!r}"}
            )
        scenario_id = (body or {}).get("scenario_id") or None
        try:
            return monitor.new_run(workspace_id, scenario_id)
        except Exception as exc:
            return _JSONResponse(
                status_code=400,
                content={"detail": f"new run refused for {workspace_id!r}: {exc}"},
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
