"""VF-vNEXT-R1 — Canonical TIPA Same-Session Production Semantics tests.

Proves (Issue #79, architecture frozen by R0 / Issue #78):

A. the selected canonical ``tipa-default`` RuntimeSession runs MEANINGFUL
   six-sub-line ASSY production (not six empty clocks), and a bounded canonical
   run reaches AP04 motor creation + genealogy through that same session path;
B. exactly six independent runtimes / configs / run-state holders, stable
   deterministic per-line seeds, no cross-line mutation;
C. scenario targeting is effective and affects ONLY the accepted target line;
D. one held/frozen line stays unchanged while the other five continue;
E. two fresh canonical sessions with the same profile are equivalent;
F. G22 lifecycle compatibility: profile-consistent reset (same run identity),
   new-attempt (fresh identity, same pinned inputs), replay (bounded
   production-state equivalence);
plus frozen-invariant guards: no ``AssyLineRuntime`` rewrite, no second runtime
authority, G4 exact-boundary/no-fractional-dwell unchanged, legacy accepted demo
behaviour regression-green.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from virtual_factory.assembly import AssyLineRuntime
from virtual_factory.assembly.assy_run_profile import (
    AP06_FAIL_RETEST_PASS,
    AP08_NG_REINSPECT_PASS,
    FAILED_FINAL,
    HAPPY_PATH,
    PROFILE_PROVENANCE,
    AssyRunProfileError,
    apply_scenario_quality_overrides,
    build_tipa_run_profile,
    resolve_run_scenario,
    resolve_scenario_target_id,
)
from virtual_factory.assembly.demo_composition import (
    AssyDemoComposition,
    DemoScenario,
)
from virtual_factory.federation import (
    SUB_LINE_IDS,
    FederationError,
    TipaAssyFederation,
)
from virtual_factory.runcontrol import (
    AssyExecutionBridge,
    build_tipa_session,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
TIPA_CONFIG = str(REPO_ROOT / "configs" / "plants" / "tipa_assy_demo.yaml")

#: Accepted target lines (unchanged accepted demo policy).
AP06_TARGET = "ASSY-SL03"
AP08_TARGET = "ASSY-SL02"


# ═══════════════════════════════════════════════════════════════
# Helpers (public API only)
# ═══════════════════════════════════════════════════════════════

def _session(scenario_id: str = "tipa-default"):
    return build_tipa_session(TIPA_CONFIG, scenario_id)


def _federation(session) -> TipaAssyFederation:
    """The selected session's OWN federation (built lazily on first step)."""
    return session.record.bridge.federation


def _line_state(runtime: AssyLineRuntime) -> tuple:
    """Deterministic per-line domain-state projection (public reads only)."""
    return (
        runtime.simulation_time_s,
        runtime.conveyor.dwell_number,
        tuple(
            (pos, runtime.conveyor.wip_at(pos)) for pos in runtime.conveyor.positions
        ),
        runtime.wip_count,
        runtime.motor_count,
        runtime.rso2_buffer_size,
        tuple(
            sorted(
                (g.child_wip_id, tuple(g.parent_wip_ids))
                for g in runtime.genealogy.all_records()
            )
        ),
    )


def _line_summary(runtime: AssyLineRuntime) -> tuple:
    """Coarse production summary used for cross-line/session equivalence."""
    return (
        runtime.simulation_time_s,
        runtime.conveyor.dwell_number,
        runtime.wip_count,
        runtime.motor_count,
        runtime.rso2_buffer_size,
        tuple(
            (pos, runtime.conveyor.wip_at(pos)) for pos in runtime.conveyor.positions
        ),
    )


def _all_summaries(federation: TipaAssyFederation) -> tuple:
    return tuple(
        (sid, _line_summary(federation.runtime(sid))) for sid in SUB_LINE_IDS
    )


def _step_prepared_session(scenario_id: str, steps: int):
    session = _session(scenario_id)
    for _ in range(steps):
        session.advance()
    return session, _federation(session)


# ═══════════════════════════════════════════════════════════════
# 0. Profile resolution / explicit run input
# ═══════════════════════════════════════════════════════════════

class TestRunProfileResolution:
    def test_tipa_default_resolves_to_accepted_production_profile(self):
        profile = build_tipa_run_profile("tipa-default")
        assert profile.session_scenario_id == "tipa-default"
        assert profile.scenario == HAPPY_PATH
        assert profile.target_sub_line_id == ""          # all lines HAPPY_PATH
        assert profile.initial_sso2_inventory == 7
        assert profile.initial_rso2_inventory == 7
        assert profile.continuous_feed_enabled is True
        assert profile.feed_policy.sso2_target == 10
        assert profile.feed_policy.sso2_low_watermark == 3
        assert profile.feed_policy.rso2_target == 6
        assert profile.provenance == PROFILE_PROVENANCE  # simulation/synthetic
        assert "site truth" not in profile.to_dict()["provenance"]
        assert profile.to_dict()["provenance"].startswith("simulation_synthetic")

    def test_accepted_scenario_values_are_accepted_too(self):
        for value in (HAPPY_PATH, AP06_FAIL_RETEST_PASS, AP08_NG_REINSPECT_PASS, FAILED_FINAL):
            assert resolve_run_scenario(value) == value
            assert resolve_run_scenario(value.lower()) == value

    def test_unknown_scenario_fails_closed(self):
        with pytest.raises(AssyRunProfileError):
            resolve_run_scenario("tipa-not-a-scenario")
        with pytest.raises(AssyRunProfileError):
            build_tipa_run_profile("")

    def test_unknown_session_scenario_fails_closed_before_runtime_construction(self):
        with pytest.raises(AssyRunProfileError):
            _session("tipa-nope")

    def test_profile_is_immutable_run_input(self):
        profile = build_tipa_run_profile("tipa-default")
        with pytest.raises(dataclasses.FrozenInstanceError):
            profile.scenario = AP06_FAIL_RETEST_PASS  # type: ignore[misc]
        with pytest.raises(dataclasses.FrozenInstanceError):
            profile.feed_policy.rso2_target = 99  # type: ignore[misc]

    def test_target_resolution_precedence_unchanged(self):
        assert resolve_scenario_target_id(HAPPY_PATH, "ASSY-SL05") == ""
        assert resolve_scenario_target_id(AP06_FAIL_RETEST_PASS) == AP06_TARGET
        assert resolve_scenario_target_id(AP08_NG_REINSPECT_PASS) == AP08_TARGET
        assert resolve_scenario_target_id(FAILED_FINAL) == AP06_TARGET
        # identity default is the accepted fallback only
        assert resolve_scenario_target_id(HAPPY_PATH, "ASSY-SL05") == ""
        assert resolve_scenario_target_id("UNKNOWN", "ASSY-SL05") == "ASSY-SL05"

    def test_session_pins_the_resolved_profile_identity(self):
        session = _session()
        assert session.scenario_id == "tipa-default"
        assert session.profile_id == "tipa-assy-happy_path"


# ═══════════════════════════════════════════════════════════════
# A. Meaningful production through the selected session
# ═══════════════════════════════════════════════════════════════

class TestSelectedSessionProduction:
    def test_prepared_six_line_production_runtime_on_first_step(self):
        session = _session()
        session.advance()  # bridge/federation built lazily here
        federation = _federation(session)
        assert type(federation) is TipaAssyFederation
        for sid in SUB_LINE_IDS:
            runtime = federation.runtime(sid)
            assert runtime.simulation_time_s == 120.0
            assert runtime.conveyor.dwell_number == 1
            # non-empty production: upstream inventory + a unit already entered
            assert runtime.wip_count > 0
            assert runtime.rso2_buffer_size > 0
            occupied = [
                pos for pos in runtime.conveyor.positions
                if runtime.conveyor.wip_at(pos)
            ]
            assert occupied, sid
            # accepted preparation: first unit at AP01, next carrier queued
            assert runtime.conveyor.wip_at("AP01") is not None
            assert runtime.conveyor.wip_at("PRE-ASSY") is not None

    def test_hard_guard_no_six_empty_lines_after_meaningful_stepping(self):
        """R0 hard guard: six lines with wip_count == 0 after stepping is FAIL."""
        session, federation = _step_prepared_session("tipa-default", 4)
        for sid in SUB_LINE_IDS:
            runtime = federation.runtime(sid)
            assert runtime.wip_count > 0, f"{sid} is empty -> FAIL"
            assert runtime.conveyor.dwell_number == 4
            assert runtime.simulation_time_s == 480.0

    def test_bounded_run_reaches_ap04_motor_creation_and_genealogy(self):
        session, federation = _step_prepared_session("tipa-default", 5)
        for sid in SUB_LINE_IDS:
            runtime = federation.runtime(sid)
            assert runtime.motor_count == 1
            assert runtime.conveyor.wip_at("AP05") == "MTR-0001"
            records = [
                (g.child_wip_id, tuple(g.parent_wip_ids))
                for g in runtime.genealogy.all_records()
            ]
            assert ("MTR-0001", ("SSO2-0001", "RSO2-0001")) in records
        # AP04 join is what consumed the first RSO2
        assert federation.runtime("ASSY-SL01").rso2_buffer_size == 6

    def test_production_continues_to_release_and_line_out(self):
        session, federation = _step_prepared_session("tipa-default", 16)
        runtime = federation.runtime("ASSY-SL01")
        released = [
            wid
            for wid in runtime.wip_ids
            if runtime.get_wip(wid) is not None
            and runtime.get_wip(wid).lifecycle.value == "released"
        ]
        assert released, "bounded canonical run never produced a released motor"
        assert runtime.motor_count >= 2

    def test_selected_session_matches_accepted_demo_reference_progression(self):
        """The canonical path reproduces the accepted demo production progression."""
        session, federation = _step_prepared_session("tipa-default", 5)
        canonical = _line_summary(federation.runtime("ASSY-SL01"))

        comp = AssyDemoComposition(config_path=TIPA_CONFIG, scenario=DemoScenario.HAPPY_PATH)
        comp.initialize()
        for _ in range(5):
            comp.step_all()
        reference = _line_summary(comp.contexts["ASSY-SL01"].runtime)

        assert canonical == reference


# ═══════════════════════════════════════════════════════════════
# B. Six isolated runtimes
# ═══════════════════════════════════════════════════════════════

class TestSixIsolatedRuntimes:
    def test_six_distinct_runtimes_configs_and_run_states(self):
        session, federation = _step_prepared_session("tipa-default", 1)
        assert federation.sub_line_ids == SUB_LINE_IDS
        assert len({id(federation.runtime(sid)) for sid in SUB_LINE_IDS}) == 6
        assert len({id(federation.get(sid).config) for sid in SUB_LINE_IDS}) == 6
        assert len({id(federation.run_state(sid)) for sid in SUB_LINE_IDS}) == 6
        assert len({id(federation.adapter(sid)) for sid in SUB_LINE_IDS}) == 6
        for sid in SUB_LINE_IDS:
            entry = federation.get(sid)
            # no AssyLineRuntime rewrite: the exact accepted class is used
            assert type(entry.runtime) is AssyLineRuntime
            # the adapter drives THIS line's own runtime and run state
            assert entry.adapter.runtime is entry.runtime
            assert entry.adapter.run_state is entry.run_state
            assert entry.adapter.is_prepared is True
            # isolated feed queues (never shared lists)
            assert entry.run_state.sso2_ids is not federation.get(
                SUB_LINE_IDS[0]
            ).run_state.sso2_ids if sid != SUB_LINE_IDS[0] else True

    def test_stable_deterministic_per_line_seed_mapping(self):
        first = TipaAssyFederation(config_path=TIPA_CONFIG).initialize(
            run_profile=build_tipa_run_profile("tipa-default")
        )
        second = TipaAssyFederation(config_path=TIPA_CONFIG).initialize(
            run_profile=build_tipa_run_profile("tipa-default")
        )
        seeds_a = {sid: first.get(sid).config.random_seed for sid in SUB_LINE_IDS}
        seeds_b = {sid: second.get(sid).config.random_seed for sid in SUB_LINE_IDS}
        assert seeds_a == seeds_b
        assert len(set(seeds_a.values())) == 6
        base = seeds_a[SUB_LINE_IDS[0]]
        for ordinal, sid in enumerate(SUB_LINE_IDS):
            assert seeds_a[sid] == base + ordinal

    def test_progressing_one_line_does_not_mutate_another(self):
        session = _session()
        session.advance()
        federation = _federation(session)
        bridge: AssyExecutionBridge = session.record.bridge
        others_before = {
            sid: _line_state(federation.runtime(sid)) for sid in SUB_LINE_IDS[1:]
        }
        target = bridge.natural_next_boundary((SUB_LINE_IDS[0],))
        result = bridge.advance(target, (SUB_LINE_IDS[0],), "r1-isolation")
        assert result.status == "completed"
        assert federation.runtime(SUB_LINE_IDS[0]).simulation_time_s == target
        for sid, state in others_before.items():
            assert _line_state(federation.runtime(sid)) == state, sid

    def test_run_states_hold_no_shared_mutable_lists(self):
        session, federation = _step_prepared_session("tipa-default", 1)
        sl01 = federation.run_state("ASSY-SL01")
        sl02 = federation.run_state("ASSY-SL02")
        assert sl01 is not sl02
        before = list(sl02.sso2_ids)
        sl01.sso2_ids.append("SENTINEL-NOT-REAL")
        sl01.sso2_ids.remove("SENTINEL-NOT-REAL")
        assert list(sl02.sso2_ids) == before


# ═══════════════════════════════════════════════════════════════
# C. Scenario targeting is effective (not metadata-only)
# ═══════════════════════════════════════════════════════════════

class TestScenarioTargeting:
    def test_happy_default_effective_on_all_six(self):
        session, federation = _step_prepared_session("tipa-default", 1)
        for sid in SUB_LINE_IDS:
            assert federation.effective_scenario(sid) == HAPPY_PATH
            assert federation.get(sid).config.quality.ap06.scenario == "PASS"
            assert federation.get(sid).config.quality.ap06.overrides == {}
            assert federation.get(sid).config.quality.ap08.overrides == {}
        assert federation.run_profile.target_sub_line_id == ""

    @pytest.mark.parametrize(
        "scenario_id,scenario_value,target",
        [
            ("tipa-ap06-retest", AP06_FAIL_RETEST_PASS, AP06_TARGET),
            ("tipa-ap08-reinspect", AP08_NG_REINSPECT_PASS, AP08_TARGET),
        ],
    )
    def test_synthetic_exception_applies_only_to_target_line(
        self, scenario_id, scenario_value, target
    ):
        session = _session(scenario_id)
        session.advance()
        federation = _federation(session)
        for sid in SUB_LINE_IDS:
            if sid == target:
                assert federation.effective_scenario(sid) == scenario_value
            else:
                assert federation.effective_scenario(sid) == HAPPY_PATH
        # the exception transform is present only on the target config
        target_cfg = federation.get(target).config.quality
        reference = federation.get("ASSY-SL01").config.quality
        if scenario_value == AP06_FAIL_RETEST_PASS:
            assert target_cfg.ap06.overrides == {1: ["PASS"], 2: ["FAIL", "PASS"]}
            assert reference.ap06.overrides == {}
            assert target_cfg.ap08.overrides == {}
        else:
            assert target_cfg.ap08.overrides == {1: ["PASS"], 2: ["NG", "PASS"]}
            assert reference.ap08.overrides == {}
            assert target_cfg.ap06.overrides == {}

    def test_ap06_target_line_actually_retests_others_do_not(self):
        session, federation = _step_prepared_session("tipa-ap06-retest", 20)
        target = federation.runtime(AP06_TARGET)
        other = federation.runtime("ASSY-SL01")

        target_history = target.get_quality_history("MTR-0002")
        other_history = other.get_quality_history("MTR-0002")
        assert target_history is not None and other_history is not None
        # the accepted exception = motor 2 FAIL then PASS on the target line
        assert [r.disposition for r in target_history.records_for("AP06")] == [
            "FAIL",
            "PASS",
        ]
        assert target_history.attempt_count("AP06") == 2
        assert other_history.attempt_count("AP06") == 1
        assert [r.disposition for r in other_history.records_for("AP06")] == ["PASS"]
        # and every non-target line stays on the normal single-pass route
        for sid in SUB_LINE_IDS:
            if sid == AP06_TARGET:
                continue
            runtime = federation.runtime(sid)
            history = runtime.get_quality_history("MTR-0002")
            assert history is not None
            assert history.attempt_count("AP06") == 1, sid
            assert federation.effective_scenario(sid) == HAPPY_PATH

    def test_ap08_target_line_actually_reinspected_others_do_not(self):
        session, federation = _step_prepared_session("tipa-ap08-reinspect", 20)
        target_history = federation.runtime(AP08_TARGET).get_quality_history("MTR-0002")
        other_history = federation.runtime("ASSY-SL01").get_quality_history("MTR-0002")
        assert target_history is not None and other_history is not None
        # the accepted exception = motor 2 NG then PASS on the target line
        assert [r.disposition for r in target_history.records_for("AP08")] == [
            "NG",
            "PASS",
        ]
        assert target_history.attempt_count("AP08") == 2
        assert other_history.attempt_count("AP08") == 1
        for sid in SUB_LINE_IDS:
            if sid == AP08_TARGET:
                continue
            history = federation.runtime(sid).get_quality_history("MTR-0002")
            assert history is not None
            assert history.attempt_count("AP08") == 1, sid

    def test_failed_final_mapping_retained_by_shared_resolver(self):
        session, federation = _step_prepared_session("tipa-failed-final", 20)
        assert federation.run_profile.scenario == FAILED_FINAL
        assert federation.effective_scenario(AP06_TARGET) == FAILED_FINAL
        cfg = federation.get(AP06_TARGET).config.quality.ap06
        assert cfg.scenario == "ALWAYS_FAIL"
        assert cfg.max_attempts == 2
        # non-target lines keep normal behaviour
        assert federation.effective_scenario("ASSY-SL01") == HAPPY_PATH
        # runtime proof: only the target line's motor terminates FAILED_FINAL
        target_runtime = federation.runtime(AP06_TARGET)
        history = target_runtime.get_quality_history("MTR-0001")
        assert history is not None
        assert [r.disposition for r in history.records_for("AP06")] == ["FAIL", "FAIL"]
        assert history.current_status.value == "failed_final"
        assert [r for r in history.records_for("AP08")] == []
        assert not [
            wid
            for wid in target_runtime.wip_ids
            if target_runtime.get_wip(wid) is not None
            and target_runtime.get_wip(wid).lifecycle.value == "released"
        ]
        other_runtime = federation.runtime("ASSY-SL01")
        assert [
            wid
            for wid in other_runtime.wip_ids
            if other_runtime.get_wip(wid) is not None
            and other_runtime.get_wip(wid).lifecycle.value == "released"
        ]

    def test_shared_transform_applies_to_a_single_config_only(self):
        federation = TipaAssyFederation(config_path=TIPA_CONFIG).initialize()
        sl01 = federation.get("ASSY-SL01")
        sl02 = federation.get("ASSY-SL02")
        before_sl01 = sl01.config.quality.ap06.scenario
        before_sl02 = (
            sl02.config.quality.ap06.scenario,
            dict(sl02.config.quality.ap06.overrides),
        )
        apply_scenario_quality_overrides(sl01.config, AP06_FAIL_RETEST_PASS)
        assert sl01.config.quality.ap06.scenario == "PASS"
        assert sl01.config.quality.ap06.overrides == {1: ["PASS"], 2: ["FAIL", "PASS"]}
        # the other config is untouched (no shared nested config objects)
        assert sl02.config.quality.ap06.scenario == before_sl02[0]
        assert dict(sl02.config.quality.ap06.overrides) == before_sl02[1]
        assert before_sl01 != ""  # the base config carries the demo exception route


# ═══════════════════════════════════════════════════════════════
# D. One-line hold/freeze, five continue
# ═══════════════════════════════════════════════════════════════

class TestHoldFreezeIndependence:
    def test_held_line_is_unchanged_while_five_continue(self):
        session = _session()
        session.advance()
        federation = _federation(session)
        bridge: AssyExecutionBridge = session.record.bridge

        assert bridge.held_sub_line_ids == ()
        bridge.hold_sub_line("ASSY-SL03")
        assert bridge.held_sub_line_ids == ("ASSY-SL03",)

        held_before = _line_state(federation.runtime("ASSY-SL03"))
        others_before = {
            sid: _line_state(federation.runtime(sid))
            for sid in SUB_LINE_IDS if sid != "ASSY-SL03"
        }

        for _ in range(5):
            session.advance()

        # held line: identical domain state AND simulation time
        assert _line_state(federation.runtime("ASSY-SL03")) == held_before
        assert federation.runtime("ASSY-SL03").simulation_time_s == 120.0
        assert federation.runtime("ASSY-SL03").motor_count == 0
        # the other five advanced all the way to AP04 join / motor creation
        for sid, before in others_before.items():
            after = _line_state(federation.runtime(sid))
            assert after != before, sid
            assert federation.runtime(sid).simulation_time_s == 720.0
            assert federation.runtime(sid).conveyor.dwell_number == 6
            assert federation.runtime(sid).motor_count >= 1
        # no shared-state corruption: the five remain mutually equivalent
        summaries = {sid: _line_summary(federation.runtime(sid)) for sid in SUB_LINE_IDS}
        reference = summaries["ASSY-SL01"]
        for sid, summary in summaries.items():
            if sid == "ASSY-SL03":
                continue
            assert summary == reference, sid

    def test_release_resumes_the_held_line(self):
        session = _session()
        session.advance()
        federation = _federation(session)
        bridge: AssyExecutionBridge = session.record.bridge
        bridge.hold_sub_line("ASSY-SL04")
        session.advance()
        session.advance()
        assert federation.runtime("ASSY-SL04").simulation_time_s == 120.0
        bridge.release_sub_line("ASSY-SL04")
        assert bridge.held_sub_line_ids == ()
        session.advance()
        assert federation.runtime("ASSY-SL04").simulation_time_s == 480.0

    def test_hold_fails_closed_on_unknown_sub_line(self):
        session = _session()
        session.advance()
        bridge: AssyExecutionBridge = session.record.bridge
        with pytest.raises(FederationError):
            bridge.hold_sub_line("ASSY-SL99")
        with pytest.raises(FederationError):
            bridge.release_sub_line("ASSY-SL99")

    def test_all_lines_held_fails_closed_without_advancing(self):
        session = _session()
        session.advance()
        federation = _federation(session)
        bridge: AssyExecutionBridge = session.record.bridge
        for sid in SUB_LINE_IDS:
            bridge.hold_sub_line(sid)
        before = {sid: _line_state(federation.runtime(sid)) for sid in SUB_LINE_IDS}
        result = bridge.advance(240.0, tuple(SUB_LINE_IDS), "hold-all")
        assert result.status == "failed"
        assert result.participants == ()
        assert "held" in (result.failure or "")
        for sid, state in before.items():
            assert _line_state(federation.runtime(sid)) == state, sid


# ═══════════════════════════════════════════════════════════════
# E. Determinism
# ═══════════════════════════════════════════════════════════════

class TestDeterminism:
    def test_two_fresh_sessions_produce_equivalent_bounded_production(self):
        _, a = _step_prepared_session("tipa-default", 15)
        _, b = _step_prepared_session("tipa-default", 15)
        assert _all_summaries(a) == _all_summaries(b)

    def test_two_fresh_sessions_equivalent_including_genealogy(self):
        _, a = _step_prepared_session("tipa-default", 6)
        _, b = _step_prepared_session("tipa-default", 6)
        for sid in SUB_LINE_IDS:
            assert _line_state(a.runtime(sid)) == _line_state(b.runtime(sid)), sid


# ═══════════════════════════════════════════════════════════════
# F. G22 lifecycle compatibility
# ═══════════════════════════════════════════════════════════════

class TestLifecycleCompatibility:
    def test_reset_keeps_run_identity_and_rebuilds_profile_consistent_state(self):
        session = _session()
        for _ in range(5):
            session.advance()
        federation = _federation(session)
        run_before = session.run_id
        profile_before = session.profile_id
        first_step_key = _all_summaries(federation)
        # capture the accepted first-step state for comparison after reset
        session.reset()
        assert session.run_id == run_before
        assert session.profile_id == profile_before
        for sid in SUB_LINE_IDS:
            runtime = federation.runtime(sid)
            assert runtime.simulation_time_s == 0.0
            assert runtime.conveyor.dwell_number == 0
            assert runtime.motor_count == 0
            assert len(runtime.genealogy.all_records()) == 0
            # re-prepared from the same immutable profile (no hidden carry-over)
            assert runtime.wip_count == 7
            assert runtime.rso2_buffer_size == 7
            state = federation.run_state(sid)
            assert state.sso2_idx == 1
            assert state.carrier_seq == 2
            assert state.profile_id == profile_before

        # stepping forward again reproduces the SAME accepted production state
        for _ in range(5):
            session.advance()
        assert _all_summaries(federation) == first_step_key

    def test_new_attempt_gets_fresh_run_identity_and_same_pinned_inputs(self):
        session = _session()
        session.advance()
        first_key = _all_summaries(_federation(session))
        old_run = session.run_id

        new_run = session.new_attempt()
        assert new_run != old_run
        assert session.profile_id == "tipa-assy-happy_path"
        session.advance()
        assert _all_summaries(_federation(session)) == first_key

    def test_replay_bounded_production_state_equivalence(self):
        session = _session()
        for _ in range(5):
            session.advance()
        first_key = _all_summaries(_federation(session))
        old_run = session.run_id

        new_run = session.replay()
        assert new_run != old_run
        for _ in range(5):
            session.advance()
        assert _all_summaries(_federation(session)) == first_key

    def test_no_state_carry_over_between_attempts(self):
        session = _session()
        for _ in range(5):
            session.advance()
        federation_before = _federation(session)
        session.new_attempt()
        session.advance()
        federation_after = _federation(session)
        # a fresh attempt owns its OWN runtime objects (no reuse)
        assert federation_after is not federation_before
        for sid in SUB_LINE_IDS:
            assert federation_after.runtime(sid) is not federation_before.runtime(sid)


# ═══════════════════════════════════════════════════════════════
# Frozen-invariant guards
# ═══════════════════════════════════════════════════════════════

class TestFrozenInvariants:
    def test_g4_exact_natural_boundary_unchanged(self):
        session = _session()
        session.advance()
        federation = _federation(session)
        bridge: AssyExecutionBridge = session.record.bridge
        # each accepted dwell is exactly the nominal 120 s boundary
        assert bridge.natural_next_boundary(SUB_LINE_IDS) == 240.0
        for _ in range(3):
            session.advance()
        for sid in SUB_LINE_IDS:
            assert federation.runtime(sid).simulation_time_s == 480.0
            assert federation.runtime(sid).conveyor.dwell_number == 4

    def test_fractional_or_arbitrary_boundary_still_fails_closed(self):
        federation = TipaAssyFederation(config_path=TIPA_CONFIG).initialize(
            run_profile=build_tipa_run_profile("tipa-default")
        )
        bridge = AssyExecutionBridge(federation)
        result = bridge.advance(60.0, ("ASSY-SL01",), "r1-fractional")
        assert result.status == "failed"
        assert "overshoots" in (result.failure or "")
        # no fractional dwell was invented
        assert federation.runtime("ASSY-SL01").simulation_time_s == 120.0 or (
            federation.runtime("ASSY-SL01").simulation_time_s == 0.0
        )

    def test_legacy_accepted_demo_behaviour_regression_green(self):
        comp = AssyDemoComposition(config_path=TIPA_CONFIG, scenario=DemoScenario.HAPPY_PATH)
        comp.initialize()
        assert comp.demo_step_number == 0
        for _ in range(5):
            comp.step_all()
        runtime = comp.contexts["ASSY-SL01"].runtime
        assert runtime.simulation_time_s == 600.0
        assert runtime.conveyor.dwell_number == 5
        assert runtime.wip_count == 16
        assert runtime.motor_count == 1
        assert runtime.rso2_buffer_size == 6
        assert [
            (g.child_wip_id, tuple(g.parent_wip_ids))
            for g in runtime.genealogy.all_records()
        ] == [("MTR-0001", ("SSO2-0001", "RSO2-0001"))]
        # per-context feed state still exposed through the compatibility views
        ctx = comp.contexts["ASSY-SL01"]
        assert ctx.sso2_idx == 6
        assert len(ctx.sso2_ids) == 15
        assert ctx.carrier_seq == 7

    def test_no_second_runtime_authority_under_the_session(self):
        import virtual_factory.assembly.demo_controller as demo_controller

        session = _session()
        session.advance()
        federation = _federation(session)
        assert type(federation) is TipaAssyFederation
        # the canonical session never hosts the legacy demo controller /
        # composition as its runtime authority
        assert not isinstance(federation, demo_controller.DemoController)
        assert not isinstance(federation, AssyDemoComposition)
        for value in vars(federation).values():
            assert not isinstance(value, demo_controller.DemoController)
            assert not isinstance(value, AssyDemoComposition)
        # one session -> one bridge -> one federation (six runtimes, no more)
        assert session.record.bridge is not None
        assert len(federation.sub_lines) == 6

    def test_no_demo_policy_names_leak_into_the_production_host(self):
        import virtual_factory.federation.assy_host as host_module

        for name in ("AssyDemoComposition", "DemoScenario", "ContinuousFeedPolicy"):
            assert name not in host_module.__dict__, name

    def test_unprepared_federation_contract_unchanged(self):
        """The plain production host still creates six unseeded runtimes."""
        federation = TipaAssyFederation(config_path=TIPA_CONFIG).initialize()
        assert federation.run_profile is None
        for sid in SUB_LINE_IDS:
            runtime = federation.runtime(sid)
            assert runtime.simulation_time_s == 0.0
            assert runtime.wip_count == 0
            assert federation.run_state(sid) is None
            assert federation.adapter(sid).is_prepared is False
