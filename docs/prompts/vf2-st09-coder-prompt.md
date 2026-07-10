# Prompt for Coder — VF-2 ST09: CLI & API Server

> **Parent:** VF-2 PIM-native Simulation Runtime  
> **Task:** VF2-ST09 — CLI & API Server (FINAL STEP)  
> **Prerequisite:** ST01-ST08 completed (full simulator running)

---

## Context

ST09 makes VF-2 usable — a command-line interface to run simulations, and a FastAPI server to interact with the running simulator. This is the final coding task for VF-2 MVP.

---

## What You're Building

### 1. `main.py` — CLI entry point

```bash
# Validate a package
python -m simulators.vf2.main --package path/to/package.json --validate-only

# Run dry simulation
python -m simulators.vf2.main --package path/to/package.json --steps 60

# Run with CSV output
python -m simulators.vf2.main --package path/to/package.json --steps 60 --output csv --output-path ./out/result.csv

# Run with scenario
python -m simulators.vf2.main --package path/to/package.json --scenario SCN-PUMP-TRIP-002 --steps 120

# Start API server
python -m simulators.vf2.main --package path/to/package.json --api-server --port 8102
```

```python
import argparse
from pathlib import Path
from .package_loader import load_package
from .package_validator import validate_package
from .simulation_loop import Vf2SimulationLoop
from .config import load_config, Vf2Config
from .output.memory_output import MemoryOutput
from .output.csv_output import CsvOutput
from .output.stdout_output import StdoutOutput

def main():
    parser = argparse.ArgumentParser(prog="vf2-sim", description="VF-2 PIM-native Simulator")
    parser.add_argument("--package", required=True)
    parser.add_argument("--config", default=None)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--steps", type=int, default=0)
    parser.add_argument("--scenario", default=None)
    parser.add_argument("--output", choices=["memory","csv","stdout"], default="memory")
    parser.add_argument("--output-path", default="./out/vf2_output.csv")
    parser.add_argument("--api-server", action="store_true")
    parser.add_argument("--port", type=int, default=8102)
    args = parser.parse_args()
    
    config = load_config(args.config)
    if args.port: config.api_port = args.port
    
    # Load & validate
    pkg = load_package(args.package)
    result = validate_package(pkg)
    if result.errors:
        print("Validation errors:")
        for e in result.errors: print(f"  ERROR: {e}")
        if not args.validate_only: return 1
    for w in result.warnings: print(f"  WARNING: {w}")
    if args.validate_only:
        print("Validation OK" if result.valid else "Validation FAILED")
        return 0 if result.valid else 1
    
    # Create simulator
    loop = Vf2SimulationLoop(pkg, config)
    
    # Setup output
    if args.output == "csv":
        output = CsvOutput(args.output_path)
    elif args.output == "stdout":
        output = StdoutOutput()
    else:
        output = MemoryOutput(config.max_frames_buffer)
    
    # Activate scenario if specified
    if args.scenario:
        loop.activate_scenario(args.scenario)
    
    # API server mode
    if args.api_server:
        from .api_server import Vf2ApiServer
        server = Vf2ApiServer(loop, output, config)
        server.run()
        return 0
    
    # Batch run mode
    frames = loop.run(args.steps, config.interval_s)
    for frame in frames:
        output.write(frame)
    output.close()
    print(f"Done. {args.steps} steps, {len(frames)} frames.")
```

### 2. `api_server.py` — FastAPI REST API

```python
from fastapi import FastAPI, HTTPException
import uvicorn, threading, time
from pydantic import BaseModel

class Vf2ApiServer:
    """REST API for VF-2 simulator control and monitoring."""
    
    def __init__(self, loop, output, config):
        self.loop = loop
        self.output = output
        self.config = config
        self.start_time = time.time()
        self._running = False
        self._thread = None
    
    def _create_app(self):
        app = FastAPI(title="VF-2 Simulator API", version="1.0.0")
        
        @app.get("/health")
        def health():
            return {"status": "ok", "simulator": self.config.name}
        
        @app.get("/status")
        def status():
            frames = self.output.get_all() if hasattr(self.output, 'get_all') else []
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
        def run_steps(steps: int = 60):
            frames = self.loop.run(steps)
            for f in frames: self.output.write(f)
            return {"frames": len(frames), "last": [m.__dict__ for m in frames[-1]]}
        
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
                raise HTTPException(404, result["message"])
            return result
        
        @app.get("/telemetry/latest")
        def telemetry_latest():
            if hasattr(self.output, 'get_latest'):
                latest = self.output.get_latest()
                if latest: return [m.__dict__ for m in latest]
            return []
        
        @app.get("/telemetry/signal/{signal_id}")
        def telemetry_signal(signal_id: str):
            if hasattr(self.output, 'get_latest'):
                latest = self.output.get_latest()
                if latest:
                    for m in latest:
                        if m.signal_id == signal_id:
                            return m.__dict__
            raise HTTPException(404, f"Signal '{signal_id}' not found")
        
        @app.get("/objects")
        def list_objects():
            return {"objects": [{"id": o.simulation_object_id, "type": o.object_type.value, "name": o.name} for o in self.loop.obj_reg.all_objects]}
        
        @app.get("/signals")
        def list_signals():
            return {"signals": [{"id": s.simulation_signal_id, "type": s.behavior.signal_type.value, "unit": s.engineering_unit} for s in self.loop.sig_reg._by_id.values()]}
        
        return app
    
    def run(self):
        self._running = True
        app = self._create_app()
        uvicorn.run(app, host=self.config.api_host, port=self.config.api_port, log_level="info")
```

### 3. `tests/test_api_server.py` (optional, lightweight)

```python
from fastapi.testclient import TestClient

class TestApiServer:
    def test_health(self):
        pkg = load_package(GOLDEN)
        loop = Vf2SimulationLoop(pkg)
        out = MemoryOutput()
        server = Vf2ApiServer(loop, out, Vf2Config())
        client = TestClient(server._create_app())
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
    
    def test_status(self):
        ...
        r = client.get("/status")
        assert r.json()["signal_count"] == 4
    
    def test_scenarios_list(self):
        ...
        r = client.get("/scenarios")
        assert len(r.json()["scenarios"]) == 6
    
    def test_step(self):
        ...
        r = client.post("/step")
        assert len(r.json()["frame"]) == 4
```

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC-1 | `--validate-only` loads + validates, exits with proper code |
| AC-2 | `--steps 60 --output csv` writes valid CSV with 61 lines |
| AC-3 | `--scenario SCN-PUMP-TRIP-002 --steps 60` activates scenario |
| AC-4 | `--api-server` starts FastAPI on port 8102 |
| AC-5 | `GET /health` returns `{"status":"ok"}` |
| AC-6 | `GET /status` returns signal_count=4, object_count=8 |
| AC-7 | `POST /step` returns 4 measurements |
| AC-8 | `POST /scenarios/SCN-PUMP-TRIP-002` returns transition status |
| AC-9 | `GET /telemetry/latest` returns current frame |
| AC-10 | All tests pass + VF-1 OK |
