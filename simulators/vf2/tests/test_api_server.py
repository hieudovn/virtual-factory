"""Tests for VF-2 API server (ST09)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from simulators.vf2.api_server import Vf2ApiServer
from simulators.vf2.config import Vf2Config
from simulators.vf2.output.memory_output import MemoryOutput
from simulators.vf2.package_loader import load_package
from simulators.vf2.simulation_loop import Vf2SimulationLoop

GOLDEN = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "simulators" / "vf2" / "examples"
    / "sample_pim_package.json"
)


@pytest.fixture(scope="module")
def client():
    pkg = load_package(GOLDEN)
    loop = Vf2SimulationLoop(pkg)
    out = MemoryOutput()
    server = Vf2ApiServer(loop, out, Vf2Config())
    app = server._create_app()
    return TestClient(app)


class TestApiServer:

    # AC-5
    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    # AC-6
    def test_status(self, client):
        r = client.get("/status")
        data = r.json()
        assert r.status_code == 200
        assert data["signal_count"] == 4
        assert data["object_count"] == 8

    # AC-7
    def test_step(self, client):
        r = client.post("/step")
        assert r.status_code == 200
        data = r.json()
        assert "frame" in data
        assert len(data["frame"]) == 4

    def test_step_contains_expected_signals(self, client):
        r = client.post("/step")
        data = r.json()
        signal_ids = {m["signal_id"] for m in data["frame"]}
        assert "VF2.PUMP_STATION_01.FT_101.DISCHARGE_FLOW_TRANSMITTER" in signal_ids
        assert "VF2.PUMP_STATION_01.PT_101.DISCHARGE_PRESSURE_TRANSMITTER" in signal_ids
        assert "VF2.PUMP_STATION_01.LT_101.SUCTION_LEVEL_TRANSMITTER" in signal_ids
        assert "VF2.PUMP_STATION_01.VB_101.PUMP_A_VIBRATION_SENSOR" in signal_ids

    def test_run(self, client):
        r = client.post("/run", json={"steps": 10})
        assert r.status_code == 200
        data = r.json()
        assert data["frames"] == 10
        assert len(data["last"]) == 4

    # AC-8
    def test_activate_scenario(self, client):
        r = client.post("/scenarios/SCN-PUMP-TRIP-002")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "transitioning"
        assert data["to_scenario"] == "SCN-PUMP-TRIP-002"

    def test_activate_nonexistent_scenario_404(self, client):
        r = client.post("/scenarios/NONEXISTENT")
        assert r.status_code == 404

    def test_list_scenarios(self, client):
        r = client.get("/scenarios")
        assert r.status_code == 200
        data = r.json()
        assert len(data["scenarios"]) == 6

    def test_current_scenario(self, client):
        r = client.get("/scenarios/current")
        assert r.status_code == 200

    # AC-9
    def test_telemetry_latest(self, client):
        # Run a step first
        client.post("/step")
        r = client.get("/telemetry/latest")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 4

    def test_telemetry_signal_found(self, client):
        client.post("/step")
        r = client.get(
            "/telemetry/signal/VF2.PUMP_STATION_01.FT_101.DISCHARGE_FLOW_TRANSMITTER"
        )
        assert r.status_code == 200
        data = r.json()
        assert data["signal_id"] == (
            "VF2.PUMP_STATION_01.FT_101.DISCHARGE_FLOW_TRANSMITTER"
        )

    def test_telemetry_signal_not_found(self, client):
        r = client.get("/telemetry/signal/NONEXISTENT")
        assert r.status_code == 404

    def test_objects(self, client):
        r = client.get("/objects")
        assert r.status_code == 200
        data = r.json()
        assert len(data["objects"]) == 8

    def test_signals(self, client):
        r = client.get("/signals")
        assert r.status_code == 200
        data = r.json()
        assert len(data["signals"]) == 4
