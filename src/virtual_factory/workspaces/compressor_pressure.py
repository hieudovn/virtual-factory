"""DDAY-B5-C01 — Bottled Water Compressor secondary utility scenario.

A small bounded state machine that realises ``BW-CMP-SAG-01`` on
``BW-UT-CMP01`` as the Issue #107 5-phase causal story:

``NORMAL → DEGRADING → LOW_PRESSURE_WARNING → UNDERSUPPLY → RECOVERY``

It is a workspace helper, not a generic scenario framework and not a
compressor-train physics model. Hidden ground truth lives only on this
object and must never be copied into the outward industrial projection.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

PHASES = (
    "NORMAL",
    "DEGRADING",
    "LOW_PRESSURE_WARNING",
    "UNDERSUPPLY",
    "RECOVERY",
)

_PHASE_INDEX = {name: index for index, name in enumerate(PHASES)}

EVENT_PHASE = "SCENARIO_PHASE_CHANGED"
EVENT_ALARM_RAISED = "ALARM_RAISED"
EVENT_ALARM_CLEARED = "ALARM_CLEARED"

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
class CompressorRuntimeConfig:
    """Config-driven bounds and phase durations. Phase *order* is frozen."""

    scenario_id: str
    target_asset: str
    phase_duration_s: dict[str, float]
    cycle_time_factor: dict[str, float]
    degrading_target_bar: float
    warning_target_bar: float
    sag_floor_bar: float
    recovery_target_bar: float
    fall_bar_per_s: float
    rise_bar_per_s: float
    power_span_fraction: float
    highlight: dict[str, str]


def load_compressor_phases(contract_path: str | Path) -> tuple[str, str, tuple[str, ...]]:
    """Read identity and the frozen phase order from the compressor contract."""
    data = yaml.safe_load(Path(contract_path).read_text(encoding="utf-8")) or {}
    scenario_id = data.get("id")
    target = data.get("target_asset")
    phases = tuple(entry["id"] for entry in (data.get("phases") or ()))
    if phases != PHASES:
        raise ValueError(
            f"compressor contract phase order {phases} does not match frozen {PHASES}"
        )
    if data.get("manual_trigger_required"):
        raise ValueError("compressor contract forbids a required manual trigger")
    return str(scenario_id), str(target), phases


def load_compressor_runtime(
    runtime_path: str | Path,
    contract_path: str | Path,
) -> CompressorRuntimeConfig:
    """Load runtime bounds after verifying the compressor contract."""
    scenario_id, target, _phases = load_compressor_phases(contract_path)
    data = yaml.safe_load(Path(runtime_path).read_text(encoding="utf-8")) or {}
    if data.get("scenario_id") not in (None, scenario_id):
        raise ValueError("runtime scenario_id does not match the compressor contract")
    if data.get("target_asset") not in (None, target):
        raise ValueError("runtime target_asset does not match the compressor contract")

    durations = {
        name: float((_get(data, "phase_duration_s", {}) or {}).get(name, 0.0))
        for name in PHASES
    }
    if any(durations[name] <= 0.0 for name in PHASES[:-1]):
        raise ValueError("every phase before RECOVERY must have a positive duration")
    factors = dict(_get(data, "cycle_time_factor", {}) or {})
    highlight = dict(_get(data, "highlight", {}) or {})

    return CompressorRuntimeConfig(
        scenario_id=scenario_id,
        target_asset=target,
        phase_duration_s=durations,
        cycle_time_factor={
            name: float(factors.get(name, 1.0)) for name in PHASES
        },
        degrading_target_bar=float(_get(data, "signals.degrading_target_bar", 6.1)),
        warning_target_bar=float(_get(data, "signals.warning_target_bar", 5.8)),
        sag_floor_bar=float(_get(data, "signals.sag_floor_bar", 5.6)),
        recovery_target_bar=float(_get(data, "signals.recovery_target_bar", 6.4)),
        fall_bar_per_s=float(_get(data, "signals.fall_bar_per_s", 0.04)),
        rise_bar_per_s=float(_get(data, "signals.rise_bar_per_s", 0.04)),
        power_span_fraction=float(_get(data, "signals.power_span_fraction", 0.15)),
        highlight={name: str(highlight.get(name, "normal")) for name in PHASES},
    )


class CompressorPressureScenario:
    """Deterministic one-shot compressor undersupply scenario.

    Time is simulated time supplied by the factory. Classification is not
    stored here and never feeds back into pressure, phase, or inhibit.
    """

    def __init__(self, config: CompressorRuntimeConfig) -> None:
        self.config = config
        self.reset()

    def reset(self) -> None:
        self._phase = "NORMAL"
        self._elapsed_s = 0.0
        self._phase_elapsed_s = 0.0
        self._completed = False
        self._alarm_raised = False
        self._alarm_cleared = False
        self._pending_events: list[dict] = []
        self._emit_phase("NORMAL", 0.0)

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
        return self._phase == "UNDERSUPPLY"

    def effective_dwell_s(self, nominal_dwell_s: float) -> float:
        factor = self.cycle_time_factor()
        if factor <= 0.0:
            return float("inf")
        return nominal_dwell_s * factor

    def overrides_pressure(self) -> bool:
        return self._phase != "NORMAL"

    def pressure_target_bar(self) -> float:
        if self._phase == "DEGRADING":
            return self.config.degrading_target_bar
        if self._phase == "LOW_PRESSURE_WARNING":
            return self.config.warning_target_bar
        if self._phase == "UNDERSUPPLY":
            return self.config.sag_floor_bar
        return self.config.recovery_target_bar

    def step_pressure(self, current_bar: float, dt_s: float) -> float:
        """Deterministic first-order approach to the phase pressure target."""
        target = self.pressure_target_bar()
        if dt_s <= 0.0:
            return current_bar
        if current_bar > target:
            return max(target, current_bar - self.config.fall_bar_per_s * dt_s)
        if current_bar < target:
            return min(target, current_bar + self.config.rise_bar_per_s * dt_s)
        return current_bar

    def compressor_active_power_kw(self, standby_kw: float, running_kw: float,
                                   loaded: bool) -> float:
        """Loaded power rises with the hidden sag factor. Not a KPI."""
        if not loaded:
            return standby_kw
        return running_kw * (1.0 + self.config.power_span_fraction * self._factor())

    def advance(self, dt_s: float, simulation_time_s: float) -> list[dict]:
        """Advance scenario truth by ``dt_s`` simulated seconds.

        Callers must pass dt only while the factory is RUNNING. PAUSE and
        operator STOP freeze this clock by not calling advance.
        """
        if dt_s <= 0.0:
            return self._take_events()
        if self._completed:
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
        if self._phase == "LOW_PRESSURE_WARNING" and not self._alarm_raised:
            self._alarm_raised = True
            self._pending_events.append(self._event(
                EVENT_ALARM_RAISED,
                "compressor low pressure",
                simulation_time_s,
            ))
        if self._phase == "RECOVERY" and self._alarm_raised and not self._alarm_cleared:
            self._alarm_cleared = True
            self._pending_events.append(self._event(
                EVENT_ALARM_CLEARED,
                "compressor pressure restored",
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

    def _phase_progress(self) -> float:
        duration = self.config.phase_duration_s[self._phase]
        if duration <= 0.0:
            return 1.0
        return max(0.0, min(1.0, self._phase_elapsed_s / duration))

    def _factor(self) -> float:
        """Internal injected-sag strength in [0, 1]. Not publishable."""
        progress = self._phase_progress()
        if self._phase == "NORMAL":
            return 0.0
        if self._phase == "DEGRADING":
            return 0.15 + 0.35 * progress
        if self._phase == "LOW_PRESSURE_WARNING":
            return 0.50 + 0.35 * progress
        if self._phase == "UNDERSUPPLY":
            return 1.0
        return max(0.0, 1.0 - progress)
