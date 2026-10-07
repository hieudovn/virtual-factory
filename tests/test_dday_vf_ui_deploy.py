"""DDAY-VF-UI-DEPLOY — FactoriX Sim public skin on the MQTT factory."""

from __future__ import annotations

import time
from pathlib import Path

import pytest
import yaml

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

from virtual_factory.main import build_parser
from virtual_factory.ui.api import create_app
from virtual_factory.workspaces.bottled_water import BottledWaterFactory
from virtual_factory.workspaces.dday_bw_runtime import WORKSPACE_DIR

REPO = Path(__file__).resolve().parent.parent
COMPOSE = REPO / "deploy" / "dday-vf-uat.compose.yml"
NGINX = REPO / "deploy" / "dday-vf-uat.nginx.conf"
DEMO_HTML = REPO / "src" / "virtual_factory" / "ui" / "static" / "bottled_water_demo.html"
OVERVIEW_HTML = REPO / "src" / "virtual_factory" / "ui" / "static" / "bottled_water_overview.html"
FORBIDDEN_KPI = ("oee", "availability", "performance_pct", "quality_pct")


@pytest.fixture()
def factory() -> BottledWaterFactory:
    return BottledWaterFactory(
        WORKSPACE_DIR / "line.yaml",
        WORKSPACE_DIR / "factory.yaml",
    )


@pytest.fixture()
def client(factory: BottledWaterFactory):
    app = create_app(factory_autorun=False, bw_factory=factory, auto_start=False)
    with TestClient(app) as test_client:
        yield test_client


def test_factorix_sim_branding_and_alias_routes(client, factory):
    page = client.get("/factorix-sim")
    assert page.status_code == 200
    assert "FactoriX Sim" in page.text
    assert "FACTORIX SIM" in page.text
    assert "Bottled Water" in page.text
    assert "VIRTUAL FACTORY" not in page.text

    overview = client.get("/factorix-sim/overview")
    assert overview.status_code == 200
    assert "FactoriX Sim" in overview.text
    assert "FACTORIX SIM" in overview.text

    alias = client.get("/bottled-water-demo")
    assert alias.status_code == 200
    assert "FACTORIX SIM" in alias.text
    assert 'href="/bottled-water-demo/overview"' in alias.text


def test_factorix_sim_uses_injected_factory_only(client, factory):
    factory.start()
    factory.step()
    snap = factory.snapshot()
    via_ui = client.get("/factorix-sim/factory").json()
    via_alias = client.get("/bottled-water-demo/factory").json()
    health = client.get("/factorix-sim/health").json()

    assert via_ui["workspace_id"] == "bottled-water-dday"
    assert via_ui["plant_id"] == "BW-DEMO-01"
    assert via_ui["factory"]["simulation_time_s"] == snap["factory"]["simulation_time_s"]
    assert via_alias["factory"]["simulation_time_s"] == snap["factory"]["simulation_time_s"]
    assert health["product"] == "FactoriX Sim"
    assert health["public_route"] == "/factorix-sim"
    assert health["simulation_owner"] == "dday-bw-runtime"
    assert health["single_factory"] is True
    assert health["factory_object_id"] == id(factory)
    assert health["workspace_id"] == "bottled-water-dday"

    before = snap["factory"]["simulation_time_s"]
    time.sleep(0.3)
    later = client.get("/factorix-sim/factory").json()
    assert later["factory"]["simulation_time_s"] == before


def test_factorix_sim_line_has_eight_stations_and_capper(client, factory):
    factory.start()
    factory.step()
    state = client.get("/factorix-sim/state").json()
    assert state["workspace_id"] == "bottled-water-dday"
    assert state["line_id"] == "BW-FP"
    assert len(state["route"]) == 8
    assert "BW-FP-CAP01" in state["route"]
    assert state["route"][3] == "BW-FP-CAP01"


def test_factorix_sim_has_no_kpi_fields(client, factory):
    factory.start()
    factory.step()
    serialised = str(client.get("/factorix-sim/factory").json()).lower()
    for kpi in FORBIDDEN_KPI:
        assert kpi not in serialised


def test_cli_accepts_http_bind_without_renaming_mqtt():
    args = build_parser().parse_args([
        "dday-bw-runtime",
        "--mqtt-host",
        "plantos-emqx",
        "--http-host",
        "127.0.0.1",
        "--http-port",
        "8090",
    ])
    assert args.mqtt_host == "plantos-emqx"
    assert args.http_host == "127.0.0.1"
    assert args.http_port == 8090


def test_compose_http_is_loopback_only():
    compose = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    service = compose["services"]["virtual-factory-dday"]
    assert service["command"][1] == "dday-bw-runtime"
    assert service["environment"]["MQTT_CLIENT_ID"] == "vf-dday-bw-demo-01"
    assert service["environment"]["FACTORIX_SIM_HTTP_HOST"] == "0.0.0.0"
    assert service["ports"] == ["127.0.0.1:8090:8090"]
    assert "1883" not in str(service["ports"])
    nginx = NGINX.read_text(encoding="utf-8")
    assert "location /factorix-sim/" in nginx
    assert "127.0.0.1:8090" in nginx
    assert "1883" not in nginx


def test_skin_files_keep_internal_ids():
    text = DEMO_HTML.read_text(encoding="utf-8") + OVERVIEW_HTML.read_text(encoding="utf-8")
    assert "BW-DEMO-01" in text
    assert "BW-FP" in text
    assert "FACTORIX SIM" in text
