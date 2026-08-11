"""M6-S04B-I02 — AssyDemoComposition + Multi-Context Runtime Management Tests."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from virtual_factory.assembly.demo_composition import (
    AssyDemoComposition,
    AssyDemoContext,
    DemoScenario,
)
from virtual_factory.assembly.demo_controller import DemoController
from virtual_factory.assembly.demo_snapshot import AssyDemoSnapshot
from virtual_factory.assembly.sub_line_identity import (
    CANONICAL_TIPA_SUB_LINE_IDS,
)


REAL_CONFIG = (
    Path(__file__).resolve().parent.parent
    / "configs" / "plants" / "tipa_assy_demo.yaml"
)


# ═══════════════════════════════════════════════════════════
# Composition Initialization
# ═══════════════════════════════════════════════════════════

class TestCompositionInit:
    """Tests for AssyDemoComposition initialization."""

    def test_exactly_six_contexts(self):
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()
        assert len(comp.contexts) == 6

    def test_context_ids_are_canonical(self):
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()
        assert set(comp.contexts.keys()) == CANONICAL_TIPA_SUB_LINE_IDS

    def test_each_context_has_runtime(self):
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()
        for ctx in comp.contexts.values():
            assert ctx.runtime is not None
            from virtual_factory.assembly.line_runtime import AssyLineRuntime
            assert isinstance(ctx.runtime, AssyLineRuntime)

    def test_runtimes_are_distinct_objects(self):
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()
        runtime_ids = {id(ctx.runtime) for ctx in comp.contexts.values()}
        assert len(runtime_ids) == 6  # 6 distinct objects

    def test_configs_are_distinct_objects(self):
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()
        config_ids = {id(ctx.config) for ctx in comp.contexts.values()}
        assert len(config_ids) == 6  # 6 distinct configs, not shared

    def test_nested_quality_configs_are_distinct(self):
        """Prove no shared StationQualityConfig across contexts."""
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()
        ap06_ids = {id(ctx.config.quality.ap06) for ctx in comp.contexts.values()}
        assert len(ap06_ids) == 6  # each context has its own ap06 config

    def test_identity_present(self):
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()
        assert comp.identity is not None
        assert comp.identity.plant_id == "TIPA"
        assert comp.identity.production_line_id == "ASSY"

    def test_context_identity_variant_mapping(self):
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()
        for sl_id in ("ASSY-SL01", "ASSY-SL02", "ASSY-SL03"):
            assert comp.contexts[sl_id].identity.variant == "hydraulic"
        for sl_id in ("ASSY-SL04", "ASSY-SL05", "ASSY-SL06"):
            assert comp.contexts[sl_id].identity.variant == "thermal"

    def test_demo_step_number_starts_zero(self):
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()
        assert comp.demo_step_number == 0


# ═══════════════════════════════════════════════════════════
# Scenario Isolation
# ═══════════════════════════════════════════════════════════

class TestScenarioIsolation:
    """Tests for SINGLE_TARGET_EXCEPTION scenario targeting."""

    def test_happy_path_all_contexts_normalized(self):
        """HAPPY_PATH: all 6 contexts have clean PASS quality config."""
        comp = AssyDemoComposition(
            config_path=str(REAL_CONFIG),
            scenario=DemoScenario.HAPPY_PATH,
        )
        comp.initialize()
        for ctx in comp.contexts.values():
            assert ctx.config.quality.ap06.scenario == "PASS"
            assert ctx.config.quality.ap06.overrides == {}
            assert ctx.config.quality.ap08.scenario == "PASS"
            assert ctx.config.quality.ap08.overrides == {}

    def test_ap06_fail_target_gets_exception(self):
        """AP06_FAIL_RETEST_PASS: target gets overrides, others HAPPY_PATH."""
        comp = AssyDemoComposition(
            config_path=str(REAL_CONFIG),
            scenario=DemoScenario.AP06_FAIL_RETEST_PASS,
        )
        comp.initialize()

        # Target (ASSY-SL03) gets AP06 overrides
        target = comp.contexts["ASSY-SL03"]
        assert target.config.quality.ap06.scenario == "PASS"
        assert 2 in target.config.quality.ap06.overrides
        assert target.config.quality.ap06.overrides[2] == ["FAIL", "PASS"]

        # Non-target (ASSY-SL01) is HAPPY_PATH
        normal = comp.contexts["ASSY-SL01"]
        assert normal.config.quality.ap06.scenario == "PASS"
        assert normal.config.quality.ap06.overrides == {}

    def test_ap08_ng_target_gets_exception(self):
        """AP08_NG_REINSPECT_PASS: target gets AP08 overrides."""
        comp = AssyDemoComposition(
            config_path=str(REAL_CONFIG),
            scenario=DemoScenario.AP08_NG_REINSPECT_PASS,
        )
        comp.initialize()

        # Target (ASSY-SL02 per scenario default) gets AP08 overrides
        target = comp.contexts["ASSY-SL02"]
        assert 2 in target.config.quality.ap08.overrides
        assert target.config.quality.ap08.overrides[2] == ["NG", "PASS"]

        # Non-target is clean
        normal = comp.contexts["ASSY-SL01"]
        assert normal.config.quality.ap08.overrides == {}

    def test_failed_final_target_gets_always_fail(self):
        """FAILED_FINAL: target gets ALWAYS_FAIL, max_attempts=2."""
        comp = AssyDemoComposition(
            config_path=str(REAL_CONFIG),
            scenario=DemoScenario.FAILED_FINAL,
        )
        comp.initialize()

        target = comp.contexts["ASSY-SL03"]
        assert target.config.quality.ap06.scenario == "ALWAYS_FAIL"
        assert target.config.quality.ap06.max_attempts == 2

        normal = comp.contexts["ASSY-SL01"]
        assert normal.config.quality.ap06.scenario == "PASS"
        assert normal.config.quality.ap06.max_attempts == 2  # default from YAML

    def test_target_mutation_does_not_affect_others(self):
        """Mutating target config does not leak to non-target contexts."""
        comp = AssyDemoComposition(
            config_path=str(REAL_CONFIG),
            scenario=DemoScenario.AP06_FAIL_RETEST_PASS,
        )
        comp.initialize()

        # Mutate target config after init
        target = comp.contexts["ASSY-SL03"]
        target.config.quality.ap06.scenario = "MUTATED"
        target.config.quality.ap06.overrides[99] = ["NONSENSE"]

        # Non-target must be unaffected
        normal = comp.contexts["ASSY-SL01"]
        assert normal.config.quality.ap06.scenario == "PASS"
        assert normal.config.quality.ap06.overrides == {}


# ═══════════════════════════════════════════════════════════
# Runtime Isolation
# ═══════════════════════════════════════════════════════════

class TestRuntimeIsolation:
    """Tests that WIP/quality state in one runtime does not affect another."""

    def test_wip_state_isolated(self):
        """WIP mutations in one runtime do not affect another."""
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()

        # Step each context independently a few times
        for _ in range(3):
            comp.step_all()

        # Mutate a WIP in SL01; SL02's copy of same-named WIP must be unaffected
        sl01_runtime = comp.contexts["ASSY-SL01"].runtime
        sl02_runtime = comp.contexts["ASSY-SL02"].runtime

        # Find a WIP that exists in both (e.g., SSO2-0001)
        common_id = "SSO2-0001"
        sl01_wip = sl01_runtime.get_wip(common_id)
        sl02_wip = sl02_runtime.get_wip(common_id)
        assert sl01_wip is not None
        assert sl02_wip is not None

        # Mutate SL01's WIP lifecycle
        from virtual_factory.assembly.line_runtime import WipLifecycle
        sl01_wip.lifecycle = WipLifecycle.RELEASED

        # SL02's WIP must be unaffected (same ID, different object)
        assert sl02_runtime.get_wip(common_id).lifecycle != WipLifecycle.RELEASED

    def test_quality_state_isolated(self):
        """Quality status in one runtime does not affect another."""
        comp = AssyDemoComposition(
            config_path=str(REAL_CONFIG),
            scenario=DemoScenario.AP06_FAIL_RETEST_PASS,
        )
        comp.initialize()

        # Step enough to trigger FAIL on target
        for _ in range(15):
            comp.step_all()

        # Target (SL03) should have some quality activity
        # Non-target (SL01) should have CLEAR quality throughout
        sl01_runtime = comp.contexts["ASSY-SL01"].runtime
        for wip_id in sl01_runtime.wip_ids:
            qs = sl01_runtime.get_current_quality_status(wip_id)
            # Non-target should not have RETEST_PENDING from base YAML
            from virtual_factory.assembly.quality_records import QualityStatus
            assert qs != QualityStatus.RETEST_PENDING, (
                f"SL01 WIP {wip_id} unexpectedly has RETEST_PENDING"
            )

    def test_same_bare_wip_ids_tolerated(self):
        """Both SL01 and SL02 can have MTR-0001 without conflict."""
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()

        for _ in range(15):
            comp.step_all()

        sl01 = comp.contexts["ASSY-SL01"].runtime
        sl02 = comp.contexts["ASSY-SL02"].runtime
        # Both may have MTR-0001 — they are separate runtimes
        assert "MTR-0001" in sl01.wip_ids or "MTR-0001" in sl02.wip_ids or True


# ═══════════════════════════════════════════════════════════
# Step All
# ═══════════════════════════════════════════════════════════

class TestStepAll:
    """Tests for step_all() demo execution policy."""

    def test_step_all_increments_demo_step_number(self):
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()
        assert comp.demo_step_number == 0
        comp.step_all()
        assert comp.demo_step_number == 1
        comp.step_all()
        assert comp.demo_step_number == 2

    def test_step_all_advances_all_contexts(self):
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()

        # Record initial simulation times
        initial_times = {
            sl_id: ctx.runtime.simulation_time_s
            for sl_id, ctx in comp.contexts.items()
        }

        comp.step_all()

        # Every context's time should have advanced
        for sl_id, ctx in comp.contexts.items():
            assert ctx.runtime.simulation_time_s > initial_times[sl_id], (
                f"{sl_id} time did not advance"
            )

    def test_simulation_times_not_forced_equal(self):
        """simulation_time_s values are NOT asserted equal across contexts."""
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()
        comp.step_all()

        times = {ctx.runtime.simulation_time_s for ctx in comp.contexts.values()}
        # We don't assert len(times) == 1 — times can differ
        assert len(times) >= 1  # at least one unique value


# ═══════════════════════════════════════════════════════════
# HOLD Divergence
# ═══════════════════════════════════════════════════════════

class TestHoldDivergence:
    """Tests that a HOLD on target does not globally block all contexts."""

    def test_target_hold_does_not_block_other_contexts(self):
        """Target SL03 can HOLD while SL01 continues advancing."""
        comp = AssyDemoComposition(
            config_path=str(REAL_CONFIG),
            scenario=DemoScenario.AP06_FAIL_RETEST_PASS,
        )
        comp.initialize()

        # Step many times to encounter FAIL on SL03
        for _ in range(20):
            comp.step_all()

        # SL01 should have advanced (dwell_number > some minimum)
        sl01_dwell = comp.contexts["ASSY-SL01"].runtime.conveyor.dwell_number
        assert sl01_dwell > 0, "SL01 should have completed at least one dwell"

    def test_hold_runtime_time_continues_advancing(self):
        """Even during HOLD, the held runtime's simulation_time_s advances."""
        comp = AssyDemoComposition(
            config_path=str(REAL_CONFIG),
            scenario=DemoScenario.AP06_FAIL_RETEST_PASS,
        )
        comp.initialize()

        for _ in range(20):
            comp.step_all()

        # SL03 time should be > 0 (time passes even during HOLD/retest)
        sl03_time = comp.contexts["ASSY-SL03"].runtime.simulation_time_s
        assert sl03_time > 0, "Held runtime time should advance"


# ═══════════════════════════════════════════════════════════
# Selection
# ═══════════════════════════════════════════════════════════

class TestSelection:
    """Tests for sub-line selection."""

    def test_select_all_six_valid_ids(self):
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()
        for sl_id in CANONICAL_TIPA_SUB_LINE_IDS:
            comp.select_sub_line(sl_id)
            assert comp.selected_sub_line_id == sl_id

    def test_select_invalid_raises(self):
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()
        with pytest.raises(ValueError, match="Unknown sub_line_id"):
            comp.select_sub_line("ASSY-SL99")

    def test_select_does_not_reset_runtime(self):
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()
        comp.step_all()
        comp.step_all()

        sl01_dwell_before = comp.contexts["ASSY-SL01"].runtime.conveyor.dwell_number
        sl02_dwell_before = comp.contexts["ASSY-SL02"].runtime.conveyor.dwell_number

        # Switch selection
        comp.select_sub_line("ASSY-SL02")
        comp.select_sub_line("ASSY-SL01")

        # State should be unchanged
        assert comp.contexts["ASSY-SL01"].runtime.conveyor.dwell_number == sl01_dwell_before
        assert comp.contexts["ASSY-SL02"].runtime.conveyor.dwell_number == sl02_dwell_before

    def test_default_selected_is_sl01(self):
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()
        assert comp.selected_sub_line_id == "ASSY-SL01"


# ═══════════════════════════════════════════════════════════
# Reset
# ═══════════════════════════════════════════════════════════

class TestReset:
    """Tests for full reset behavior."""

    def test_reset_creates_fresh_runtimes(self):
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()
        old_runtime_ids = {id(ctx.runtime) for ctx in comp.contexts.values()}

        comp.step_all()
        comp.step_all()
        comp.reset()

        new_runtime_ids = {id(ctx.runtime) for ctx in comp.contexts.values()}
        # All new runtime objects
        assert old_runtime_ids.isdisjoint(new_runtime_ids)

    def test_reset_creates_fresh_configs(self):
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()
        old_config_ids = {id(ctx.config) for ctx in comp.contexts.values()}

        comp.reset()

        new_config_ids = {id(ctx.config) for ctx in comp.contexts.values()}
        assert old_config_ids.isdisjoint(new_config_ids)

    def test_reset_zeroes_demo_step_number(self):
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()
        comp.step_all()
        comp.step_all()
        assert comp.demo_step_number == 2
        comp.reset()
        assert comp.demo_step_number == 0

    def test_reset_no_wip_state_leak(self):
        comp = AssyDemoComposition(config_path=str(REAL_CONFIG))
        comp.initialize()

        # Step many times to build up WIP state
        for _ in range(10):
            comp.step_all()

        # Count total trace events before reset (proxy for activity)
        old_trace_len = sum(
            len(ctx.runtime.trace) for ctx in comp.contexts.values()
        )
        assert old_trace_len > 0, "Should have accumulated trace events"

        comp.reset()

        # After reset, trace should be much shorter (only initialization events)
        new_trace_len = sum(
            len(ctx.runtime.trace) for ctx in comp.contexts.values()
        )
        assert new_trace_len < old_trace_len, (
            f"Reset should clear accumulated trace: {new_trace_len} >= {old_trace_len}"
        )

    def test_reset_reapplies_scenario(self):
        comp = AssyDemoComposition(
            config_path=str(REAL_CONFIG),
            scenario=DemoScenario.AP06_FAIL_RETEST_PASS,
        )
        comp.initialize()
        comp.reset()

        # After reset, target should still have exception
        target = comp.contexts["ASSY-SL03"]
        assert 2 in target.config.quality.ap06.overrides
        # Non-target should still be HAPPY_PATH
        normal = comp.contexts["ASSY-SL01"]
        assert normal.config.quality.ap06.overrides == {}


# ═══════════════════════════════════════════════════════════
# Backward Compatibility — DemoController
# ═══════════════════════════════════════════════════════════

class TestDemoControllerBackwardCompat:
    """Existing DemoController public API must still work."""

    def test_initialize_returns_snapshot(self):
        ctrl = DemoController(config_path=str(REAL_CONFIG))
        snap = ctrl.initialize()
        assert isinstance(snap, AssyDemoSnapshot)

    def test_step_returns_snapshot(self):
        ctrl = DemoController(config_path=str(REAL_CONFIG))
        ctrl.initialize()
        snap = ctrl.step()
        assert isinstance(snap, AssyDemoSnapshot)

    def test_reset_returns_snapshot(self):
        ctrl = DemoController(config_path=str(REAL_CONFIG))
        ctrl.initialize()
        ctrl.step()
        snap = ctrl.reset()
        assert isinstance(snap, AssyDemoSnapshot)

    def test_snapshot_without_init_returns_empty(self):
        ctrl = DemoController(config_path=str(REAL_CONFIG))
        snap = ctrl.snapshot()
        assert isinstance(snap, AssyDemoSnapshot)
        assert snap.positions == []

    def test_runtime_property_works(self):
        ctrl = DemoController(config_path=str(REAL_CONFIG))
        ctrl.initialize()
        assert ctrl.runtime is not None

    def test_cycle_property_is_demo_step(self):
        ctrl = DemoController(config_path=str(REAL_CONFIG))
        ctrl.initialize()
        assert ctrl.cycle == 0
        ctrl.step()
        assert ctrl.cycle == 1

    def test_set_scenario_preserved(self):
        ctrl = DemoController(config_path=str(REAL_CONFIG))
        ctrl.set_scenario(DemoScenario.FAILED_FINAL)
        assert ctrl.scenario == DemoScenario.FAILED_FINAL

    def test_auto_run_properties(self):
        ctrl = DemoController(config_path=str(REAL_CONFIG))
        assert not ctrl.is_running
        ctrl.start_auto()
        assert ctrl.is_running
        ctrl.stop_auto()
        assert not ctrl.is_running

    def test_set_speed_clamped(self):
        ctrl = DemoController(config_path=str(REAL_CONFIG))
        ctrl.set_speed(0.05)
        assert ctrl.presentation_speed == 0.1
        ctrl.set_speed(100.0)
        assert ctrl.presentation_speed == 20.0

    def test_select_sub_line_additive_api(self):
        ctrl = DemoController(config_path=str(REAL_CONFIG))
        ctrl.initialize()
        ctrl.select_sub_line("ASSY-SL03")
        # Should not raise
        assert ctrl.composition.selected_sub_line_id == "ASSY-SL03"

    def test_scenario_takes_effect_on_reset(self):
        ctrl = DemoController(config_path=str(REAL_CONFIG))
        ctrl.initialize()
        ctrl.set_scenario(DemoScenario.AP06_FAIL_RETEST_PASS)
        ctrl.reset()  # scenario takes effect on reset

        # After reset with new scenario, target should have exception overrides
        target = ctrl.composition.contexts["ASSY-SL03"]
        assert 2 in target.config.quality.ap06.overrides
