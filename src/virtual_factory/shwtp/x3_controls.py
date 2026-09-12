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
    detail["committed_actual_mv"] = actual_mv
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

    @property
    def protection(self) -> str | None:
        """The protective owner of this scan (``trip``/``interlock``/``c1_override``)."""
        value = self.detail.get("protection")
        return str(value) if value else None

    @property
    def integral_held(self) -> bool:
        """True when the integral was HELD because a protective rule owned the MV."""
        return bool(self.detail.get("integral_held", False))

    @property
    def committed_actual_mv(self) -> float:
        """The FINAL realized actuator value committed to the controller this scan."""
        return float(self.detail.get("committed_actual_mv", self.applied_mv))


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
        #: the ACTUAL actuator value the plant last received: the slew base and the
        #: release anchor. A protective stop commits its value here too (SA C01-1).
        self._applied_mv = self.config.bias
        self._manual_mv = self.config.manual_default
        self._forced_stop = False
        #: which protective owner held the actuator on the previous scan
        self._protection: str | None = None
        #: (u_raw, PI applied value, dt) still to be reconciled against the FINAL
        #: realized command by :meth:`commit_actual`
        self._pending_back_calc: tuple[float, float, float] | None = None

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

    @property
    def protection(self) -> str | None:
        """The protective owner of the last scan (``None`` when the PI owns it)."""
        return self._protection

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

    def set_setpoint(self, sp: float) -> dict[str, float]:
        """Change the loop setpoint INSIDE an ongoing attempt (SA C01-1 repair 2).

        The controller state (integral, tracked actuator, mode) is retained, so a
        feasible setpoint step and an unreachable->reachable recovery can be proven on
        ONE continuing attempt instead of two independently initialised models. The
        value must stay inside the declared admissible range (fail closed).
        """
        value = _num(sp, "sp")
        low, high = self.config.sp_admissible
        if not low - 1e-12 <= value <= high + 1e-12:
            raise X3ControlError(
                f"{self.config.controller_id}: setpoint {value!r} is outside the "
                f"admissible range [{low}, {high}]"
            )
        previous = self.config.sp
        self.config = replace(self.config, sp=value)
        return {"previous_sp": previous, "sp": value}

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
        external_override_mv: float | None = None,
        external_override_reason: str | None = None,
    ) -> PIStatus:
        """Evaluate one scan (SA C01-1 ordering).

        The CALLER decides protective ownership (trip, interlock, C1 arbitration)
        BEFORE this scan, so: the integral is held from the FIRST protected scan, the
        actual protective value is committed into actuator tracking, the release is
        preloaded from that actual value and an ordinary reopening/re-starting step is
        slew limited. ``external_override`` means the C1 arbitration owns the actuator
        this tick: the PI still reports its own request (``pi_output_mv``) but neither
        integrates nor fights the protecting rule.
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
        pi_request = _clamp(self._requested_mv(error), config.output_min, config.output_max)

        # Priority 1: physical feasibility / trips. A forced stop holds the integral,
        # bypasses the slew (a PROTECTIVE action is allowed to) and commits the actual
        # value so a later release cannot jump from a stale pre-stop command.
        if forced_stop:
            self._forced_stop = True
            self._protection = "trip"
            self._pending_back_calc = None
            return self._protective_status(
                pv=pv,
                error=error,
                sp=sp,
                pi_request=pi_request,
                applied=config.output_min,
                protection="trip",
                reason="forced_stop_integral_held",
                alarm="controller_forced_stop",
            )

        # Priority 2: interlocks apply in MANUAL too.
        if interlock:
            self._protection = "interlock"
            self._pending_back_calc = None
            return self._protective_status(
                pv=pv,
                error=error,
                sp=sp,
                pi_request=pi_request,
                applied=config.output_min,
                protection="interlock",
                reason="interlock_protective_stop",
                alarm=interlock_alarm or "controller_interlock",
            )

        # Priority 3: the C1 arbitration owns the actuator this tick.
        if external_override:
            owned = (
                self._applied_mv
                if external_override_mv is None
                else _num(external_override_mv, "external_override_mv")
            )
            self._protection = "c1_override"
            self._pending_back_calc = None
            status = self._protective_status(
                pv=pv,
                error=error,
                sp=sp,
                pi_request=pi_request,
                applied=owned,
                protection="c1_override",
                reason="external_c1_override_integral_held",
                alarm=alarm,
            )
            detail = dict(status.detail)
            detail["applied_by"] = external_override_reason or "c1_arbitration"
            detail["external_override"] = True
            return replace(status, detail=detail)

        # Priority 4: the first unprotected scan after a protective episode.
        # A TRIP / INTERLOCK pins the output at its protective value, so the release
        # preloads the integral from that ACTUAL stopped value (bumpless and slew
        # limited). A C1 OVERRIDE instead only borrowed the actuator while the PI's
        # integral was HELD at its pre-override working point: the request resumes there
        # and the slew limit governs the applied value, which restores the plant in a
        # few seconds instead of re-integrating from the closed position.
        if self._protection in ("trip", "interlock"):
            self._integral = self._applied_mv - config.bias - config.kp * error
            reason = f"released_from_{self._protection}_bumpless"
            pi_request = _clamp(
                self._requested_mv(error), config.output_min, config.output_max
            )
        self._protection = None
        if self._forced_stop:
            self._forced_stop = False

        # Priority 5: MANUAL / AUTO PI request.
        if self.mode == "MANUAL":
            requested = self._manual_mv
            applied = self._apply_slew(requested, dt_s)
            self._pending_back_calc = None
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
                detail={
                    "pi_output_mv": round(applied, 9),
                    "applied_by": "pi",
                    "external_override": False,
                    "protection": None,
                    "integral_held": False,
                    "committed_actual_mv": applied,
                },
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
        # integrate only while not driving saturation further
        if not (driving_up or driving_down):
            self._integral += config.ki * error * dt_s
        applied = self._apply_slew(clamped, dt_s)
        # back-calculation: :meth:`commit_actual` reconciles this term with the FINAL
        # realized command (identical when the PI itself owns the actuator)
        self._integral += config.kb * (applied - u_raw) * dt_s
        self._pending_back_calc = (u_raw, applied, dt_s)
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
                "protection": None,
                "integral_held": False,
                "committed_actual_mv": applied,
            },
        )

    def _protective_status(
        self,
        *,
        pv: float,
        error: float,
        sp: float,
        pi_request: float,
        applied: float,
        protection: str,
        reason: str,
        alarm: str | None,
    ) -> PIStatus:
        """Build a protective status: HOLD the integral, COMMIT the actual value.

        The actuator is written exactly once (here): the value the plant really
        receives becomes the controller's tracked value, which is the slew base and
        the release anchor of the next scan (SA C01-1).
        """
        self._applied_mv = applied
        return PIStatus(
            controller_id=self.config.controller_id,
            mode=self.mode,
            sp=sp,
            pv=pv,
            error=error,
            u_raw=pi_request,
            requested_mv=pi_request,
            applied_mv=applied,
            integral=self._integral,
            saturated=False,
            limited=True,
            limitation_reason=reason,
            alarm=alarm,
            detail={
                "pi_output_mv": round(pi_request, 9),
                "applied_by": protection,
                "external_override": protection == "c1_override",
                "protection": protection,
                "integral_held": True,
                "committed_actual_mv": applied,
            },
        )

    def commit_actual(self, actual_mv: float) -> None:
        """Commit the tick's FINAL realized actuator value (SA C01-1).

        The controller records what the plant actually received, so the next slew
        starts from reality, and any difference between the PI's own applied value and
        the arbitrated one is folded into the integral through the SAME
        back-calculation gain - i.e. the back-calculation always uses the FINAL
        realized command, never a pre-arbitration copy.
        """
        actual = _num(actual_mv, "actual_mv")
        pending = self._pending_back_calc
        if pending is not None:
            u_raw, assumed, pending_dt = pending
            if abs(actual - assumed) > 1e-12:
                self._integral += self.config.kb * (actual - assumed) * pending_dt
            self._pending_back_calc = None
        self._applied_mv = actual

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
            "protection": self._protection,
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
                    "protection": status.protection,
                    "integral_held": status.integral_held,
                    "committed_actual_mv": status.committed_actual_mv,
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

        # ── protective ownership is decided BEFORE the PI scans (SA C01-1) ───
        # priority: physical trip > C1 backwash/permissive > interlock > PI, exactly
        # the accepted arbitration order; deciding it up front means the integral is
        # held from the FIRST protected scan and the actual value is committed.
        c1_valve = _num(c1.outputs.get(self.valve_signal, 100.0), "c1.inlet_valve_pos")
        inflow_enable = bool(c1.outputs.get("inflow_enable", True))
        by_controller: dict[str, dict[str, Any]] = {
            controller_id: dict(payload.get("detail", {}))
            for controller_id, payload in c1.detail.get("controllers", {}).items()
        }
        backwash_step = str(
            by_controller.get("vf-shw-ctrl-backwash-sequence", {}).get(
                "step", c1.outputs.get("backwash_step", "IDLE")
            )
        )
        c1_transfer_enable = bool(
            by_controller.get("vf-shw-ctrl-t108-permissive", {}).get(
                "transfer_enable", c1.outputs.get("transfer_enable", True)
            )
        )
        flow_trip = bool(trips.get(self.flow_loop_id, False))
        flow_interlock = bool(trips.get("f106_inlet_path_interlock", False))
        if flow_trip:
            valve_owner: str = "physical_trip_forced_stop"
            valve_owned_mv: float | None = None
        elif backwash_step in ("CLOSE", "BACKWASH", "SETTLE") and c1_valve <= 0.0:
            valve_owner = "c1_backwash_closes_inlet"
            valve_owned_mv = 0.0
        elif not inflow_enable:
            valve_owner = "c1_permissive_inhibits_upstream_path"
            valve_owned_mv = 0.0
        elif flow_interlock:
            valve_owner = "f106_inlet_interlock_protective_stop"
            valve_owned_mv = None
        else:
            valve_owner = "pi_flow_output"
            valve_owned_mv = None
        valve_external = valve_owner in (
            "c1_backwash_closes_inlet",
            "c1_permissive_inhibits_upstream_path",
        )

        c1_speed = _num(c1.outputs.get(self.pump_signal, 0.0), "c1.transfer_pump_speed_cmd")
        transfer_enable = c1_transfer_enable
        level_trip = bool(trips.get(self.level_loop_id, False))
        level_interlock = bool(trips.get("t108_pump_interlock", False))
        if level_trip:
            pump_owner: str = "physical_trip_forced_stop"
            pump_owned_mv: float | None = None
        elif not transfer_enable:
            pump_owner = "c1_permissive_trip_stops_pump"
            pump_owned_mv = 0.0
        elif level_interlock:
            pump_owner = "t108_pump_interlock_protective_stop"
            pump_owned_mv = None
        else:
            pump_owner = "pi_level_output"
            pump_owned_mv = None
        pump_external = pump_owner == "c1_permissive_trip_stops_pump"

        flow_status = self.flow_pi.evaluate(
            pv=_num(inlet_flow_m3_s, "inlet_flow_m3_s"),
            dt_s=dt_s,
            forced_stop=flow_trip,
            interlock=flow_interlock,
            interlock_alarm=interlock_alarms.get("f106_inlet_path_interlock"),
            external_override=valve_external,
            external_override_mv=valve_owned_mv,
            external_override_reason=valve_owner,
        )
        level_status = self.level_pi.evaluate(
            pv=_num(t108_level_m, "t108_level_m"),
            dt_s=dt_s,
            forced_stop=level_trip,
            interlock=level_interlock,
            interlock_alarm=interlock_alarms.get("t108_pump_interlock"),
            external_override=pump_external,
            external_override_mv=pump_owned_mv,
            external_override_reason=pump_owner,
        )

        commands: dict[str, Any] = dict(c1.outputs)
        commands["by_controller"] = {
            key: dict(value) for key, value in by_controller.items()
        }
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
        # ── T106 inlet valve: the ownership decided before the PI scan ───────
        valve = flow_status.applied_mv if valve_owned_mv is None else valve_owned_mv
        arbitration[self.valve_signal] = valve_owner
        commands[self.valve_signal] = valve
        commands["inlet_valve_pct"] = valve / 100.0
        commands["f106_inlet_valve_c1_reference_pct"] = c1_valve
        commands["f106_flow_pi_requested_pct"] = flow_status.requested_mv
        commands["f106_flow_pi_applied_pct"] = valve
        self._flow_override = valve_external
        # the FINAL realized value is committed into actuator tracking exactly once
        self.flow_pi.commit_actual(valve)
        flow_status = _with_actual_actuator(
            flow_status, actual_mv=valve, applied_by=valve_owner
        )

        # ── T108 transfer pump: the ownership decided before the PI scan ─────
        speed = level_status.applied_mv if pump_owned_mv is None else pump_owned_mv
        arbitration[self.pump_signal] = pump_owner
        commands[self.pump_signal] = speed
        commands["t108_transfer_speed_pct"] = speed / 100.0
        commands["t108_transfer_speed_c1_reference_pct"] = c1_speed
        commands["t108_level_pi_requested_pct"] = level_status.requested_mv
        commands["t108_level_pi_applied_pct"] = speed
        self._level_override = pump_external
        self.level_pi.commit_actual(speed)
        level_status = _with_actual_actuator(
            level_status, actual_mv=speed, applied_by=pump_owner
        )
        #: tracked actuator truth for evidence: the committed actual value and owner
        commands["x3_actuator_tracking"] = {
            self.valve_signal: {
                "committed_actual_mv": valve,
                "applied_by": valve_owner,
                "protection": flow_status.protection,
                "integral_held": flow_status.integral_held,
                "requested_mv": flow_status.requested_mv,
                "pi_output_mv": flow_status.pi_output_mv,
            },
            self.pump_signal: {
                "committed_actual_mv": speed,
                "applied_by": pump_owner,
                "protection": level_status.protection,
                "integral_held": level_status.integral_held,
                "requested_mv": level_status.requested_mv,
                "pi_output_mv": level_status.pi_output_mv,
            },
        }
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
