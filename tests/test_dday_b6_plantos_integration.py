"""DDAY-B6 — PlantOS local integration proof + lightweight factory overview.

Governed by .ai-harness/tasks/DDAY-B6.json. The mapper is a view over the
existing autonomous Bottled Water factory. It does not create a second
simulator, duplicate topology/state, or calculate PlantOS-owned KPI.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import re
from pathlib import Path

import pytest
import yaml

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

from virtual_factory.protocols.mqtt_gateway import MqttGateway
from virtual_factory.ui.api import create_app
from virtual_factory.workspaces.bottled_water import (
    FORBIDDEN_KPI_KEYS as FACTORY_KPI,
    HIDDEN_TRUTH_KEYS as FACTORY_HIDDEN,
    BottledWaterFactory,
)
from virtual_factory.workspaces.plantos_export import (
    ACCEPTED_AREAS,
    CONTRACT_VERSION,
    DRILL_DOWN,
    FORBIDDEN_KPI_KEYS,
    HIDDEN_TRUTH_KEYS,
    PLANT_SOURCE_ID,
    RELATIONSHIPS,
    TOPIC_PATTERN,
    TOPIC_PREFIX,
    build_topic,
    load_plantos_mapping,
    map_snapshot,
    overview_from_snapshot,
    publish_via_existing_mqtt,
    resolve_ids,
    selected_signal_keys,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = REPO_ROOT / "configs" / "workspaces" / "bottled-water-dday"
LINE_YAML = WORKSPACE / "line.yaml"
FACTORY_YAML = WORKSPACE / "factory.yaml"
TOPOLOGY_YAML = WORKSPACE / "topology.yaml"
STATIC = REPO_ROOT / "src" / "virtual_factory" / "ui" / "static"
APP_CONFIG = REPO_ROOT / "configs" / "plants" / "continuous_mvp_01.yaml"
# Content identity of generic protocol/telemetry files at the SA-closed B5
# head. CI checkouts are shallow and do not contain that commit object, so
# tests compare SHA-256 rather than `git diff`.
FROZEN_PROTOCOL_HASHES = {
    "src/virtual_factory/protocols/mqtt_gateway.py":
        "f540ef429dbcedfef4baeddbe2f5c41c152d547f057a4a3d93762c6406414872",
    "src/virtual_factory/telemetry/signal_value.py":
        "67fb1387495cecc3e9b9f39954166d01bdec2738f3d18331f74d79811fd1c009",
}

TOPIC_RE = re.compile(
    r"^virtual-factory/bottled-water-dday/(signal|event)/[A-Z0-9-]+/[A-Za-z0-9_]+$"
)


def _factory(**kwargs) -> BottledWaterFactory:
    return BottledWaterFactory(LINE_YAML, FACTORY_YAML, **kwargs)


def _run(factory: BottledWaterFactory, steps: int, dt: float = 1.0) -> None:
    for _ in range(steps):
        factory.step(dt)


def _walk_keys(value, keys: set[str]) -> None:
    if isinstance(value, dict):
        for key, inner in value.items():
            keys.add(str(key))
            _walk_keys(inner, keys)
    elif isinstance(value, list):
        for inner in value:
            _walk_keys(inner, keys)


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.delenv("BOTTLED_WATER_CONFIG", raising=False)
    monkeypatch.delenv("BOTTLED_WATER_FACTORY_CONFIG", raising=False)
    app = create_app(config_path=APP_CONFIG, dt_s=1.0, factory_autorun=False)
    with TestClient(app) as test_client:
        test_client.post("/bottled-water-demo/reset")
        yield test_client


def test_b6_01_mapped_topics_and_payloads_match_b1_contract():
    factory = _factory()
    factory.start()
    _run(factory, 8)
    snapshot = factory.snapshot()
    messages = map_snapshot(snapshot)
    assert messages
    assert any(message.kind == "signal" for message in messages)
    for message in messages:
        assert TOPIC_RE.match(message.topic), message.topic
        assert message.topic == build_topic(
            message.kind, message.asset_id, message.signal_or_event
        )
        payload = message.payload
        assert payload["contract_version"] == CONTRACT_VERSION
        assert payload["workspace_id"] == "bottled-water-dday"
        assert payload["plant_source_id"] == snapshot["plant_id"] == PLANT_SOURCE_ID
        assert payload["source_id"] == message.asset_id
        assert payload["asset_id"] == message.asset_id
        assert payload.get("provenance") == "SIMULATED_RAW"
        assert payload["timestamp"].endswith("Z")
        assert "T" in payload["timestamp"]
        assert "timestamp_s" not in payload
        assert "simulation_time_s" in payload
        if message.kind == "signal":
            assert payload["signal_id"] == message.signal_or_event
            assert "value" in payload
            assert "unit" in payload
            assert payload.get("quality") == "GOOD"
        else:
            assert payload["event_type"] == message.signal_or_event
    assert TOPIC_PATTERN.startswith(TOPIC_PREFIX)


def test_b6_02_published_ids_resolve_against_frozen_plantos_mapping():
    factory = _factory()
    factory.start()
    _run(factory, 4)
    snapshot = factory.snapshot()
    mapping = load_plantos_mapping(TOPOLOGY_YAML)
    topology = yaml.safe_load(TOPOLOGY_YAML.read_text(encoding="utf-8"))
    assert mapping["areas"] == list(ACCEPTED_AREAS)
    assert mapping["plant"] == topology["plant"]["id"] == snapshot["plant_id"]
    assert mapping["line_mapping"]["vf_id"] == "BW-FP"
    assert mapping["line_mapping"]["plantos_entity"] == "Area"
    resolution = resolve_ids(map_snapshot(snapshot), snapshot, mapping)
    assert resolution["resolved"] is True
    assert resolution["unresolved_ids"] == []
    assert resolution["areas_match_contract"] is True
    hierarchy_ids = {node["source_id"] for node in snapshot["hierarchy"]}
    for asset_id in resolution["published_ids"]:
        assert asset_id in hierarchy_ids


def test_b6_03_current_values_equal_factory_snapshot():
    factory = _factory()
    factory.start()
    _run(factory, 12)
    snapshot = factory.snapshot()
    bundle = factory.plantos_export()
    by_key = {
        (item["asset_id"], item["signal_or_event"]): item["payload"]["value"]
        for item in bundle["current_values"]
    }
    compared = 0
    for asset_id, signal_id in selected_signal_keys():
        signal = snapshot["nodes"][asset_id]["signals"][signal_id]
        assert by_key[(asset_id, signal_id)] == signal["value"]
        compared += 1
    assert compared >= 12
    assert bundle["simulation_time_s"] == snapshot["factory"]["simulation_time_s"]
    exported = {(item["asset_id"], item["signal_or_event"]) for item in bundle["current_values"]}
    assert exported <= set(selected_signal_keys())


def test_b6_04_historian_retains_timestamped_samples():
    factory = _factory()
    factory.start()
    _run(factory, 6)
    first = factory.plantos_export()
    assert first["message_count"] > 0
    first_times = {
        item["payload"]["simulation_time_s"]
        for item in first["historian"]
        if item["kind"] == "signal"
    }
    first_utc = {
        item["payload"]["timestamp"]
        for item in first["historian"]
        if item["kind"] == "signal"
    }
    _run(factory, 6)
    second = factory.plantos_export()
    second_times = {
        item["payload"]["simulation_time_s"]
        for item in second["historian"]
        if item["kind"] == "signal"
    }
    second_utc = {
        item["payload"]["timestamp"]
        for item in second["historian"]
        if item["kind"] == "signal"
    }
    assert second["message_count"] > first["message_count"]
    assert len(second_times) >= 2
    assert first_times
    assert max(second_times) > min(first_times)
    assert first_utc
    assert max(second_utc) > min(first_utc)
    for item in second["historian"]:
        assert item["payload"]["timestamp"].endswith("Z")
        assert "timestamp_s" not in item["payload"]


def test_b6_05_events_include_downtime_alarm_and_phase():
    factory = _factory()
    factory.start()
    _run(factory, 130)
    events = factory.plantos_export()["events"]
    types = {item["payload"]["event_type"] for item in events}
    assert "MACHINE_STATE_CHANGED" in types
    assert "SCENARIO_PHASE_CHANGED" in types
    assert "DOWNTIME_START" in types or "ALARM_RAISED" in types
    for item in events:
        assert item["kind"] == "event"
        assert item["topic"].startswith(f"{TOPIC_PREFIX}/event/")


def test_b6_06_no_kpi_or_hidden_truth_in_export_or_overview():
    assert HIDDEN_TRUTH_KEYS == FACTORY_HIDDEN
    assert FORBIDDEN_KPI_KEYS == FACTORY_KPI
    factory = _factory()
    factory.start()
    _run(factory, 40)
    bundle = factory.plantos_export()
    overview = overview_from_snapshot(factory.snapshot())
    serialised = json.dumps({"export": bundle, "overview": overview}).lower()
    for hidden in HIDDEN_TRUTH_KEYS:
        assert hidden.lower() not in serialised
    for kpi in FORBIDDEN_KPI_KEYS:
        assert kpi.lower() not in serialised
    keys: set[str] = set()
    _walk_keys(bundle, keys)
    _walk_keys(overview, keys)
    for hidden in HIDDEN_TRUTH_KEYS:
        assert hidden not in keys


def test_b6_07_mapper_is_a_view_not_a_second_simulator():
    source = Path(
        "src/virtual_factory/workspaces/plantos_export.py"
    )
    text = (REPO_ROOT / source).read_text(encoding="utf-8")
    assert "class BottledWaterFactory" not in text
    assert "DemoController" not in text
    assert "step(" not in inspect.getsource(map_snapshot)
    factory = _factory()
    factory.start()
    _run(factory, 5)
    left = map_snapshot(factory.snapshot())
    right = map_snapshot(factory.snapshot())
    assert [item.as_dict() for item in left] == [item.as_dict() for item in right]
    # One runtime: factory snapshot and line projection stay the same object family.
    snap = factory.snapshot()
    assert snap["target_line"]["counts"]["total"] == factory.controller.line.total_count


def test_b6_08_existing_mqtt_gateway_unchanged_and_can_carry_payload():
    for rel, expected in FROZEN_PROTOCOL_HASHES.items():
        digest = hashlib.sha256((REPO_ROOT / rel).read_bytes()).hexdigest()
        assert digest == expected, f"{rel} changed vs B5-closed content"

    factory = _factory()
    factory.start()
    _run(factory, 2)
    messages = [item for item in map_snapshot(factory.snapshot()) if item.kind == "signal"]
    recorded = []

    class _Fake:
        def publish(self, topic, payload, qos=0, retain=False):
            recorded.append((topic, payload, qos, retain))
            return type("Result", (), {"rc": 0})()

    gateway = MqttGateway(enabled=True, client=_Fake())
    published = publish_via_existing_mqtt(gateway, messages[:3])
    assert published == 3
    assert recorded[0][0].startswith(f"{TOPIC_PREFIX}/signal/")
    payload = json.loads(recorded[0][1])
    assert payload["workspace_id"] == "bottled-water-dday"
    assert inspect.getsource(MqttGateway.build_topic)


def test_b6_09_overview_shows_five_accepted_areas(client):
    page = (STATIC / "bottled_water_overview.html").read_text(encoding="utf-8")
    for area_id in ACCEPTED_AREAS:
        assert f'data-area="{area_id}"' in page
        assert f"area-{area_id}" in page
    html = client.get("/bottled-water-demo/overview")
    assert html.status_code == 200
    body = html.text
    for area_id in ACCEPTED_AREAS:
        assert area_id in body
    factory = client.get("/bottled-water-demo/factory").json()
    overview = overview_from_snapshot(factory)
    assert [area["id"] for area in overview["areas"]] == list(ACCEPTED_AREAS)


def test_b6_10_overview_shows_process_and_utility_relationships(client):
    page = (STATIC / "bottled_water_overview.html").read_text(encoding="utf-8")
    for item in RELATIONSHIPS:
        assert f'data-from="{item["from_area"]}"' in page
        assert f'data-to="{item["to_area"]}"' in page
        assert f'data-kind="{item["kind"]}"' in page
        assert item["label"] in page
    kinds = {item["kind"] for item in RELATIONSHIPS}
    assert kinds == {"process", "utility"}
    export = client.get("/bottled-water-demo/plantos-export").json()
    assert export["overview"]["relationships"] == [dict(item) for item in RELATIONSHIPS]


def test_b6_11_overview_raw_values_bind_to_factory_snapshot(client):
    client.post("/bottled-water-demo/start")
    for _ in range(8):
        client.post("/bottled-water-demo/advance")
    factory = client.get("/bottled-water-demo/factory").json()
    overview = overview_from_snapshot(factory)
    by_id = {area["id"]: area for area in overview["areas"]}
    assert by_id["BW-FP"]["raw_values"]["total_count"] == factory["nodes"]["BW-FP"]["signals"]["total_count"]["value"]
    assert by_id["BW-WT"]["raw_values"]["tank_level_pct"] == factory["balances"]["water"]["tank_level_pct"]
    assert by_id["BW-UT"]["raw_values"]["air_pressure_bar"] == factory["nodes"]["BW-UT-CMP01"]["signals"]["air_pressure"]["value"]
    assert by_id["BW-WH"]["raw_values"]["inventory_count"] == factory["balances"]["finished_goods"]["inventory_count"]
    js = (STATIC / "bottled_water_overview.js").read_text(encoding="utf-8")
    assert "ovFetch('/factory')" in js or 'ovFetch("/factory")' in js
    assert "/factory" in js


def test_b6_12_area_abnormal_uses_public_phase_not_health_score(client):
    client.post("/bottled-water-demo/start")
    for _ in range(8):
        client.post("/bottled-water-demo/advance")
    factory = client.get("/bottled-water-demo/factory").json()
    overview = overview_from_snapshot(factory)
    by_id = {area["id"]: area for area in overview["areas"]}
    assert by_id["BW-FP"]["abnormal"]["source"] == "capper_phase"
    assert by_id["BW-FP"]["abnormal"]["phase"] == factory["scenario"]["phase"]
    assert by_id["BW-UT"]["abnormal"]["source"] == "compressor_phase"
    assert by_id["BW-UT"]["abnormal"]["phase"] == factory["compressor_scenario"]["phase"]
    js = (STATIC / "bottled_water_overview.js").read_text(encoding="utf-8")
    assert "health_score" not in js
    assert "oee" not in js.lower()
    assert "scenario" in js
    assert "compressor_scenario" in js


def test_b6_13_bw_fp_drills_down_to_existing_filling_packaging_ui(client):
    page = (STATIC / "bottled_water_overview.html").read_text(encoding="utf-8")
    assert 'id="ov-fp-drilldown"' in page
    assert 'href="/bottled-water-demo"' in page
    assert DRILL_DOWN == {"BW-FP": "/bottled-water-demo"}
    detail = client.get("/bottled-water-demo")
    assert detail.status_code == 200
    assert "Filling" in detail.text
    assert "bw-svg" in detail.text
    skin = (STATIC / "bottled_water_demo.html").read_text(encoding="utf-8")
    assert 'href="/bottled-water-demo/overview"' in skin
    overview = client.get("/bottled-water-demo/overview")
    assert overview.status_code == 200
    assert "/bottled-water-demo" in overview.text


def test_b6_15_protocols_and_telemetry_unchanged_vs_b5_closed_head():
    for rel, expected in FROZEN_PROTOCOL_HASHES.items():
        digest = hashlib.sha256((REPO_ROOT / rel).read_bytes()).hexdigest()
        assert digest == expected, f"{rel} changed vs B5-closed content"
