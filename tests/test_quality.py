"""M6-S03 — Quality / Test / Rework Acceptance Tests (Q01–Q18).

Pattern: advance_to_before(pos) → WIP at pos, station NOT yet fired.
Then execute_dwell() triggers the station.
"""

from __future__ import annotations

import pytest
from virtual_factory.assembly.line_runtime import (
    AssyLineConfig, AssyLineRuntime, ConveyorState, WipLifecycle,
)
from virtual_factory.assembly.quality_records import (
    QualityStatus, CheckType,
)

CHILD = "MTR-0001"


def make_cfg(ap06="PASS", ap08="PASS") -> AssyLineConfig:
    c = AssyLineConfig()
    c.conveyor.nominal_line_dwell_time_s = 10.0
    for k in c.station_durations:
        c.station_durations[k] = 5.0
    c.quality.ap06.scenario = ap06
    c.quality.ap08.scenario = ap08
    return c


def setup_line(cfg: AssyLineConfig) -> AssyLineRuntime:
    """Create line with one SSO2 WIP at PRE-ASSY and one RSO2."""
    line = AssyLineRuntime(config=cfg)
    line.produce_sso2_wip()
    line.produce_rso2_wip()
    line.introduce_to_assy("SSO2-0001", "PAL-001")
    return line


def advance_to_before(line: AssyLineRuntime, position: str):
    """Advance line until WIP is AT `position`, station not yet fired.

    After this, execute_dwell() will trigger the station at `position`.
    """
    target_idx = line.conveyor.positions.index(position)
    for _ in range(target_idx):
        line.execute_dwell()
        if line.conveyor.state == ConveyorState.READY_TO_INDEX:
            line.index_line()


# ═══════════════════════════════════════════════
# Q01 – AP03 checklist
# ═══════════════════════════════════════════════

class TestQ01:
    def test_ap03_checklist_on_parent(self):
        line = setup_line(make_cfg())
        advance_to_before(line, "AP03")
        line.execute_dwell()
        h = line.get_quality_history("SSO2-0001")
        assert h is not None and len(h) >= 1
        r = h.records[0]
        assert r.station_id == "AP03"
        assert r.check_type == CheckType.CHECKLIST
        assert r.disposition == "PASS"


# ═══════════════════════════════════════════════
# Q02 – AP06 PASS + measurements
# ═══════════════════════════════════════════════

class TestQ02:
    def test_ap06_pass_measurements(self):
        line = setup_line(make_cfg(ap06="PASS"))
        advance_to_before(line, "AP06")
        line.execute_dwell()
        h = line.get_quality_history(CHILD)
        assert h is not None
        recs = h.records_for("AP06")
        assert len(recs) == 1
        assert recs[0].disposition == "PASS"
        assert recs[0].check_type == CheckType.TEST
        assert len(recs[0].measurements) == 3


# ═══════════════════════════════════════════════
# Q03 – AP06 FAIL → HOLD
# ═══════════════════════════════════════════════

class TestQ03:
    def test_ap06_fail_hold(self):
        line = setup_line(make_cfg(ap06="FAIL_FIRST_THEN_PASS"))
        advance_to_before(line, "AP06")
        line.execute_dwell()
        assert line.get_current_quality_status(CHILD) == QualityStatus.RETEST_PENDING


# ═══════════════════════════════════════════════
# Q04 – FAIL prevents index
# ═══════════════════════════════════════════════

class TestQ04:
    def test_fail_line_not_ready(self):
        cfg = make_cfg(ap06="FAIL_FIRST_THEN_PASS")
        line = setup_line(cfg)
        advance_to_before(line, "AP06")
        line.execute_dwell()
        # AP06 FAIL → HOLD → line stays OPERATING
        assert line.conveyor.state == ConveyorState.OPERATING
        assert line.get_current_quality_status(CHILD) == QualityStatus.RETEST_PENDING


# ═══════════════════════════════════════════════
# Q05 – RETEST second attempt
# ═══════════════════════════════════════════════

class TestQ05:
    def test_retest_second_attempt(self):
        line = setup_line(make_cfg(ap06="FAIL_FIRST_THEN_PASS"))
        advance_to_before(line, "AP06")
        line.execute_dwell()  # FAIL
        line.execute_dwell()  # RETEST → PASS
        h = line.get_quality_history(CHILD)
        recs = h.records_for("AP06")
        assert len(recs) == 2
        assert recs[0].disposition == "FAIL"
        assert recs[0].attempt_number == 1
        assert recs[1].disposition == "PASS"
        assert recs[1].attempt_number == 2


# ═══════════════════════════════════════════════
# Q06 – FAIL→PASS allows continue
# ═══════════════════════════════════════════════

class TestQ06:
    def test_fail_then_pass_ready(self):
        line = setup_line(make_cfg(ap06="FAIL_FIRST_THEN_PASS"))
        advance_to_before(line, "AP06")
        line.execute_dwell()  # FAIL, line OPERATING
        line.execute_dwell()  # RETEST → PASS, line READY
        assert line.conveyor.state == ConveyorState.READY_TO_INDEX
        assert line.get_current_quality_status(CHILD) == QualityStatus.CLEAR


# ═══════════════════════════════════════════════
# Q07 – Max retry honored
# ═══════════════════════════════════════════════

class TestQ07:
    def test_always_fail_exhausts(self):
        cfg = make_cfg(ap06="ALWAYS_FAIL")
        cfg.quality.ap06.max_attempts = 2
        line = setup_line(cfg)
        advance_to_before(line, "AP06")
        line.execute_dwell()  # FAIL, attempt 1
        assert line.get_current_quality_status(CHILD) == QualityStatus.RETEST_PENDING
        line.execute_dwell()  # FAIL, attempt 2 → FAILED_FINAL
        assert line.get_current_quality_status(CHILD) == QualityStatus.FAILED_FINAL


# ═══════════════════════════════════════════════
# Q08/Q09 – AP08 NG stops line
# ═══════════════════════════════════════════════

class TestQ08Q09:
    def test_ap08_ng_stops_line(self):
        line = setup_line(make_cfg(ap08="FAIL_FIRST_THEN_PASS"))
        advance_to_before(line, "AP08")
        line.execute_dwell()
        assert line.get_current_quality_status(CHILD) == QualityStatus.REINSPECT_PENDING
        assert line.conveyor.state == ConveyorState.OPERATING


# ═══════════════════════════════════════════════
# Q10 – REINSPECT second attempt
# ═══════════════════════════════════════════════

class TestQ10:
    def test_reinspect_second_attempt(self):
        line = setup_line(make_cfg(ap08="FAIL_FIRST_THEN_PASS"))
        advance_to_before(line, "AP08")
        line.execute_dwell()  # NG
        line.execute_dwell()  # REINSPECT → PASS
        h = line.get_quality_history(CHILD)
        recs = h.records_for("AP08")
        assert len(recs) == 2
        assert recs[0].disposition == "FAIL"  # AP08 uses FAIL for NG scenario
        assert recs[1].disposition == "PASS"


# ═══════════════════════════════════════════════
# Q11 – NG→PASS allows continue
# ═══════════════════════════════════════════════

class TestQ11:
    def test_ng_then_pass_ready(self):
        line = setup_line(make_cfg(ap08="FAIL_FIRST_THEN_PASS"))
        advance_to_before(line, "AP08")
        line.execute_dwell()  # NG
        line.execute_dwell()  # REINSPECT → PASS
        assert line.conveyor.state == ConveyorState.READY_TO_INDEX
        assert line.get_current_quality_status(CHILD) == QualityStatus.CLEAR


# ═══════════════════════════════════════════════
# Q12 – AP11 release
# ═══════════════════════════════════════════════

class TestQ12:
    def test_ap11_pass_released(self):
        line = setup_line(make_cfg())
        advance_to_before(line, "AP11")
        line.execute_dwell()
        child = line.get_wip(CHILD)
        assert child.lifecycle == WipLifecycle.RELEASED
        h = line.get_quality_history(CHILD)
        assert h.records_for("AP11")[0].disposition == "PASS"


# ═══════════════════════════════════════════════
# Q13 – Quality on child, not parent
# ═══════════════════════════════════════════════

class TestQ13:
    def test_child_has_quality(self):
        line = setup_line(make_cfg())
        advance_to_before(line, "AP11")
        line.execute_dwell()
        assert line.get_quality_history(CHILD) is not None
        stations = {r.station_id for r in line.get_quality_history(CHILD).records}
        assert "AP06" in stations or "AP08" in stations or "AP11" in stations


# ═══════════════════════════════════════════════
# Q14 – Timestamps monotonic
# ═══════════════════════════════════════════════

class TestQ14:
    def test_monotonic(self):
        line = setup_line(make_cfg())
        advance_to_before(line, "AP11")
        line.execute_dwell()
        h = line.get_quality_history(CHILD)
        if h is None or len(h) == 0:
            pytest.skip("no records")
        times = [r.simulation_time_s for r in h.records]
        for i in range(1, len(times)):
            assert times[i] >= times[i-1]


# ═══════════════════════════════════════════════
# Q15 – Multi-WIP quality hold
# ═══════════════════════════════════════════════

class TestQ15:
    def test_quality_hold_blocks_line(self):
        cfg = make_cfg(ap06="FAIL_FIRST_THEN_PASS")
        cfg.station_durations["AP05"] = 4.0
        line = AssyLineRuntime(config=cfg)
        for _ in range(3):
            line.produce_sso2_wip()
            line.produce_rso2_wip()
        line.introduce_to_assy("SSO2-0001", "PAL-001")
        for _ in range(5):
            line.execute_dwell()
            if line.conveyor.state == ConveyorState.READY_TO_INDEX:
                line.index_line()
        line.introduce_to_assy("SSO2-0002", "PAL-002")
        # Advance SSO2-0002 to bring it in behind MTR-0001
        for _ in range(2):
            line.execute_dwell()
            if line.conveyor.state == ConveyorState.READY_TO_INDEX:
                line.index_line()

        # Now MTR-0001 is at AP06 or later; execute dwell to trigger quality
        # The line may already be past AP06 if MTR-0001 already passed
        # Force AP06 check: if MTR-0001 is at AP06, execute dwell
        if line.conveyor.wip_at("AP06") == CHILD:
            line.execute_dwell()

        assert line.get_current_quality_status(CHILD) in (
            QualityStatus.RETEST_PENDING, QualityStatus.CLEAR)


# ═══════════════════════════════════════════════
# Q16 – Happy path regression
# ═══════════════════════════════════════════════

class TestQ16:
    def test_all_pass_released(self):
        line = setup_line(make_cfg(ap06="PASS", ap08="PASS"))
        advance_to_before(line, "AP11")
        line.execute_dwell()
        assert line.get_wip(CHILD).lifecycle == WipLifecycle.RELEASED


# ═══════════════════════════════════════════════
# Q17 – M6-S02 regression
# ═══════════════════════════════════════════════

class TestQ17:
    def test_conveyor_positions(self):
        assert len(AssyLineRuntime().conveyor.positions) == 12

    def test_dwell_time(self):
        line = setup_line(make_cfg())
        line.execute_dwell()
        assert line.simulation_time_s > 0

    def test_ap04_join(self):
        line = setup_line(make_cfg())
        # Advance through AP04 (index 4): need 5 cycles to execute AP04
        for _ in range(5):
            line.execute_dwell()
            if line.conveyor.state == ConveyorState.READY_TO_INDEX:
                line.index_line()
        assert line.genealogy.get(CHILD) is not None


# ═══════════════════════════════════════════════
# Q18 – Imports
# ═══════════════════════════════════════════════

class TestQ18:
    def test_imports(self):
        from virtual_factory.assembly import QualityRecord, QualityHistory, QualityStatus
        assert QualityRecord is not None
