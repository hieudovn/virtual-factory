from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

from virtual_factory.ui.api import create_app


def _client() -> TestClient:
    app = create_app(config_path=Path("configs/plants/continuous_mvp_01.yaml"), dt_s=1.0)
    return TestClient(app)


def _assert_no_internal_truth(payload) -> None:
    if isinstance(payload, list):
        assert all(item.get("category") != "internal_truth" for item in payload if isinstance(item, dict))
        assert all(item.get("name") != "T102_LEVEL_TRUE" for item in payload if isinstance(item, dict))
    elif isinstance(payload, dict):
        assert payload.get("category") != "internal_truth"
        assert payload.get("name") != "T102_LEVEL_TRUE"


def test_health_returns_ok() -> None:
    client = _client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_dashboard_root_returns_html() -> None:
    client = _client()

    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Virtual Factory Monitoring Dashboard" in response.text


def test_static_app_js_is_accessible() -> None:
    client = _client()

    response = client.get("/static/app.js")

    assert response.status_code == 200
    assert "filterPublishable" in response.text


def test_status_returns_service_status_without_truth() -> None:
    client = _client()

    response = client.get("/status")
    payload = response.json()

    assert response.status_code == 200
    assert payload["status"] == "stopped"
    assert payload["running"] is False
    assert payload["mqtt_enabled"] is False
    assert payload["plant_id"] == "continuous_mvp_01"
    assert "truth" not in payload


def test_start_and_stop_update_running_status() -> None:
    client = _client()

    start_response = client.post("/start")
    stop_response = client.post("/stop")

    assert start_response.status_code == 200
    assert start_response.json()["running"] is True
    assert stop_response.status_code == 200
    assert stop_response.json()["running"] is False


def test_step_returns_publishable_telemetry() -> None:
    client = _client()

    response = client.post("/step")
    payload = response.json()

    assert response.status_code == 200
    assert isinstance(payload, list)
    assert payload
    _assert_no_internal_truth(payload)


def test_latest_returns_publishable_signals() -> None:
    client = _client()

    response = client.get("/telemetry/latest")
    payload = response.json()
    names = {item["name"] for item in payload}

    assert response.status_code == 200
    assert "LT102_LEVEL" in names
    assert "T102_LEVEL_TRUE" not in names
    _assert_no_internal_truth(payload)


def test_alarms_returns_industrial_events_after_step() -> None:
    client = _client()

    client.post("/step")
    response = client.get("/alarms")
    payload = response.json()

    assert response.status_code == 200
    assert payload
    assert all(item["category"] == "industrial_event" for item in payload)
    _assert_no_internal_truth(payload)


def test_history_excludes_internal_truth() -> None:
    client = _client()

    client.post("/run-steps", params={"n": 3})
    response = client.get("/telemetry/history", params={"limit": 2})
    payload = response.json()

    assert response.status_code == 200
    assert payload
    _assert_no_internal_truth(payload)
