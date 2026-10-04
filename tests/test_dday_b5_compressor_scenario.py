"""DDAY-B5 — Compressor secondary utility scenario tests.

Governed by .ai-harness/tasks/DDAY-B5.json (Capper hero + Compressor secondary).
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


def _factory(**kwargs) -> BottledWaterFactory:
    return BottledWaterFactory(LINE_YAML, FACTORY_YAML, **kwargs)


def _short_compressor() -> CompressorPressureScenario:
    config = load_compressor_runtime(RUNTIME, CONTRACT)
    return CompressorPressureScenario(replace(
        config,
        phase_duration_s={"NORMAL": 2.0, "PRESSURE_SAG": 20.0, "RECOVERY": 16.0},
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
    factory: BottledWaterFactory, phase: str, limit: int = 80
) -> dict:
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


def test_b5_c1_phase_order_is_exactly_the_compressor_contract():
    factory = _factory(enable_capper=False, compressor=_short_compressor())
    factory.start()
    seen = [factory.snapshot()["compressor_scenario"]["phase"]]
    for _ in range(50):
        factory.step(1.0)
        phase = factory.snapshot()["compressor_scenario"]["phase"]
        if phase != seen[-1]:
            seen.append(phase)
    assert tuple(seen) == PHASES


def test_b5_c2_reset_replays_the_same_trace():
    traces = []
    for _ in range(2):
        factory = _factory(enable_capper=False, compressor=_short_compressor())
        factory.start()
        _run(factory, 30)
        snapshot = factory.snapshot()
        traces.append((
            [event["event_type"] for event in _cmp_events(snapshot)],
            snapshot["compressor_scenario"]["phase"],
            _signal(snapshot, CMP, "air_pressure"),
        ))
    assert traces[0] == traces[1]

    factory = _factory(enable_capper=False, compressor=_short_compressor())
    factory.start()
    _run(factory, 30)
    after = factory.snapshot()
    factory.reset()
    assert factory.snapshot()["compressor_scenario"]["phase"] == "NORMAL"
    assert after["compressor_scenario"]["phase"] != "NORMAL"


def test_b5_c3_one_alarm_pair_and_no_downtime():
    factory = _factory(enable_capper=False, compressor=_short_compressor())
    factory.start()
    _run(factory, 50)
    types = [event["event_type"] for event in _cmp_events(factory.snapshot())]
    assert types.count("ALARM_RAISED") == 1
    assert types.count("ALARM_CLEARED") == 1
    assert types.count("DOWNTIME_START") == 0
    assert types.count("DOWNTIME_END") == 0
    assert types.index("ALARM_RAISED") < types.index("ALARM_CLEARED")
    assert factory.snapshot()["compressor_scenario"]["id"] == "BW-CMP-SAG-01"


def test_b5_c4_compressor_does_not_inhibit_production():
    factory = _factory(enable_capper=False, compressor=_short_compressor())
    factory.start()
    _run_to_compressor_phase(factory, "PRESSURE_SAG")
    during = factory.snapshot()
    _run(factory, 20)
    later = factory.snapshot()
    assert later["compressor_scenario"]["phase"] in ("PRESSURE_SAG", "RECOVERY")
    assert later["target_line"]["counts"]["total"] > during["target_line"][
        "counts"]["total"]
    assert later["scenario"]["phase"] == "NORMAL"


def test_b5_c5_default_demo_windows_do_not_overlap():
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
    assert after_capper["compressor_scenario"]["phase"] == "PRESSURE_SAG"
    _run(factory, 8)
    sagging = factory.snapshot()
    assert sagging["compressor_scenario"]["phase"] == "PRESSURE_SAG"
    assert _signal(sagging, CMP, "air_pressure") < 6.4

    _run(factory, 30)
    sag_end = factory.snapshot()
    assert sag_end["compressor_scenario"]["phase"] == "RECOVERY"
    assert sag_end["scenario"]["phase"] == "RECOVERY"


def test_b5_c6_each_scenario_is_independently_disableable():
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
    _run(compressor_only, 25)
    cmp_snap = compressor_only.snapshot()
    assert cmp_snap["scenario"]["phase"] == "NORMAL"
    assert cmp_snap["compressor_scenario"]["phase"] in ("PRESSURE_SAG", "RECOVERY")
    assert not any(
        event.get("scenario_id") == "BW-CAP-DEG-01"
        for event in cmp_snap["recent_events"]
    )


def test_b5_c7_pause_freezes_and_stop_is_not_a_line_fault():
    factory = _factory(enable_capper=False, compressor=_short_compressor())
    factory.start()
    _run_to_compressor_phase(factory, "PRESSURE_SAG")
    factory.pause()
    paused = factory.snapshot()
    _run(factory, 20)
    held = factory.snapshot()
    assert held["compressor_scenario"]["phase"] == "PRESSURE_SAG"
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
    assert stopped["compressor_scenario"]["phase"] == "PRESSURE_SAG"


def test_b5_c8_pressure_moves_causally_and_stays_bounded():
    factory = _factory(enable_capper=False, compressor=_short_compressor())
    factory.start()
    _run(factory, 2)
    normal = factory.snapshot()
    sag = _run_to_compressor_phase(factory, "PRESSURE_SAG")
    _run(factory, 19)
    deep = factory.snapshot()
    assert _signal(deep, CMP, "air_pressure") < _signal(sag, CMP, "air_pressure")
    assert _signal(deep, CMP, "air_pressure") < _signal(normal, CMP, "air_pressure")
    assert _signal(deep, CMP, "air_pressure") >= 5.5
    recovered = _run_to_compressor_phase(factory, "RECOVERY")
    _run(factory, 16)
    after = factory.snapshot()
    assert _signal(after, CMP, "air_pressure") > _signal(
        recovered, CMP, "air_pressure")
