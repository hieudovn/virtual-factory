"""FastAPI server for WTP Simulator control and monitoring."""

from __future__ import annotations

import threading
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .actuator_engine import ActuatorEngine
from .disturbance_engine import DisturbanceEngine
from .ingest_client import IngestClient
from .scenario_manager import ScenarioManager
from .simulation_loop import WtpSimulationLoop


class SetpointRequest(BaseModel):
    value: float


class DisturbanceOverrideRequest(BaseModel):
    value: float
    override: bool = True


class WtpApiServer:
    """FastAPI server for the WTP Simulator."""

    def __init__(
        self,
        sim_loop: WtpSimulationLoop,
        ingest_client: IngestClient,
        scenario_manager: ScenarioManager,
        actuator_engine: ActuatorEngine,
        disturbance_engine: DisturbanceEngine,
        opcua_gateway: Any | None,
        config: Any,
    ) -> None:
        self.sim_loop = sim_loop
        self.ingest_client = ingest_client
        self.scenario_manager = scenario_manager
        self.actuator_engine = actuator_engine
        self.disturbance_engine = disturbance_engine
        self.opcua_gateway = opcua_gateway
        self.config = config
        self.app = self._create_app()
        self.start_time: float = 0.0

    def _create_app(self) -> FastAPI:
        import os
        static_dir = os.path.join(os.path.dirname(__file__), "static")

        app = FastAPI(title="WTP Simulator API", version="1.0.0")

        @app.get("/health")
        def health():
            return {"status": "ok", "simulator": self.config.name}

        @app.get("/")
        def dashboard():
            dash_path = os.path.join(static_dir, "dashboard.html")
            if os.path.exists(dash_path):
                return FileResponse(dash_path)
            return {"status": "ok", "message": "Dashboard not found"}

        @app.get("/status")
        def status():
            from time import time
            uptime = time() - self.start_time if self.start_time > 0 else 0
            return {
                "simulator": self.config.name,
                "status": "running",
                "plant_id": "WTP-DEMO-01",
                "current_scenario": self.scenario_manager.get_current(),
                "scenario_active_since_s": round(self.sim_loop.state.time_s, 1),
                "total_frames_generated": self.sim_loop.state.step_count,
                "total_measurements_ingested": self.ingest_client.total_ingested,
                "ingestion_errors": self.ingest_client.total_errors,
                "ingestion_status": self.ingest_client.status,
                "uptime_s": round(uptime, 1),
                "signals_count": 92,
                "opcua": {
                    "enabled": bool(getattr(self.config, "opcua_enabled", False)),
                    "running": self.opcua_gateway is not None,
                    "endpoint": getattr(self.config, "opcua_endpoint", None),
                    "namespace": getattr(self.config, "opcua_namespace", None),
                    "node_count": self.opcua_gateway.node_count if self.opcua_gateway else 0,
                },
                "time_s": round(self.sim_loop.state.time_s, 1),
            }

        @app.get("/api/v1/control")
        def get_control():
            return {
                "manipulated_variables": self.actuator_engine.get_status(),
            }

        @app.post("/api/v1/control/{signal_id}")
        def set_control(signal_id: str, req: SetpointRequest):
            if not self.sim_loop.registry.is_mv(signal_id):
                raise HTTPException(422, detail=f"'{signal_id}' is not a manipulated variable")

            cfg = self.sim_loop.registry.get_mv_config(signal_id)
            if cfg and (req.value < cfg.min_sp or req.value > cfg.max_sp):
                raise HTTPException(422, detail=f"Value {req.value} out of range [{cfg.min_sp}, {cfg.max_sp}]")

            actuator = self.actuator_engine.set_setpoint(signal_id, req.value)
            if actuator is None:
                raise HTTPException(404, detail=f"Actuator '{signal_id}' not found")

            return {
                "signal_id": signal_id,
                "old_sp": actuator.setpoint,
                "new_sp": req.value,
                "status": "accepted",
            }

        @app.get("/api/v1/disturbances")
        def get_disturbances():
            return {
                "disturbance_variables": self.disturbance_engine.get_status(),
            }

        @app.post("/api/v1/disturbances/{signal_id}")
        def set_disturbance(signal_id: str, req: DisturbanceOverrideRequest):
            if not self.sim_loop.registry.is_dv(signal_id):
                raise HTTPException(422, detail=f"'{signal_id}' is not a disturbance variable")

            self.disturbance_engine.override(signal_id, req.value)
            return {
                "signal_id": signal_id,
                "value": req.value,
                "override": req.override,
                "status": "accepted",
            }

        @app.delete("/api/v1/disturbances/{signal_id}")
        def release_disturbance(signal_id: str):
            self.disturbance_engine.release_override(signal_id)
            return {"signal_id": signal_id, "status": "released"}

        @app.get("/api/v1/scenarios")
        def list_scenarios():
            return {"scenarios": self.scenario_manager.list_scenarios()}

        @app.get("/api/v1/scenarios/current")
        def current_scenario():
            return {
                "scenario_id": self.scenario_manager.get_current(),
            }

        @app.post("/api/v1/scenarios/{scenario_id}")
        def switch_scenario(scenario_id: str):
            result = self.scenario_manager.switch_scenario(
                scenario_id,
                self.actuator_engine,
                self.disturbance_engine,
            )
            if result.get("status") == "error":
                raise HTTPException(404, detail=result["message"])
            return result

        @app.get("/api/v1/telemetry/latest")
        def telemetry_latest():
            return [
                m.to_dict()
                for m in self.sim_loop.get_latest_measurements()
            ]

        @app.get("/api/v1/telemetry/signal/{signal_id}")
        def telemetry_signal(signal_id: str):
            for measurement in self.sim_loop.get_latest_measurements():
                if measurement.signal_id == signal_id:
                    return measurement.to_dict()
            raise HTTPException(404, detail=f"Signal '{signal_id}' not found")

        return app

    def start(self, host: str | None = None, port: int | None = None) -> None:
        """Start uvicorn server in a background thread."""
        import uvicorn

        host = host or self.config.api_host
        port = port or self.config.api_port

        from time import time
        self.start_time = time()

        config = uvicorn.Config(self.app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        import time as t
        t.sleep(1)  # Give server a moment to start
