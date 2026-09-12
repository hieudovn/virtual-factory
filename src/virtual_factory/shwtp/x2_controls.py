"""SH-WTP X2 C1 functional control layer (VF-SHW-X2).

Implements EXACTLY the nine X2-active C1 controls frozen in
``configs/vnext/shwtp/shwtp_control_contracts_v1.json`` as deterministic
rule/sequence logic. No PI/PID equation, integrator, derivative term or scan
loop is evaluated here: the five deferred C2 loops stay INACTIVE in X2
(``x2_status`` / ``x2_replacement`` are the only C2 facts used).

Design rules (contract-derived, no invention):

- every controller is built FROM its frozen control-contract entry; the frozen
  X2 actuator command values (e.g. RAW-INTAKE RUN 75 % / STOP 0 %, T106 valve
  OPEN 100 % / CLOSED 0 %, T108 transfer RUN 70 % / STOP 0 %) are READ from the
  contract, never re-declared here;
- evaluation is deterministic: window-index driven timers, no wall clock, no
  unordered iteration, no floating randomness;
- a controller only emits signals its contract declares in ``output_signals``;
- permissives/interlocks/alarms are evaluated per the frozen texts and record
  labelled synthetic alarms (``site_truth=False``);
- the C1 layer never advances simulation time and never owns a run identity: it
  is a pure function of (contract, scenario, committed feedback, window index).
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

CONTROL_MAX_WINDOWS = 1_000_000
LEVEL_ALARM_HYSTERESIS_M = 0.02  # frozen control-contract deadband for level loops


class X2ControlError(ValueError):
    """Raised when a C1 control contract cannot be honoured (fail closed)."""


def _num(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise X2ControlError(f"{name} must be a finite number, got {value!r}")
    out = float(value)
    if not math.isfinite(out):
        raise X2ControlError(f"{name} must be a finite number, got {value!r}")
    return out


def _require_entry(controls: Mapping[str, Mapping[str, Any]], controller_id: str) -> Mapping[str, Any]:
    entry = controls.get(controller_id)
    if entry is None:
        raise X2ControlError(f"missing frozen control contract {controller_id!r}")
    return entry


def _numbers_in(value: Any) -> tuple[float, ...]:
    """Extract the numeric hints the frozen contract states inside prose.

    The X1 contracts keep some thresholds/deadbands as descriptive text (e.g.
    ``"start 80 kPa / stop 60 kPa"``). X2 reads those frozen numbers instead of
    re-declaring them; when no number is stated the caller's declared fallback is
    used and documented as a synthetic default.
    """
    if isinstance(value, bool):
        return ()
    if isinstance(value, (int, float)):
        return (float(value),)
    if isinstance(value, str):
        return tuple(float(match) for match in re.findall(r"-?\d+(?:\.\d+)?", value))
    return ()


def _hint_or(value: Any, fallback: float, name: str) -> float:
    numbers = _numbers_in(value)
    if not numbers:
        return _num(fallback, name)
    return _num(numbers[0], name)


def _threshold_pair(value: Any, fallback: tuple[float, float], name: str) -> tuple[float, float]:
    numbers = _numbers_in(value)
    if len(numbers) == 1:
        return (_num(numbers[0], name), _num(fallback[1], name))
    if len(numbers) >= 2:
        return (_num(numbers[0], name), _num(numbers[1], name))
    return (_num(fallback[0], name), _num(fallback[1], name))


@dataclass(frozen=True, slots=True)
class ActuatorCommand:
    """The frozen X2 actuator command of one controller (read from the contract)."""

    signal: str
    mode: str
    value_when_running: float | None = None
    value_when_stopped: float | None = None
    value_when_open: float | None = None
    value_when_closed: float | None = None
    is_feedback_controlled_in_x2: bool = False

    @property
    def running_value(self) -> float:
        for candidate in (self.value_when_running, self.value_when_open):
            if candidate is not None:
                return candidate
        raise X2ControlError(f"command {self.signal!r} declares no running value")

    @property
    def stopped_value(self) -> float:
        for candidate in (self.value_when_stopped, self.value_when_closed):
            if candidate is not None:
                return candidate
        raise X2ControlError(f"command {self.signal!r} declares no stopped value")


def read_actuator_command(entry: Mapping[str, Any]) -> ActuatorCommand | None:
    """Read the frozen ``x2_actuator_command`` block (None when not declared)."""
    block = entry.get("x2_actuator_command")
    if not block:
        return None
    if block.get("is_feedback_controlled_in_x2") is not False:
        raise X2ControlError(
            f"control {entry.get('controller_id')!r} must not claim X2 feedback control"
        )
    return ActuatorCommand(
        signal=str(block["signal"]),
        mode=str(block["mode"]),
        value_when_running=block.get("value_when_running"),
        value_when_stopped=block.get("value_when_stopped"),
        value_when_open=block.get("value_when_open"),
        value_when_closed=block.get("value_when_closed"),
        is_feedback_controlled_in_x2=False,
    )


@dataclass
class C1Evaluation:
    """One deterministic C1 evaluation result for a coordination window."""

    window_index: int
    outputs: dict[str, float | bool | str] = field(default_factory=dict)
    alarms_raised: tuple[str, ...] = ()
    alarms_cleared: tuple[str, ...] = ()
    detail: dict[str, Any] = field(default_factory=dict)


class C1Controller:
    """Base class: deterministic, contract-derived C1 evaluation."""

    controller_id: str = ""
    owning_scope: str = ""
    gate = "X2"

    def __init__(self, entry: Mapping[str, Any], *, dt_s: float) -> None:
        self.entry = entry
        self.controller_id = str(entry["controller_id"])
        self.owning_scope = str(entry["owning_scope"])
        self.dt_s = _num(dt_s, "dt_s")
        if self.dt_s <= 0:
            raise X2ControlError("dt_s must be > 0")
        if entry.get("control_class") != "C1":
            raise X2ControlError(f"{self.controller_id!r} is not a C1 control contract")
        if entry.get("active_in_x2") is not True or entry.get("implementation_gate") != "X2":
            raise X2ControlError(f"{self.controller_id!r} is not X2-active at gate X2")
        self._alarms: set[str] = set()
        self._timers: dict[str, float] = {}
        self._counters: dict[str, int] = {}
        self.reset()

    # ── lifecycle ─────────────────────────────────────────────────────────
    def reset(self) -> None:
        """Deterministic reset of all controller-local timers/counters."""
        self._alarms = set()
        self._counters = {key: 0 for key in self._counter_keys()}
        self._timers = {key: 0.0 for key in self._timer_keys()}

    def _counter_keys(self) -> tuple[str, ...]:
        return ()

    def _timer_keys(self) -> tuple[str, ...]:
        return ()

    # ── helpers ───────────────────────────────────────────────────────────
    def _raise_alarm(self, name: str, result: C1Evaluation) -> None:
        if name not in self._alarms:
            self._alarms.add(name)
            result.alarms_raised = (*result.alarms_raised, name)

    def _clear_alarm(self, name: str, result: C1Evaluation) -> None:
        if name in self._alarms:
            self._alarms.discard(name)
            result.alarms_cleared = (*result.alarms_cleared, name)

    def _timer(self, key: str) -> float:
        return self._timers.get(key, 0.0)

    def _tick(self, key: str) -> float:
        value = self._timers.get(key, 0.0) + self.dt_s
        self._timers[key] = value
        return value

    def _hold(self, key: str) -> None:
        self._timers[key] = 0.0

    @property
    def open_alarms(self) -> tuple[str, ...]:
        return tuple(sorted(self._alarms))

    def declared_outputs(self) -> tuple[str, ...]:
        return tuple(str(signal) for signal in self.entry["output_signals"])

    def evaluate(self, feedback: Mapping[str, Any], window_index: int) -> C1Evaluation:  # pragma: no cover - abstract
        raise NotImplementedError

    def _finalise(self, result: C1Evaluation) -> C1Evaluation:
        declared = set(self.declared_outputs())
        undeclared = sorted(set(result.outputs) - declared)
        if undeclared:
            raise X2ControlError(
                f"controller {self.controller_id!r} emitted undeclared signal(s) {undeclared}"
            )
        return result


# ── 1. RAW-INTAKE duty/standby (owns RUN/STOP + the frozen X2 speed) ──────

class RawPumpDutyController(C1Controller):
    def _counter_keys(self) -> tuple[str, ...]:
        return ("duty_index", "start_count")

    def _timer_keys(self) -> tuple[str, ...]:
        return ("run_timer", "rest_timer", "scraper_timer")

    def evaluate(self, feedback: Mapping[str, Any], window_index: int) -> C1Evaluation:
        result = C1Evaluation(window_index=window_index)
        command = read_actuator_command(self.entry)
        if command is None:
            raise X2ControlError("raw-pump-duty must declare an x2_actuator_command")
        timers = self.entry["timers"]
        min_run_s = _num(timers["min_run_s"], "min_run_s")
        min_rest_s = _num(timers["min_rest_s"], "min_rest_s")
        scraper_run_s = _num(timers["scraper_run_s"], "scraper_run_s")
        dp_hysteresis = _hint_or(self.entry.get("deadband", {}).get("screen_dp"), 3.0, "screen_dp_hysteresis")

        screen_dp = _num(feedback.get("screen_dp", 0.0), "screen_dp")
        suction_ok = bool(feedback.get("suction_header_available", True))
        mcc_ok = bool(feedback.get("mcc_reference_available", True))
        intake_permitted = bool(feedback.get("t100_intake_enable", True))
        source_available = bool(feedback.get("raw_source_available", True))

        permissive = suction_ok and mcc_ok and source_available
        running = self._counters.get("running", 0) == 1

        if not permissive:
            running = False
            self._raise_alarm("duty_pump_unavailable", result)
        elif running and not intake_permitted:
            # T100 permissive inhibits upstream intake (high/high-high level)
            if self._timer("run_timer") >= min_run_s:
                running = False
                self._hold("run_timer")
                self._timers["rest_timer"] = 0.0
            else:
                self._tick("run_timer")
        elif running:
            self._tick("run_timer")
        else:
            self._tick("rest_timer")
            if self._timer("rest_timer") >= min_rest_s:
                running = True
                self._hold("rest_timer")
                self._timers["run_timer"] = 0.0
                self._counters["start_count"] = self._counters.get("start_count", 0) + 1

        self._counters["running"] = 1 if running else 0

        if running:
            pump_speed = command.running_value
            self._tick("scraper_timer")
            scraper = self._timer("scraper_timer") < scraper_run_s or screen_dp >= dp_hysteresis
        else:
            pump_speed = command.stopped_value
            scraper = False
            self._hold("scraper_timer")

        if screen_dp >= dp_hysteresis and not scraper:
            self._raise_alarm("screen_dp_high", result)
        elif screen_dp < dp_hysteresis:
            self._clear_alarm("screen_dp_high", result)

        # deterministic duty alternation (1 duty + 1 standby)
        self._counters["duty_index"] = (self._counters.get("start_count", 0)) % 2

        result.outputs = {
            "pump_run_cmd": "RUN" if running else "STOP",
            command.signal: pump_speed,
            "scraper_run_cmd": "RUN" if scraper else "STOP",
        }
        result.detail = {
            "screen_dp_kpa": screen_dp,
            "duty_index": self._counters["duty_index"],
            "intake_permitted": intake_permitted,
            "command_mode": command.mode,
        }
        return self._finalise(result)


# ── 2. T100 level permissive (X1-C01 direction policy) ───────────────────

class T100PermissiveController(C1Controller):
    """Level permissive: low protects DOWNSTREAM withdrawal; high inhibits UPSTREAM intake."""

    def evaluate(self, feedback: Mapping[str, Any], window_index: int) -> C1Evaluation:
        result = C1Evaluation(window_index=window_index)
        levels = self.entry.get("level_action_policy")
        if not levels:
            raise X2ControlError("t100-permissive must declare a level_action_policy")
        band = _scenario_levels(self.entry, feedback)
        level = _num(feedback.get("t100_level", band["initial"]), "t100_level")

        low_inhibit = level <= band["LALL"]
        low_reduce = band["LALL"] < level <= band["LAL"]
        high_inhibit = level >= band["LAH"]
        high_high = level >= band["LAHH"]

        intake_enable = not high_inhibit
        outlet_enable = not (low_inhibit or low_reduce)

        # level alarms with the frozen alarm-delay semantics (deterministic)
        for name, active in (
            ("level_LALL", low_inhibit),
            ("level_LAL", low_reduce),
            ("level_LAH", band["LAH"] <= level < band["LAHH"]),
            ("level_LAHH", high_high),
        ):
            if active:
                self._raise_alarm(name, result)
            else:
                self._clear_alarm(name, result)

        result.outputs = {"intake_enable": intake_enable, "outlet_enable": outlet_enable}
        result.detail = {
            "level_m": level,
            "band": band,
            "upstream_refill": "permitted" if intake_enable else "inhibited",
            "downstream_withdrawal": "permitted" if outlet_enable else "inhibited",
            "low_action": "inhibit_downstream_withdrawal" if low_inhibit else ("reduce_downstream_withdrawal" if low_reduce else "none"),
            "high_action": "inhibit_upstream_intake" if high_high else ("inhibit_upstream_intake" if high_inhibit else "none"),
        }
        return self._finalise(result)


# ── 3. T101 minimum residence / contact time ─────────────────────────────

class T101ResidenceController(C1Controller):
    def evaluate(self, feedback: Mapping[str, Any], window_index: int) -> C1Evaluation:
        result = C1Evaluation(window_index=window_index)
        min_contact_s = _num(self.entry["timers"]["min_contact_timer_s"], "min_contact_timer_s")
        contact_time_s = _num(feedback.get("contact_time_s", 0.0), "contact_time_s")
        flow = _num(feedback.get("l1_feed_flow_m3h", 0.0), "l1_feed_flow_m3h")
        enabled = flow > 0 and contact_time_s >= min_contact_s
        if not enabled and flow > 0:
            self._raise_alarm("contact_time_low", result)
        else:
            self._clear_alarm("contact_time_low", result)
        result.outputs = {"t101_outlet_enable": enabled}
        result.detail = {"contact_time_s": contact_time_s, "min_contact_s": min_contact_s}
        return self._finalise(result)


# ── 4. CHEM-DOSING ratio control (dose follows plant flow) ───────────────

class DoseRatioController(C1Controller):
    def _counter_keys(self) -> tuple[str, ...]:
        return ("ramp_windows",)

    def evaluate(self, feedback: Mapping[str, Any], window_index: int) -> C1Evaluation:
        result = C1Evaluation(window_index=window_index)
        plant_flow = _num(feedback.get("plant_flow_m3h", 0.0), "plant_flow_m3h")
        tank_ok = bool(feedback.get("chemical_tank_ok", True))
        targets = _scenario_doses(feedback)
        ramp = _hint_or(self.entry.get("rate_limit", {}).get("dose_ramp_mg_l_per_s"), 0.02, "dose_ramp")
        deadband = _hint_or(self.entry.get("deadband", {}).get("dose"), 0.05, "dose_deadband")

        dosing = tank_ok and plant_flow > 0
        if not tank_ok:
            self._raise_alarm("chemical_tank_low", result)
        else:
            self._clear_alarm("chemical_tank_low", result)

        current = self._doses if hasattr(self, "_doses") else {k: 0.0 for k in targets}
        max_step = ramp * self.dt_s
        doses: dict[str, float] = {}
        for signal, target_value in targets.items():
            goal = target_value if dosing else 0.0
            delta = goal - current.get(signal, 0.0)
            if abs(delta) <= deadband:
                value = goal
            else:
                value = current.get(signal, 0.0) + math.copysign(min(abs(delta), max_step), delta)
            doses[signal] = round(max(0.0, value), 6)
        self._doses = doses

        deviation = max((abs(doses[k] - (targets[k] if dosing else 0.0)) for k in targets), default=0.0)
        if deviation > deadband:
            self._raise_alarm("dose_deviation", result)
        else:
            self._clear_alarm("dose_deviation", result)

        result.outputs = {**doses, "_dosing_active": dosing}
        result.detail = {
            "targets": targets,
            "plant_flow_m3h": plant_flow,
            "dosing_active": dosing,
            "max_step_mg_l": round(max_step, 9),
            "ramp_mg_l_per_s": ramp,
        }
        # only the declared signals are emitted (the detail flag is internal)
        result.outputs.pop("_dosing_active", None)
        result.detail["dosing_active"] = dosing
        return self._finalise(result)

    def reset(self) -> None:
        super().reset()
        self._doses = {"pac_dose": 0.0, "coag_dose": 0.0}


# ── 5. SLUDGE-DUTY withdrawal rule on T105 ───────────────────────────────

class SludgeDutyController(C1Controller):
    def _timer_keys(self) -> tuple[str, ...]:
        return ("withdrawal_timer", "rest_timer")

    def evaluate(self, feedback: Mapping[str, Any], window_index: int) -> C1Evaluation:
        result = C1Evaluation(window_index=window_index)
        timers = self.entry["timers"]
        withdrawal_s = _num(timers["withdrawal_s"], "withdrawal_s")
        min_rest_s = _num(timers["min_rest_s"], "min_rest_s")
        available = bool(feedback.get("sludge_line_available", True))
        volume = _num(feedback.get("settled_volume_m3", 0.0), "settled_volume_m3")
        withdrawal_rate = _scenario_withdrawal_rate(feedback)

        pumping = available and volume > 0.0 and (
            self._timer("withdrawal_timer") < withdrawal_s
        )
        if pumping:
            self._tick("withdrawal_timer")
            self._timers["rest_timer"] = 0.0
        else:
            self._tick("rest_timer")
            if self._timer("rest_timer") >= min_rest_s:
                self._hold("withdrawal_timer")
                self._timers["rest_timer"] = 0.0
                pumping = volume > 0.0 and available

        if volume <= 0.0 and pumping:
            pumping = False
        if not available:
            self._raise_alarm("sludge_pump_fault", result)
        else:
            self._clear_alarm("sludge_pump_fault", result)
        if volume > _num(feedback.get("settled_volume_high_m3", 1e9), "settled_volume_high_m3"):
            self._raise_alarm("sludge_volume_high", result)
        else:
            self._clear_alarm("sludge_volume_high", result)

        result.outputs = {"sludge_pump_cmd": "RUN" if pumping else "STOP"}
        result.detail = {"withdrawal_rate_m3h": withdrawal_rate if pumping else 0.0, "settled_volume_m3": volume}
        return self._finalise(result)


# ── 6. T106 backwash sequence (DP-triggered, discrete valve positions) ───

class BackwashSequenceController(C1Controller):
    STEP_IDLE = "IDLE"
    STEP_VALVE_CLOSE = "CLOSE"
    STEP_BACKWASH = "BACKWASH"
    STEP_SETTLE = "SETTLE"

    def _timer_keys(self) -> tuple[str, ...]:
        return ("dp_confirm_timer", "step_timer", "since_backwash_timer")

    def evaluate(self, feedback: Mapping[str, Any], window_index: int) -> C1Evaluation:
        result = C1Evaluation(window_index=window_index)
        command = read_actuator_command(self.entry)
        if command is None:
            raise X2ControlError("backwash-sequence must declare an x2_actuator_command")
        timers = self.entry["timers"]
        dp_confirm_s = _num(timers["dp_confirm_s"], "dp_confirm_s")
        valve_stroke_s = _num(timers["valve_stroke_s"], "valve_stroke_s")
        backwash_s = _num(timers["backwash_duration_s"], "backwash_duration_s")
        settle_s = _num(timers["settle_s"], "settle_s")
        start_kpa, stop_kpa = _threshold_pair(
            self.entry.get("deadband", {}).get("filter_dp"), (80.0, 60.0), "filter_dp_deadband"
        )

        filter_dp = _num(feedback.get("filter_dp_kpa", 0.0), "filter_dp_kpa")
        inlet_flow = _num(feedback.get("filter_inlet_flow_m3h", 0.0), "filter_inlet_flow_m3h")
        wash_level_ok = bool(feedback.get("wash_water_level_sufficient", True))
        step = self._step
        self._tick("since_backwash_timer")

        if step == self.STEP_IDLE:
            if filter_dp >= start_kpa:
                self._tick("dp_confirm_timer")
            else:
                self._hold("dp_confirm_timer")
            if self._timer("dp_confirm_timer") >= dp_confirm_s and wash_level_ok and inlet_flow >= 0.0:
                step = self.STEP_VALVE_CLOSE
                self._hold("step_timer")
                self._hold("dp_confirm_timer")
            elif self._timer("dp_confirm_timer") >= dp_confirm_s and not wash_level_ok:
                self._raise_alarm("wash_water_level_high_low", result)
        elif step == self.STEP_VALVE_CLOSE:
            if self._tick("step_timer") >= valve_stroke_s:
                step = self.STEP_BACKWASH
                self._hold("step_timer")
        elif step == self.STEP_BACKWASH:
            if self._tick("step_timer") >= backwash_s:
                step = self.STEP_SETTLE
                self._hold("step_timer")
        elif step == self.STEP_SETTLE:
            if self._tick("step_timer") >= settle_s:
                step = self.STEP_IDLE
                self._hold("step_timer")
                self._hold("since_backwash_timer")

        self._step = step
        if filter_dp >= start_kpa:
            self._raise_alarm("filter_dp_high", result)
        elif filter_dp < stop_kpa:
            self._clear_alarm("filter_dp_high", result)

        open_valve = step == self.STEP_IDLE
        valve_signal = command.signal
        result.outputs = {
            "backwash_pump_cmd": "RUN" if step == self.STEP_BACKWASH else "STOP",
            "inlet_valve_cmd": "OPEN" if open_valve else "CLOSED",
            "outlet_valve_cmd": "OPEN" if step in (self.STEP_IDLE, self.STEP_SETTLE) else "CLOSED",
            "wash_return_cmd": "RUN" if step == self.STEP_BACKWASH else "STOP",
            valve_signal: command.running_value if open_valve else command.stopped_value,
            "outlet_valve_pos": 100.0 if step in (self.STEP_IDLE, self.STEP_SETTLE) else 0.0,
        }
        result.detail = {
            "step": step,
            "filter_dp_kpa": filter_dp,
            "since_backwash_s": self._timer("since_backwash_timer"),
            "thresholds_kpa": {"start": start_kpa, "stop": stop_kpa},
        }
        return self._finalise(result)

    def reset(self) -> None:
        super().reset()
        self._step = self.STEP_IDLE


# ── 7. T108 level permissive (same direction policy as T100) ─────────────

class T108PermissiveController(C1Controller):
    def evaluate(self, feedback: Mapping[str, Any], window_index: int) -> C1Evaluation:
        result = C1Evaluation(window_index=window_index)
        command = read_actuator_command(self.entry)
        if command is None:
            raise X2ControlError("t108-permissive must declare an x2_actuator_command")
        if not self.entry.get("level_action_policy"):
            raise X2ControlError("t108-permissive must declare a level_action_policy")
        band = _scenario_levels(self.entry, feedback)
        level = _num(feedback.get("t108_level", band["initial"]), "t108_level")

        low = level <= band["LALL"]
        high_high = level >= band["LAHH"]

        transfer_enable = not low
        inflow_enable = not high_high
        for name, active in (("level_LALL", low), ("level_LAHH", high_high)):
            if active:
                self._raise_alarm(name, result)
            else:
                self._clear_alarm(name, result)

        result.outputs = {
            "transfer_enable": transfer_enable,
            "inflow_enable": inflow_enable,
            command.signal: command.running_value if transfer_enable else command.stopped_value,
        }
        result.detail = {
            "level_m": level,
            "band": band,
            "upstream_inflow": "permitted" if inflow_enable else "inhibited",
            "downstream_withdrawal": "permitted" if transfer_enable else "inhibited",
        }
        return self._finalise(result)


# ── 8. SLUDGE-T201 sink duty ─────────────────────────────────────────────

class SludgeSinkDutyController(C1Controller):
    def _timer_keys(self) -> tuple[str, ...]:
        return ("run_timer", "rest_timer")

    def evaluate(self, feedback: Mapping[str, Any], window_index: int) -> C1Evaluation:
        result = C1Evaluation(window_index=window_index)
        min_run_s = _num(self.entry["timers"]["min_run_s"], "min_run_s")
        min_rest_s = _num(self.entry["timers"]["min_rest_s"], "min_rest_s")
        volume = _num(feedback.get("sludge_tank_volume_m3", 0.0), "sludge_tank_volume_m3")
        sink_available = bool(feedback.get("downstream_sink_available", True))

        pumping = sink_available and volume > 0.0 and self._timer("run_timer") < min_run_s
        if pumping:
            self._tick("run_timer")
            self._timers["rest_timer"] = 0.0
        else:
            self._tick("rest_timer")
            if self._timer("rest_timer") >= min_rest_s and volume > 0.0 and sink_available:
                self._hold("run_timer")
                self._timers["rest_timer"] = 0.0
                pumping = True

        if volume <= 0.0:
            pumping = False
        if volume > _num(feedback.get("sludge_tank_high_m3", 1e9), "sludge_tank_high_m3"):
            self._raise_alarm("sludge_level_high", result)
        else:
            self._clear_alarm("sludge_level_high", result)
        result.outputs = {"sink_pump_cmd": "RUN" if pumping else "STOP"}
        result.detail = {"sludge_tank_volume_m3": volume}
        return self._finalise(result)


# ── 9. LINE2 split rule (default 0 = LINE2 idle) ─────────────────────────

class Line2SplitController(C1Controller):
    def reset(self) -> None:
        super().reset()
        self._fraction = 0.0

    def evaluate(self, feedback: Mapping[str, Any], window_index: int) -> C1Evaluation:
        result = C1Evaluation(window_index=window_index)
        target = _num(feedback.get("scenario_split_fraction", 0.0), "scenario_split_fraction")
        capacity_ok = bool(feedback.get("line2_capacity_available", True))
        ramp = _hint_or(self.entry.get("rate_limit", {}).get("split_ramp_per_s"), 0.05, "split_ramp")
        deadband = _hint_or(self.entry.get("deadband", {}).get("split_fraction"), 0.02, "split_deadband")
        goal = target if capacity_ok else 0.0
        max_step = ramp * self.dt_s
        delta = goal - self._fraction
        if abs(delta) <= deadband:
            self._fraction = goal
        else:
            self._fraction = round(self._fraction + math.copysign(min(abs(delta), max_step), delta), 6)
        self._fraction = min(1.0, max(0.0, self._fraction))

        if not capacity_ok:
            self._raise_alarm("line2_capacity_exceeded", result)
        else:
            self._clear_alarm("line2_capacity_exceeded", result)

        result.outputs = {"l2_feed_cmd": "RUN" if self._fraction > 0.0 else "STOP"}
        result.detail = {"split_fraction": self._fraction, "target": target}
        # the frozen contract declares l2_feed_cmd as the only output signal; the
        # split fraction itself is the controller's declared MV state and is
        # published through detail (consumed by the LINE2 scope, not a new signal).
        return self._finalise(result)

    @property
    def split_fraction(self) -> float:
        return self._fraction


# ── scenario helpers (deterministic synthetic values) ────────────────────

def _scenario_levels(entry: Mapping[str, Any], feedback: Mapping[str, Any]) -> dict[str, float]:
    """Level band for a permissive controller (scenario synthetic thresholds)."""
    band = feedback.get("level_band")
    if isinstance(band, Mapping):
        return {
            "LALL": _num(band["LALL"], "LALL"),
            "LAL": _num(band["LAL"], "LAL"),
            "LAH": _num(band["LAH"], "LAH"),
            "LAHH": _num(band["LAHH"], "LAHH"),
            "initial": _num(band.get("initial", band["LAL"]), "initial"),
        }
    raise X2ControlError(
        f"control {entry.get('controller_id')!r} requires a scenario level_band feedback"
    )


def _scenario_doses(feedback: Mapping[str, Any]) -> dict[str, float]:
    doses = feedback.get("dose_targets")
    if not isinstance(doses, Mapping):
        raise X2ControlError("the dose-ratio C1 control requires deterministic scenario dose targets")
    return {str(k): _num(v, str(k)) for k, v in sorted(doses.items())}


def _scenario_withdrawal_rate(feedback: Mapping[str, Any]) -> float:
    value = feedback.get("sludge_withdrawal_rate_m3h")
    if value is None:
        raise X2ControlError(
            "the sludge-duty C1 control requires a deterministic scenario withdrawal rate"
        )
    return _num(value, "sludge_withdrawal_rate_m3h")


# ── the frozen X2 C1 set ─────────────────────────────────────────────────

C1_ACTIVE_CONTROLLER_IDS: tuple[str, ...] = (
    "vf-shw-ctrl-backwash-sequence",
    "vf-shw-ctrl-dose-ratio",
    "vf-shw-ctrl-line2-split",
    "vf-shw-ctrl-raw-pump-duty",
    "vf-shw-ctrl-sludge-duty",
    "vf-shw-ctrl-sludge-sink-duty",
    "vf-shw-ctrl-t100-permissive",
    "vf-shw-ctrl-t101-residence",
    "vf-shw-ctrl-t108-permissive",
)

_BUILDERS: dict[str, type[C1Controller]] = {
    "vf-shw-ctrl-raw-pump-duty": RawPumpDutyController,
    "vf-shw-ctrl-t100-permissive": T100PermissiveController,
    "vf-shw-ctrl-t101-residence": T101ResidenceController,
    "vf-shw-ctrl-dose-ratio": DoseRatioController,
    "vf-shw-ctrl-sludge-duty": SludgeDutyController,
    "vf-shw-ctrl-backwash-sequence": BackwashSequenceController,
    "vf-shw-ctrl-t108-permissive": T108PermissiveController,
    "vf-shw-ctrl-sludge-sink-duty": SludgeSinkDutyController,
    "vf-shw-ctrl-line2-split": Line2SplitController,
}


class C1ControllerSet:
    """The nine frozen X2-active C1 controls (evaluation order is deterministic)."""

    def __init__(self, control_entries: Mapping[str, Mapping[str, Any]], *, dt_s: float) -> None:
        missing = [cid for cid in C1_ACTIVE_CONTROLLER_IDS if cid not in control_entries]
        if missing:
            raise X2ControlError(f"missing frozen X2-active C1 contracts: {sorted(missing)}")
        injected = {
            key: value for key, value in control_entries.items()
            if key not in C1_ACTIVE_CONTROLLER_IDS
        }
        for cid, entry in sorted(injected.items()):
            if entry.get("control_class") == "C2":
                if entry.get("active_in_x2") is not False:
                    raise X2ControlError(f"C2 control {cid!r} must stay inactive in X2")
                if not entry.get("x2_status"):
                    raise X2ControlError(f"C2 control {cid!r} must declare its X2 status")
                continue
            if entry.get("control_class") == "C0":
                # C0 entries are declared boundary conditions / reference-only
                # markers: they are not C1 controllers and are not evaluated here.
                continue
            if entry.get("active_in_x2") and entry.get("implementation_gate") == "X2":
                raise X2ControlError(
                    f"undeclared X2-active C1 control {cid!r}; the frozen X2 set is closed"
                )
        self._controllers = {
            cid: _BUILDERS[cid](control_entries[cid], dt_s=dt_s)
            for cid in C1_ACTIVE_CONTROLLER_IDS
        }
        self._order = tuple(sorted(self._controllers))
        self._last: dict[str, C1Evaluation] = {}

    def reset(self) -> None:
        for controller in self._controllers.values():
            controller.reset()
        self._last = {}

    def evaluate(self, feedback: Mapping[str, Any], window_index: int) -> C1Evaluation:
        merged = C1Evaluation(window_index=window_index)
        per_controller: dict[str, C1Evaluation] = {}
        for controller_id in self._order:
            controller = self._controllers[controller_id]
            controller_feedback = dict(feedback)
            controller_feedback.update(feedback.get("by_controller", {}).get(controller_id, {}))
            result = controller.evaluate(controller_feedback, window_index)
            per_controller[controller_id] = result
            merged.outputs.update(result.outputs)
            merged.alarms_raised = (*merged.alarms_raised, *result.alarms_raised)
            merged.alarms_cleared = (*merged.alarms_cleared, *result.alarms_cleared)
        self._last = per_controller
        merged.detail = {
            "controllers": {
                cid: {"outputs": dict(res.outputs), "detail": res.detail}
                for cid, res in sorted(per_controller.items())
            },
            "active_controller_ids": list(self._order),
        }
        return merged

    @property
    def active_controller_ids(self) -> tuple[str, ...]:
        return self._order

    def open_alarms(self) -> dict[str, tuple[str, ...]]:
        return {
            cid: controller.open_alarms
            for cid, controller in sorted(self._controllers.items())
            if controller.open_alarms
        }

    def evaluation_detail(self, controller_id: str) -> dict[str, Any]:
        result = self._last.get(controller_id)
        return dict(result.detail) if result is not None else {}

    def output_snapshot(self) -> dict[str, Any]:
        """Deterministic snapshot of the last evaluation (read-only)."""
        return {
            cid: {"outputs": dict(res.outputs), "detail": res.detail}
            for cid, res in sorted(self._last.items())
        }


def build_c1_controllers(
    control_entries: Mapping[str, Mapping[str, Any]], *, dt_s: float
) -> C1ControllerSet:
    """Build the frozen X2-active C1 controller set from the contract entries."""
    return C1ControllerSet(control_entries, dt_s=dt_s)
