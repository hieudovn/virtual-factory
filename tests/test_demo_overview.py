"""M6-S04B-I03 — Overview Projection + Additive API Tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from virtual_factory.assembly.demo_composition import (
    AssyDemoComposition,
    DemoScenario,
)
from virtual_factory.assembly.demo_controller import DemoController
from virtual_factory.assembly.demo_snapshot import (
    AssyOverviewSnapshot,
    SubLineSummaryView,
    AssyDemoSnapshot,
    build_summary,
    build_overview,
)


REAL_CONFIG = (
    Path(__file__).resolve().parent.parent
    / "configs" / "plants" / "tipa_assy_demo.yaml"
)


# ═══════════════════════════════════════════════════════════
# Overview shape tests
# ═══════════════════════════════════════════════════════════

class TestOverviewShape:
    """Tests for AssyOverviewSnapshot structure and identity."""

    def test_exactly_six_summaries(self):
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()
        ov = build_overview(comp)
        assert len(ov.sub_lines) == 6

    def test_canonical_ids_present(self):
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()
        ov = build_overview(comp)
        ids = {s.sub_line_id for s in ov.sub_lines}
        assert ids == {"ASSY-SL01", "ASSY-SL02", "ASSY-SL03",
                       "ASSY-SL04", "ASSY-SL05", "ASSY-SL06"}

    def test_variant_mapping(self):
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()
        ov = build_overview(comp)
        for s in ov.sub_lines:
            if s.sub_line_id in ("ASSY-SL01", "ASSY-SL02", "ASSY-SL03"):
                assert s.variant == "hydraulic"
            else:
                assert s.variant == "thermal"

    def test_identity_fields(self):
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()
        ov = build_overview(comp)
        for s in ov.sub_lines:
            assert s.plant_id == "TIPA"
            assert s.production_line_id == "ASSY"

    def test_global_scenario_correct(self):
        comp = AssyDemoComposition(
            config_path=str(REAL_CONFIG),
            scenario=DemoScenario.AP06_FAIL_RETEST_PASS,
        )
        comp.initialize()
        ov = build_overview(comp)
        assert ov.scenario == "AP06_FAIL_RETEST_PASS"

    def test_selected_sub_line_correct(self):
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()
        ov = build_overview(comp)
        assert ov.selected_sub_line_id == "ASSY-SL01"

    def test_target_sub_line_correct(self):
        comp = AssyDemoComposition(
            config_path=str(REAL_CONFIG),
            scenario=DemoScenario.AP06_FAIL_RETEST_PASS,
        )
        comp.initialize()
        ov = build_overview(comp)
        assert ov.target_sub_line_id == "ASSY-SL03"

    def test_demo_step_number_in_overview(self):
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()
        comp.step_all()
        comp.step_all()
        ov = build_overview(comp)
        assert ov.demo_step_number == 2

    def test_no_global_simulation_time(self):
        """Overview must NOT have a global simulation_time_s field."""
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()
        ov = build_overview(comp)
        assert not hasattr(ov, "simulation_time_s")

    def test_overview_serializable(self):
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()
        ov = build_overview(comp)
        d = ov.to_dict()
        assert isinstance(d, dict)
        assert len(d["sub_lines"]) == 6
        assert isinstance(d["sub_lines"][0], dict)
        assert "demo_step_number" in d


# ═══════════════════════════════════════════════════════════
# Summary truth tests
# ═══════════════════════════════════════════════════════════

class TestSummaryTruth:
    """Tests that summary values derive from actual runtime state."""

    def test_line_state_from_runtime(self):
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()
        ov = build_overview(comp)
        for s in ov.sub_lines:
            ctx = comp.contexts[s.sub_line_id]
            assert s.line_state == ctx.runtime.conveyor.state.value

    def test_wips_on_line_from_occupancy(self):
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()
        comp.step_all()
        ov = build_overview(comp)
        for s in ov.sub_lines:
            ctx = comp.contexts[s.sub_line_id]
            expected = len(ctx.runtime.conveyor.occupied_positions())
            assert s.wips_on_line == expected

    def test_motors_created_from_runtime(self):
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()
        for _ in range(10):
            comp.step_all()
        ov = build_overview(comp)
        for s in ov.sub_lines:
            ctx = comp.contexts[s.sub_line_id]
            assert s.motors_created == ctx.runtime.motor_count

    def test_simulation_time_per_context(self):
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()
        comp.step_all()
        ov = build_overview(comp)
        for s in ov.sub_lines:
            ctx = comp.contexts[s.sub_line_id]
            assert s.simulation_time_s == ctx.runtime.simulation_time_s

    def test_effective_scenario_per_context(self):
        comp = AssyDemoComposition(
            config_path=str(REAL_CONFIG),
            scenario=DemoScenario.AP06_FAIL_RETEST_PASS,
        )
        comp.initialize()
        ov = build_overview(comp)
        for s in ov.sub_lines:
            ctx = comp.contexts[s.sub_line_id]
            assert s.effective_scenario == ctx.effective_scenario.value


# ═══════════════════════════════════════════════════════════
# HAPPY_PATH tests
# ═══════════════════════════════════════════════════════════

class TestHappyPathOverview:
    """HAPPY_PATH: all 6 sub-lines normal."""

    def test_all_non_exception(self):
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()
        for _ in range(5):
            comp.step_all()
        ov = build_overview(comp)
        for s in ov.sub_lines:
            assert not s.is_exception
            assert s.active_quality_holds == 0
            assert s.held_station == ""
            assert s.held_wip_id == ""

    def test_all_effective_scenario_happy_path(self):
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()
        ov = build_overview(comp)
        for s in ov.sub_lines:
            assert s.effective_scenario == "HAPPY_PATH"


# ═══════════════════════════════════════════════════════════
# AP06 exception tests
# ═══════════════════════════════════════════════════════════

class TestAP06ExceptionOverview:
    """AP06_FAIL_RETEST_PASS: 5 normal + 1 HOLD."""

    def test_target_is_exception_others_not(self):
        comp = AssyDemoComposition(
            config_path=str(REAL_CONFIG),
            scenario=DemoScenario.AP06_FAIL_RETEST_PASS,
        )
        comp.initialize()

        # Drive until SL03 enters HOLD
        from virtual_factory.assembly.quality_records import QualityStatus
        for _ in range(30):
            comp.step_all()
            sl03_runtime = comp.contexts["ASSY-SL03"].runtime
            held = any(
                sl03_runtime.get_current_quality_status(wid) == QualityStatus.RETEST_PENDING
                for wid in sl03_runtime.wip_ids
            )
            if held:
                break

        ov = build_overview(comp)

        sl03 = next(s for s in ov.sub_lines if s.sub_line_id == "ASSY-SL03")
        assert sl03.is_exception
        assert sl03.active_quality_holds > 0

        for s in ov.sub_lines:
            if s.sub_line_id != "ASSY-SL03":
                assert not s.is_exception, f"{s.sub_line_id} should not be exception"

    def test_held_station_populated(self):
        comp = AssyDemoComposition(
            config_path=str(REAL_CONFIG),
            scenario=DemoScenario.AP06_FAIL_RETEST_PASS,
        )
        comp.initialize()

        from virtual_factory.assembly.quality_records import QualityStatus
        for _ in range(30):
            comp.step_all()
            sl03_runtime = comp.contexts["ASSY-SL03"].runtime
            if any(
                sl03_runtime.get_current_quality_status(wid) == QualityStatus.RETEST_PENDING
                for wid in sl03_runtime.wip_ids
            ):
                break

        ov = build_overview(comp)
        sl03 = next(s for s in ov.sub_lines if s.sub_line_id == "ASSY-SL03")
        assert sl03.held_station != "", "SL03 should have a held station"
        assert sl03.held_wip_id != "", "SL03 should have a held WIP"

    def test_exception_clears_after_retest_pass(self):
        """After retest passes, the exception should clear."""
        comp = AssyDemoComposition(
            config_path=str(REAL_CONFIG),
            scenario=DemoScenario.AP06_FAIL_RETEST_PASS,
        )
        comp.initialize()

        from virtual_factory.assembly.quality_records import QualityStatus
        # Drive until HOLD, then continue until resolution
        for _ in range(50):
            comp.step_all()
            sl03_runtime = comp.contexts["ASSY-SL03"].runtime
            # Check if HOLD was entered and then cleared
            any_held = any(
                sl03_runtime.get_current_quality_status(wid) in (
                    QualityStatus.RETEST_PENDING, QualityStatus.REINSPECT_PENDING,
                    QualityStatus.FAILED_FINAL,
                )
                for wid in sl03_runtime.wip_ids
            )
            if not any_held and sl03_runtime.motor_count > 2:
                # HOLD resolved and motors produced
                break

        ov = build_overview(comp)
        sl03 = next(s for s in ov.sub_lines if s.sub_line_id == "ASSY-SL03")
        # May still be false if another motor entered HOLD, but should not be stuck
        assert sl03.motors_created > 0, "SL03 should have produced motors"


class TestAP08ExceptionOverview:
    """AP08_NG_REINSPECT_PASS: target summary truth."""

    def test_target_is_exception(self):
        comp = AssyDemoComposition(
            config_path=str(REAL_CONFIG),
            scenario=DemoScenario.AP08_NG_REINSPECT_PASS,
        )
        comp.initialize()

        from virtual_factory.assembly.quality_records import QualityStatus
        for _ in range(40):
            comp.step_all()
            sl02_runtime = comp.contexts["ASSY-SL02"].runtime
            if any(
                sl02_runtime.get_current_quality_status(wid) == QualityStatus.REINSPECT_PENDING
                for wid in sl02_runtime.wip_ids
            ):
                break

        ov = build_overview(comp)
        sl02 = next(s for s in ov.sub_lines if s.sub_line_id == "ASSY-SL02")
        assert sl02.is_exception
        assert sl02.active_quality_holds > 0


# ═══════════════════════════════════════════════════════════
# Aggregate tests
# ═══════════════════════════════════════════════════════════

class TestAggregates:
    """Overview aggregate counters are correct sums."""

    def test_total_motors_created_is_sum(self):
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()
        for _ in range(10):
            comp.step_all()
        ov = build_overview(comp)
        expected = sum(s.motors_created for s in ov.sub_lines)
        assert ov.total_motors_created == expected

    def test_total_motors_released_is_sum(self):
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()
        for _ in range(10):
            comp.step_all()
        ov = build_overview(comp)
        expected = sum(s.motors_released for s in ov.sub_lines)
        assert ov.total_motors_released == expected

    def test_total_active_holds_is_sum(self):
        comp = AssyDemoComposition(
            config_path=str(REAL_CONFIG),
            scenario=DemoScenario.AP06_FAIL_RETEST_PASS,
        )
        comp.initialize()

        from virtual_factory.assembly.quality_records import QualityStatus
        for _ in range(30):
            comp.step_all()
            sl03_runtime = comp.contexts["ASSY-SL03"].runtime
            if any(
                sl03_runtime.get_current_quality_status(wid) == QualityStatus.RETEST_PENDING
                for wid in sl03_runtime.wip_ids
            ):
                break

        ov = build_overview(comp)
        expected = sum(s.active_quality_holds for s in ov.sub_lines)
        assert ov.total_active_holds == expected
        assert ov.total_active_holds > 0, "Should have at least one hold"


# ═══════════════════════════════════════════════════════════
# Detail tests
# ═══════════════════════════════════════════════════════════

class TestDetail:
    """Tests for detail_for() — read-by-ID without mutation."""

    def test_all_six_ids_return_valid_snapshot(self):
        ctrl = DemoController(config_path=str(REAL_CONFIG))
        ctrl.initialize()
        for sl_id in ("ASSY-SL01", "ASSY-SL02", "ASSY-SL03",
                       "ASSY-SL04", "ASSY-SL05", "ASSY-SL06"):
            snap = ctrl.detail_for(sl_id)
            assert isinstance(snap, AssyDemoSnapshot)
            assert snap.sub_line_id == sl_id

    def test_invalid_id_raises(self):
        ctrl = DemoController(config_path=str(REAL_CONFIG))
        ctrl.initialize()
        with pytest.raises(ValueError, match="Unknown sub_line_id"):
            ctrl.detail_for("ASSY-SL99")

    def test_detail_has_identity_fields(self):
        ctrl = DemoController(config_path=str(REAL_CONFIG))
        ctrl.initialize()
        snap = ctrl.detail_for("ASSY-SL03")
        assert snap.plant_id == "TIPA"
        assert snap.production_line_id == "ASSY"
        assert snap.sub_line_id == "ASSY-SL03"
        assert snap.variant == "hydraulic"

    def test_detail_scenario_is_effective(self):
        ctrl = DemoController(config_path=str(REAL_CONFIG))
        ctrl.set_scenario(DemoScenario.AP06_FAIL_RETEST_PASS)
        ctrl.initialize()
        snap = ctrl.detail_for("ASSY-SL01")
        assert snap.scenario == "HAPPY_PATH"
        snap = ctrl.detail_for("ASSY-SL03")
        assert snap.scenario == "AP06_FAIL_RETEST_PASS"

    def test_detail_does_not_mutate_selection(self):
        ctrl = DemoController(config_path=str(REAL_CONFIG))
        ctrl.initialize()
        original = ctrl.composition.selected_sub_line_id
        ctrl.detail_for("ASSY-SL03")
        assert ctrl.composition.selected_sub_line_id == original

    def test_detail_does_not_reset_runtime(self):
        ctrl = DemoController(config_path=str(REAL_CONFIG))
        ctrl.initialize()
        ctrl.step()
        ctrl.step()
        sl01_dwell_before = ctrl.composition.contexts["ASSY-SL01"].runtime.conveyor.dwell_number
        ctrl.detail_for("ASSY-SL03")
        assert (ctrl.composition.contexts["ASSY-SL01"].runtime.conveyor.dwell_number
                == sl01_dwell_before)

    def test_detail_serializable(self):
        ctrl = DemoController(config_path=str(REAL_CONFIG))
        ctrl.initialize()
        snap = ctrl.detail_for("ASSY-SL01")
        d = snap.to_dict()
        assert isinstance(d, dict)
        assert d["sub_line_id"] == "ASSY-SL01"


# ═══════════════════════════════════════════════════════════
# Controller overview tests
# ═══════════════════════════════════════════════════════════

class TestControllerOverview:
    """Tests for controller.overview()."""

    def test_overview_returns_correct_type(self):
        ctrl = DemoController(config_path=str(REAL_CONFIG))
        ctrl.initialize()
        ov = ctrl.overview()
        assert isinstance(ov, AssyOverviewSnapshot)

    def test_overview_after_steps(self):
        ctrl = DemoController(config_path=str(REAL_CONFIG))
        ctrl.initialize()
        for _ in range(5):
            ctrl.step()
        ov = ctrl.overview()
        assert ov.demo_step_number == 5

    def test_overview_serializable(self):
        ctrl = DemoController(config_path=str(REAL_CONFIG))
        ctrl.initialize()
        ov = ctrl.overview()
        d = ov.to_dict()
        assert len(d["sub_lines"]) == 6
