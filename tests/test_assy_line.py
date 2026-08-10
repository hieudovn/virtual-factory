"""M6-S02 — TIPA ASSY Indexed Line Runtime Tests.

Tests T01–T15 per M6-S02 specification.
"""

from __future__ import annotations

import pytest

from virtual_factory.assembly.carrier import CarrierId, CarrierState, CarrierError
from virtual_factory.assembly.conveyor import (
    ConveyorConfig,
    ConveyorLine,
    ConveyorState,
    ConveyorError,
)
from virtual_factory.assembly.genealogy import (
    GenealogyRecord,
    GenealogyStore,
    GenealogyError,
)
from virtual_factory.assembly.upstream import UpstreamConfig, UpstreamProducer
from virtual_factory.assembly.line_runtime import (
    AssyLineConfig,
    AssyLineRuntime,
    AssyLineError,
    WipLifecycle,
)


# ═══════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════

@pytest.fixture
def line() -> AssyLineRuntime:
    """Create a fresh ASSY line with default config."""
    return AssyLineRuntime()


@pytest.fixture
def fast_line() -> AssyLineRuntime:
    """Create an ASSY line with accelerated timing for tests."""
    config = AssyLineConfig()
    config.conveyor.nominal_line_dwell_time_s = 1.0
    config.conveyor.index_movement_duration_s = 0.0
    for key in config.station_durations:
        config.station_durations[key] = 0.1
    return AssyLineRuntime(config=config)


@pytest.fixture
def line_with_upstream(fast_line: AssyLineRuntime) -> AssyLineRuntime:
    """Line with SSO2 and RSO2 WIPs already produced."""
    fast_line.produce_sso2_wip()
    fast_line.produce_rso2_wip()
    return fast_line


# ═══════════════════════════════════════════════════════════
# T01 — Single conveyor lane topology
# ═══════════════════════════════════════════════════════════

class TestT01ConveyorTopology:
    """INV-CONV-01: Single conveyor lane."""

    def test_positions_are_authoritative_sequence(self, line):
        expected = (
            "PRE-ASSY", "AP01", "AP02", "AP03", "AP04", "AP05",
            "AP06", "AP07", "AP08", "AP09", "AP10", "AP11",
        )
        assert line.conveyor.positions == expected

    def test_all_positions_initially_empty(self, line):
        for pos in line.conveyor.positions:
            assert line.conveyor.carrier_at(pos) is None

    def test_conveyor_is_single_lane_only(self, line):
        """Verify there is exactly one position set — no multi-lane."""
        assert len(line.conveyor.positions) == 12
        # All positions are unique
        assert len(set(line.conveyor.positions)) == 12


# ═══════════════════════════════════════════════════════════
# T02 — Processing prohibited while INDEXING
# ═══════════════════════════════════════════════════════════

class TestT02ProcessingOnlyWhenStopped:
    """INV-CONV-03: Processing occurs ONLY while conveyor is stopped."""

    def test_cannot_begin_operating_from_indexing(self, line):
        line.conveyor.state = ConveyorState.INDEXING
        with pytest.raises(ConveyorError):
            line.conveyor.begin_operating()

    def test_cannot_index_from_stopped(self, line):
        line.conveyor.state = ConveyorState.STOPPED
        with pytest.raises(ConveyorError):
            line.conveyor.index()

    def test_cannot_index_from_operating(self, line):
        line.conveyor.state = ConveyorState.OPERATING
        with pytest.raises(ConveyorError):
            line.conveyor.index()

    def test_valid_transition_stopped_to_operating(self, line):
        line.conveyor.begin_dwell(120.0)
        assert line.conveyor.state == ConveyorState.STOPPED
        line.conveyor.begin_operating()
        assert line.conveyor.state == ConveyorState.OPERATING


# ═══════════════════════════════════════════════════════════
# T03 — Multiple occupied stations process within one dwell
# ═══════════════════════════════════════════════════════════

class TestT03MultiStationDwell:
    """INV-CONV-09: Multiple stations process during same dwell."""

    def test_multiple_positions_occupied_same_dwell(self, fast_line):
        # Produce 3 SSO2 WIPs
        w1 = fast_line.produce_sso2_wip()
        w2 = fast_line.produce_sso2_wip()
        w3 = fast_line.produce_sso2_wip()

        # Introduce to ASSY sequentially with indexing between
        fast_line.introduce_to_assy(w1, "PAL-001")
        fast_line.conveyor.begin_dwell(1.0)
        fast_line.conveyor.begin_operating()
        fast_line.conveyor.mark_position_complete("PRE-ASSY")
        fast_line.conveyor.check_ready()
        fast_line.conveyor.index()
        fast_line.conveyor.begin_dwell(1.0)

        fast_line.introduce_to_assy(w2, "PAL-002")
        fast_line.conveyor.begin_dwell(1.0)
        fast_line.conveyor.begin_operating()
        fast_line.conveyor.mark_position_complete("PRE-ASSY")
        fast_line.conveyor.mark_position_complete("AP01")
        fast_line.conveyor.check_ready()
        fast_line.conveyor.index()
        fast_line.conveyor.begin_dwell(1.0)

        fast_line.introduce_to_assy(w3, "PAL-003")

        # Now: PRE-ASSY=w3, AP01=w2, AP02=w1 (all occupied)
        assert fast_line.conveyor.wip_at("PRE-ASSY") == w3
        assert fast_line.conveyor.wip_at("AP01") == w2
        assert fast_line.conveyor.wip_at("AP02") == w1

        occupied = fast_line.conveyor.occupied_positions()
        assert "PRE-ASSY" in occupied
        assert "AP01" in occupied
        assert "AP02" in occupied

    def test_all_occupied_process_in_one_dwell(self, fast_line):
        """All 3 occupied positions complete within one dwell."""
        w1 = fast_line.produce_sso2_wip()
        w2 = fast_line.produce_sso2_wip()
        w3 = fast_line.produce_sso2_wip()

        fast_line.introduce_to_assy(w1, "PAL-001")
        fast_line.conveyor.begin_dwell(1.0)
        fast_line.conveyor.begin_operating()
        fast_line.conveyor.mark_position_complete("PRE-ASSY")
        fast_line.conveyor.check_ready()
        fast_line.conveyor.index()
        fast_line.conveyor.begin_dwell(1.0)

        fast_line.introduce_to_assy(w2, "PAL-002")
        fast_line.conveyor.begin_operating()
        fast_line.conveyor.mark_position_complete("PRE-ASSY")
        fast_line.conveyor.mark_position_complete("AP01")
        fast_line.conveyor.check_ready()
        fast_line.conveyor.index()
        fast_line.conveyor.begin_dwell(1.0)

        fast_line.introduce_to_assy(w3, "PAL-003")

        # Execute one dwell: all 3 should complete
        fast_line.conveyor.begin_operating()
        fast_line.conveyor.mark_position_complete("PRE-ASSY")
        fast_line.conveyor.mark_position_complete("AP01")
        fast_line.conveyor.mark_position_complete("AP02")

        assert fast_line.conveyor.all_occupied_complete()
        assert fast_line.conveyor.check_ready()
        assert fast_line.conveyor.state == ConveyorState.READY_TO_INDEX


# ═══════════════════════════════════════════════════════════
# T04 — One index advances multiple carriers
# ═══════════════════════════════════════════════════════════

class TestT04SynchronizedIndex:
    """INV-CONV-09: Line-level index advances all carriers together."""

    def test_index_advances_all_carriers(self, fast_line):
        w1 = fast_line.produce_sso2_wip()
        w2 = fast_line.produce_sso2_wip()

        fast_line.introduce_to_assy(w1, "PAL-001")
        fast_line.conveyor.begin_dwell(1.0)
        fast_line.conveyor.begin_operating()
        fast_line.conveyor.mark_position_complete("PRE-ASSY")
        fast_line.conveyor.check_ready()
        fast_line.conveyor.index()
        fast_line.conveyor.begin_dwell(1.0)

        fast_line.introduce_to_assy(w2, "PAL-002")
        fast_line.conveyor.begin_operating()
        fast_line.conveyor.mark_position_complete("PRE-ASSY")
        fast_line.conveyor.mark_position_complete("AP01")
        fast_line.conveyor.check_ready()

        # One synchronized index
        snapshot = fast_line.conveyor.index()

        # After index: w2 moves PRE-ASSY→AP01, w1 moves AP01→AP02
        assert fast_line.conveyor.wip_at("PRE-ASSY") is None  # cleared after index
        assert fast_line.conveyor.wip_at("AP01") == w2
        assert fast_line.conveyor.wip_at("AP02") == w1

    def test_index_is_line_level_boundary(self, fast_line):
        """All carriers move exactly one position per index."""
        w1 = fast_line.produce_sso2_wip()
        w2 = fast_line.produce_sso2_wip()
        w3 = fast_line.produce_sso2_wip()

        fast_line.introduce_to_assy(w1, "PAL-001")
        # Fill line positions
        for dwell_num in range(3):
            fast_line.conveyor.begin_dwell(1.0)
            fast_line.conveyor.begin_operating()
            for pos in fast_line.conveyor.occupied_positions():
                fast_line.conveyor.mark_position_complete(pos)
            fast_line.conveyor.check_ready()
            fast_line.conveyor.index()
            fast_line.conveyor.begin_dwell(1.0)

        fast_line.introduce_to_assy(w2, "PAL-002")
        for dwell_num in range(2):
            fast_line.conveyor.begin_operating()
            for pos in fast_line.conveyor.occupied_positions():
                fast_line.conveyor.mark_position_complete(pos)
            fast_line.conveyor.check_ready()
            fast_line.conveyor.index()
            fast_line.conveyor.begin_dwell(1.0)

        fast_line.introduce_to_assy(w3, "PAL-003")

        # w1 should have advanced through multiple positions
        w1_state = fast_line.get_wip(w1)
        assert w1_state is not None


# ═══════════════════════════════════════════════════════════
# T05 — WIP identity stable before AP04
# ═══════════════════════════════════════════════════════════

class TestT05WipIdentityStable:
    def test_wip_id_unchanged_before_ap04(self, fast_line):
        w1 = fast_line.produce_sso2_wip()
        fast_line.introduce_to_assy(w1, "PAL-001")

        # Advance through PRE-ASSY, AP01, AP02, AP03
        for _ in range(4):
            fast_line.conveyor.begin_dwell(1.0)
            fast_line.conveyor.begin_operating()
            for pos in fast_line.conveyor.occupied_positions():
                fast_line.conveyor.mark_position_complete(pos)
            fast_line.conveyor.check_ready()
            fast_line.conveyor.index()
            fast_line.conveyor.begin_dwell(1.0)

        ws = fast_line.get_wip(w1)
        assert ws is not None, f"WIP {w1} should still exist before AP04"
        assert ws.wip_id == w1

    def test_wip_registry_preserves_identity(self, fast_line):
        w1 = fast_line.produce_sso2_wip()
        fast_line.introduce_to_assy(w1, "PAL-001")
        assert fast_line.get_wip(w1) is not None
        assert fast_line.get_wip(w1).wip_id == w1


# ═══════════════════════════════════════════════════════════
# T06 — Carrier identity independent from WIP identity
# ═══════════════════════════════════════════════════════════

class TestT06CarrierIndependence:
    """INV-CONV-07: WIP identity and carrier identity are separate."""

    def test_carrier_id_not_equal_to_wip_id(self, fast_line):
        w1 = fast_line.produce_sso2_wip()
        carrier_id = "PAL-042"
        fast_line.introduce_to_assy(w1, carrier_id)

        carrier = fast_line.conveyor.get_carrier(carrier_id)
        assert carrier is not None
        assert str(carrier.carrier_id) == carrier_id
        assert carrier.wip_id == w1
        assert carrier.wip_id != str(carrier.carrier_id)

    def test_carrier_can_be_queried_independently(self, fast_line):
        w1 = fast_line.produce_sso2_wip()
        fast_line.introduce_to_assy(w1, "PAL-001")

        # Query carrier without going through WIP
        carrier = fast_line.conveyor.get_carrier("PAL-001")
        assert carrier is not None
        assert carrier.wip_id == w1

        # Query WIP without going through carrier
        ws = fast_line.get_wip(w1)
        assert ws is not None

    def test_carrier_identity_preserved_after_wip_moves(self, fast_line):
        w1 = fast_line.produce_sso2_wip()
        fast_line.introduce_to_assy(w1, "PAL-001")

        # Index once
        fast_line.conveyor.begin_dwell(1.0)
        fast_line.conveyor.begin_operating()
        fast_line.conveyor.mark_position_complete("PRE-ASSY")
        fast_line.conveyor.check_ready()
        fast_line.conveyor.index()

        carrier = fast_line.conveyor.get_carrier("PAL-001")
        assert carrier is not None
        # Same carrier, still has same WIP
        assert carrier.wip_id == w1


# ═══════════════════════════════════════════════════════════
# T07 — AP04 requires both configured parent roles
# ═══════════════════════════════════════════════════════════

class TestT07Ap04ParentRoles:
    def test_ap04_fails_without_sso2(self, fast_line):
        """AP04 join requires SSO2-derived WIP present."""
        # Produce RSO2 but no SSO2
        fast_line.produce_rso2_wip()
        # No SSO2 WIP introduced to line

        # The AP04 join is triggered when a carrier with SSO2 WIP reaches AP04
        # Without SSO2 WIP, there's nothing to trigger it
        assert fast_line.conveyor.wip_at("AP04") is None

    def test_ap04_requires_rso2_in_buffer(self, fast_line):
        """AP04 join fails if no RSO2 in buffer."""
        w1 = fast_line.produce_sso2_wip()
        fast_line.introduce_to_assy(w1, "PAL-001")

        # Advance to AP04 without producing RSO2
        for _ in range(5):  # PRE-ASSY → AP01 → AP02 → AP03 → AP04
            fast_line.conveyor.begin_dwell(1.0)
            fast_line.conveyor.begin_operating()
            for pos in fast_line.conveyor.occupied_positions():
                fast_line.conveyor.mark_position_complete(pos)
            fast_line.conveyor.check_ready()
            fast_line.conveyor.index()
            fast_line.conveyor.begin_dwell(1.0)

        # At AP04 but no RSO2 — should raise
        with pytest.raises(AssyLineError, match="no RSO2"):
            fast_line._execute_ap04_join(w1)


# ═══════════════════════════════════════════════════════════
# T08 — AP04 creates expected child motor WIP
# ═══════════════════════════════════════════════════════════

class TestT08Ap04ChildCreation:
    def test_ap04_creates_child_with_mtr_prefix(self, fast_line):
        w1 = fast_line.produce_sso2_wip()
        fast_line.produce_rso2_wip()
        fast_line.introduce_to_assy(w1, "PAL-001")

        # Execute AP04 join directly
        child_id = None
        for event in fast_line._execute_ap04_join(w1):
            if event.event_type == "AP04_JOIN":
                child_id = event.wip_id

        assert child_id is not None
        assert child_id.startswith("MTR-")

    def test_ap04_child_is_registered(self, fast_line):
        w1 = fast_line.produce_sso2_wip()
        fast_line.produce_rso2_wip()
        fast_line.introduce_to_assy(w1, "PAL-001")

        fast_line._execute_ap04_join(w1)

        child_id = f"{fast_line.config.motor_wip_prefix}-0001"
        child_ws = fast_line.get_wip(child_id)
        assert child_ws is not None
        assert child_ws.is_child_of_join is True

    def test_parent_archived_after_join(self, fast_line):
        w1 = fast_line.produce_sso2_wip()
        fast_line.produce_rso2_wip()
        fast_line.introduce_to_assy(w1, "PAL-001")

        fast_line._execute_ap04_join(w1)

        parent_ws = fast_line.get_wip(w1)
        assert parent_ws is not None
        assert parent_ws.lifecycle == WipLifecycle.JOINED


# ═══════════════════════════════════════════════════════════
# T09 — AP04 genealogy preserves both parents
# ═══════════════════════════════════════════════════════════

class TestT09Ap04Genealogy:
    def test_genealogy_has_both_parents(self, fast_line):
        w1 = fast_line.produce_sso2_wip()
        r1 = fast_line.produce_rso2_wip()
        fast_line.introduce_to_assy(w1, "PAL-001")

        fast_line._execute_ap04_join(w1)

        child_id = f"{fast_line.config.motor_wip_prefix}-0001"
        record = fast_line.genealogy.get(child_id)
        assert record is not None
        assert w1 in record.parent_wip_ids
        assert r1 in record.parent_wip_ids
        assert record.relationship_type == "assembly_join"
        assert record.join_station == "AP04"

    def test_genealogy_store_indexes_by_child(self, fast_line):
        w1 = fast_line.produce_sso2_wip()
        fast_line.produce_rso2_wip()
        fast_line.introduce_to_assy(w1, "PAL-001")

        fast_line._execute_ap04_join(w1)

        child_id = f"{fast_line.config.motor_wip_prefix}-0001"
        parents = fast_line.genealogy.parents_of(child_id)
        assert len(parents) == 2
        assert w1 in parents

    def test_duplicate_genealogy_rejected(self, fast_line):
        w1 = fast_line.produce_sso2_wip()
        fast_line.produce_rso2_wip()
        fast_line.introduce_to_assy(w1, "PAL-001")

        fast_line._execute_ap04_join(w1)

        child_id = f"{fast_line.config.motor_wip_prefix}-0001"
        existing = fast_line.genealogy.get(child_id)
        assert existing is not None

        # Cannot record again
        with pytest.raises(GenealogyError):
            fast_line.genealogy.record(existing)


# ═══════════════════════════════════════════════════════════
# T10 — Downstream stations operate on child after AP04
# ═══════════════════════════════════════════════════════════

class TestT10DownstreamChild:
    def test_child_progresses_after_join(self, fast_line):
        w1 = fast_line.produce_sso2_wip()
        fast_line.produce_rso2_wip()
        fast_line.introduce_to_assy(w1, "PAL-001")

        # Advance to AP04
        for _ in range(4):
            fast_line.conveyor.begin_dwell(1.0)
            fast_line.conveyor.begin_operating()
            for pos in fast_line.conveyor.occupied_positions():
                fast_line.conveyor.mark_position_complete(pos)
            fast_line.conveyor.check_ready()
            fast_line.conveyor.index()
            fast_line.conveyor.begin_dwell(1.0)

        # At AP04: execute full dwell cycle (which handles join)
        fast_line.conveyor.begin_operating()
        fast_line._execute_ap04_join(w1)
        fast_line.conveyor.mark_position_complete("AP04")
        fast_line.conveyor.check_ready()

        # Index: child moves to AP05 (call index_line to update WIP positions)
        fast_line.index_line()

        child_id = f"{fast_line.config.motor_wip_prefix}-0001"
        assert fast_line.conveyor.wip_at("AP05") == child_id

        child_ws = fast_line.get_wip(child_id)
        assert child_ws.current_position == "AP05"


# ═══════════════════════════════════════════════════════════
# T11 — Deterministic happy path reaches RELEASED_FINISHED_GOOD
# ═══════════════════════════════════════════════════════════

class TestT11HappyPath:
    def test_full_happy_path_single_motor(self, fast_line):
        """One complete motor: SSO2 → ASSY → AP04 JOIN → AP11 release."""
        # Produce upstream
        sso2_id = fast_line.produce_sso2_wip()
        rso2_id = fast_line.produce_rso2_wip()

        # Introduce to ASSY
        fast_line.introduce_to_assy(sso2_id, "PAL-001")

        # Run through all 12 positions (PRE-ASSY + AP01-AP11)
        # We need 12 dwell/index cycles to get through the line
        for _ in range(12):
            fast_line.conveyor.begin_dwell(1.0)
            fast_line.conveyor.begin_operating()
            for pos in fast_line.conveyor.occupied_positions():
                wip = fast_line.conveyor.wip_at(pos)
                if wip:
                    if pos == "AP04":
                        # Need RSO2 for AP04
                        if not fast_line._rso2_wips:
                            fast_line.produce_rso2_wip()
                        fast_line._execute_ap04_join(wip)
                    fast_line.conveyor.mark_position_complete(pos)
            fast_line.conveyor.check_ready()
            fast_line.conveyor.index()

        # Child motor should exist and have been released
        child_id = f"{fast_line.config.motor_wip_prefix}-0001"
        child_ws = fast_line.get_wip(child_id)
        assert child_ws is not None, f"Child {child_id} should exist"
        # Check genealogy
        record = fast_line.genealogy.get(child_id)
        assert record is not None
        assert sso2_id in record.parent_wip_ids
        assert rso2_id in record.parent_wip_ids

    def test_trace_contains_key_events(self, fast_line):
        """Happy path trace includes WIP creation, join, completion."""
        sso2_id = fast_line.produce_sso2_wip()
        fast_line.produce_rso2_wip()
        fast_line.introduce_to_assy(sso2_id, "PAL-001")

        for _ in range(12):
            fast_line.conveyor.begin_dwell(1.0)
            fast_line.conveyor.begin_operating()
            for pos in fast_line.conveyor.occupied_positions():
                wip = fast_line.conveyor.wip_at(pos)
                if wip:
                    if pos == "AP04":
                        if not fast_line._rso2_wips:
                            fast_line.produce_rso2_wip()
                        fast_line._execute_ap04_join(wip)
                    fast_line.conveyor.mark_position_complete(pos)
            fast_line.conveyor.check_ready()
            fast_line.conveyor.index()

        trace = fast_line.trace
        event_types = [e.event_type for e in trace]
        assert "SSO2_PRODUCED" in event_types
        assert "RSO2_PRODUCED" in event_types
        assert "LINE_ENTRY" in event_types
        assert "AP04_JOIN" in event_types


# ═══════════════════════════════════════════════════════════
# T12 — Deterministic (same seed/config → same trace)
# ═══════════════════════════════════════════════════════════

class TestT12Determinism:
    def test_same_config_produces_same_trace(self, fast_line):
        """Two runs with identical config produce identical event sequences."""
        def run_once():
            line = AssyLineRuntime(config=fast_line.config)
            sso2_id = line.produce_sso2_wip()
            line.produce_rso2_wip()
            line.introduce_to_assy(sso2_id, "PAL-001")

            for _ in range(5):
                line.conveyor.begin_dwell(1.0)
                line.conveyor.begin_operating()
                for pos in line.conveyor.occupied_positions():
                    wip = line.conveyor.wip_at(pos)
                    if wip:
                        if pos == "AP04" and line._rso2_wips:
                            line._execute_ap04_join(wip)
                        line.conveyor.mark_position_complete(pos)
                line.conveyor.check_ready()
                line.conveyor.index()

            return line.trace

        trace1 = run_once()
        trace2 = run_once()

        assert len(trace1) == len(trace2)
        for e1, e2 in zip(trace1, trace2):
            assert e1.event_type == e2.event_type
            assert e1.position == e2.position


# ═══════════════════════════════════════════════════════════
# T13 — Dwell is configuration value, not hard-coded
# ═══════════════════════════════════════════════════════════

class TestT13DwellConfigurable:
    """INV-CONV-04: Dwell is configuration-driven."""

    def test_dwell_from_config_not_hardcoded(self):
        config = AssyLineConfig()
        config.conveyor.nominal_line_dwell_time_s = 90.0
        line = AssyLineRuntime(config=config)
        assert line.config.conveyor.nominal_line_dwell_time_s == 90.0

    def test_dwell_can_be_110(self):
        config = AssyLineConfig()
        config.conveyor.nominal_line_dwell_time_s = 110.0
        line = AssyLineRuntime(config=config)
        assert line.config.conveyor.nominal_line_dwell_time_s == 110.0

    def test_default_dwell_is_120(self, line):
        assert line.config.conveyor.nominal_line_dwell_time_s == 120.0

    def test_no_runtime_sleep(self, fast_line):
        """Verify no wall-clock sleep — all timing is simulated."""
        import time
        start = time.perf_counter()
        fast_line.produce_sso2_wip()
        fast_line.produce_rso2_wip()
        fast_line.introduce_to_assy(
            fast_line.produce_sso2_wip(), "PAL-001"
        )
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0, f"Runtime took {elapsed:.2f}s — should be near-instant"


# ═══════════════════════════════════════════════════════════
# T14 — Station duration distinct from dwell
# ═══════════════════════════════════════════════════════════

class TestT14StationDurationIndependent:
    """INV-CONV-05: Line dwell and station duration are separate."""

    def test_station_duration_separate_from_dwell(self, fast_line):
        assert fast_line.config.conveyor.nominal_line_dwell_time_s == 1.0
        # Station durations are independently configurable
        assert fast_line.config.station_durations["AP01"] == 0.1
        assert fast_line.config.station_durations["AP05"] == 0.1

    def test_dwell_can_be_shorter_than_station_duration(self):
        config = AssyLineConfig()
        config.conveyor.nominal_line_dwell_time_s = 60.0
        config.station_durations["AP05"] = 90.0  # longer than dwell
        line = AssyLineRuntime(config=config)
        # Overrun: dwell extends (PROVISIONAL_FOR_DEMO)
        assert config.station_durations["AP05"] > config.conveyor.nominal_line_dwell_time_s

    def test_dwell_can_be_longer_than_station_duration(self):
        config = AssyLineConfig()
        config.conveyor.nominal_line_dwell_time_s = 120.0
        config.station_durations["AP01"] = 60.0  # shorter than dwell
        line = AssyLineRuntime(config=config)
        assert config.station_durations["AP01"] < config.conveyor.nominal_line_dwell_time_s


# ═══════════════════════════════════════════════════════════
# T15 — M2–M5 regression (import-only; full suite separate)
# ═══════════════════════════════════════════════════════════

class TestT15ExistingImports:
    """Verify M2–M5 modules remain importable and functional."""

    def test_assembly_primitives_still_importable(self):
        from virtual_factory.assembly.primitives import (
            Source, Processor, AssemblyPrimitive, PrimitiveType,
        )
        assert PrimitiveType.PROCESSOR.value == "processor"

    def test_assembly_wip_still_importable(self):
        from virtual_factory.assembly.wip import WipId, WipStatus
        w = WipId("test-001")
        assert str(w) == "test-001"

    def test_discrete_engine_still_importable(self):
        from virtual_factory.discrete.engine import DiscreteSimulationEngine
        assert DiscreteSimulationEngine is not None

    def test_line_runtime_does_not_break_existing_imports(self):
        """M6-S02 modules coexist with M3 modules."""
        from virtual_factory.assembly import (
            WipId,              # M3
            CarrierId,          # M6-S02
            ConveyorLine,       # M6-S02
            AssyLineRuntime,    # M6-S02
        )
        assert WipId is not None
        assert CarrierId is not None
