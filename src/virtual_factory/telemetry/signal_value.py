"""Common industrial telemetry signal representation."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SignalValue:
    """One measured, controller, actuator feedback, or event signal sample."""

    name: str
    value: float | int | str | bool | None
    unit: str | None
    category: str
    timestamp_s: float
    quality: str = "GOOD"
    source: str | None = None
