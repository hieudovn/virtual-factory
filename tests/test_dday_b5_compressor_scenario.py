"""DDAY-B5-C01 — Compressor 5-phase causal scenario tests.

Governed by .ai-harness/tasks/DDAY-B5-C01.json.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from virtual_factory.workspaces.bottled_water import BottledWaterFactory
from virtual_factory.workspaces.compressor_pressure import (
    PHASES,
    CompressorPressureScenario,
    load_compressor_runtime,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = REPO_ROOT / "configs" / "workspaces" / "bottled-water-dday"
LINE_YAML = WORKSPACE / "line.yaml"
FACTORY_YAML = WORKSPACE / "factory.yaml"
CMP = "BW-UT-CMP01"
CAP = "BW-FP-CAP01"
CONTRACT = WORKSPACE / "scenarios" / "compressor_pressure.contract.yaml"
RUNTIME = WORKSPACE / "scenarios" / "compressor_pressure.runtime.yaml"

SHORT_DURATIONS = {
    "NORMAL": 22.0,
    "DEGRADING": 8.0,
    "LOW_PRESSURE_WARNING": 12.0,
    "UNDERSUPPLY": 22.0,
    "RECOVERY": 24.0,
}


def _factory(**kwargs) -> BottledWaterFactory:
    return BottledWaterFactory(LINE_YAML, FACTORY_YAML, **kwargs)


def _short_compressor() -> CompressorPressureScenario:
    config = load_compressor_runtime(RUNTIME, CONTRACT)
    return CompressorPressureScenario(replace(
        config, phase_duration_s=dict(SHORT_DURATIONS),
    ))


def _run(factory: BottledWaterFactory, steps: int, dt: float = 1.0) -> None:
    for _ in range(steps):
        factory.step(dt)


def _signal(snapshot: dict, node_id: str, signal_id: str):
    return snapshot["nodes"][node_id]["signals"][signal_id]["value"]


def _cmp_events(snapshot: dict) -> list[dict]:
    return [
        event for event in snapshot["recent_events"]
        if event.get("source_id") == CMP
        or event.get("scenario_id") == "BW-CMP-SAG-01"
    ]


def _run_to_compressor_phase(
    factory: BottledWaterFactory, phase: str, limit: int = 120
) -> dict:
    if factory.snapshot()["factory"]["run_state"] != "RUNNING":
        factory.start()
    snapshot = factory.snapshot()
    if snapshot["compressor_scenario"]["phase"] == phase:
        return snapshot
    for _ in range(limit):
        factory.step(1.0)
        snapshot = factory.snapshot()
        if snapshot["compressor_scenario"]["phase"] == phase:
            return snapshot
    raise AssertionError(f"did not reach compressor {phase} within {limit}s")


def test_c01_1_phase_order_is_exactly_the_sa_contract():
    factory = _factory(enable_capper=False, compressor=_short_compressor())
    factory.start()
    seen = [factory.snapshot()["compressor_scenario"]["phase"]]
    for _ in range(90):
        factory.step(1.0)
        phase = factory.snapshot()["compressor_scenario"]["phase"]
        if phase != seen[-1]:
            seen.append(phase)
    assert tuple(seen) == PHASES


def test_c01_2_reset_replays_the_same_trace():
    traces = []
    for _ in range(2):
        factory = _factory(enable_capper=False, compressor=_short_compressor())
        factory.start()
        _run(factory, 50)
        snapshot = factory.snapshot()
        traces.append((
            [event["event_type"] for event in _cmp_events(snapshot)],
            snapshot["compressor_scenario"]["phase"],
            _signal(snapshot, CMP, "air_pressure"),
            _signal(snapshot, CMP, "active_power"),
        ))
    assert traces[0] == traces[1]

    factory = _factory(enable_capper=False, compressor=_short_compressor())
    factory.start()
    _run(factory, 50)
    after = factory.snapshot()
    factory.reset()
    assert factory.snapshot()["compressor_scenario"]["phase"] == "NORMAL"
    assert after["compressor_scenario"]["phase"] != "NORMAL"


def test_c01_3_pressure_load_power_degrade_coherently():
    factory = _factory(enable_capper=False, compressor=_short_compressor())
    factory.start()
    _run(factory, 2)
    normal = factory.snapshot()
    degrading = _run_to_compressor_phase(factory, "DEGRADING")
    _run(factory, 7)
    deep_deg = factory.snapshot()
    warning = _run_to_compressor_phase(factory, "LOW_PRESSURE_WARNING")
    _run(factory, 7)
    deep_warn = factory.snapshot()
    under = _run_to_compressor_phase(factory, "UNDERSUPPLY")
    _run(factory, 10)
    deep_under = factory.snapshot()

    assert _signal(deep_deg, CMP, "air_pressure") < _signal(normal, CMP, "air_pressure")
    assert _signal(deep_warn, CMP, "air_pressure") < _signal(deep_deg, CMP, "air_pressure")
    assert _signal(deep_under, CMP, "air_pressure") <= _signal(
        deep_warn, CMP, "air_pressure")
    assert _signal(deep_under, CMP, "air_pressure") >= 5.5
    assert _signal(deep_deg, CMP, "active_power") > _signal(normal, CMP, "active_power")
    assert _signal(deep_under, CMP, "active_power") >= _signal(
        deep_deg, CMP, "active_power")
    assert deep_deg["compressor_scenario"]["phase"] == "DEGRADING"
    assert warning["compressor_scenario"]["phase"] == "LOW_PRESSURE_WARNING"
    assert under["compressor_scenario"]["phase"] == "UNDERSUPPLY"


def test_c01_4_warning_alarm_precedes_undersupply():
    factory = _factory(enable_capper=False, compressor=_short_compressor())
    factory.start()
    _run(factory, 90)
    events = _cmp_events(factory.snapshot())
    types = [event["event_type"] for event in events]
    assert types.count("ALARM_RAISED") == 1
    assert types.count("ALARM_CLEARED") == 1
    assert types.count("DOWNTIME_START") == 0
    alarm = next(event for event in events if event["event_type"] == "ALARM_RAISED")
    under = next(
        event for event in events
        if event["event_type"] == "SCENARIO_PHASE_CHANGED"
        and event["detail"] == "phase=UNDERSUPPLY"
    )
    assert alarm["simulation_time_s"] < under["simulation_time_s"]
    assert alarm["detail"] == "compressor low pressure"


def test_c01_5_and_6_undersupply_inhibits_and_recovery_restores():
    factory = _factory(enable_capper=False, compressor=_short_compressor())
    factory.start()
    _run_to_compressor_phase(factory, "LOW_PRESSURE_WARNING")
    before = factory.snapshot()
    under = _run_to_compressor_phase(factory, "UNDERSUPPLY")
    assert under["target_line"]["counts"]["total"] > 0
    _run(factory, 21)
    held = factory.snapshot()
    assert held["compressor_scenario"]["phase"] == "UNDERSUPPLY"
    assert held["target_line"]["counts"]["total"] == under["target_line"][
        "counts"]["total"]
    recovered = _run_to_compressor_phase(factory, "RECOVERY")
    _run(factory, 25)
    after = factory.snapshot()
    assert after["target_line"]["counts"]["total"] > held["target_line"][
        "counts"]["total"]
    goods = after["balances"]["finished_goods"]
    assert goods["receipt_count"] == after["target_line"]["counts"]["good"]
    assert goods["inventory_count"] == goods["receipt_count"] - goods[
        "dispatch_count"]
    assert _signal(after, CMP, "air_pressure") > _signal(
        recovered, CMP, "air_pressure")
    assert before["target_line"]["counts"]["total"] >= 0


def test_c01_7_default_demo_windows_do_not_overlap():
    factory = _factory()
    factory.start()
    _run(factory, 150)
    mid = factory.snapshot()
    assert mid["scenario"]["phase"] == "INTERMITTENT_STOP"
    assert mid["compressor_scenario"]["phase"] == "NORMAL"
    assert pytest.approx(_signal(mid, CMP, "air_pressure"), abs=0.05) == 6.4

    _run(factory, 90)
    after_capper = factory.snapshot()
    assert after_capper["factory"]["simulation_time_s"] == 240.0
    assert after_capper["scenario"]["phase"] == "RECOVERY"
    assert after_capper["compressor_scenario"]["phase"] == "DEGRADING"
    _run(factory, 8)
    sagging = factory.snapshot()
    assert sagging["compressor_scenario"]["phase"] == "DEGRADING"
    assert _signal(sagging, CMP, "air_pressure") < 6.4


def test_c01_8_each_scenario_is_independently_disableable():
    capper_only = _factory(enable_compressor=False)
    capper_only.start()
    _run(capper_only, 150)
    capper_snap = capper_only.snapshot()
    assert capper_snap["scenario"]["phase"] == "INTERMITTENT_STOP"
    assert capper_snap["compressor_scenario"]["phase"] == "NORMAL"
    assert not any(
        event.get("scenario_id") == "BW-CMP-SAG-01"
        for event in capper_snap["recent_events"]
    )

    compressor_only = _factory(enable_capper=False, compressor=_short_compressor())
    compressor_only.start()
    _run(compressor_only, 45)
    cmp_snap = compressor_only.snapshot()
    assert cmp_snap["scenario"]["phase"] == "NORMAL"
    assert cmp_snap["compressor_scenario"]["phase"] in (
        "LOW_PRESSURE_WARNING", "UNDERSUPPLY",
    )
    assert not any(
        event.get("scenario_id") == "BW-CAP-DEG-01"
        for event in cmp_snap["recent_events"]
    )


def test_c01_9_pause_freezes_and_stop_is_not_a_line_fault():
    factory = _factory(enable_capper=False, compressor=_short_compressor())
    factory.start()
    _run_to_compressor_phase(factory, "DEGRADING")
    factory.pause()
    paused = factory.snapshot()
    _run(factory, 20)
    held = factory.snapshot()
    assert held["compressor_scenario"]["phase"] == "DEGRADING"
    assert held["factory"]["simulation_time_s"] == paused["factory"][
        "simulation_time_s"]
    assert _signal(held, CMP, "air_pressure") == _signal(
        paused, CMP, "air_pressure")

    factory.resume()
    factory.stop()
    _run(factory, 8)
    stopped = factory.snapshot()
    assert stopped["factory"]["run_state"] == "STOPPED"
    assert _signal(stopped, CAP, "operating_state") == "STOPPED"
    assert _signal(stopped, CAP, "operating_state") != "FAULT"
    assert stopped["compressor_scenario"]["phase"] == "DEGRADING"


def test_c01_10_classification_does_not_change_compressor_trajectory():
    plain = _factory(enable_capper=False, compressor=_short_compressor())
    labelled = _factory(enable_capper=False, compressor=_short_compressor())
    plain.start()
    labelled.start()
    labelled.classify("downtime_code", "DT-AIR")
    labelled.classify("failure_code", "FAIL-AIR")
    _run(plain, 50)
    _run(labelled, 50)
    assert labelled.snapshot()["compressor_scenario"]["phase"] == plain.snapshot()[
        "compressor_scenario"]["phase"]
    assert _signal(labelled.snapshot(), CMP, "air_pressure") == _signal(
        plain.snapshot(), CMP, "air_pressure")
    assert _signal(labelled.snapshot(), CMP, "active_power") == _signal(
        plain.snapshot(), CMP, "active_power")
    assert labelled.snapshot()["classification"]["downtime_code"] == "DT-AIR"


def _warning_threshold(factory: BottledWaterFactory) -> float:
    return float(factory._compressor.config.warning_threshold_bar)


def test_c02_1_and_2_alarm_waits_for_pressure_threshold():
    factory = _factory(enable_capper=False, compressor=_short_compressor())
    factory.start()
    warning = _run_to_compressor_phase(factory, "LOW_PRESSURE_WARNING")
    threshold = _warning_threshold(factory)
    assert _signal(warning, CMP, "air_pressure") > threshold
    assert not any(
        event["event_type"] == "ALARM_RAISED" for event in _cmp_events(warning)
    )

    alarm_snap = None
    for _ in range(20):
        factory.step(1.0)
        snap = factory.snapshot()
        if any(
            event["event_type"] == "ALARM_RAISED" for event in _cmp_events(snap)
        ):
            alarm_snap = snap
            break
    assert alarm_snap is not None
    assert alarm_snap["compressor_scenario"]["phase"] == "LOW_PRESSURE_WARNING"
    assert _signal(alarm_snap, CMP, "air_pressure") <= threshold
    under = _run_to_compressor_phase(factory, "UNDERSUPPLY")
    alarm = next(
        event for event in _cmp_events(under)
        if event["event_type"] == "ALARM_RAISED"
    )
    under_event = next(
        event for event in _cmp_events(under)
        if event["event_type"] == "SCENARIO_PHASE_CHANGED"
        and event["detail"] == "phase=UNDERSUPPLY"
    )
    assert alarm["simulation_time_s"] < under_event["simulation_time_s"]


def test_c02_3_and_4_targeted_classify_enriches_compressor_context():
    plain = _factory(enable_capper=False, compressor=_short_compressor())
    labelled = _factory(enable_capper=False, compressor=_short_compressor())
    plain.start()
    labelled.start()
    labelled.classify("downtime_code", "DT-AIR", target="compressor")
    labelled.classify("failure_code", "FAIL-AIR", target="BW-UT-CMP01")
    _run(plain, 70)
    _run(labelled, 70)
    labelled_snap = labelled.snapshot()
    plain_snap = plain.snapshot()
    assert labelled_snap["compressor_scenario"]["phase"] == plain_snap[
        "compressor_scenario"]["phase"]
    assert _signal(labelled_snap, CMP, "air_pressure") == _signal(
        plain_snap, CMP, "air_pressure")
    assert labelled_snap["target_line"]["counts"]["total"] == plain_snap[
        "target_line"]["counts"]["total"]
    assert labelled_snap["compressor_scenario"]["downtime_code"] == "DT-AIR"
    assert labelled_snap["compressor_scenario"]["failure_code"] == "FAIL-AIR"
    assert labelled_snap["classification"]["downtime_code"] is None
    cmp_events = _cmp_events(labelled_snap)
    stamped = [
        event for event in cmp_events
        if event.get("downtime_code") == "DT-AIR"
        and event.get("failure_code") == "FAIL-AIR"
    ]
    assert any(event["event_type"] == "ALARM_RAISED" for event in stamped)
    assert any(
        event["event_type"] == "SCENARIO_PHASE_CHANGED"
        and event["detail"] == "phase=UNDERSUPPLY"
        for event in stamped
    )


def test_c02_5_matched_control_run_shows_lower_abnormal_output():
    abnormal = _factory(enable_capper=False)
    control = _factory(enable_capper=False, enable_compressor=False)
    abnormal.start()
    control.start()

    def _both_to(seconds: int) -> tuple[dict, dict]:
        while abnormal.snapshot()["factory"]["simulation_time_s"] < seconds:
            abnormal.step(1.0)
            control.step(1.0)
        return abnormal.snapshot(), control.snapshot()

    at_under, control_under = _both_to(284)
    assert at_under["compressor_scenario"]["phase"] == "UNDERSUPPLY"
    assert control_under["compressor_scenario"]["phase"] == "NORMAL"
    assert at_under["target_line"]["counts"]["total"] == control_under[
        "target_line"]["counts"]["total"]
    assert at_under["target_line"]["counts"]["good"] == control_under[
        "target_line"]["counts"]["good"]
    assert at_under["balances"]["finished_goods"]["receipt_count"] == (
        control_under["balances"]["finished_goods"]["receipt_count"]
    )

    at_recover, control_recover = _both_to(304)
    assert at_recover["compressor_scenario"]["phase"] == "RECOVERY"
    assert at_recover["target_line"]["counts"]["total"] == at_under[
        "target_line"]["counts"]["total"]
    assert at_recover["target_line"]["counts"]["good"] == at_under[
        "target_line"]["counts"]["good"]
    assert at_recover["balances"]["finished_goods"]["receipt_count"] == (
        at_under["balances"]["finished_goods"]["receipt_count"]
    )
    assert control_recover["target_line"]["counts"]["total"] > at_recover[
        "target_line"]["counts"]["total"]
    assert control_recover["target_line"]["counts"]["good"] > at_recover[
        "target_line"]["counts"]["good"]
    assert control_recover["balances"]["finished_goods"]["receipt_count"] > (
        at_recover["balances"]["finished_goods"]["receipt_count"]
    )

    after, control_after = _both_to(340)
    assert after["target_line"]["counts"]["total"] > at_recover[
        "target_line"]["counts"]["total"]
    assert after["target_line"]["counts"]["good"] > at_recover[
        "target_line"]["counts"]["good"]
    assert after["balances"]["finished_goods"]["receipt_count"] > (
        at_recover["balances"]["finished_goods"]["receipt_count"]
    )
    assert after["balances"]["finished_goods"]["receipt_count"] == after[
        "target_line"]["counts"]["good"]
    assert (
        after["target_line"]["counts"]["total"]
        - at_recover["target_line"]["counts"]["total"]
    ) >= 1
    _ = control_after
