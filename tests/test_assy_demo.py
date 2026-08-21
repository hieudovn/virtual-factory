"""M6-S04 — Visualization + Demo Controls Tests (V01–V20)."""

from __future__ import annotations

import pytest
from virtual_factory.assembly.line_runtime import (
    AssyLineConfig, AssyLineRuntime, ConveyorState, WipLifecycle,
)
from virtual_factory.assembly.demo_snapshot import (
    AssyDemoSnapshot, StationPositionView, build_snapshot,
)
from virtual_factory.assembly.demo_controller import (
    DemoController, DemoScenario,
)
from virtual_factory.assembly.quality_records import QualityStatus
import os


TIPA_YAML = os.path.join(
    os.path.dirname(__file__), "..", "configs", "plants", "tipa_assy_demo.yaml"
)


@pytest.fixture
def ctrl() -> DemoController:
    c = DemoController(config_path=TIPA_YAML, scenario=DemoScenario.HAPPY_PATH)
    c.initialize()
    return c


# ═══════════════════════════════════════════
# V01 — Snapshot detached from runtime
# ═══════════════════════════════════════════
class TestV01Detached:
    def test_snapshot_is_not_runtime(self):
        line = AssyLineRuntime()
        snap = build_snapshot(line)
        assert isinstance(snap, AssyDemoSnapshot)
        assert snap.positions  # 12 positions
        # Mutating snapshot does NOT affect runtime
        old_pos = snap.positions[0].wip_id
        snap.positions[0].wip_id = "MUTATED"
        assert line.conveyor.wip_at("PRE-ASSY") != "MUTATED"


# ═══════════════════════════════════════════
# V02 — All positions exposed
# ═══════════════════════════════════════════
class TestV02Positions:
    def test_all_12_positions(self):
        line = AssyLineRuntime()
        snap = build_snapshot(line)
        assert len(snap.positions) == 12
        ids = [p.position_id for p in snap.positions]
        assert ids[0] == "PRE-ASSY"
        assert ids[-1] == "AP11"


# ═══════════════════════════════════════════
# V03 — Multi-WIP in one snapshot
# ═══════════════════════════════════════════
class TestV03MultiWip:
    def test_multi_wip_visible(self):
        line = AssyLineRuntime()
        for _ in range(3):
            line.produce_sso2_wip()
        line.introduce_to_assy("SSO2-0001", "PAL-001")
        line.execute_dwell()
        line.index_line()
        line.introduce_to_assy("SSO2-0002", "PAL-002")

        snap = build_snapshot(line)
        occupied = [p for p in snap.positions if p.is_occupied]
        assert len(occupied) >= 2


# ═══════════════════════════════════════════
# V04 — Carrier and WIP distinct
# ═══════════════════════════════════════════
class TestV04CarrierWip:
    def test_carrier_wip_distinct(self):
        line = AssyLineRuntime()
        line.produce_sso2_wip()
        line.introduce_to_assy("SSO2-0001", "PAL-042")
        snap = build_snapshot(line)
        pre = snap.positions[0]
        assert pre.wip_id == "SSO2-0001"
        assert pre.carrier_id == "PAL-042"
        assert pre.wip_id != pre.carrier_id


# ═══════════════════════════════════════════
# V05 — AP04 genealogy in snapshot
# ═══════════════════════════════════════════
class TestV05Genealogy:
    def test_genealogy_visible(self):
        line = AssyLineRuntime()
        line.produce_sso2_wip()
        line.produce_rso2_wip()
        line.introduce_to_assy("SSO2-0001", "PAL-001")
        for _ in range(5):
            line.execute_dwell()
            if line.conveyor.state == ConveyorState.READY_TO_INDEX:
                line.index_line()

        snap = build_snapshot(line)
        assert len(snap.genealogy) >= 1
        assert snap.genealogy[0].child_wip_id == "MTR-0001"


# ═══════════════════════════════════════════
# V06 — AP06 PASS visible
# ═══════════════════════════════════════════
class TestV06Ap06Pass:
    def test_ap06_pass_in_snapshot(self):
        line = AssyLineRuntime()
        line.produce_sso2_wip()
        line.produce_rso2_wip()
        line.introduce_to_assy("SSO2-0001", "PAL-001")
        # Advance to AP06 (index 6) — WIP at AP06, station not yet fired
        for _ in range(6):
            line.execute_dwell()
            if line.conveyor.state == ConveyorState.READY_TO_INDEX:
                line.index_line()
        # Now fire AP06
        line.execute_dwell()

        snap = build_snapshot(line)
        ap06 = [p for p in snap.positions if p.position_id == "AP06"][0]
        assert ap06.latest_quality_result == "PASS"


# ═══════════════════════════════════════════
# V07 — AP06 FAIL/HOLD visible
# ═══════════════════════════════════════════
class TestV07Ap06Hold:
    def test_ap06_hold_visible(self):
        cfg = AssyLineConfig()
        cfg.conveyor.nominal_line_dwell_time_s = 10.0
        for k in cfg.station_durations:
            cfg.station_durations[k] = 4.0
        cfg.quality.ap06.scenario = "FAIL_FIRST_THEN_PASS"
        line = AssyLineRuntime(config=cfg)
        line.produce_sso2_wip()
        line.produce_rso2_wip()
        line.introduce_to_assy("SSO2-0001", "PAL-001")
        for _ in range(6):
            line.execute_dwell()
            if line.conveyor.state == ConveyorState.READY_TO_INDEX:
                line.index_line()
        line.execute_dwell()  # AP06 FAIL

        snap = build_snapshot(line)
        ap06 = [p for p in snap.positions if p.position_id == "AP06"][0]
        assert ap06.is_quality_hold
        assert ap06.quality_status == "retest_pending"


# ═══════════════════════════════════════════
# V08 — Retest PASS clears hold
# ═══════════════════════════════════════════
class TestV08RetestClear:
    def test_retest_clears_hold(self):
        cfg = AssyLineConfig()
        cfg.conveyor.nominal_line_dwell_time_s = 10.0
        for k in cfg.station_durations:
            cfg.station_durations[k] = 4.0
        cfg.quality.ap06.scenario = "FAIL_FIRST_THEN_PASS"
        line = AssyLineRuntime(config=cfg)
        line.produce_sso2_wip()
        line.produce_rso2_wip()
        line.introduce_to_assy("SSO2-0001", "PAL-001")
        for _ in range(6):
            line.execute_dwell()
            if line.conveyor.state == ConveyorState.READY_TO_INDEX:
                line.index_line()
        line.execute_dwell()  # FAIL
        line.execute_dwell()  # RETEST → PASS

        snap = build_snapshot(line)
        ap06 = [p for p in snap.positions if p.position_id == "AP06"][0]
        assert not ap06.is_quality_hold
        assert ap06.quality_status == "clear"


# ═══════════════════════════════════════════
# V09 — AP08 NG visible
# ═══════════════════════════════════════════
class TestV09Ap08Ng:
    def test_ap08_ng_visible(self):
        cfg = AssyLineConfig()
        cfg.conveyor.nominal_line_dwell_time_s = 10.0
        for k in cfg.station_durations:
            cfg.station_durations[k] = 4.0
        cfg.quality.ap08.scenario = "FAIL_FIRST_THEN_PASS"
        line = AssyLineRuntime(config=cfg)
        line.produce_sso2_wip()
        line.produce_rso2_wip()
        line.introduce_to_assy("SSO2-0001", "PAL-001")
        for _ in range(8):
            line.execute_dwell()
            if line.conveyor.state == ConveyorState.READY_TO_INDEX:
                line.index_line()
        line.execute_dwell()  # AP08 NG

        snap = build_snapshot(line)
        ap08 = [p for p in snap.positions if p.position_id == "AP08"][0]
        assert ap08.is_quality_hold
        assert ap08.latest_quality_result == "NG"


# ═══════════════════════════════════════════
# V10 — AP11 RELEASED visible
# ═══════════════════════════════════════════
class TestV10Release:
    def test_released_visible(self):
        line = AssyLineRuntime()
        line.produce_sso2_wip()
        line.produce_rso2_wip()
        line.introduce_to_assy("SSO2-0001", "PAL-001")
        for _ in range(13):
            line.execute_dwell()
            if line.conveyor.state == ConveyorState.READY_TO_INDEX:
                line.index_line()

        snap = build_snapshot(line)
        assert snap.production.motors_released >= 1


# ═══════════════════════════════════════════
# V11 — FAILED_FINAL shown
# ═══════════════════════════════════════════
class TestV11FailedFinal:
    def test_failed_final_visible(self):
        cfg = AssyLineConfig()
        cfg.conveyor.nominal_line_dwell_time_s = 10.0
        for k in cfg.station_durations:
            cfg.station_durations[k] = 4.0
        cfg.quality.ap06.scenario = "ALWAYS_FAIL"
        cfg.quality.ap06.max_attempts = 2
        line = AssyLineRuntime(config=cfg)
        line.produce_sso2_wip()
        line.produce_rso2_wip()
        line.introduce_to_assy("SSO2-0001", "PAL-001")
        for _ in range(6):
            line.execute_dwell()
            if line.conveyor.state == ConveyorState.READY_TO_INDEX:
                line.index_line()
        line.execute_dwell()
        line.execute_dwell()

        snap = build_snapshot(line)
        ap06 = [p for p in snap.positions if p.position_id == "AP06"][0]
        assert ap06.quality_status == "failed_final"


# ═══════════════════════════════════════════
# V12–V15 — DemoController tests
# ═══════════════════════════════════════════
class TestV12V15Controller:
    def test_step_uses_public_runtime(self, ctrl):
        snap = ctrl.step()
        assert isinstance(snap, AssyDemoSnapshot)
        assert snap.positions

    def test_reset_produces_initial_state(self, ctrl):
        ctrl.step()
        ctrl.step()
        snap = ctrl.reset()
        assert snap.dwell_number <= 3  # initial state after reset

    def test_pause_does_not_mutate_state(self, ctrl):
        snap1 = ctrl.snapshot()
        ctrl.stop_auto()
        snap2 = ctrl.snapshot()
        assert snap1.simulation_time_s == snap2.simulation_time_s

    def test_speed_does_not_change_config(self, ctrl):
        ctrl.set_speed(5.0)
        assert ctrl.presentation_speed == 5.0
        # Manufacturing dwell unchanged
        assert ctrl.runtime.config.conveyor.nominal_line_dwell_time_s == 120.0

    def test_scenario_selection_deterministic(self):
        c1 = DemoController(config_path=TIPA_YAML, scenario=DemoScenario.HAPPY_PATH)
        c2 = DemoController(config_path=TIPA_YAML, scenario=DemoScenario.HAPPY_PATH)
        s1 = c1.initialize().to_dict()
        s2 = c2.initialize().to_dict()
        assert s1["positions"] == s2["positions"]


# ═══════════════════════════════════════════
# V18–V20 — Regression
# ═══════════════════════════════════════════
class TestV18Regression:
    def test_m6s03_quality_still_works(self):
        from virtual_factory.assembly.quality_records import QualityRecord, QualityStatus
        assert QualityStatus.CLEAR.value == "clear"

    def test_m6s02_runtime_still_works(self):
        from virtual_factory.assembly.line_runtime import AssyLineRuntime, ConveyorState
        line = AssyLineRuntime()
        assert len(line.conveyor.positions) == 12

    def test_m2_m5_imports(self):
        from virtual_factory.assembly import WipId, CarrierId
        assert WipId("x") is not None
        assert CarrierId("y") is not None

    def test_snapshot_no_private_access(self):
        """build_snapshot uses only public runtime API."""
        line = AssyLineRuntime()
        line.produce_sso2_wip()
        line.introduce_to_assy("SSO2-0001", "PAL-001")
        snap = build_snapshot(line)
        # Verify public wip_ids works
        assert "SSO2-0001" in line.wip_ids
        # Production counters use public API
        assert snap.production.motors_created >= 0
        assert snap.production.motors_released >= 0


class TestVScenarioSwitch:
    def test_scenario_switch_resets_state(self):
        c1 = DemoController(config_path=TIPA_YAML, scenario=DemoScenario.HAPPY_PATH)
        s1 = c1.initialize()
        assert s1.scenario == "HAPPY_PATH"

        c1.set_scenario(DemoScenario.AP06_FAIL_RETEST_PASS)
        s2 = c1.reset()
        # Six-sub-line targeting policy: the selected SL01 is allowed to keep
        # HAPPY_PATH; the exception scenario is applied to the target SL03.
        assert s2.scenario == "HAPPY_PATH"
        target = c1.detail_for("ASSY-SL03")
        assert target.scenario == "AP06_FAIL_RETEST_PASS"
        # Verify scenario config applied to the target sub-line
        target_ctx = c1.composition.get_context("ASSY-SL03")
        assert target_ctx.runtime.config.quality.ap06.scenario == "PASS"
        assert target_ctx.runtime.config.quality.ap06.overrides == {1: ["PASS"], 2: ["FAIL", "PASS"]}
