"""DDAY-B2 — Bottled Water hero line runtime reuse acceptance tests (T01–T12).

Governed by .ai-harness/tasks/DDAY-B2.json (authored from SA Issue #102).

The tests exercise the *reused* discrete foundation
(``virtual_factory.assembly.line_runtime``) driven by the Bottled Water
workspace configuration. No new engine is introduced, so every assertion below
goes through the same public runtime API that already serves the existing
discrete workspace.

T13 (relevant legacy regression) is the pre-existing suite and is reported
separately — it is not duplicated here.
"""

from __future__ import annotations

import copy
import re
from pathlib import Path

import pytest

from virtual_factory.assembly.demo_controller import DemoController
from virtual_factory.assembly.line_runtime import (
    AssyLineRuntime,
    LineRunState,
    load_assy_config_from_yaml,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = (
    REPO_ROOT / "configs" / "workspaces" / "bottled-water-dday" / "line.yaml"
)

# Frozen target route (B1 topology contract, area BW-FP).
EXPECTED_ROUTE = [
    "BW-FP-BLW01",   # Blower / Infeed
    "BW-FP-RIN01",   # Rinser
    "BW-FP-FIL01",   # Filler
    "BW-FP-CAP01",   # Capper
    "BW-FP-INS01",   # Inspection (consolidated checkpoint)
    "BW-FP-LAB01",   # Labeler
    "BW-FP-CPK01",   # Case Packer
    "BW-FP-PAL01",   # Palletizer
]

INSPECTION = "BW-FP-INS01"
NOMINAL_DWELL_S = 20.0

# Domain-isolation tokens that must never appear in Bottled Water outward
# runtime/config/event surfaces.
FORBIDDEN_LITERALS = (
    "TIPA", "ASSY", "PRE-ASSY", "AP05_JAM", "SSO2", "RSO2",
)
FORBIDDEN_PATTERN = re.compile(r"\bAP\d{2}\b")


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════

def load_config(inspection_scenario: str | None = None):
    """Load the Bottled Water line config, optionally forcing inspection."""
    config = load_assy_config_from_yaml(str(CONFIG_PATH))
    if inspection_scenario is not None:
        config.quality_stations[INSPECTION].quality.scenario = inspection_scenario
    return config


def make_line(inspection_scenario: str | None = None) -> AssyLineRuntime:
    return AssyLineRuntime(config=load_config(inspection_scenario))


def run_cycles(line: AssyLineRuntime, cycles: int) -> None:
    for _ in range(cycles):
        line.advance_cycle()


def trace_signature(line: AssyLineRuntime) -> list[tuple]:
    """Comparable signature of the *production* trace.

    Operator control-plane events (``LINE_RUN_STATE``) are excluded: they record
    START/PAUSE/RESUME/STOP actions rather than plant progression, so a paused
    and resumed run must still be production-identical to an uninterrupted one.
    """
    return [
        (e.event_type, e.position, e.wip_id, e.detail,
         round(e.simulation_time_s, 6), e.dwell_number)
        for e in line.trace
        if e.event_type != "LINE_RUN_STATE"
    ]


def run_state_events(line: AssyLineRuntime) -> list[str]:
    """Ordered control-plane run-state transitions recorded by the runtime."""
    return [e.detail for e in line.trace if e.event_type == "LINE_RUN_STATE"]


def iter_strings(value):
    """Yield every string found anywhere inside a nested structure."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from iter_strings(item)
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            yield from iter_strings(item)


def positions_visited(line: AssyLineRuntime, wip_id: str) -> list[str]:
    """Ordered list of distinct stations a unit passed through, from the trace.

    Uses movement facts (UNIT_ENTERED + WIP_MOVED) rather than station-complete
    events, so stations whose completion is expressed as a quality result (the
    Inspection checkpoint) are included as well.
    """
    visited: list[str] = []
    for event in line.trace:
        if event.wip_id != wip_id:
            continue
        if event.event_type in ("UNIT_ENTERED", "WIP_MOVED"):
            if not visited or visited[-1] != event.position:
                visited.append(event.position)
    return visited


def state_neutral_facts(line: AssyLineRuntime) -> dict:
    """Raw facts excluding the run state (which intentionally changes)."""
    facts = line.line_facts()
    facts.pop("run_state", None)
    facts.pop("operating_state", None)
    return facts


# ═══════════════════════════════════════════════════════════
# T01 — exact 8-station route/order
# ═══════════════════════════════════════════════════════════

def test_t01_exact_eight_station_route_and_order():
    line = make_line()

    assert list(line.conveyor.positions) == EXPECTED_ROUTE
    assert len(line.conveyor.positions) == 8
    assert len(set(line.conveyor.positions)) == 8

    # Contract-driven, not adapted: exactly one contract per frozen station id.
    assert sorted(line.station_contracts) == sorted(EXPECTED_ROUTE)

    # The routing order is the configured conveyor order, and every station has
    # a configured logical cycle duration.
    assert list(line.config.conveyor.positions) == EXPECTED_ROUTE
    for station in EXPECTED_ROUTE:
        assert station in line.config.station_durations

    # Only the consolidated Inspection checkpoint carries a quality capability.
    quality_stations = [
        sid for sid, contract in line.station_contracts.items()
        if contract.capabilities.quality_decision
    ]
    assert quality_stations == [INSPECTION]


# ═══════════════════════════════════════════════════════════
# T02 — automatic unit progression
# ═══════════════════════════════════════════════════════════

def test_t02_automatic_unit_progression_without_manual_actions():
    line = make_line()
    line.start()

    run_cycles(line, 1)
    assert line.total_count == 1, "a unit must be released automatically at line entry"
    assert line.units_on_line() == 1
    assert line.conveyor.wip_at(EXPECTED_ROUTE[0]) is None  # already indexed

    # No manual station command is ever required: nothing waits for operator
    # input and no command other than the automatic DONE is recorded.
    assert [e for e in line.trace
            if e.event_type == "OPERATION_WAITING_COMMAND"] == []
    assert all(op.command is None or op.command.value == "DONE"
               for op in line.active_operations())

    run_cycles(line, 7)
    unit_id = "BTL-000001"
    ws = line.get_wip(unit_id)
    assert ws is not None
    # Unit 1 traversed every station in the frozen order and left the line.
    assert positions_visited(line, unit_id) == EXPECTED_ROUTE
    assert line.good_count == 1
    assert line.simulation_time_s == pytest.approx(8 * NOMINAL_DWELL_S)
    assert line.conveyor.dwell_number == 8

    # Progression is takt-driven: one new unit per completed cycle while the
    # entry position is free.
    assert line.total_count == 8
    assert line.units_on_line() == 7


# ═══════════════════════════════════════════════════════════
# T03 — deterministic replay
# ═══════════════════════════════════════════════════════════

def test_t03_deterministic_replay_same_config_seed_initial_state():
    line_a = make_line()
    line_b = make_line()
    line_a.start()
    line_b.start()

    run_cycles(line_a, 12)
    run_cycles(line_b, 12)

    assert trace_signature(line_a) == trace_signature(line_b)
    assert line_a.unit_counts() == line_b.unit_counts()
    assert line_a.line_facts() == line_b.line_facts()
    assert line_a.simulation_time_s == line_b.simulation_time_s

    # Replaying the same runtime from reset must reproduce the same trace too.
    baseline = trace_signature(line_a)
    line_a.reset()
    assert line_a.unit_counts() == {
        "total_count": 0, "good_count": 0, "reject_count": 0}
    line_a.start()
    run_cycles(line_a, 12)
    assert trace_signature(line_a) == baseline


# ═══════════════════════════════════════════════════════════
# T04 — PASS reaches good downstream completion
# ═══════════════════════════════════════════════════════════

def test_t04_inspection_pass_reaches_good_downstream_completion():
    line = make_line("PASS")
    line.start()
    run_cycles(line, 8)

    results = [e for e in line.trace
               if e.event_type == "QUALITY_RESULT" and e.position == INSPECTION]
    assert results, "Inspection must produce an automatic quality result"
    assert "disposition=PASS" in results[0].detail
    assert line.last_quality_disposition(INSPECTION) == "PASS"

    completed = [e for e in line.trace if e.event_type == "UNIT_COMPLETED"]
    assert len(completed) == 1
    assert completed[0].position == EXPECTED_ROUTE[-1]
    assert completed[0].wip_id == "BTL-000001"

    ws = line.get_wip("BTL-000001")
    assert ws is not None
    assert ws.lifecycle.value == "released"
    assert ws.rejected is False
    assert line.good_count == 1
    assert line.reject_count == 0

    # The good unit passed through the stations downstream of Inspection.
    visited = positions_visited(line, "BTL-000001")
    assert visited.index(INSPECTION) < visited.index("BW-FP-LAB01")
    assert visited[-1] == EXPECTED_ROUTE[-1]


# ═══════════════════════════════════════════════════════════
# T05 — FAIL at Inspection rejects and does not count good
# ═══════════════════════════════════════════════════════════

def test_t05_inspection_fail_rejects_and_never_counts_good():
    line = make_line("ALWAYS_FAIL")
    line.start()
    run_cycles(line, 12)

    rejects = [e for e in line.trace if e.event_type == "REJECT"]
    assert rejects, "a failed inspection must reject the unit"
    assert all(e.position == INSPECTION for e in rejects)
    assert len(rejects) == line.reject_count == 8

    # No rejected unit is ever counted good, and none completes the route.
    assert line.good_count == 0
    assert [e for e in line.trace if e.event_type == "UNIT_COMPLETED"] == []
    for unit_id in ("BTL-000001", "BTL-000008"):
        ws = line.get_wip(unit_id)
        assert ws is not None
        assert ws.rejected is True
        assert ws.lifecycle.value == "rejected"
        assert ws.counted_good is False
        assert EXPECTED_ROUTE[-1] not in positions_visited(line, unit_id)

    # The line keeps running: rejected units are ejected, not held.
    assert line.units_on_line() == 4
    assert line.total_count == 12

    # The rejected unit's carrier is released so it cannot block the takt.
    rejected_units = {e.wip_id for e in rejects}
    for position in EXPECTED_ROUTE:
        carrier = line.conveyor.carrier_at(position)
        if carrier is not None:
            assert carrier.wip_id not in rejected_units


# ═══════════════════════════════════════════════════════════
# T06 — count invariant
# ═══════════════════════════════════════════════════════════

@pytest.mark.parametrize("scenario,cycles", [
    ("PASS", 1), ("PASS", 8), ("PASS", 20),
    ("ALWAYS_FAIL", 1), ("ALWAYS_FAIL", 8), ("ALWAYS_FAIL", 20),
])
def test_t06_count_invariant(scenario, cycles):
    line = make_line(scenario)
    line.start()
    run_cycles(line, cycles)

    counts = line.unit_counts()
    assert counts["good_count"] + counts["reject_count"] <= counts["total_count"]
    assert counts["total_count"] == line.total_count
    assert line.total_count == cycles  # one unit released per completed cycle

    # Units on the line are still "in progress" and are never double counted.
    in_progress = counts["total_count"] - counts["good_count"] - counts["reject_count"]
    assert in_progress == line.units_on_line()


# ═══════════════════════════════════════════════════════════
# T07 — START
# ═══════════════════════════════════════════════════════════

def test_t07_start_begins_automatic_progression():
    line = make_line()

    # Before START the line is STOPPED and does not progress at all.
    assert line.run_state == LineRunState.STOPPED
    assert line.advance_cycle() == []
    assert line.simulation_time_s == 0.0
    assert line.total_count == 0

    state = line.start()
    assert state == LineRunState.RUNNING
    assert line.run_state == LineRunState.RUNNING

    events = line.advance_cycle()
    assert events, "START must allow automatic progression"
    assert line.simulation_time_s == pytest.approx(NOMINAL_DWELL_S)
    assert line.total_count == 1
    assert line.operating_state() == "RUNNING"


# ═══════════════════════════════════════════════════════════
# T08 — PAUSE freezes progression
# ═══════════════════════════════════════════════════════════

def test_t08_pause_freezes_progression_and_preserves_state():
    line = make_line()
    line.start()
    run_cycles(line, 3)

    frozen_facts = copy.deepcopy(state_neutral_facts(line))
    frozen_trace = trace_signature(line)
    frozen_dwell = line.conveyor.dwell_number

    assert line.pause() == LineRunState.PAUSED
    assert line.run_state == LineRunState.PAUSED
    for _ in range(5):
        assert line.advance_cycle() == []

    assert state_neutral_facts(line) == frozen_facts
    assert trace_signature(line) == frozen_trace
    assert line.conveyor.dwell_number == frozen_dwell
    assert line.simulation_time_s == pytest.approx(3 * NOMINAL_DWELL_S)
    assert run_state_events(line) == ["state=RUNNING", "state=PAUSED"]


# ═══════════════════════════════════════════════════════════
# T09 — RESUME continues preserved state
# ═══════════════════════════════════════════════════════════

def test_t09_resume_continues_from_preserved_state():
    control = make_line()
    control.start()
    run_cycles(control, 4)

    interrupted = make_line()
    interrupted.start()
    run_cycles(interrupted, 3)
    preserved = copy.deepcopy(state_neutral_facts(interrupted))

    interrupted.pause()
    for _ in range(4):
        interrupted.advance_cycle()

    # Nothing moved while paused.
    assert state_neutral_facts(interrupted) == preserved

    assert interrupted.resume() == LineRunState.RUNNING
    resumed_events = interrupted.advance_cycle()
    assert resumed_events, "RESUME must continue the line"

    # The resumed line is indistinguishable from one that never paused.
    assert trace_signature(interrupted) == trace_signature(control)
    assert interrupted.line_facts() == control.line_facts()
    assert interrupted.simulation_time_s == control.simulation_time_s
    assert run_state_events(interrupted) == [
        "state=RUNNING", "state=PAUSED", "state=RUNNING"]


# ═══════════════════════════════════════════════════════════
# T10 — STOP is a controlled stop, not FAULT
# ═══════════════════════════════════════════════════════════

def test_t10_stop_is_controlled_stop_not_fault():
    line = make_line()
    line.start()
    run_cycles(line, 2)

    stopped_at = line.simulation_time_s
    assert line.stop() == LineRunState.STOPPED
    assert line.run_state == LineRunState.STOPPED
    assert line.operating_state() == "STOPPED"

    # A STOP is not a fault and produces no downtime semantics.
    assert "FAULT" not in {state.value for state in LineRunState}
    assert LineRunState.STOPPED.value != "FAULT"
    assert line.operating_state() != "FAULT"

    surface = " ".join(iter_strings(line.line_facts()))
    surface += " " + " ".join(
        f"{e.event_type} {e.position} {e.wip_id} {e.detail}" for e in line.trace)
    assert "FAULT" not in surface
    assert "DOWNTIME" not in surface

    # Progression stops, and the state is preserved rather than discarded.
    for _ in range(3):
        assert line.advance_cycle() == []
    assert line.simulation_time_s == stopped_at
    assert line.units_on_line() > 0


# ═══════════════════════════════════════════════════════════
# T11 — RESET restores a valid initial state and deterministic rerun
# ═══════════════════════════════════════════════════════════

def test_t11_reset_restores_initial_state_and_deterministic_rerun():
    line = make_line()
    line.start()
    run_cycles(line, 5)
    assert line.total_count == 5

    line.reset()

    # Known initial state.
    assert line.run_state == LineRunState.STOPPED
    assert line.unit_counts() == {
        "total_count": 0, "good_count": 0, "reject_count": 0}
    assert line.units_on_line() == 0
    assert line.simulation_time_s == 0.0
    assert line.conveyor.dwell_number == 0
    assert line.operating_state() == "STOPPED"
    assert line.trace == ()
    for position in EXPECTED_ROUTE:
        assert line.conveyor.wip_at(position) is None

    # Deterministic rerun from the restored initial state.
    fresh = make_line()
    fresh.start()
    line.start()
    run_cycles(line, 12)
    run_cycles(fresh, 12)
    assert trace_signature(line) == trace_signature(fresh)
    assert line.line_facts() == fresh.line_facts()


# ═══════════════════════════════════════════════════════════
# T12 — no TIPA/APxx leakage in Bottled Water outward state
# ═══════════════════════════════════════════════════════════

def _assert_clean(label: str, texts) -> None:
    for text in texts:
        for token in FORBIDDEN_LITERALS:
            assert token not in text, f"{label}: leaked '{token}' in {text!r}"
        assert not FORBIDDEN_PATTERN.search(text), (
            f"{label}: leaked APxx station id in {text!r}")


def test_t12_no_legacy_domain_leakage_in_outward_surfaces():
    line = make_line("ALWAYS_FAIL")   # exercise both outcomes
    line.start()
    run_cycles(line, 12)

    # 1. Configuration file itself.
    _assert_clean("config", [CONFIG_PATH.read_text(encoding="utf-8")])

    # 2. Runtime outward raw facts.
    facts = line.line_facts()
    _assert_clean("line_facts", list(iter_strings(facts)))

    # 3. Trace events (event type / station / unit / detail).
    trace_text = [
        f"{e.event_type} {e.position} {e.wip_id} {e.detail}" for e in line.trace
    ]
    _assert_clean("trace", trace_text)

    # 4. Station contracts and unit identities.
    contract_text = [
        f"{sid} {contract.to_dict()}" for sid, contract in line.station_contracts.items()
    ]
    _assert_clean("contracts", contract_text)
    _assert_clean("units", [" ".join(line.wip_ids)])
    assert all(w.startswith("BTL-") for w in line.wip_ids)

    # 5. The legacy demo snapshot path publishes no Bottled Water state.
    controller = DemoController(config_path=str(CONFIG_PATH))
    controller.initialize()
    assert controller.is_generic_line is True
    legacy = controller.snapshot().to_dict()
    assert legacy["positions"] == []
    assert legacy["genealogy"] == []
    assert legacy["quality_records"] == []
    assert legacy["production"]["wips_on_line"] == 0

    # 6. The generic workspace surface is the raw-fact view, and it resolves.
    controller.start()
    controller.advance()
    generic_facts = controller.line_facts()
    assert generic_facts["line_id"] == "BW-FP"
    assert generic_facts["unit_type"] == "bottle"
    assert generic_facts["product_code"] == "WATER-500ML"
    assert generic_facts["route"] == EXPECTED_ROUTE
    _assert_clean("controller facts", list(iter_strings(generic_facts)))
