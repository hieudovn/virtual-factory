"""DDAY-B5 — Bottled Water Capper deterministic abnormal scenario.

A small bounded state machine that realises the frozen B1 contract
``BW-CAP-DEG-01``. It is a workspace helper, not a generic scenario
framework and not a physics-grade bearing model.

Hidden ground truth (factor, timers, thresholds) lives only on this object
and must never be copied into the outward industrial projection.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml

PHASES = (
    "NORMAL",
    "DEGRADING",
    "WARNING",
    "INTERMITTENT_STOP",
    "RECOVERY",
)

_PHASE_INDEX = {name: index for index, name in enumerate(PHASES)}

EVENT_PHASE = "SCENARIO_PHASE_CHANGED"
EVENT_ALARM_RAISED = "ALARM_RAISED"
EVENT_ALARM_CLEARED = "ALARM_CLEARED"
EVENT_DOWNTIME_START = "DOWNTIME_START"
EVENT_DOWNTIME_END = "DOWNTIME_END"

_QUALITY_GOOD = "GOOD"
_PROVENANCE_RAW = "SIMULATED_RAW"


def _get(data: dict, path: str, default: Any) -> Any:
    node: Any = data
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node


@dataclass(frozen=True)
class ScenarioRuntimeConfig:
    """Config-driven bounds and phase durations. Phase *order* is frozen."""

    scenario_id: str
    target_asset: str
    phase_duration_s: dict[str, float]
    cycle_time_factor: dict[str, float]
    fault_hold_s: float
    speed_nominal_bpm: float
    cycle_time_nominal_s: float
    motor_current_nominal_a: float
    motor_current_span_a: float
    drive_load_nominal_pct: float
    drive_load_span_pct: float
    vibration_nominal_mms: float
    vibration_span_mms: float
    bearing_temp_nominal_c: float
    bearing_temp_span_c: float
    bearing_temp_lag_tau_s: float
    cap_torque_nominal_nm: float
    intermittent_power_kw: float
    highlight: dict[str, str]


def load_b1_phases(contract_path: str | Path) -> tuple[str, str, tuple[str, ...]]:
    """Read identity and the frozen phase order from the B1 contract."""
    data = yaml.safe_load(Path(contract_path).read_text(encoding="utf-8")) or {}
    scenario_id = data.get("id")
    target = data.get("target_asset")
    phases = tuple(entry["id"] for entry in (data.get("phases") or ()))
    if phases != PHASES:
        raise ValueError(
            f"B1 contract phase order {phases} does not match frozen {PHASES}"
        )
    if data.get("manual_trigger_required"):
        raise ValueError("B1 contract forbids a required manual trigger")
    return str(scenario_id), str(target), phases


def load_runtime_config(
    runtime_path: str | Path,
    contract_path: str | Path,
) -> ScenarioRuntimeConfig:
    """Load runtime bounds after verifying the B1 contract is authoritative."""
    scenario_id, target, _phases = load_b1_phases(contract_path)
    data = yaml.safe_load(Path(runtime_path).read_text(encoding="utf-8")) or {}
    if data.get("scenario_id") not in (None, scenario_id):
        raise ValueError("runtime scenario_id does not match the B1 contract")
    if data.get("target_asset") not in (None, target):
        raise ValueError("runtime target_asset does not match the B1 contract")

    durations = {
        name: float((_get(data, "phase_duration_s", {}) or {}).get(name, 0.0))
        for name in PHASES
    }
    if any(durations[name] <= 0.0 for name in PHASES[:-1]):
        raise ValueError("every phase before RECOVERY must have a positive duration")
    factors = dict(_get(data, "cycle_time_factor", {}) or {})
    highlight = dict(_get(data, "highlight", {}) or {})

    return ScenarioRuntimeConfig(
        scenario_id=scenario_id,
        target_asset=target,
        phase_duration_s=durations,
        cycle_time_factor={
            name: float(factors.get(name, 1.0)) for name in PHASES
        },
        fault_hold_s=float(data.get("fault_hold_s", 4.0)),
        speed_nominal_bpm=float(_get(data, "signals.speed_nominal_bpm", 3.0)),
        cycle_time_nominal_s=float(_get(data, "signals.cycle_time_nominal_s", 20.0)),
        motor_current_nominal_a=float(
            _get(data, "signals.motor_current_nominal_a", 11.0)
        ),
        motor_current_span_a=float(_get(data, "signals.motor_current_span_a", 7.0)),
        drive_load_nominal_pct=float(
            _get(data, "signals.drive_load_nominal_pct", 42.0)
        ),
        drive_load_span_pct=float(_get(data, "signals.drive_load_span_pct", 38.0)),
        vibration_nominal_mms=float(
            _get(data, "signals.vibration_nominal_mms", 1.1)
        ),
        vibration_span_mms=float(_get(data, "signals.vibration_span_mms", 4.4)),
        bearing_temp_nominal_c=float(
            _get(data, "signals.bearing_temp_nominal_c", 41.0)
        ),
        bearing_temp_span_c=float(_get(data, "signals.bearing_temp_span_c", 22.0)),
        bearing_temp_lag_tau_s=float(
            _get(data, "signals.bearing_temp_lag_tau_s", 12.0)
        ),
        cap_torque_nominal_nm=float(_get(data, "signals.cap_torque_nominal_nm", 1.6)),
        intermittent_power_kw=float(
            _get(data, "signals.intermittent_power_kw", 1.2)
        ),
        highlight={name: str(highlight.get(name, "normal")) for name in PHASES},
    )


def _lerp(start: float, end: float, progress: float) -> float:
    progress = max(0.0, min(1.0, progress))
    return start + (end - start) * progress


class CapperDegradationScenario:
    """Deterministic one-shot Capper abnormal scenario.

    Time is simulated time supplied by the factory. The object never reads
    wall-clock time. Classification is stored here and never feeds back into
    the factor / phase / signal trajectory.
    """

    def __init__(self, config: ScenarioRuntimeConfig) -> None:
        self.config = config
        self.reset()

    def reset(self) -> None:
        self._phase = "NORMAL"
        self._elapsed_s = 0.0
        self._phase_elapsed_s = 0.0
        self._completed = False
        self._bearing_temp_c = self.config.bearing_temp_nominal_c
        self._alarm_raised = False
        self._alarm_cleared = False
        self._downtime_started = False
        self._downtime_ended = False
        self._pending_events: list[dict] = []
        self._downtime_code: Optional[str] = None
        self._failure_code: Optional[str] = None
        self._emit_phase("NORMAL", 0.0)

    # --- public (non-hidden) surfaces ---

    @property
    def phase(self) -> str:
        return self._phase

    @property
    def target_asset(self) -> str:
        return self.config.target_asset

    @property
    def scenario_id(self) -> str:
        return self.config.scenario_id

    def public_context(self) -> dict:
        """Scenario/event context only — no hidden factor or timer."""
        return {
            "id": self.config.scenario_id,
            "target_asset": self.config.target_asset,
            "phase": self._phase,
            "highlight": self.config.highlight.get(self._phase, "normal"),
        }

    def cycle_time_factor(self) -> float:
        return float(self.config.cycle_time_factor[self._phase])

    def production_inhibited(self) -> bool:
        return self._phase == "INTERMITTENT_STOP"

    def effective_dwell_s(self, nominal_dwell_s: float) -> float:
        factor = self.cycle_time_factor()
        if factor <= 0.0:
            return float("inf")
        return nominal_dwell_s * factor

    # --- clock ---

    def advance(self, dt_s: float, simulation_time_s: float) -> list[dict]:
        """Advance scenario truth by ``dt_s`` simulated seconds.

        Callers must pass dt only while the factory is RUNNING. PAUSE and
        operator STOP freeze this clock by not calling advance.
        """
        if dt_s <= 0.0:
            return self._take_events()
        if self._completed:
            self._update_temperature(dt_s)
            return self._take_events()

        remaining = float(dt_s)
        while remaining > 1e-12 and not self._completed:
            duration = self.config.phase_duration_s[self._phase]
            room = duration - self._phase_elapsed_s
            if self._phase == "RECOVERY" and room <= 0.0:
                self._completed = True
                break
            chunk = remaining if room <= 0.0 else min(remaining, room)
            self._elapsed_s += chunk
            self._phase_elapsed_s += chunk
            remaining -= chunk
            self._maybe_raise_phase_events(simulation_time_s)
            if (
                not self._completed
                and self._phase != "RECOVERY"
                and self._phase_elapsed_s + 1e-12 >= duration
            ):
                self._enter(PHASES[_PHASE_INDEX[self._phase] + 1], simulation_time_s)
            elif self._phase == "RECOVERY" and self._phase_elapsed_s + 1e-12 >= duration:
                self._completed = True

        self._update_temperature(dt_s)
        return self._take_events()

    def _enter(self, phase: str, simulation_time_s: float) -> None:
        self._phase = phase
        self._phase_elapsed_s = 0.0
        self._emit_phase(phase, simulation_time_s)
        self._maybe_raise_phase_events(simulation_time_s)

    def _emit_phase(self, phase: str, simulation_time_s: float) -> None:
        self._pending_events.append(self._event(
            EVENT_PHASE,
            f"phase={phase}",
            simulation_time_s,
        ))

    def _maybe_raise_phase_events(self, simulation_time_s: float) -> None:
        if self._phase == "WARNING" and not self._alarm_raised:
            self._alarm_raised = True
            event = self._event(
                EVENT_ALARM_RAISED,
                "capper warning",
                simulation_time_s,
            )
            self._pending_events.append(event)
        if self._phase == "INTERMITTENT_STOP" and not self._downtime_started:
            self._downtime_started = True
            event = self._event(
                EVENT_DOWNTIME_START,
                "capper intermittent stop",
                simulation_time_s,
            )
            if self._downtime_code:
                event["downtime_code"] = self._downtime_code
            if self._failure_code:
                event["failure_code"] = self._failure_code
            self._pending_events.append(event)
        if self._phase == "RECOVERY":
            if self._downtime_started and not self._downtime_ended:
                self._downtime_ended = True
                event = self._event(
                    EVENT_DOWNTIME_END,
                    "capper downtime ended",
                    simulation_time_s,
                )
                if self._downtime_code:
                    event["downtime_code"] = self._downtime_code
                if self._failure_code:
                    event["failure_code"] = self._failure_code
                self._pending_events.append(event)
            if self._alarm_raised and not self._alarm_cleared:
                self._alarm_cleared = True
                self._pending_events.append(self._event(
                    EVENT_ALARM_CLEARED,
                    "capper warning cleared",
                    simulation_time_s,
                ))

    def _event(self, event_type: str, detail: str, simulation_time_s: float) -> dict:
        return {
            "event_type": event_type,
            "scenario_id": self.config.scenario_id,
            "source_id": self.config.target_asset,
            "station_id": self.config.target_asset,
            "detail": detail,
            "simulation_time_s": round(float(simulation_time_s), 3),
            "quality": _QUALITY_GOOD,
            "provenance": _PROVENANCE_RAW,
        }

    def _take_events(self) -> list[dict]:
        events = list(self._pending_events)
        self._pending_events.clear()
        return events

    # --- hidden causal model (never published) ---

    def _phase_progress(self) -> float:
        duration = self.config.phase_duration_s[self._phase]
        if duration <= 0.0:
            return 1.0
        return max(0.0, min(1.0, self._phase_elapsed_s / duration))

    def _factor(self) -> float:
        """Internal injected-fault strength in [0, 1]. Not publishable."""
        progress = self._phase_progress()
        if self._phase == "NORMAL":
            return 0.0
        if self._phase == "DEGRADING":
            return _lerp(0.15, 0.45, progress)
        if self._phase == "WARNING":
            return _lerp(0.45, 0.85, progress)
        if self._phase == "INTERMITTENT_STOP":
            return 1.0
        return _lerp(1.0, 0.0, progress)

    def _update_temperature(self, dt_s: float) -> None:
        cfg = self.config
        target = cfg.bearing_temp_nominal_c + self._factor() * cfg.bearing_temp_span_c
        if dt_s <= 0.0 or cfg.bearing_temp_lag_tau_s <= 0.0:
            return
        alpha = min(1.0, dt_s / cfg.bearing_temp_lag_tau_s)
        self._bearing_temp_c += (target - self._bearing_temp_c) * alpha

    # --- published raw signals ---

    def capper_operating_state(self, factory_run_state: str) -> str:
        """Capper machine state. Operator STOP always wins over scenario FAULT."""
        if factory_run_state == "STOPPED":
            return "STOPPED"
        if factory_run_state == "PAUSED":
            return "IDLE"
        if self._phase == "INTERMITTENT_STOP":
            if self._phase_elapsed_s < self.config.fault_hold_s:
                return "FAULT"
            return "STOPPED"
        if factory_run_state == "RUNNING":
            return "RUNNING"
        return "IDLE"

    def published_signals(self, factory_run_state: str) -> dict[str, tuple[Any, str]]:
        """Return ``signal_id -> (value, unit)`` for BW-FP-CAP01.

        Values are raw facts. Hidden factor / timers are not included.
        """
        cfg = self.config
        factor = self._factor()
        inhibited = self.production_inhibited()
        running = factory_run_state == "RUNNING" and not inhibited
        cycle_factor = self.cycle_time_factor()
        if inhibited or factory_run_state != "RUNNING":
            speed = 0.0
            cycle_time = cfg.cycle_time_nominal_s
        else:
            speed = cfg.speed_nominal_bpm / max(cycle_factor, 1e-6)
            cycle_time = cfg.cycle_time_nominal_s * cycle_factor
        return {
            "operating_state": (self.capper_operating_state(factory_run_state), "-"),
            "speed": (round(speed, 4), "bottle/min"),
            "cycle_time": (round(cycle_time, 4), "s"),
            "motor_current": (
                round(cfg.motor_current_nominal_a + factor * cfg.motor_current_span_a, 4),
                "A",
            ),
            "drive_load": (
                round(cfg.drive_load_nominal_pct + factor * cfg.drive_load_span_pct, 4),
                "%",
            ),
            "vibration_rms": (
                round(cfg.vibration_nominal_mms + factor * cfg.vibration_span_mms, 4),
                "mm/s",
            ),
            "bearing_temperature": (round(self._bearing_temp_c, 4), "degC"),
            "cap_torque": (round(cfg.cap_torque_nominal_nm, 4), "N.m"),
        }

    def capper_active_power_kw(self, factory_run_state: str, standby_kw: float,
                               running_kw: float) -> float:
        if factory_run_state == "STOPPED":
            return standby_kw
        if self._phase == "INTERMITTENT_STOP":
            if self.capper_operating_state(factory_run_state) == "FAULT":
                return self.config.intermittent_power_kw
            return standby_kw
        if factory_run_state == "RUNNING":
            return running_kw * (1.0 + 0.12 * self._factor())
        return standby_kw

    # --- classification (enrichment only) ---

    def classify(self, kind: str, code: str) -> dict:
        """Attach a human code to the existing/pending downtime context.

        Never mutates phase, factor, timers or published signal physics.
        """
        if kind not in ("downtime_code", "failure_code"):
            raise ValueError(f"unsupported classification kind: {kind!r}")
        cleaned = str(code).strip()
        if not cleaned:
            raise ValueError("classification code must be non-empty")
        if kind == "downtime_code":
            self._downtime_code = cleaned
        else:
            self._failure_code = cleaned
        return {
            "kind": kind,
            "code": cleaned,
            "scenario_id": self.config.scenario_id,
            "target_asset": self.config.target_asset,
            "attached_to_phase": self._phase,
        }

    def classification(self) -> dict:
        return {
            "downtime_code": self._downtime_code,
            "failure_code": self._failure_code,
        }
