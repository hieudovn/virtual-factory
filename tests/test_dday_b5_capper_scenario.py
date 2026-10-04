"""DDAY-B5 — Capper deterministic abnormal scenario tests.

Governed by .ai-harness/tasks/DDAY-B5.json (authored from SA Issue #107).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

from virtual_factory.ui.api import create_app
from virtual_factory.workspaces.bottled_water import (
    FORBIDDEN_KPI_KEYS,
    HIDDEN_TRUTH_KEYS,
    BottledWaterFactory,
)
from virtual_factory.workspaces.capper_degradation import PHASES

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = REPO_ROOT / "configs" / "workspaces" / "bottled-water-dday"
LINE_YAML = WORKSPACE / "line.yaml"
FACTORY_YAML = WORKSPACE / "factory.yaml"
STATIC = REPO_ROOT / "src" / "virtual_factory" / "ui" / "static"
APP_CONFIG = REPO_ROOT / "configs" / "plants" / "continuous_mvp_01.yaml"
CAP = "BW-FP-CAP01"


def _factory() -> BottledWaterFactory:
    return BottledWaterFactory(LINE_YAML, FACTORY_YAML)


def _run(factory: BottledWaterFactory, steps: int, dt: float = 1.0) -> None:
    for _ in range(steps):
        factory.step(dt)


def _signal(snapshot: dict, node_id: str, signal_id: str):
    return snapshot["nodes"][node_id]["signals"][signal_id]["value"]


def _digest(payload) -> str:
    import hashlib

    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def _walk_keys(node, acc: set[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            acc.add(str(key).lower())
            _walk_keys(value, acc)
    elif isinstance(node, list):
        for item in node:
            _walk_keys(item, acc)


def _event_types(snapshot: dict, source_id: str | None = None) -> list[str]:
    events = snapshot["recent_events"]
    if source_id is not None:
        events = [event for event in events if event.get("source_id") == source_id]
    return [event["event_type"] for event in events]


def _run_to_phase(factory: BottledWaterFactory, phase: str, limit: int = 400) -> dict:
    factory.start()
    snapshot = factory.snapshot()
    if snapshot["scenario"]["phase"] == phase:
        return snapshot
    for _ in range(limit):
        factory.step(1.0)
        snapshot = factory.snapshot()
        if snapshot["scenario"]["phase"] == phase:
            return snapshot
    raise AssertionError(f"did not reach {phase} within {limit}s")


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.delenv("BOTTLED_WATER_CONFIG", raising=False)
    monkeypatch.delenv("BOTTLED_WATER_FACTORY_CONFIG", raising=False)
    app = create_app(config_path=APP_CONFIG, dt_s=1.0, factory_autorun=False)
    with TestClient(app) as test_client:
        test_client.post("/bottled-water-demo/reset")
        yield test_client


def test_b5_01_and_10_reset_replays_the_same_trace():
    traces = []
    for _ in range(2):
        factory = _factory()
        factory.start()
        _run(factory, 180)
        traces.append((
            [event["event_type"] for event in factory.snapshot()["recent_events"]],
            factory.snapshot()["scenario"]["phase"],
            _signal(factory.snapshot(), CAP, "vibration_rms"),
            _digest(factory.snapshot()),
        ))
    assert traces[0] == traces[1]

    factory = _factory()
    factory.start()
    _run(factory, 180)
    after = factory.snapshot()
    factory.reset()
    fresh = _factory().snapshot()
    assert factory.snapshot()["scenario"]["phase"] == "NORMAL"
    assert _digest(factory.snapshot()) == _digest(fresh)
    assert after["scenario"]["phase"] != "NORMAL"


def test_b5_02_phase_order_is_exactly_the_b1_contract():
    factory = _factory()
    factory.start()
    seen = [factory.snapshot()["scenario"]["phase"]]
    for _ in range(220):
        factory.step(1.0)
        phase = factory.snapshot()["scenario"]["phase"]
        if phase != seen[-1]:
            seen.append(phase)
    assert tuple(seen) == PHASES


def test_b5_03_condition_signals_move_causally_by_phase():
    factory = _factory()
    samples = {}
    factory.start()
    samples["NORMAL"] = factory.snapshot()
    for phase in PHASES[1:]:
        samples[phase] = _run_to_phase(factory, phase)

    def vib(phase: str) -> float:
        return _signal(samples[phase], CAP, "vibration_rms")

    def current(phase: str) -> float:
        return _signal(samples[phase], CAP, "motor_current")

    def load(phase: str) -> float:
        return _signal(samples[phase], CAP, "drive_load")

    assert vib("NORMAL") < vib("DEGRADING") < vib("WARNING") < vib(
        "INTERMITTENT_STOP")
    assert current("NORMAL") < current("DEGRADING") < current("WARNING")
    assert load("NORMAL") < load("WARNING")
    assert _signal(samples["RECOVERY"], CAP, "speed") > _signal(
        samples["INTERMITTENT_STOP"], CAP, "speed")
    assert _signal(samples["WARNING"], CAP, "cycle_time") > _signal(
        samples["NORMAL"], CAP, "cycle_time")


def test_b5_04_temperature_lags_primary_indicators():
    factory = _factory()
    factory.start()
    _run(factory, 101)
    before = factory.snapshot()
    factory.step(1.0)
    after = factory.snapshot()
    assert before["scenario"]["phase"] == "NORMAL"
    assert after["scenario"]["phase"] == "DEGRADING"
    dv = _signal(after, CAP, "vibration_rms") - _signal(before, CAP, "vibration_rms")
    dt = _signal(after, CAP, "bearing_temperature") - _signal(
        before, CAP, "bearing_temperature")
    assert dv > 0.0
    assert dt >= 0.0
    assert dt < dv
    # Temperature stays below the instantaneous vibration-implied span.
    assert _signal(after, CAP, "bearing_temperature") < 45.0


def test_b5_05_and_06_alarm_and_downtime_pair_once():
    factory = _factory()
    factory.start()
    _run(factory, 220)
    types = _event_types(factory.snapshot(), CAP)
    assert types.count("ALARM_RAISED") == 1
    assert types.count("ALARM_CLEARED") == 1
    assert types.count("DOWNTIME_START") == 1
    assert types.count("DOWNTIME_END") == 1
    assert types.index("ALARM_RAISED") < types.index("DOWNTIME_START")
    assert types.index("DOWNTIME_START") < types.index("DOWNTIME_END")
    assert types.index("ALARM_CLEARED") > types.index("ALARM_RAISED")
    phases = [
        event["detail"] for event in factory.snapshot()["recent_events"]
        if event["event_type"] == "SCENARIO_PHASE_CHANGED"
        and event.get("source_id") == CAP
    ]
    assert phases == [f"phase={name}" for name in PHASES]


def test_b5_07_and_08_production_and_fg_follow_actual_output():
    factory = _factory()
    factory.start()
    _run_to_phase(factory, "WARNING")
    before_stop = factory.snapshot()
    _run_to_phase(factory, "INTERMITTENT_STOP")
    during = factory.snapshot()
    _run(factory, 19)
    held = factory.snapshot()
    assert held["scenario"]["phase"] == "INTERMITTENT_STOP"
    assert held["target_line"]["counts"]["total"] == during["target_line"][
        "counts"]["total"]
    _run_to_phase(factory, "RECOVERY")
    _run(factory, 40)
    recovered = factory.snapshot()
    assert recovered["target_line"]["counts"]["total"] > held["target_line"][
        "counts"]["total"]
    goods = recovered["balances"]["finished_goods"]
    assert goods["receipt_count"] == recovered["target_line"]["counts"]["good"]
    assert goods["inventory_count"] == goods["receipt_count"] - goods[
        "dispatch_count"]
    assert before_stop["target_line"]["counts"]["total"] >= 5


def test_b5_09_pause_freezes_scenario_time():
    factory = _factory()
    factory.start()
    _run_to_phase(factory, "DEGRADING")
    factory.pause()
    paused = factory.snapshot()
    _run(factory, 40)
    held = factory.snapshot()
    assert held["scenario"]["phase"] == paused["scenario"]["phase"] == "DEGRADING"
    assert held["factory"]["simulation_time_s"] == paused["factory"][
        "simulation_time_s"]
    assert _signal(held, CAP, "vibration_rms") == _signal(
        paused, CAP, "vibration_rms")
    factory.resume()
    _run(factory, 24)
    assert factory.snapshot()["scenario"]["phase"] in (
        "DEGRADING", "WARNING", "INTERMITTENT_STOP")


def test_b5_11_operator_stop_is_not_a_scenario_fault():
    factory = _factory()
    factory.start()
    _run_to_phase(factory, "INTERMITTENT_STOP")
    assert _signal(factory.snapshot(), CAP, "operating_state") == "FAULT"
    factory.stop()
    _run(factory, 10)
    after = factory.snapshot()
    assert after["factory"]["run_state"] == "STOPPED"
    assert _signal(after, CAP, "operating_state") == "STOPPED"
    assert after["nodes"]["BW-DEMO-01"]["signals"]["operating_state"][
        "value"] == "STOPPED"
    assert after["nodes"]["BW-DEMO-01"]["signals"]["run_state"]["value"] == (
        "STOPPED")
    assert _signal(after, CAP, "operating_state") != "FAULT"


def test_b5_12_classification_does_not_change_the_trajectory():
    plain = _factory()
    labelled = _factory()
    plain.start()
    labelled.start()
    labelled.classify("downtime_code", "DT-BRG")
    labelled.classify("failure_code", "FAIL-BRG")
    assert labelled.snapshot()["scenario"]["phase"] == "NORMAL"
    assert _signal(labelled.snapshot(), CAP, "vibration_rms") == _signal(
        plain.snapshot(), CAP, "vibration_rms")
    _run(plain, 180)
    _run(labelled, 180)
    plain_snap = plain.snapshot()
    labelled_snap = labelled.snapshot()
    for signal_id in (
        "vibration_rms", "motor_current", "drive_load",
        "bearing_temperature", "speed", "cycle_time",
    ):
        assert _signal(plain_snap, CAP, signal_id) == _signal(
            labelled_snap, CAP, signal_id)
    assert plain_snap["scenario"]["phase"] == labelled_snap["scenario"]["phase"]
    assert labelled_snap["classification"]["downtime_code"] == "DT-BRG"
    assert labelled_snap["classification"]["failure_code"] == "FAIL-BRG"
    downtime = [
        event for event in labelled_snap["recent_events"]
        if event["event_type"] == "DOWNTIME_START"
    ]
    assert downtime and downtime[0]["downtime_code"] == "DT-BRG"
    assert downtime[0]["failure_code"] == "FAIL-BRG"


def test_b5_13_and_14_no_hidden_truth_or_kpi_fields():
    factory = _factory()
    factory.start()
    _run(factory, 180)
    snapshot = factory.snapshot()
    keys: set[str] = set()
    _walk_keys(snapshot, keys)
    for hidden in HIDDEN_TRUTH_KEYS:
        assert hidden not in keys, f"hidden truth leaked: {hidden}"
    serialised = json.dumps(snapshot).lower()
    for kpi in FORBIDDEN_KPI_KEYS:
        assert kpi not in serialised, f"kpi leaked: {kpi}"
    assert "degradation_factor" not in serialised
    assert "injected_fault_strength" not in serialised


def test_b5_16_skin_exposes_capper_condition_without_redesign(client):
    html = (STATIC / "bottled_water_demo.html").read_text(encoding="utf-8")
    js = (STATIC / "bottled_water_demo.js").read_text(encoding="utf-8")
    css = (STATIC / "bottled_water_demo.css").read_text(encoding="utf-8")
    combined = f"{html}\n{js}\n{css}".lower()
    for later in ("degradation", "degrading", "warning_phase", "recovery_phase",
                  "mqtt", "opcua", "plantos", "docker"):
        assert later not in combined
    assert "bw-capper-mark" in html
    assert "bw-cmp-mark" in html
    assert "ALARM_RAISED" in js
    assert "/classify" in js
    assert "bw-dot-warn" in css

    client.post("/bottled-water-demo/start")
    for _ in range(6):
        client.post("/bottled-water-demo/advance")
    state = client.get("/bottled-water-demo/state").json()
    factory = client.get("/bottled-water-demo/factory").json()
    assert state["scenario"]["id"] == "BW-CAP-DEG-01"
    assert CAP in state["asset_signals"]
    assert "vibration_rms" in state["asset_signals"][CAP]
    assert factory["target_line"]["scenario"] == state["scenario"]
    response = client.post(
        "/bottled-water-demo/classify",
        json={"kind": "downtime_code", "code": "DT-MECH"},
    )
    assert response.status_code == 200
    assert response.json()["classification"]["downtime_code"] == "DT-MECH"


def test_b5_http_pause_and_stop_keep_operator_semantics(client):
    client.post("/bottled-water-demo/start")
    for _ in range(5):
        client.post("/bottled-water-demo/advance")
    paused = client.post("/bottled-water-demo/pause").json()
    assert paused["run_state"] == "PAUSED"
    client.post("/bottled-water-demo/stop")
    stopped = client.get("/bottled-water-demo/factory").json()
    assert stopped["factory"]["run_state"] == "STOPPED"
    assert _signal(stopped, CAP, "operating_state") == "STOPPED"
