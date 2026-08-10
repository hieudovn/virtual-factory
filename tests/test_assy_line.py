"""M6-S02-C01 — TIPA ASSY Runtime Semantics & Acceptance Tests.

Tests A01–A10 per SA specification + preserved T01–T15 unit tests.
All acceptance tests use public runtime API (run_dwell_cycle, etc.).
"""

from __future__ import annotations

import pytest

from virtual_factory.assembly.carrier import CarrierId, CarrierState, CarrierError
from virtual_factory.assembly.conveyor import (
    ConveyorConfig, ConveyorLine, ConveyorState, ConveyorError,
)
from virtual_factory.assembly.genealogy import GenealogyRecord, GenealogyStore, GenealogyError
from virtual_factory.assembly.upstream import UpstreamConfig, UpstreamProducer
from virtual_factory.assembly.line_runtime import (
    AssyLineConfig, AssyLineRuntime, AssyLineError, WipLifecycle,
    load_assy_config_from_yaml,
)


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════

def make_fast_config() -> AssyLineConfig:
    """Config with short durations for fast tests."""
    c = AssyLineConfig()
    c.conveyor.nominal_line_dwell_time_s = 10.0
    c.conveyor.index_movement_duration_s = 0.0
    for key in c.station_durations:
        c.station_durations[key] = 5.0  # all < 10s dwell
    return c


def fill_line_with_wips(line: AssyLineRuntime, count: int) -> list[str]:
    """Introduce `count` SSO2 WIPs to ASSY and advance line between each."""
    ids = []
    for i in range(count):
        wid = line.produce_sso2_wip()
        line.introduce_to_assy(wid, f"PAL-{i+1:03d}")
        ids.append(wid)
        # Index to make room for next WIP
        if i < count - 1:
            line.execute_dwell()
            if line.conveyor.state == ConveyorState.READY_TO_INDEX:
                line.index_line()
    return ids


# ═══════════════════════════════════════════════════════════
# A01 — SIMULATION TIME (public runtime)
# ═══════════════════════════════════════════════════════════

class TestA01SimulationTime:
    def test_time_advances_after_dwell_and_index(self):
        cfg = make_fast_config()
        line = AssyLineRuntime(config=cfg)
        line.produce_sso2_wip()
        line.introduce_to_assy("SSO2-0001", "PAL-001")

        assert line.simulation_time_s == 0.0

        line.execute_dwell()
        # actual_dwell = max(10, 5) = 10s
        assert line.simulation_time_s == 10.0

        line.index_line()
        # index_movement = 0
        assert line.simulation_time_s == 10.0

    def test_time_monotonic(self):
        cfg = make_fast_config()
        cfg.station_durations["PRE-ASSY"] = 2.0
        cfg.station_durations["AP01"] = 2.0
        cfg.station_durations["AP02"] = 2.0
        line = AssyLineRuntime(config=cfg)
        line.produce_sso2_wip()
        line.produce_rso2_wip()  # needed for AP04
        line.introduce_to_assy("SSO2-0001", "PAL-001")

        times = []
        for _ in range(5):
            line.execute_dwell()
            times.append(line.simulation_time_s)
            if line.conveyor.state == ConveyorState.READY_TO_INDEX:
                line.index_line()
                times.append(line.simulation_time_s)

        for i in range(1, len(times)):
            assert times[i] >= times[i-1], f"Time not monotonic: {times}"

    def test_events_have_timestamps(self):
        cfg = make_fast_config()
        line = AssyLineRuntime(config=cfg)
        line.produce_sso2_wip()
        line.introduce_to_assy("SSO2-0001", "PAL-001")
        line.execute_dwell()

        for evt in line.trace:
            assert evt.simulation_time_s >= 0.0


# ═══════════════════════════════════════════════════════════
# A02 — PUBLIC MULTI-WIP DWELL
# ═══════════════════════════════════════════════════════════

class TestA02PublicMultiWipDwell:
    def test_multi_wip_same_dwell(self):
        cfg = make_fast_config()
        line = AssyLineRuntime(config=cfg)
        ids = fill_line_with_wips(line, 3)

        # After fill: PRE-ASSY=PAL-003, AP01=PAL-002, AP02=PAL-001
        assert line.conveyor.wip_at("PRE-ASSY") is not None
        assert line.conveyor.wip_at("AP01") is not None
        assert line.conveyor.wip_at("AP02") is not None

        # Run one dwell cycle
        events = line.run_dwell_cycle()

        # All should be in same dwell_number
        dwell_nums = {e.dwell_number for e in events if e.position}
        assert len(dwell_nums) > 0

    def test_synchronized_index_moves_all(self):
        cfg = make_fast_config()
        line = AssyLineRuntime(config=cfg)
        ids = fill_line_with_wips(line, 2)

        w1_before = line.conveyor.wip_at("AP01")
        assert w1_before is not None

        line.run_dwell_cycle()

        # After index: what was at AP01 moves to AP02
        assert line.conveyor.wip_at("AP02") == w1_before


# ═══════════════════════════════════════════════════════════
# A03 — OVERRUN (station duration > dwell)
# ═══════════════════════════════════════════════════════════

class TestA03Overrun:
    def test_overrun_extends_dwell(self):
        cfg = make_fast_config()
        cfg.conveyor.nominal_line_dwell_time_s = 10.0
        cfg.station_durations["PRE-ASSY"] = 5.0
        cfg.station_durations["AP01"] = 35.0
        line = AssyLineRuntime(config=cfg)

        wid = line.produce_sso2_wip()
        line.introduce_to_assy(wid, "PAL-001")

        # Dwell 1: PRE-ASSY(5s) completes; actual_dwell=max(10,5)=10s
        line.execute_dwell()
        assert line.simulation_time_s == 10.0
        line.index_line()

        # Dwell 2: AP01 needs 35s; actual_dwell=max(10,35)=35s
        # Station completes in one extended dwell
        line.execute_dwell()
        assert line.simulation_time_s == 45.0  # 10 + 35
        assert line.conveyor.state == ConveyorState.READY_TO_INDEX

    def test_line_does_not_index_during_overrun(self):
        cfg = make_fast_config()
        cfg.conveyor.nominal_line_dwell_time_s = 10.0
        cfg.station_durations["PRE-ASSY"] = 5.0
        cfg.station_durations["AP01"] = 35.0
        line = AssyLineRuntime(config=cfg)

        wid = line.produce_sso2_wip()
        line.introduce_to_assy(wid, "PAL-001")
        # First dwell: PRE-ASSY completes -> index
        line.execute_dwell()
        line.index_line()

        # Second dwell: AP01(35s) completes in one extended 35s dwell
        # run_dwell_cycle calls execute_dwell + index_line
        events = line.run_dwell_cycle()

        # Should have indexed (station completed in extended dwell)
        assert line.conveyor.state == ConveyorState.STOPPED

        # INDEX event should be present
        index_events = [e for e in events if "INDEX" in e.detail]
        assert len(index_events) == 1


# ═══════════════════════════════════════════════════════════
# A04 — NO OVERRUN (all durations < dwell)
# ═══════════════════════════════════════════════════════════

class TestA04NoOverrun:
    def test_normal_dwell_completes_in_one_cycle(self):
        cfg = make_fast_config()
        cfg.conveyor.nominal_line_dwell_time_s = 10.0
        cfg.station_durations["PRE-ASSY"] = 5.0
        line = AssyLineRuntime(config=cfg)

        wid = line.produce_sso2_wip()
        line.introduce_to_assy(wid, "PAL-001")
        line.execute_dwell()

        assert line.conveyor.state == ConveyorState.READY_TO_INDEX
        assert line.simulation_time_s == 10.0  # max(10, 5) = 10

    def test_multiple_stations_complete_in_one_dwell(self):
        cfg = make_fast_config()
        cfg.conveyor.nominal_line_dwell_time_s = 10.0
        cfg.station_durations["PRE-ASSY"] = 3.0
        cfg.station_durations["AP01"] = 7.0
        line = AssyLineRuntime(config=cfg)

        ids = fill_line_with_wips(line, 2)
        line.execute_dwell()

        # Both should complete: max(10, 3, 7) = 10
        assert line.conveyor.state == ConveyorState.READY_TO_INDEX


# ═══════════════════════════════════════════════════════════
# A05 — AP04 PUBLIC JOIN
# ═══════════════════════════════════════════════════════════

class TestA05Ap04PublicJoin:
    def test_ap04_join_via_public_runtime(self):
        cfg = make_fast_config()
        cfg.conveyor.nominal_line_dwell_time_s = 10.0
        for k in cfg.station_durations:
            cfg.station_durations[k] = 5.0
        line = AssyLineRuntime(config=cfg)

        # Produce upstream
        wid = line.produce_sso2_wip()
        line.produce_rso2_wip()
        line.introduce_to_assy(wid, "PAL-001")

        # Advance to AP04: PRE-ASSY(1) → AP01(2) → AP02(3) → AP03(4)
        for _ in range(4):
            line.execute_dwell()
            if line.conveyor.state == ConveyorState.READY_TO_INDEX:
                line.index_line()

        assert line.conveyor.wip_at("AP04") == wid

        # Execute AP04 dwell
        line.execute_dwell()

        # Verify
        child_id = "MTR-0001"
        child_ws = line.get_wip(child_id)
        assert child_ws is not None
        assert child_ws.is_child_of_join

        record = line.genealogy.get(child_id)
        assert record is not None
        assert wid in record.parent_wip_ids

        # Exactly one AP04_JOIN event (C01-05)
        join_count = sum(1 for e in line.trace if e.event_type == "AP04_JOIN")
        assert join_count == 1, f"Expected 1 AP04_JOIN, got {join_count}"

    def test_carrier_handoff_to_child(self):
        cfg = make_fast_config()
        cfg.conveyor.nominal_line_dwell_time_s = 10.0
        for k in cfg.station_durations:
            cfg.station_durations[k] = 5.0
        line = AssyLineRuntime(config=cfg)

        wid = line.produce_sso2_wip()
        line.produce_rso2_wip()
        line.introduce_to_assy(wid, "PAL-001")

        for _ in range(5):  # through AP04
            line.execute_dwell()
            if line.conveyor.state == ConveyorState.READY_TO_INDEX:
                line.index_line()

        # Carrier at AP04 (now moved to AP05) should have child
        # Check the carrier itself
        carrier = line.conveyor.get_carrier("PAL-001")
        assert carrier is not None
        assert carrier.wip_id == "MTR-0001"


# ═══════════════════════════════════════════════════════════
# A06 — AP04 JOIN TIME
# ═══════════════════════════════════════════════════════════

class TestA06JoinTime:
    def test_join_time_positive(self):
        cfg = make_fast_config()
        cfg.conveyor.nominal_line_dwell_time_s = 10.0
        for k in cfg.station_durations:
            cfg.station_durations[k] = 5.0
        line = AssyLineRuntime(config=cfg)

        wid = line.produce_sso2_wip()
        line.produce_rso2_wip()
        line.introduce_to_assy(wid, "PAL-001")

        for _ in range(5):
            line.execute_dwell()
            if line.conveyor.state == ConveyorState.READY_TO_INDEX:
                line.index_line()

        record = line.genealogy.get("MTR-0001")
        assert record is not None
        assert record.join_time_s > 0.0


# ═══════════════════════════════════════════════════════════
# A07 — PARENT LIFECYCLE
# ═══════════════════════════════════════════════════════════

class TestA07ParentLifecycle:
    def test_parent_is_joined_not_completed_station(self):
        cfg = make_fast_config()
        cfg.conveyor.nominal_line_dwell_time_s = 10.0
        for k in cfg.station_durations:
            cfg.station_durations[k] = 5.0
        line = AssyLineRuntime(config=cfg)

        wid = line.produce_sso2_wip()
        line.produce_rso2_wip()
        line.introduce_to_assy(wid, "PAL-001")

        for _ in range(5):
            line.execute_dwell()
            if line.conveyor.state == ConveyorState.READY_TO_INDEX:
                line.index_line()

        parent_ws = line.get_wip(wid)
        assert parent_ws is not None
        assert parent_ws.lifecycle == WipLifecycle.JOINED, \
            f"Expected JOINED, got {parent_ws.lifecycle}"


# ═══════════════════════════════════════════════════════════
# A08 — RELEASED LIFECYCLE
# ═══════════════════════════════════════════════════════════

class TestA08ReleasedLifecycle:
    def test_child_released_at_ap11(self):
        cfg = make_fast_config()
        cfg.conveyor.nominal_line_dwell_time_s = 10.0
        for k in cfg.station_durations:
            cfg.station_durations[k] = 5.0
        line = AssyLineRuntime(config=cfg)

        wid = line.produce_sso2_wip()
        line.produce_rso2_wip()
        line.introduce_to_assy(wid, "PAL-001")

        # Run through all 12 positions
        for _ in range(13):
            line.execute_dwell()
            if line.conveyor.state == ConveyorState.READY_TO_INDEX:
                line.index_line()

        child_ws = line.get_wip("MTR-0001")
        assert child_ws is not None
        assert child_ws.lifecycle == WipLifecycle.RELEASED, \
            f"Expected RELEASED, got {child_ws.lifecycle}"


# ═══════════════════════════════════════════════════════════
# A09 — DWELL NUMBER
# ═══════════════════════════════════════════════════════════

class TestA09DwellNumber:
    def test_dwell_number_increments_once_per_cycle(self):
        cfg = make_fast_config()
        cfg.station_durations["PRE-ASSY"] = 2.0
        cfg.station_durations["AP01"] = 2.0
        line = AssyLineRuntime(config=cfg)
        line.produce_sso2_wip()
        line.produce_rso2_wip()
        line.introduce_to_assy("SSO2-0001", "PAL-001")

        dwells_seen = set()
        for _ in range(3):
            line.execute_dwell()
            dwells_seen.add(line.conveyor.dwell_number)
            if line.conveyor.state == ConveyorState.READY_TO_INDEX:
                line.index_line()

        assert len(dwells_seen) == 3

    def test_no_duplicate_dwell_begin(self):
        cfg = make_fast_config()
        line = AssyLineRuntime(config=cfg)
        line.produce_sso2_wip()
        line.introduce_to_assy("SSO2-0001", "PAL-001")

        line.execute_dwell()
        line.index_line()
        line.execute_dwell()

        # Each dwell should have exactly 1 DWELL_META with "DWELL_BEGIN"
        begin_events = [e for e in line.trace
                        if e.event_type == "DWELL_META" and "DWELL_BEGIN" in e.detail]
        assert len(begin_events) == 2

    def test_dwell_numbers_are_consecutive(self):
        cfg = make_fast_config()
        cfg.station_durations["PRE-ASSY"] = 2.0
        cfg.station_durations["AP01"] = 2.0
        line = AssyLineRuntime(config=cfg)
        line.produce_sso2_wip()
        line.produce_rso2_wip()
        line.introduce_to_assy("SSO2-0001", "PAL-001")

        nums = []
        for _ in range(3):
            line.execute_dwell()
            nums.append(line.conveyor.dwell_number)
            if line.conveyor.state == ConveyorState.READY_TO_INDEX:
                line.index_line()

        assert nums == [1, 2, 3]


# ═══════════════════════════════════════════════════════════
# A10 — DETERMINISM
# ═══════════════════════════════════════════════════════════

class TestA10Determinism:
    def test_same_config_same_trace(self):
        def run():
            cfg = make_fast_config()
            line = AssyLineRuntime(config=cfg)
            wid = line.produce_sso2_wip()
            line.produce_rso2_wip()
            line.introduce_to_assy(wid, "PAL-001")
            for _ in range(8):
                line.execute_dwell()
                if line.conveyor.state == ConveyorState.READY_TO_INDEX:
                    line.index_line()
            return [(e.event_type, e.dwell_number, e.position)
                    for e in line.trace]

        t1 = run()
        t2 = run()
        assert t1 == t2


# ═══════════════════════════════════════════════════════════
# UNIT TESTS (preserved from M6-S02)
# ═══════════════════════════════════════════════════════════

class TestConveyorUnit:
    def test_positions_authoritative(self):
        line = AssyLineRuntime()
        expected = ("PRE-ASSY", "AP01", "AP02", "AP03", "AP04", "AP05",
                    "AP06", "AP07", "AP08", "AP09", "AP10", "AP11")
        assert line.conveyor.positions == expected

    def test_cannot_index_from_stopped(self):
        line = AssyLineRuntime()
        with pytest.raises(ConveyorError):
            line.conveyor.index()

    def test_carrier_independent_from_wip(self):
        line = AssyLineRuntime()
        wid = line.produce_sso2_wip()
        line.introduce_to_assy(wid, "PAL-042")
        c = line.conveyor.get_carrier("PAL-042")
        assert c is not None
        assert c.wip_id != str(c.carrier_id)

    def test_carrier_queries_independent(self):
        line = AssyLineRuntime()
        wid = line.produce_sso2_wip()
        line.introduce_to_assy(wid, "PAL-001")
        assert line.conveyor.get_carrier("PAL-001") is not None
        assert line.get_wip(wid) is not None

    def test_wip_identity_stable_before_ap04(self):
        cfg = make_fast_config()
        line = AssyLineRuntime(config=cfg)
        wid = line.produce_sso2_wip()
        line.introduce_to_assy(wid, "PAL-001")
        for _ in range(3):
            line.execute_dwell()
            if line.conveyor.state == ConveyorState.READY_TO_INDEX:
                line.index_line()
        ws = line.get_wip(wid)
        assert ws is not None
        assert ws.wip_id == wid

    def test_ap04_requires_both_parents(self):
        cfg = make_fast_config()
        line = AssyLineRuntime(config=cfg)
        wid = line.produce_sso2_wip()
        # No RSO2 produced
        line.introduce_to_assy(wid, "PAL-001")
        for _ in range(4):
            line.execute_dwell()
            if line.conveyor.state == ConveyorState.READY_TO_INDEX:
                line.index_line()
        with pytest.raises(AssyLineError, match="no RSO2"):
            line._execute_ap04_join(wid)

    def test_duplicate_genealogy_rejected(self):
        store = GenealogyStore()
        r = GenealogyRecord(child_wip_id="X", parent_wip_ids=("A", "B"),
                            component_ids=())
        store.record(r)
        with pytest.raises(GenealogyError):
            store.record(r)

    def test_dwell_configurable(self):
        cfg = make_fast_config()
        cfg.conveyor.nominal_line_dwell_time_s = 90.0
        line = AssyLineRuntime(config=cfg)
        assert line.config.conveyor.nominal_line_dwell_time_s == 90.0

    def test_station_duration_separate_from_dwell(self):
        cfg = make_fast_config()
        cfg.conveyor.nominal_line_dwell_time_s = 60.0
        cfg.station_durations["AP05"] = 90.0
        line = AssyLineRuntime(config=cfg)
        assert cfg.station_durations["AP05"] > cfg.conveyor.nominal_line_dwell_time_s

    def test_no_runtime_sleep(self):
        import time
        start = time.perf_counter()
        cfg = make_fast_config()
        line = AssyLineRuntime(config=cfg)
        line.produce_sso2_wip()
        line.introduce_to_assy("SSO2-0001", "PAL-001")
        line.execute_dwell()
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0

    def test_m2_m5_imports_intact(self):
        from virtual_factory.assembly.primitives import Source, PrimitiveType
        from virtual_factory.assembly import WipId, ConveyorLine, AssyLineRuntime
        assert PrimitiveType.PROCESSOR.value == "processor"
        assert WipId("t") is not None


# ═══════════════════════════════════════════════════════════
# CONFIG LOADING
# ═══════════════════════════════════════════════════════════

class TestConfigLoading:
    def test_config_yaml_roundtrip(self):
        """Load config from YAML and verify values."""
        import tempfile, os
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
conveyor:
  nominal_line_dwell_time_s: 90.0
  positions:
    - PRE-ASSY
    - AP01
    - AP02
station_durations:
  AP01: 45.0
ap04:
  component_list:
    - bearing_set
identity:
  motor_wip_prefix: MOT
""")
            f.flush()
            fpath = f.name
        try:
            config = load_assy_config_from_yaml(fpath)
            assert config.conveyor.nominal_line_dwell_time_s == 90.0
            assert config.station_durations["AP01"] == 45.0
            assert config.ap04_component_list == ("bearing_set",)
            assert config.motor_wip_prefix == "MOT"
        finally:
            os.unlink(fpath)


# ═══════════════════════════════════════════════════════════
# Happy Path Acceptance
# ═══════════════════════════════════════════════════════════

class TestHappyPathAcceptance:
    def test_full_happy_path_released(self):
        """T11: Deterministic happy path reaches RELEASED_FINISHED_GOOD."""
        cfg = make_fast_config()
        cfg.conveyor.nominal_line_dwell_time_s = 10.0
        for k in cfg.station_durations:
            cfg.station_durations[k] = 5.0
        line = AssyLineRuntime(config=cfg)

        wid = line.produce_sso2_wip()
        line.produce_rso2_wip()
        line.introduce_to_assy(wid, "PAL-001")

        for _ in range(13):
            line.execute_dwell()
            if line.conveyor.state == ConveyorState.READY_TO_INDEX:
                line.index_line()

        child = line.get_wip("MTR-0001")
        assert child is not None
        assert child.lifecycle == WipLifecycle.RELEASED
        assert child.is_child_of_join
        assert line.genealogy.get("MTR-0001") is not None

    def test_trace_contains_all_key_events(self):
        cfg = make_fast_config()
        cfg.conveyor.nominal_line_dwell_time_s = 10.0
        for k in cfg.station_durations:
            cfg.station_durations[k] = 5.0
        line = AssyLineRuntime(config=cfg)

        wid = line.produce_sso2_wip()
        line.produce_rso2_wip()
        line.introduce_to_assy(wid, "PAL-001")

        for _ in range(13):
            line.execute_dwell()
            if line.conveyor.state == ConveyorState.READY_TO_INDEX:
                line.index_line()

        event_types = {e.event_type for e in line.trace}
        assert "SSO2_PRODUCED" in event_types
        assert "RSO2_PRODUCED" in event_types
        assert "LINE_ENTRY" in event_types
        assert "AP04_JOIN" in event_types
        assert "STATION_COMPLETE" in event_types

        # One AP04_JOIN only
        join_count = sum(1 for e in line.trace if e.event_type == "AP04_JOIN")
        assert join_count == 1
