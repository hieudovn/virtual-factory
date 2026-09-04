"""Alarm/event generation from measured and industrial signal values.

ARCH-03 / Issue #48 (G3): Alarm ⊂ Event. Runtime state is the sole mutable
truth; each configured alarm's current condition is written as an
``industrial_event`` ``SignalValue`` into runtime state and mirrored in a
mutable :class:`AlarmState` (a DERIVED current-state projection — never
historical authority). On activation/clear transitions the manager additionally
appends an immutable :class:`AlarmEventFact` (an ``EventFact`` with
``category=ALARM``) to its append-style :class:`EventStore`. Existing
threshold/output ``SignalValue`` behavior is unchanged.
"""

from dataclasses import dataclass
from typing import Any

from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.core.schema import AlarmConfig, PlantConfig
from virtual_factory.telemetry.event_fact import (
    AlarmEventFact,
    EventCategory,
)
from virtual_factory.telemetry.event_store import EventStore
from virtual_factory.telemetry.signal_value import SignalValue


@dataclass(slots=True)
class AlarmState:
    """Current (derived, mutable) state for one configured alarm.

    This is a DERIVED projection of the current runtime condition — not a
    historical authority. It is updated in place on each evaluation and never
    mutates the immutable alarm Event facts stored in ``AlarmManager.event_store``.
    """

    id: str
    active: bool
    severity: str
    message: str | None
    last_value: object
    timestamp_s: float


class AlarmManager:
    """Evaluates configured alarms from measured and industrial signals."""

    def __init__(self, alarms: list[AlarmConfig], *, event_store: EventStore | None = None) -> None:
        self.alarms = alarms
        self.states: dict[str, AlarmState] = {}
        self._event_store = event_store if event_store is not None else EventStore()
        self._event_seq = 0

    @property
    def event_store(self) -> EventStore:
        """Append-style store of immutable alarm Event facts produced by this manager."""
        return self._event_store

    def evaluate(self, state: RuntimeState, config: PlantConfig, timestamp_s: float) -> list[SignalValue]:
        """Evaluate alarms, write output SignalValues, and return alarm samples.

        Existing behavior is preserved: the returned ``SignalValue`` list and the
        ``industrial_event`` writes into ``state`` are unchanged. Additively, on
        activation/clear transitions (detected against the prior derived
        ``AlarmState``) the manager appends an immutable ``AlarmEventFact`` to
        ``self.event_store``.
        """
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
            previous = self.states.get(alarm.id)
            self.states[alarm.id] = AlarmState(
                id=alarm.id,
                active=active,
                severity=alarm.severity,
                message=alarm.message,
                last_value=source_value,
                timestamp_s=timestamp_s,
            )
            # Emit immutable alarm Event facts on transition only (smallest
            # correct contract): a first observation establishes the baseline
            # condition; subsequent assert/clear transitions become facts.
            if previous is not None and previous.active != active:
                self._append_alarm_fact(
                    alarm=alarm,
                    active=active,
                    source_value=source_value,
                    timestamp_s=timestamp_s,
                )
            alarm_values.append(alarm_value)
        return alarm_values

    def _append_alarm_fact(
        self,
        *,
        alarm: AlarmConfig,
        active: bool,
        source_value: object,
        timestamp_s: float,
    ) -> None:
        """Append one immutable AlarmEventFact for an assert/clear transition."""
        self._event_seq += 1
        transition = "assert" if active else "clear"
        fact = AlarmEventFact(
            event_id=f"{alarm.id}.{transition}.{self._event_seq}",
            event_type=f"alarm.{transition}",
            category=EventCategory.ALARM,
            simulation_time_s=timestamp_s,
            source=alarm.id,
            severity=alarm.severity,
            payload={"source_value": _json_scalar(source_value)},
            alarm_id=alarm.id,
            alarm_kind=alarm.type,
            transition=transition,
            threshold=alarm.threshold,
            message=alarm.message,
        )
        self._event_store.append(fact)

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


def _json_scalar(value: object) -> object:
    """Coerce a source value into a JSON-safe scalar for an event payload."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)
