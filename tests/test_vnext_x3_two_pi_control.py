"""VF-SHW-X3 - the two admitted C2 PI loops and the C1 command arbitration.

The SA requires ACTUAL actuator response (not only a signal change): the inlet
valve must change the measured T106 inlet flow and the transfer pump must change
the measured T108 level, with feasible setpoint tracking, a disturbance response,
unreachable-setpoint saturation with an explicit reason, interlock/backwash
behaviour with the integral held, AUTO/MANUAL bumpless continuity and a declared
energy accounting including an exactly-zero OFF pump.
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from virtual_factory.shwtp.contracts import load_whole_plant_contracts  # noqa: E402
from virtual_factory.shwtp.x3_controls import (  # noqa: E402
    X3_CONTROL_ERROR_SIGN_FLOW,
    X3_CONTROL_ERROR_SIGN_LEVEL,
    PIController,
)
from virtual_factory.shwtp.x3_profile import load_x3_profile  # noqa: E402
from virtual_factory.shwtp.x3_whole_plant import (  # noqa: E402
    build_shwtp_whole_plant_x3,
)

X3_PROFILE_PATH = ROOT / "configs" / "vnext" / "shwtp" / "shwtp_x3_profile_v1.json"
FLOW_LOOP = "vf-shw-ctrl-f106-inlet-flow-pi"
LEVEL_LOOP = "vf-shw-ctrl-t108-level-pi"


@pytest.fixture(scope="module")
def profile():
    return load_x3_profile(X3_PROFILE_PATH)


@pytest.fixture(scope="module")
def contracts():
    return load_whole_plant_contracts()


def _profile_with(profile, **controller_overrides):
    controllers = dict(profile.controllers)
    for loop_id, changes in controller_overrides.items():
        controllers[loop_id] = replace(controllers[loop_id], **changes)
    return replace(profile, controllers=controllers)


def _profile_with_tank(profile, scope_id, **changes):
    tanks = dict(profile.tanks)
    tanks[scope_id] = replace(tanks[scope_id], **changes)
    return replace(profile, tanks=tanks)


def _run(model, ticks: int, *, offset: int = 0) -> None:
    for index in range(1, ticks + 1):
        model.run_window(f"w{offset + index}")


def _rows(model):
    return {row["controller_id"]: row for row in model.control_rows()}


class TestExactlyTwoLoops:
    def test_only_the_two_admitted_loops_are_active(self, profile, contracts):
        model = build_shwtp_whole_plant_x3(profile=profile, contracts=contracts, run_id="x3-two")
        _run(model, 5)
        report = model.control_report()
        assert report["active_c2_loop_ids"] == [FLOW_LOOP, LEVEL_LOOP]
        assert set(report["pi"]) == {FLOW_LOOP, LEVEL_LOOP}
        c1_ids = {row["controller_id"] for row in model.control_rows() if row["control_class"] == "C1"}
        assert len(c1_ids) == 9
        assert not any("pressure" in loop for loop in report["pi"])
        assert not any("raw-flow" in loop for loop in report["pi"])
        assert not any("t100-level" in loop for loop in report["pi"])
        # the deferred loops must be declared unavailable, never simulated
        for loop_id, note in profile.deferred_loops.items():
            if loop_id in (FLOW_LOOP, LEVEL_LOOP):
                assert "ACTIVE" in note
            else:
                assert "defer" in note.lower()


class TestRealActuatorResponse:
    def test_the_valve_changes_the_measured_inlet_flow(self, profile, contracts):
        low = _profile_with(profile, **{FLOW_LOOP: {"sp": 0.006}})
        high = _profile_with(profile, **{FLOW_LOOP: {"sp": 0.009}})
        rows = []
        for declared, model_profile in (("low", low), ("high", high)):
            model = build_shwtp_whole_plant_x3(
                profile=model_profile, contracts=contracts, run_id=f"x3-flow-{declared}"
            )
            _run(model, 1800)
            row = _rows(model)[FLOW_LOOP]
            measured = (
                model.participants["vf-shw-node-t106"].monitor_values()["inflow_m3h"] / 3600.0
            )
            rows.append((declared, row, measured))
            assert row["applied_by"] == "pi_flow_output"
            assert abs(measured - row["sp"]) / row["sp"] <= profile.acceptance.flow_steady_error_frac_of_sp
        (_, low_row, low_flow), (_, high_row, high_flow) = rows
        assert high_flow > low_flow
        assert high_row["applied_mv"] > low_row["applied_mv"], "the valve must open further"

    def test_the_pump_changes_the_measured_t108_level(self, profile, contracts):
        low = _profile_with(profile, **{LEVEL_LOOP: {"sp": 2.3}})
        high = _profile_with(profile, **{LEVEL_LOOP: {"sp": 2.7}})
        levels = []
        for declared, model_profile in (("low", low), ("high", high)):
            model = build_shwtp_whole_plant_x3(
                profile=model_profile, contracts=contracts, run_id=f"x3-level-{declared}"
            )
            _run(model, 2400)
            measured = model.participants["vf-shw-node-t108"].monitor_values()["level_m"]
            levels.append(measured)
            # the declared synthetic tuning meets the nominal acceptance band; an
            # off-nominal setpoint is documented to settle inside a 0.10 m band
            assert abs(measured - model_profile.controllers[LEVEL_LOOP].sp) <= 0.10
            assert model.balance_report()["plant_water"]["physical_valid"] is True
        assert levels[1] > levels[0], "the pump must actually move the level"

    def test_level_disturbance_is_rejected(self, profile, contracts):
        """A tank that starts off-setpoint ends inside the declared band."""
        disturbed = _profile_with_tank(profile, "vf-shw-node-t108", initial_volume_m3=44.0)
        model = build_shwtp_whole_plant_x3(
            profile=disturbed, contracts=contracts, run_id="x3-dist"
        )
        tank = model.participants["vf-shw-node-t108"]
        assert tank.monitor_values()["level_m"] == pytest.approx(2.2, abs=1e-9)
        _run(model, profile.acceptance.nominal_settling_window_s + 1200)
        measured = tank.monitor_values()["level_m"]
        assert abs(measured - profile.controllers[LEVEL_LOOP].sp) <= (
            profile.acceptance.level_steady_error_m
        )
        assert model.balance_report()["plant_water"]["physical_valid"] is True


class TestSaturationAndRecovery:
    def test_unreachable_flow_setpoint_saturates_with_a_reason(self, profile, contracts):
        unreachable = _profile_with(profile, **{FLOW_LOOP: {"sp": 0.012}})
        model = build_shwtp_whole_plant_x3(
            profile=unreachable, contracts=contracts, run_id="x3-unreachable"
        )
        _run(model, 1800)
        row = _rows(model)[FLOW_LOOP]
        measured = model.participants["vf-shw-node-t106"].monitor_values()["inflow_m3h"] / 3600.0
        assert row["applied_mv"] == pytest.approx(100.0, abs=1e-6), "the valve must go fully open"
        assert row["saturated"] is True
        assert row["limitation_reason"] == "output_saturated"
        assert row["alarm"] == "setpoint_unreachable_or_output_saturated"
        assert measured < row["sp"], "an unreachable SP must not be reported as met"
        # anti-windup: while the output is pinned at its limit the integral is held
        integral_before = row["integral"]
        _run(model, 60, offset=1800)
        assert _rows(model)[FLOW_LOOP]["integral"] == pytest.approx(integral_before, abs=1e-6)

    def test_reachable_setpoint_recovers_after_the_saturated_case(self, profile, contracts):
        model = build_shwtp_whole_plant_x3(profile=profile, contracts=contracts, run_id="x3-recover")
        _run(model, 1800)
        row = _rows(model)[FLOW_LOOP]
        assert row["saturated"] is False
        assert row["limitation_reason"] in ("ok", "actuator_slew_limit")
        measured = model.participants["vf-shw-node-t106"].monitor_values()["inflow_m3h"] / 3600.0
        assert abs(measured - row["sp"]) / row["sp"] <= profile.acceptance.flow_steady_error_frac_of_sp

    def test_slew_rate_is_enforced_on_the_actuators(self, profile, contracts):
        model = build_shwtp_whole_plant_x3(profile=profile, contracts=contracts, run_id="x3-slew")
        previous = None
        for index in range(1, 120):
            model.run_window(f"w{index}")
            row = _rows(model)[FLOW_LOOP]
            if previous is not None:
                delta = abs(row["applied_mv"] - previous)
                assert delta <= profile.controllers[FLOW_LOOP].slew_per_s + 1e-9
            previous = row["applied_mv"]


class TestInterlockAndBackwash:
    def test_backwash_closes_the_inlet_and_releases_bumpless(self, profile, contracts):
        """The C1 backwash owns the valve: the PI holds its integral and recovers."""
        model = build_shwtp_whole_plant_x3(profile=profile, contracts=contracts, run_id="x3-backwash")
        arbitration_seen = False
        integral_during = None
        for index in range(1, 3601):
            model.run_window(f"w{index}")
            report = model.control_report()
            step = report["arbitration"]["inlet_valve_pos"]
            row = _rows(model)[FLOW_LOOP]
            if step == "c1_backwash_closes_inlet":
                arbitration_seen = True
                assert row["applied_mv"] == pytest.approx(0.0, abs=1e-9)
                assert row["applied_by"] == "c1_backwash_closes_inlet"
                measured = (
                    model.participants["vf-shw-node-t106"].monitor_values()["inflow_m3h"] / 3600.0
                )
                assert measured == pytest.approx(0.0, abs=1e-9), "a closed valve must stop the flow"
                integral_during = row["integral"]
                assert row["pi_output_mv"] is not None
            if arbitration_seen and step == "pi_flow_output" and index > 100:
                # released: the PI is driving again and the flow recovers
                _run(model, 900, offset=index)
                recovered = _rows(model)[FLOW_LOOP]
                measured = (
                    model.participants["vf-shw-node-t106"].monitor_values()["inflow_m3h"] / 3600.0
                )
                assert recovered["applied_by"] == "pi_flow_output"
                assert abs(measured - recovered["sp"]) / recovered["sp"] <= (
                    profile.acceptance.flow_steady_error_frac_of_sp
                )
                assert integral_during is not None
                break
        assert arbitration_seen, "the declared DP threshold must start a backwash within the run"
        assert model.balance_report()["plant_water"]["physical_valid"] is True

    def test_interlock_protective_stop_is_available_on_the_loop(self, profile, contracts):
        model = build_shwtp_whole_plant_x3(profile=profile, contracts=contracts, run_id="x3-trip")
        _run(model, 300)
        status = model.control_layer.flow_pi.evaluate(
            pv=0.005, dt_s=1.0, interlock=True, interlock_alarm="f106_inlet_path_interlock"
        )
        assert status.applied_mv == profile.controllers[FLOW_LOOP].output_min
        assert status.limitation_reason == "interlock_protective_stop"
        assert status.alarm == "f106_inlet_path_interlock"
        forced = model.control_layer.level_pi.evaluate(pv=2.5, dt_s=1.0, forced_stop=True)
        assert forced.limitation_reason == "forced_stop_integral_held"
        assert forced.applied_mv == profile.controllers[LEVEL_LOOP].output_min


class TestAutoManualContinuity:
    def test_manual_to_auto_is_bumpless(self, profile):
        controller = PIController(profile.controllers[LEVEL_LOOP], error_sign=X3_CONTROL_ERROR_SIGN_LEVEL)
        for _ in range(60):
            status = controller.evaluate(pv=2.6, dt_s=1.0)
        assert status.mode == "AUTO"
        controller.set_mode("MANUAL", manual_mv=55.0)
        manual = controller.evaluate(pv=2.6, dt_s=1.0)
        assert manual.mode == "MANUAL"
        assert manual.applied_mv == pytest.approx(55.0, abs=profile.controllers[LEVEL_LOOP].slew_per_s)
        controller.set_mode("AUTO")
        auto = controller.evaluate(pv=2.6, dt_s=1.0)
        assert auto.mode == "AUTO"
        # the transfer is continuous: the requested output does not jump
        assert abs(auto.applied_mv - manual.applied_mv) <= (
            profile.controllers[LEVEL_LOOP].slew_per_s + 1e-9
        )

    def test_flow_loop_error_sign_is_explicit(self, profile):
        flow = PIController(profile.controllers[FLOW_LOOP], error_sign=X3_CONTROL_ERROR_SIGN_FLOW)
        status = flow.evaluate(pv=0.004, dt_s=1.0)  # PV below SP
        assert status.error == pytest.approx(profile.controllers[FLOW_LOOP].sp - 0.004, abs=1e-12)
        assert status.applied_mv > profile.controllers[FLOW_LOOP].bias
        level = PIController(profile.controllers[LEVEL_LOOP], error_sign=X3_CONTROL_ERROR_SIGN_LEVEL)
        status = level.evaluate(pv=2.8, dt_s=1.0)  # PV above SP
        assert status.error == pytest.approx(2.8 - profile.controllers[LEVEL_LOOP].sp, abs=1e-12)
        assert status.applied_mv > profile.controllers[LEVEL_LOOP].bias


class TestEnergy:
    def test_energy_matches_the_declared_power_curve(self, profile, contracts):
        model = build_shwtp_whole_plant_x3(profile=profile, contracts=contracts, run_id="x3-energy")
        _run(model, 1200)
        report = model.energy_report()
        assert report["total_energy_j"] > 0.0
        for pump_id, point in report["pump_operating_points"].items():
            seconds = report["per_pump_running_s"].get(pump_id, 0.0)
            energy = report["per_pump_electric_j"].get(pump_id, 0.0)
            assert point["feasible"] is True
            assert point["electric_w"] <= point["motor_rating_w"] + 1e-6
            if point["off"]:
                assert point["electric_w"] == 0.0
            if seconds > 0.0:
                # the integrated energy must be consistent with a power that stays
                # inside the declared no-load .. motor-rating envelope
                average_w = energy / seconds
                assert average_w >= 0.0
                assert average_w <= point["motor_rating_w"] + 1e-6
        assert report["total_energy_j"] == pytest.approx(
            sum(report["per_pump_electric_j"].values()), rel=1e-9
        )
        assert report["unavailable_energy"], "unmodelled energy must be declared unavailable"

    def test_off_pump_moves_nothing_and_integrates_no_hydraulic_energy(self, profile, contracts):
        """A level far ABOVE the setpoint drives the transfer pump to OFF.

        C01-2 semantics: an OFF (not energized) pump integrates exactly zero, while an
        ENERGIZED pump that moved no water may only integrate the declared idle loss -
        never a hydraulic power derived from a capacity flow.
        """
        high_sp = _profile_with(profile, **{LEVEL_LOOP: {"sp": 3.4}})
        model = build_shwtp_whole_plant_x3(profile=high_sp, contracts=contracts, run_id="x3-off")
        _run(model, 400)
        report = model.energy_report()
        point = report["pump_operating_points"]["t108-transfer-pump"]
        pump = model.pump_models["t108-transfer-pump"].pump
        assert point["flow_m3h"] == 0.0, "the loop must be able to stop the transfer"
        assert point["hydraulic_w"] == 0.0
        assert point["off"] is True or point["idle"] is True, (
            "a stopped transfer is either OFF or energized without water"
        )
        assert point["electric_w"] == pytest.approx(
            0.0 if point["off"] else pump.no_load_w
        )
        expected = 0.0
        for row in model.energy_trace():
            data = row["pumps"]["t108-transfer-pump"]
            if data["off"]:
                assert data["electric_w"] == 0.0
                assert data["energy_delta_j"] == 0.0
                continue
            assert data["electric_w"] == pytest.approx(
                data["hydraulic_w"] / pump.eta_total + pump.no_load_w, abs=1e-9
            )
            expected += data["energy_delta_j"]
        assert report["per_pump_electric_j"].get("t108-transfer-pump", 0.0) == pytest.approx(
            expected, abs=1e-6
        )
        assert model.participants["vf-shw-node-t108"].monitor_values()["outflows_m3h"][
            "vf-shw-node-dist-p108"
        ] == 0.0


def _drive_pi(pi, *, pv: float, ticks: int) -> None:
    for _ in range(ticks):
        pi.evaluate(pv=pv, dt_s=1.0)


def _flow_pi(profile, sp: float | None = None) -> PIController:
    config = profile.controllers[FLOW_LOOP] if sp is None else replace(
        profile.controllers[FLOW_LOOP], sp=sp
    )
    return PIController(config, error_sign=X3_CONTROL_ERROR_SIGN_FLOW)


def _level_pi(profile, sp: float | None = None) -> PIController:
    config = profile.controllers[LEVEL_LOOP] if sp is None else replace(
        profile.controllers[LEVEL_LOOP], sp=sp
    )
    return PIController(config, error_sign=X3_CONTROL_ERROR_SIGN_LEVEL)


_PROTECTIONS = {
    "trip": {"forced_stop": True},
    "interlock": {"interlock": True, "interlock_alarm": "c01_interlock"},
    "c1_override": {
        "external_override": True,
        "external_override_mv": 0.0,
        "external_override_reason": "c1_backwash_closes_inlet",
    },
}


class TestC01ActuatorTrackingAndReleaseSlew:
    """SA C01-1: the final physical actuator must be the controller's actuator.

    Reproduces the SA counterexample (a valve that was forced to 0 % must not reopen
    to its pre-stop command in one second) and drives every protective path of BOTH
    loops through entry -> release, asserting the tracked actual value, the first-tick
    integral hold and a slew-limited ordinary reopening.
    """

    def test_sa_counterexample_cannot_reopen_90_percent_in_one_second(self, profile):
        """The exact SA reproduction: normal 90 % -> stop 0 % -> release."""
        pi = _flow_pi(profile)
        _drive_pi(pi, pv=0.008, ticks=60)
        assert pi.applied_mv == pytest.approx(90.0, abs=1e-6), "declared working point"
        stopped = pi.evaluate(pv=0.008, dt_s=1.0, forced_stop=True)
        assert stopped.applied_mv == 0.0
        assert pi.applied_mv == 0.0, "the stopped value must be the TRACKED value"
        released = pi.evaluate(pv=0.008, dt_s=1.0)
        step = abs(released.applied_mv - stopped.applied_mv)
        assert step <= profile.controllers[FLOW_LOOP].slew_per_s + 1e-9, (
            f"reopening jumped {step:.3f} pp in one second"
        )

    @pytest.mark.parametrize("protection", sorted(_PROTECTIONS))
    @pytest.mark.parametrize("loop", ["flow", "level"])
    def test_protective_entry_and_release_for_both_loops(self, profile, loop, protection):
        config = profile.controllers[FLOW_LOOP if loop == "flow" else LEVEL_LOOP]
        pi = _flow_pi(profile) if loop == "flow" else _level_pi(profile)
        pv = 0.008 if loop == "flow" else 2.5
        # a PV CONSISTENT with the protected actuator: a closed valve gives no inlet
        # flow, a stopped transfer pump lets the level rise above the setpoint
        release_pv = 0.0 if loop == "flow" else 2.6
        _drive_pi(pi, pv=pv, ticks=60)
        working = pi.applied_mv
        integral_before = pi.integral
        assert working > config.output_min + 1.0

        first = pi.evaluate(pv=pv, dt_s=1.0, **_PROTECTIONS[protection])
        assert first.applied_mv == config.output_min
        assert first.protection == protection
        assert first.integral_held is True
        assert first.committed_actual_mv == config.output_min
        # first-tick integral hold: ONE protected scan must not move the integral
        assert pi.integral == pytest.approx(integral_before, abs=1e-12)
        # the tracked actuator is the protective value, not the stale command
        assert pi.applied_mv == config.output_min

        # stay protected with a CHANGED PV: the integral stays held
        for index in range(5):
            pi.evaluate(
                pv=pv + (0.001 if loop == "flow" else 0.05) * (index + 1),
                dt_s=1.0,
                **_PROTECTIONS[protection],
            )
        assert pi.integral == pytest.approx(integral_before, abs=1e-12)

        # release: the first ordinary step starts FROM the actual stopped value
        release = pi.evaluate(pv=release_pv, dt_s=1.0)
        assert abs(release.applied_mv - config.output_min) <= config.slew_per_s + 1e-9
        previous = release.applied_mv
        reopened = release.applied_mv > config.output_min + 1e-9
        for _ in range(40):
            status = pi.evaluate(pv=release_pv, dt_s=1.0)
            assert abs(status.applied_mv - previous) <= config.slew_per_s + 1e-9
            previous = status.applied_mv
            if status.applied_mv > config.output_min + 1e-9:
                reopened = True
        assert reopened, "the loop must be able to take the actuator back"

    def test_manual_mode_and_changed_pv_during_a_stop(self, profile):
        """MANUAL holds the integral too and the release stays inside the slew."""
        config = profile.controllers[LEVEL_LOOP]
        pi = _level_pi(profile)
        _drive_pi(pi, pv=2.5, ticks=30)
        pi.set_mode("MANUAL", manual_mv=55.0)
        _drive_pi(pi, pv=2.5, ticks=5)
        integral_before = pi.integral
        stopped = pi.evaluate(pv=2.9, dt_s=1.0, forced_stop=True)
        assert stopped.applied_mv == 0.0
        assert pi.applied_mv == 0.0
        assert pi.integral == pytest.approx(integral_before, abs=1e-12)
        # PV changes during the stop while MANUAL stays selected
        pi.evaluate(pv=2.2, dt_s=1.0, forced_stop=True)
        assert pi.integral == pytest.approx(integral_before, abs=1e-12)
        first = pi.evaluate(pv=2.2, dt_s=1.0)
        assert abs(first.applied_mv) <= config.slew_per_s + 1e-9
        previous = first.applied_mv
        for _ in range(30):
            status = pi.evaluate(pv=2.2, dt_s=1.0)
            assert abs(status.applied_mv - previous) <= config.slew_per_s + 1e-9
            previous = status.applied_mv

    def test_runtime_actuator_continuity_across_the_backwash_episode(self, profile, contracts):
        """No ordinary step may exceed the slew; entering protection is exempt."""
        model = build_shwtp_whole_plant_x3(
            profile=profile, contracts=contracts, run_id="x3-c01-continuity"
        )
        slew = profile.controllers[FLOW_LOOP].slew_per_s
        previous_valve = None
        previous_owner = None
        violations = []
        owners = set()
        for index in range(1, 5401):
            model.run_window(f"w{index}")
            report = model.control_report()
            owner = report["arbitration"]["inlet_valve_pos"]
            valve = float(model._control.commands["inlet_valve_pos"])
            tracked = model.control_layer.flow_pi.applied_mv
            assert tracked == pytest.approx(valve, abs=1e-9), (
                f"tick {index}: tracked {tracked} != realized {valve}"
            )
            if previous_valve is not None:
                enters_protection = (
                    owner != "pi_flow_output" and previous_owner == "pi_flow_output"
                )
                step = abs(valve - previous_valve)
                if not enters_protection and step > slew + 1e-9:
                    violations.append((index, previous_owner, owner, step))
            owners.add(owner)
            previous_valve, previous_owner = valve, owner
        assert "c1_backwash_closes_inlet" in owners, "the DP threshold must start a backwash"
        assert "pi_flow_output" in owners, "the loop must take the valve back"
        assert violations == [], f"unslew re-openings: {violations[:5]}"

    def test_runtime_pump_command_continuity(self, profile, contracts):
        """The same continuity statement for the transfer pump (5 pp/s)."""
        model = build_shwtp_whole_plant_x3(
            profile=profile, contracts=contracts, run_id="x3-c01-pump"
        )
        slew = profile.controllers[LEVEL_LOOP].slew_per_s
        previous_speed = None
        previous_owner = None
        violations = []
        for index in range(1, 1801):
            model.run_window(f"w{index}")
            report = model.control_report()
            owner = report["arbitration"]["transfer_pump_speed_cmd"]
            speed = float(model._control.commands["transfer_pump_speed_cmd"])
            assert model.control_layer.level_pi.applied_mv == pytest.approx(speed, abs=1e-9)
            if previous_speed is not None:
                enters_protection = (
                    owner != "pi_level_output" and previous_owner == "pi_level_output"
                )
                step = abs(speed - previous_speed)
                if not enters_protection and step > slew + 1e-9:
                    violations.append((index, previous_owner, owner, step))
            previous_speed, previous_owner = speed, owner
        assert violations == [], f"unslew pump re-starts: {violations[:5]}"

    def test_layer_trip_and_release_stop_the_pump_without_a_jump(self, profile, contracts):
        """The pump loop through the LAYER: trip value tracked, release slew limited."""
        model = build_shwtp_whole_plant_x3(
            profile=profile, contracts=contracts, run_id="x3-c01-layer-pump"
        )
        layer = model.control_layer
        slew = profile.controllers[LEVEL_LOOP].slew_per_s
        _run(model, 400)
        feedback = model._feedback
        level = float(model.participants["vf-shw-node-t108"].monitor_values()["level_m"])
        inlet = (
            float(model.participants["vf-shw-node-t106"].monitor_values()["inflow_m3h"]) / 3600.0
        )
        assert layer.level_pi.applied_mv > 5.0

        tripped = layer.evaluate(
            feedback,
            inlet_flow_m3_s=inlet,
            t108_level_m=level,
            trips={LEVEL_LOOP: True},
        )
        assert tripped.arbitration["transfer_pump_speed_cmd"] == "physical_trip_forced_stop"
        assert tripped.commands["transfer_pump_speed_cmd"] == 0.0
        assert layer.level_pi.applied_mv == 0.0, "the trip value must be tracked"
        assert tripped.pi_statuses[LEVEL_LOOP].integral_held is True
        layer.commit_tick(tripped)

        released = layer.evaluate(feedback, inlet_flow_m3_s=inlet, t108_level_m=level)
        assert released.arbitration["transfer_pump_speed_cmd"] == "pi_level_output"
        step = abs(released.commands["transfer_pump_speed_cmd"])
        assert step <= slew + 1e-9, f"the pump re-started with {step:.3f} pp in one second"
        layer.commit_tick(released)


class TestC01SetpointStepsInsideOneAttempt:
    """SA C01-1 repair 2: steps and recovery inside ONE ongoing attempt."""

    def test_feasible_step_unreachable_then_recovery_on_one_attempt(self, profile, contracts):
        model = build_shwtp_whole_plant_x3(
            profile=profile, contracts=contracts, run_id="x3-c01-steps"
        )
        flow = model.control_layer.flow_pi
        acceptance = profile.acceptance
        advanced = {"ticks": 0}

        def advance(ticks: int) -> None:
            _run(model, ticks, offset=advanced["ticks"])
            advanced["ticks"] += ticks

        flow.set_setpoint(0.006)
        advance(acceptance.nominal_settling_window_s + 600)
        measured = (
            model.participants["vf-shw-node-t106"].monitor_values()["inflow_m3h"] / 3600.0
        )
        assert abs(measured - 0.006) / 0.006 <= acceptance.flow_steady_error_frac_of_sp
        assert flow.applied_mv > 0.0

        # step UP to the admitted maximum (unreachable here) on the SAME attempt
        flow.set_setpoint(0.0125)
        advance(acceptance.nominal_settling_window_s)
        saturated = _rows(model)[FLOW_LOOP]
        assert saturated["saturated"] is True
        assert saturated["limitation_reason"] == "output_saturated"
        assert saturated["alarm"] == "setpoint_unreachable_or_output_saturated"
        pinned = (
            model.participants["vf-shw-node-t106"].monitor_values()["inflow_m3h"] / 3600.0
        )
        assert pinned < saturated["sp"], "an unreachable SP is never reported as met"

        # recover on the SAME attempt, retaining controller state
        flow.set_setpoint(0.008)
        advance(acceptance.nominal_settling_window_s)
        recovered = _rows(model)[FLOW_LOOP]
        recovered_measured = (
            model.participants["vf-shw-node-t106"].monitor_values()["inflow_m3h"] / 3600.0
        )
        assert recovered["saturated"] is False
        assert (
            abs(recovered_measured - 0.008) / 0.008
            <= acceptance.flow_steady_error_frac_of_sp
        )
        # the valve had to come back DOWN from the saturation limit to the SP -> the
        # recovery is a real, slew-limited actuator movement on one continuing attempt
        assert recovered["applied_mv"] < saturated["applied_mv"]
        assert recovered_measured < pinned + 1e-9
        assert model.balance_report()["plant_water"]["physical_valid"] is True

    def test_setpoint_outside_the_admissible_range_fails_closed(self, profile):
        flow = _flow_pi(profile)
        with pytest.raises(Exception):
            flow.set_setpoint(0.5)
