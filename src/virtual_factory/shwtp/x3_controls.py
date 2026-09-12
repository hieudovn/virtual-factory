"""SH-WTP X3 control layer: the two admitted C2 PI loops + C1 arbitration (D7).

Implements the SA design freeze (Issue #97 D7) on top of the REUSED frozen C1
layer (:mod:`x2_controls`, all nine functions retained, X2 behaviour unchanged):

- two deterministic PI loops only - ``vf-shw-ctrl-f106-inlet-flow-pi`` (flow,
  ``u_raw = bias + Kp*e + I`` with ``e = SP - PV``) and ``vf-shw-ctrl-t108-level-pi``
  (level, ``e = PV - SP`` so a higher tank level increases withdrawal);
- scan dt = 1 s, ``I += Ki*e*dt`` only while not driving saturation further,
  back-calculation ``Kb*(u_applied - u_raw)*dt`` on the FINAL realized actuator
  command, no derivative term;
- explicit AUTO/MANUAL with bump transfer (``I = u_actual - bias - Kp*e`` on
  MANUAL->AUTO or release of a forced stop), held integral while force-stopped,
  interlocks applied in MANUAL too;
- actuator slew limits (valve, pump) with a protective close/stop overriding the
  slew;
- explicit priority: physical feasibility and trips > C1 backwash/permissive >
  MANUAL/AUTO PI request; the C1 layer can never overwrite an active PI output
  during normal enabled service - its fixed T106/T108 commands become
  enable/override arbitration;
- both the REQUESTED and the APPLIED MV plus a limitation reason are retained,
  and an unreachable setpoint saturates with an alarm instead of inventing flow.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from virtual_factory.shwtp.x2_controls import C1ControllerSet, C1Evaluation, build_c1_controllers
from virtual_factory.shwtp.x3_profile import X3PIConfig, X3Profile

X3_CONTROL_ERROR_SIGN_FLOW = "sp_minus_pv"
X3_CONTROL_ERROR_SIGN_LEVEL = "pv_minus_sp"


class X3ControlError(ValueError):
    """Raised when the X3 control layer cannot honour its contract (fail closed)."""


def _with_actual_actuator(status: PIStatus, *, actual_mv: float, applied_by: str) -> PIStatus:
    """Stamp the REAL actuator value and its owner onto a PI status.

    ``applied_mv`` always means the value the plant actually received; the PI's own
    pre-arbitration command stays available as ``pi_output_mv``.
    """
    detail = dict(status.detail)
    detail["applied_by"] = applied_by
    detail.setdefault("pi_output_mv", round(status.applied_mv, 9))
    return replace(status, applied_mv=actual_mv, detail=detail)


def _num(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise X3ControlError(f"{name} must be a finite number, got {value!r}")
    out = float(value)
    if not math.isfinite(out):
        raise X3ControlError(f"{name} must be a finite number, got {value!r}")
    return out


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@dataclass(slots=True)
class PIStatus:
    """One deterministic PI evaluation (requested vs applied MV + reason)."""

    controller_id: str
    mode: str
    sp: float
    pv: float
    error: float
    u_raw: float
    requested_mv: float
    applied_mv: float
    integral: float
    saturated: bool
    limited: bool
    limitation_reason: str
    alarm: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)

    @property
    def pi_output_mv(self) -> float:
        """What the PI itself would command (before actuator arbitration)."""
        return round(float(self.detail.get("pi_output_mv", self.applied_mv)), 9)

    @property
    def applied_by(self) -> str:
        """Who currently owns the actuator (``pi`` or the arbitrating C1 rule)."""
        return str(self.detail.get("applied_by", "pi"))


class PIController:
    """One X3 PI loop (D7): deterministic, no derivative, back-calculation."""

    def __init__(self, config: X3PIConfig, *, error_sign: str) -> None:
        if error_sign not in (X3_CONTROL_ERROR_SIGN_FLOW, X3_CONTROL_ERROR_SIGN_LEVEL):
            raise X3ControlError(f"unknown error sign {error_sign!r}")
        self.config = config
        self.error_sign = error_sign
        self.reset()

    # lifecycle -------------------------------------------------------------
    def reset(self) -> None:
        self.mode = "AUTO"
        self._integral = 0.0
        self._applied_mv = self.config.bias
        self._manual_mv = self.config.manual_default
        self._forced_stop = False

    # helpers ---------------------------------------------------------------
    @property
    def integral(self) -> float:
        return self._integral

    @property
    def applied_mv(self) -> float:
        return self._applied_mv

    @property
    def mode_name(self) -> str:
        return self.mode

    def _error(self, sp: float, pv: float) -> float:
        return sp - pv if self.error_sign == X3_CONTROL_ERROR_SIGN_FLOW else pv - sp

    def set_mode(self, mode: str, *, manual_mv: float | None = None) -> None:
        """Switch AUTO/MANUAL with an explicit bumpless transfer."""
        if mode not in ("AUTO", "MANUAL"):
            raise X3ControlError(f"unknown PI mode {mode!r}")
        if mode == "MANUAL":
            self.mode = "MANUAL"
            if manual_mv is not None:
                self._manual_mv = _num(manual_mv, "manual_mv")
            return
        if self.mode == "MANUAL":
            # MANUAL -> AUTO: preload the integral so the requested MV is continuous
            error = self._error(self.config.sp, self._last_pv)
            self._integral = self._applied_mv - self.config.bias - self.config.kp * error
        self.mode = "AUTO"

    def set_manual(self, manual_mv: float) -> None:
        self._manual_mv = _num(manual_mv, "manual_mv")

    # evaluation ------------------------------------------------------------
    _last_pv: float = 0.0

    def evaluate(
        self,
        *,
        pv: float,
        dt_s: float,
        forced_stop: bool = False,
        interlock: bool = False,
        interlock_alarm: str | None = None,
        external_override: bool = False,
    ) -> PIStatus:
        """Evaluate one scan.

        ``external_override`` means the actuator is currently owned by the C1
        arbitration (a backwash step or a permissive): the PI still reports its
        requested output but its integral is HELD, so the release is bumpless and
        the loop cannot wind up while it is not driving the plant.
        """
        pv = _num(pv, "pv")
        dt_s = _num(dt_s, "dt_s")
        if dt_s <= 0:
            raise X3ControlError("dt_s must be > 0")
        self._last_pv = pv
        config = self.config
        error = self._error(config.sp, pv)
        sp = config.sp
        alarm: str | None = None
        reason = "ok"

        # Priority 1: physical feasibility / trips. A forced stop holds the
        # integral and applies the protective close/stop value.
        if forced_stop:
            self._forced_stop = True
            requested = self._applied_mv
            applied = config.output_min
            return PIStatus(
                controller_id=config.controller_id,
                mode=self.mode,
                sp=sp,
                pv=pv,
                error=error,
                u_raw=requested,
                requested_mv=requested,
                applied_mv=applied,
                integral=self._integral,
                saturated=False,
                limited=True,
                limitation_reason="forced_stop_integral_held",
                alarm="controller_forced_stop",
            )
        if self._forced_stop:
            # release: bumpless preload of the integral
            self._integral = self._applied_mv - config.bias - config.kp * error
            self._forced_stop = False
            reason = "released_from_forced_stop_bumpless"

        # Priority 2: interlocks apply in MANUAL too.
        if interlock:
            requested = self._requested_mv(error)
            applied = config.output_min
            return PIStatus(
                controller_id=config.controller_id,
                mode=self.mode,
                sp=sp,
                pv=pv,
                error=error,
                u_raw=requested,
                requested_mv=requested,
                applied_mv=applied,
                integral=self._integral,
                saturated=False,
                limited=True,
                limitation_reason="interlock_protective_stop",
                alarm=interlock_alarm or "controller_interlock",
            )

        # Priority 3: MANUAL / AUTO PI request.
        if self.mode == "MANUAL":
            requested = self._manual_mv
            applied = self._apply_slew(requested, dt_s)
            return PIStatus(
                controller_id=config.controller_id,
                mode="MANUAL",
                sp=sp,
                pv=pv,
                error=error,
                u_raw=requested,
                requested_mv=requested,
                applied_mv=applied,
                integral=self._integral,
                saturated=False,
                limited=abs(applied - requested) > 1e-12,
                limitation_reason="manual_mode",
            )

        u_raw = self._requested_mv(error)
        clamped = _clamp(u_raw, config.output_min, config.output_max)
        driving_up = clamped >= config.output_max - 1e-12 and error > 0.0
        driving_down = clamped <= config.output_min + 1e-12 and error < 0.0
        # an output that sits at a limit while the error still drives further is a
        # SATURATED loop even when the raw request never exceeded the range: the PV
        # cannot follow the SP. Report it explicitly instead of "ok".
        saturated = abs(clamped - u_raw) > 1e-12 or driving_up or driving_down
        if saturated:
            alarm = "setpoint_unreachable_or_output_saturated"
            reason = "output_saturated"
        if external_override:
            # the C1 arbitration owns the actuator this tick: hold the integral so
            # the PI neither winds up nor fights the protecting rule
            requested = clamped
            return PIStatus(
                controller_id=config.controller_id,
                mode="AUTO",
                sp=sp,
                pv=pv,
                error=error,
                u_raw=u_raw,
                requested_mv=requested,
                applied_mv=self._applied_mv,
                integral=self._integral,
                saturated=saturated,
                limited=True,
                limitation_reason="external_c1_override_integral_held",
                alarm=alarm,
                detail={
                    "pi_output_mv": round(clamped, 9),
                    "applied_by": "c1_arbitration",
                    "external_override": True,
                },
            )
        # integrate only while not driving saturation further
        if not (driving_up or driving_down):
            self._integral += config.ki * error * dt_s
        applied = self._apply_slew(clamped, dt_s)
        # back-calculation on the FINAL realized actuator command
        self._integral += config.kb * (applied - u_raw) * dt_s
        limited = abs(applied - clamped) > 1e-12
        if limited:
            reason = "actuator_slew_limit"
        return PIStatus(
            controller_id=config.controller_id,
            mode="AUTO",
            sp=sp,
            pv=pv,
            error=error,
            u_raw=u_raw,
            requested_mv=clamped,
            applied_mv=applied,
            integral=self._integral,
            saturated=saturated,
            limited=limited,
            limitation_reason=reason,
            alarm=alarm,
            detail={
                "pi_output_mv": round(applied, 9),
                "applied_by": "pi",
                "external_override": False,
            },
        )

    def _requested_mv(self, error: float) -> float:
        return self.config.bias + self.config.kp * error + self._integral

    def _apply_slew(self, target: float, dt_s: float) -> float:
        config = self.config
        step = config.slew_per_s * _num(dt_s, "dt_s")
        lower = self._applied_mv - step
        upper = self._applied_mv + step
        applied = _clamp(target, max(config.output_min, lower), min(config.output_max, upper))
        self._applied_mv = applied
        return applied

    def status(self) -> dict[str, Any]:
        return {
            "controller_id": self.config.controller_id,
            "mode": self.mode,
            "sp": self.config.sp,
            "sp_admissible": list(self.config.sp_admissible),
            "integral": self._integral,
            "applied_mv": self._applied_mv,
            "force_stopped": self._forced_stop,
        }

@dataclass(frozen=True, slots=True)
class X3ControlEvaluation:
    """The arbitrated X3 control result of one tick."""

    tick_index: int
    c1: C1Evaluation
    pi_statuses: Mapping[str, PIStatus]
    commands: Mapping[str, Any]
    arbitration: Mapping[str, str]
    alarms: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "tick_index": self.tick_index,
            "pi": {
                loop_id: {
                    "mode": status.mode,
                    "sp": status.sp,
                    "pv": status.pv,
                    "error": status.error,
                    "u_raw": status.u_raw,
                    "requested_mv": status.requested_mv,
                    "applied_mv": status.applied_mv,
                    "pi_output_mv": status.pi_output_mv,
                    "applied_by": status.applied_by,
                    "integral": status.integral,
                    "saturated": status.saturated,
                    "limited": status.limited,
                    "limitation_reason": status.limitation_reason,
                    "alarm": status.alarm,
                }
                for loop_id, status in sorted(self.pi_statuses.items())
            },
            "arbitration": dict(sorted(self.arbitration.items())),
            "alarms": list(self.alarms),
        }


class X3ControlLayer:
    """The nine reused C1 functions + the two admitted C2 PI loops (D7)."""

    valve_signal = "inlet_valve_pos"
    valve_scope = "vf-shw-node-t106"
    pump_signal = "transfer_pump_speed_cmd"
    pump_scope = "vf-shw-node-t108"
    flow_loop_id = "vf-shw-ctrl-f106-inlet-flow-pi"
    level_loop_id = "vf-shw-ctrl-t108-level-pi"

    def __init__(
        self,
        *,
        profile: X3Profile,
        control_entries: Mapping[str, Mapping[str, Any]],
    ) -> None:
        self.profile = profile
        self.c1 = build_c1_controllers(control_entries, dt_s=profile.tick_s)
        self.flow_pi = PIController(
            profile.controllers[self.flow_loop_id], error_sign=X3_CONTROL_ERROR_SIGN_FLOW
        )
        self.level_pi = PIController(
            profile.controllers[self.level_loop_id], error_sign=X3_CONTROL_ERROR_SIGN_LEVEL
        )
        self._tick_index = 0
        #: actuator ownership of the previous tick (explicit_lagged): while a C1
        #: rule owns an actuator the corresponding PI holds its integral
        self._flow_override = False
        self._level_override = False

    # lifecycle -------------------------------------------------------------
    def reset(self) -> None:
        self.c1.reset()
        self.flow_pi.reset()
        self.level_pi.reset()
        self._tick_index = 0
        self._flow_override = False
        self._level_override = False

    @property
    def active_c2_loop_ids(self) -> tuple[str, ...]:
        return (self.flow_loop_id, self.level_loop_id)

    def controllers(self) -> Mapping[str, PIController]:
        return {self.flow_loop_id: self.flow_pi, self.level_loop_id: self.level_pi}

    # evaluation ------------------------------------------------------------
    def evaluate(
        self,
        feedback: Mapping[str, Any],
        *,
        inlet_flow_m3_s: float,
        t108_level_m: float,
        trips: Mapping[str, bool] | None = None,
        interlock_alarms: Mapping[str, str] | None = None,
    ) -> X3ControlEvaluation:
        tick = self._tick_index + 1
        c1 = self.c1.evaluate(feedback, tick)
        trips = trips or {}
        interlock_alarms = interlock_alarms or {}
        dt_s = self.profile.tick_s

        flow_status = self.flow_pi.evaluate(
            pv=_num(inlet_flow_m3_s, "inlet_flow_m3_s"),
            dt_s=dt_s,
            forced_stop=bool(trips.get(self.flow_loop_id, False)),
            interlock=bool(trips.get("f106_inlet_path_interlock", False)),
            interlock_alarm=interlock_alarms.get("f106_inlet_path_interlock"),
            external_override=self._flow_override,
        )
        level_status = self.level_pi.evaluate(
            pv=_num(t108_level_m, "t108_level_m"),
            dt_s=dt_s,
            forced_stop=bool(trips.get(self.level_loop_id, False)),
            interlock=bool(trips.get("t108_pump_interlock", False)),
            interlock_alarm=interlock_alarms.get("t108_pump_interlock"),
            external_override=self._level_override,
        )

        commands: dict[str, Any] = dict(c1.outputs)
        by_controller = {
            controller_id: dict(payload.get("detail", {}))
            for controller_id, payload in c1.detail.get("controllers", {}).items()
        }
        commands["by_controller"] = by_controller
        split_detail = by_controller.get("vf-shw-ctrl-line2-split", {})
        if "split_fraction" in split_detail:
            commands["line2_split_fraction"] = split_detail["split_fraction"]
        sludge_detail = by_controller.get("vf-shw-ctrl-sludge-duty", {})
        if "withdrawal_rate_m3h" in sludge_detail:
            commands["sludge_withdrawal_m3h"] = sludge_detail["withdrawal_rate_m3h"]
        dose_detail = by_controller.get("vf-shw-ctrl-dose-ratio", {})
        if "max_step_mg_l" in dose_detail:
            commands["dose_max_step_mg_l"] = dose_detail["max_step_mg_l"]
        backwash_detail = by_controller.get("vf-shw-ctrl-backwash-sequence", {})
        if "step" in backwash_detail:
            commands["backwash_step"] = backwash_detail["step"]
        t108_detail = by_controller.get("vf-shw-ctrl-t108-permissive", {})
        if "transfer_enable" in t108_detail:
            commands["transfer_enable"] = t108_detail["transfer_enable"]

        arbitration: dict[str, str] = {}
        # ── T106 inlet valve: trips > C1 backwash/permissive > PI ───────────
        c1_valve = _num(c1.outputs.get(self.valve_signal, 100.0), "c1.inlet_valve_pos")
        inflow_enable = bool(c1.outputs.get("inflow_enable", True))
        backwash_step = str(commands.get("backwash_step", "IDLE"))
        if trips.get(self.flow_loop_id, False):
            valve = flow_status.applied_mv
            arbitration[self.valve_signal] = "physical_trip_forced_stop"
        elif backwash_step in ("CLOSE", "BACKWASH", "SETTLE") and c1_valve <= 0.0:
            valve = 0.0
            arbitration[self.valve_signal] = "c1_backwash_closes_inlet"
        elif not inflow_enable:
            valve = 0.0
            arbitration[self.valve_signal] = "c1_permissive_inhibits_upstream_path"
        else:
            valve = flow_status.applied_mv
            arbitration[self.valve_signal] = "pi_flow_output"
        commands[self.valve_signal] = valve
        commands["inlet_valve_pct"] = valve / 100.0
        commands["f106_inlet_valve_c1_reference_pct"] = c1_valve
        commands["f106_flow_pi_requested_pct"] = flow_status.requested_mv
        commands["f106_flow_pi_applied_pct"] = valve
        self._flow_override = arbitration[self.valve_signal] != "pi_flow_output"
        flow_status = _with_actual_actuator(
            flow_status, actual_mv=valve, applied_by=arbitration[self.valve_signal]
        )

        # ── T108 transfer pump: trips > C1 permissive > PI ──────────────────
        c1_speed = _num(c1.outputs.get(self.pump_signal, 0.0), "c1.transfer_pump_speed_cmd")
        transfer_enable = bool(c1.outputs.get("transfer_enable", True))
        if trips.get(self.level_loop_id, False) or not transfer_enable:
            speed = 0.0
            arbitration[self.pump_signal] = (
                "physical_trip_forced_stop"
                if trips.get(self.level_loop_id, False)
                else "c1_permissive_trip_stops_pump"
            )
        else:
            speed = level_status.applied_mv
            arbitration[self.pump_signal] = "pi_level_output"
        commands[self.pump_signal] = speed
        commands["t108_transfer_speed_pct"] = speed / 100.0
        commands["t108_transfer_speed_c1_reference_pct"] = c1_speed
        commands["t108_level_pi_requested_pct"] = level_status.requested_mv
        commands["t108_level_pi_applied_pct"] = speed
        self._level_override = arbitration[self.pump_signal] != "pi_level_output"
        level_status = _with_actual_actuator(
            level_status, actual_mv=speed, applied_by=arbitration[self.pump_signal]
        )
        #: PI status exposed to the model/evidence (never a command override).
        commands["x3_pi_status"] = {
            self.flow_loop_id: flow_status,
            self.level_loop_id: level_status,
        }
        commands["x3_arbitration"] = dict(arbitration)
        alarms = tuple(
            sorted(
                {
                    *c1.alarms_raised,
                    *(status.alarm for status in (flow_status, level_status) if status.alarm),
                }
            )
        )
        return X3ControlEvaluation(
            tick_index=tick,
            c1=c1,
            pi_statuses={
                self.flow_loop_id: flow_status,
                self.level_loop_id: level_status,
            },
            commands=commands,
            arbitration=arbitration,
            alarms=alarms,
        )

    def commit_tick(self, evaluation: X3ControlEvaluation) -> None:
        self._tick_index = evaluation.tick_index
