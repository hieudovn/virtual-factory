"""FastAPI REST API for VF-2 simulator control and monitoring."""

from __future__ import annotations

import threading
import time
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .config import Vf2Config
from .output.base import OutputAdapter
from .output.memory_output import MemoryOutput
from .simulation_loop import Vf2SimulationLoop


# ======================================================================
# Request models
# ======================================================================


class RunRequest(BaseModel):
    steps: int = 60


# ======================================================================
# Vf2ApiServer
# ======================================================================


class Vf2ApiServer:
    """REST API for VF-2 simulator control and monitoring.

    Args:
        loop: The simulation loop instance.
        output: Output adapter (must support ``get_latest()`` /
            ``get_all()`` for telemetry endpoints).
        config: VF-2 runtime configuration.
    """

    def __init__(
        self,
        loop: Vf2SimulationLoop,
        output: OutputAdapter,
        config: Vf2Config,
    ) -> None:
        self.loop = loop
        self.output = output
        self.config = config
        self.start_time = time.time()
        self._running = False
        self._thread: threading.Thread | None = None
        self._app = self._create_app()

    # ──────────────────────────────────────────────────────────────────
    # App factory
    # ──────────────────────────────────────────────────────────────────

    def _create_app(self) -> FastAPI:
        app = FastAPI(title="VF-2 Simulator API", version="1.0.0")

        @app.get("/health")
        def health():
            return {"status": "ok", "simulator": self.config.name}

        @app.get("/status")
        def status():
            frames = (
                self.output.get_all()  # type: ignore[union-attr]
                if hasattr(self.output, "get_all")
                else []
            )
            return {
                "simulator": self.config.name,
                "package_id": self.loop.pkg.package_id,
                "running": self._running,
                "current_scenario": self.loop.scenario.get_current(),
                "total_frames": self.loop.state.step_count,
                "signal_count": self.loop.sig_reg.signal_count,
                "object_count": self.loop.obj_reg.object_count,
                "uptime_s": round(time.time() - self.start_time, 1),
                "time_s": round(self.loop.state.time_s, 1),
            }

        @app.post("/step")
        def step():
            frame = self.loop.step()
            self.output.write(frame)
            return {"frame": [m.__dict__ for m in frame]}

        @app.post("/run")
        def run_steps(req: RunRequest):
            frames = self.loop.run(req.steps)
            for f in frames:
                self.output.write(f)
            return {
                "frames": len(frames),
                "last": [m.__dict__ for m in frames[-1]],
            }

        @app.get("/scenarios")
        def list_scenarios():
            return {"scenarios": self.loop.scenario.list_scenarios()}

        @app.get("/scenarios/current")
        def current_scenario():
            return {"scenario_id": self.loop.scenario.get_current()}

        @app.post("/scenarios/{scenario_id}")
        def activate_scenario(scenario_id: str):
            result = self.loop.activate_scenario(scenario_id)
            if result.get("status") == "error":
                raise HTTPException(status_code=404, detail=result["message"])
            return result

        @app.get("/telemetry/latest")
        def telemetry_latest():
            if hasattr(self.output, "get_latest"):
                latest = self.output.get_latest()  # type: ignore[union-attr]
                if latest:
                    return [m.__dict__ for m in latest]
            return []

        @app.get("/telemetry/signal/{signal_id}")
        def telemetry_signal(signal_id: str):
            if hasattr(self.output, "get_latest"):
                latest = self.output.get_latest()  # type: ignore[union-attr]
                if latest:
                    for m in latest:
                        if m.signal_id == signal_id:
                            return m.__dict__
            raise HTTPException(
                status_code=404,
                detail=f"Signal '{signal_id}' not found",
            )

        @app.get("/objects")
        def list_objects():
            return {
                "objects": [
                    {
                        "id": o.simulation_object_id,
                        "type": o.object_type.value,
                        "name": o.name,
                    }
                    for o in self.loop.obj_reg.all_objects
                ]
            }

        @app.get("/signals")
        def list_signals():
            signals_list = []
            for sid in self.loop.sig_reg.all_signal_ids:
                s = self.loop.sig_reg.get(sid)
                if s is None:
                    continue
                signals_list.append({
                    "id": s.simulation_signal_id,
                    "type": s.behavior.signal_type.value,
                    "unit": s.engineering_unit,
                })
            return {"signals": signals_list}

        return app

    # ──────────────────────────────────────────────────────────────────
    # Run
    # ──────────────────────────────────────────────────────────────────

    def run(self) -> None:
        """Start the API server (blocking)."""
        self._running = True
        uvicorn.run(
            self._app,
            host=self.config.api_host,
            port=self.config.api_port,
            log_level="info",
        )

    def run_in_thread(self) -> None:
        """Start the API server in a background thread."""
        self._running = True
        self._thread = threading.Thread(target=self.run, daemon=True)
        self._thread.start()
