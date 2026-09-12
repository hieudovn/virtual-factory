from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

from virtual_factory.ui.api import LEGACY_AUTHORITY_REMOVED_CODE, create_app


def _client() -> TestClient:
    app = create_app(config_path=Path("configs/plants/continuous_mvp_01.yaml"), dt_s=1.0)
    return TestClient(app)


def test_health_returns_ok() -> None:
    client = _client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_dashboard_root_returns_html() -> None:
    client = _client()

    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Virtual Factory" in response.text
    assert "SCADA" in response.text


def test_static_app_js_is_accessible() -> None:
    client = _client()

    response = client.get("/static/app.js")

    assert response.status_code == 200
    assert "filterPub" in response.text


# ═══════════════════════════════════════════════════════════
# VF-vNEXT-R5 — the eager root-dashboard RuntimeService authority is REMOVED.
#
# The experimental MVP-01 continuous dashboard routes remain reachable only as
# FAIL-CLOSED deprecated aliases: HTTP 410, machine-readable payload, and ZERO
# runtime/engine construction (the construction firewall is proven in
# tests/test_vnext_r5_single_system.py). Page routes (/, /health, /static/*) are
# unaffected and the reusable kernel stays available as a library.
# ═══════════════════════════════════════════════════════════

DEAUTHORIZED_DASHBOARD_ROUTES = (
    ("get", "/status", None),
    ("get", "/telemetry/latest", None),
    ("get", "/telemetry/history", {"limit": 2}),
    ("get", "/alarms", None),
    ("post", "/step", {}),
    ("post", "/run-steps", {}),
    ("post", "/start", {}),
    ("post", "/stop", {}),
    ("post", "/reset", {}),
    ("get", "/api/plant-graph", None),
    ("get", "/api/model-types", None),
    ("patch", "/api/pid/PID-1", {}),
    ("post", "/api/fault", {}),
    ("get", "/api/opcua/status", None),
    ("get", "/api/config/current", None),
    ("post", "/api/config/switch", {}),
    ("get", "/api/ui/context/continuous", None),
)


@pytest.mark.parametrize("method,path,body", DEAUTHORIZED_DASHBOARD_ROUTES)
def test_legacy_dashboard_state_routes_are_deauthorized(method, path, body) -> None:
    client = _client()

    request = getattr(client, method)
    if method in ("post", "patch"):
        response = request(path, json=body or {})
    elif body:
        response = request(path, params=body)
    else:
        response = request(path)

    assert response.status_code == 410
    payload = response.json()
    assert payload["code"] == LEGACY_AUTHORITY_REMOVED_CODE
    assert payload["error"] == "legacy_runtime_authority_deauthorized"
    assert payload["surface"] == "root_dashboard_runtime_service"
    assert payload["legacy_runtime_authority"] is False
    assert "/workspaces" in payload["canonical_paths"]
