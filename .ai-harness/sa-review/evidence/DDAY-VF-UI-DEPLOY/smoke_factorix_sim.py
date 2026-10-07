#!/usr/bin/env python3
"""DDAY-VF-UI-DEPLOY — FactoriX Sim smoke."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
_failures: list[str] = []


def _find_src() -> None:
    sys.path.insert(0, str(REPO / "src"))


def claim(condition: bool, description: str) -> None:
    print(f"  [{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        _failures.append(description)


def main() -> int:
    _find_src()
    from fastapi.testclient import TestClient
    from virtual_factory.ui.api import create_app
    from virtual_factory.workspaces.bottled_water import BottledWaterFactory
    from virtual_factory.workspaces.dday_bw_runtime import WORKSPACE_DIR

    demo = (REPO / "src/virtual_factory/ui/static/bottled_water_demo.html").read_text()
    overview = (REPO / "src/virtual_factory/ui/static/bottled_water_overview.html").read_text()
    claim("FACTORIX SIM" in demo and "FactoriX Sim" in demo, "line skin branded FactoriX Sim")
    claim("VIRTUAL FACTORY" not in demo, "line skin no longer shows VIRTUAL FACTORY")
    claim("BW-DEMO-01" in overview and "VIRTUAL FACTORY" in overview, "overview source stays C01-frozen")
    claim("BW-DEMO-01" in demo and "BW-FP" in demo, "internal plant/line IDs unchanged")

    compose = yaml.safe_load((REPO / "deploy/dday-vf-uat.compose.yml").read_text())
    service = compose["services"]["virtual-factory-dday"]
    claim(service["command"][1] == "dday-bw-runtime", "MQTT runtime command unchanged")
    claim(service["environment"]["MQTT_CLIENT_ID"] == "vf-dday-bw-demo-01", "MQTT client-id unchanged")
    claim(service["ports"] == ["127.0.0.1:8090:8090"], "HTTP is loopback-only")
    nginx = (REPO / "deploy/dday-vf-uat.nginx.conf").read_text()
    claim("location /factorix-sim/" in nginx, "nginx exposes /factorix-sim")

    factory = BottledWaterFactory(WORKSPACE_DIR / "line.yaml", WORKSPACE_DIR / "factory.yaml")
    app = create_app(factory_autorun=False, bw_factory=factory, auto_start=False)
    with TestClient(app) as client:
        factory.start()
        factory.step()
        page = client.get("/factorix-sim")
        overview_page = client.get("/factorix-sim/overview")
        health = client.get("/factorix-sim/health").json()
        state = client.get("/factorix-sim/state").json()
        snap = client.get("/factorix-sim/factory").json()
        claim(page.status_code == 200, "GET /factorix-sim")
        claim("FACTORIX SIM" in overview_page.text, "served overview branded FactoriX Sim")
        claim("VIRTUAL FACTORY" not in overview_page.text, "served overview hides VIRTUAL FACTORY")
        claim(health["simulation_owner"] == "dday-bw-runtime", "HTTP observes MQTT factory")
        claim(health["factory_object_id"] == id(factory), "single factory object")
        claim(state["line_id"] == "BW-FP" and len(state["route"]) == 8, "8-station line")
        claim("BW-FP-CAP01" in state["route"], "Capper remains on the line")
        claim("oee" not in str(snap).lower(), "no OEE in FactoriX Sim factory")

    print("SMOKE-DDAY-VF-UI-DEPLOY", "PASS" if not _failures else "FAIL")
    for item in _failures:
        print("  -", item)
    return 0 if not _failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
