"""Alarm/event generation from measured and industrial signal values."""

from dataclasses import dataclass
from typing import Any

from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.core.schema import AlarmConfig, PlantConfig
from virtual_factory.telemetry.signal_value import SignalValue


@dataclass(slots=True)
class AlarmState:
    """Current state for one configured alarm."""

    id: str
    active: bool
    severity: str
    message: str | None
    last_value: object
    timestamp_s: float


class AlarmManager:
    """Evaluates configured alarms from measured and industrial signals."""

    def __init__(self, alarms: list[AlarmConfig]) -> None:
        self.alarms = alarms
        self.states: dict[str, AlarmState] = {}

    def evaluate(self, state: RuntimeState, config: PlantConfig, timestamp_s: float) -> list[SignalValue]:
        """Evaluate alarms, write output SignalValues, and return alarm samples."""
        alarm_values: list[SignalValue] = []
        for alarm in self.alarms:
            source_signal = state.get_signal_value(alarm.source_signal)
            if source_signal is None:
                continue
            source_value, source_quality = _source_value_and_quality(source_signal)
            active = self._is_active(alarm, source_value, source_quality)
            output_config = config.signals[alarm.output_signal]
            alarm_value = SignalValue(
                name=alarm.output_signal,
                value=active,
                unit=output_config.unit,
                category="industrial_event",
                quality=source_quality,
                timestamp_s=timestamp_s,
                source=alarm.id,
            )
            state.set_signal(alarm.output_signal, alarm_value)
            self.states[alarm.id] = AlarmState(
                id=alarm.id,
                active=active,
                severity=alarm.severity,
                message=alarm.message,
                last_value=source_value,
                timestamp_s=timestamp_s,
            )
            alarm_values.append(alarm_value)
        return alarm_values

    def _is_active(self, alarm: AlarmConfig, value: object, quality: str) -> bool:
        if alarm.type == "bad_quality":
            return quality != str(alarm.threshold or "GOOD")
        if alarm.type == "high":
            return _numeric(value) > _numeric(alarm.threshold)
        if alarm.type == "low":
            return _numeric(value) < _numeric(alarm.threshold)
        if alarm.type == "equals":
            return value == alarm.threshold
        if alarm.type == "not_equals":
            return value != alarm.threshold
        raise ValueError(f"Unsupported alarm type: {alarm.type}")


def _source_value_and_quality(source_signal: object) -> tuple[object, str]:
    if isinstance(source_signal, SignalValue):
        return source_signal.value, source_signal.quality
    return source_signal, "GOOD"


def _numeric(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, int | float):
        return float(value)
    return float(value)
