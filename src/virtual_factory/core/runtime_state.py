"""Runtime state container for truth values, signals, commands, and diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from virtual_factory.telemetry.signal_value import SignalValue

if TYPE_CHECKING:
    from virtual_factory.balance.stream import Stream


@dataclass(slots=True)
class RuntimeState:
    """Stores mutable runtime values for a simulation assembly."""

    truth: dict[str, float | int | str | bool] = field(default_factory=dict)
    signals: dict[str, object] = field(default_factory=dict)
    commands: dict[str, object] = field(default_factory=dict)
    diagnostics: dict[str, object] = field(default_factory=dict)
    streams: dict[str, Stream] = field(default_factory=dict)

    def get_truth(self, path: str, default: Any = None) -> Any:
        """Return an internal truth value by path."""
        return self.truth.get(path, default)

    def set_truth(self, path: str, value: float | int | str | bool) -> None:
        """Set an internal truth value by path."""
        self.truth[path] = value

    def get_signal(self, name: str, default: Any = None) -> Any:
        """Return a measured, controller, or feedback signal by name."""
        return self.signals.get(name, default)

    def set_signal(self, name: str, value: object) -> None:
        """Set a measured, controller, or feedback signal by name."""
        self.signals[name] = value

    def set_signal_value(
        self,
        name: str,
        value: object,
        timestamp_s: float,
        unit: str | None = None,
        category: str = "industrial_signal",
        quality: str = "GOOD",
        source: str | None = None,
    ) -> None:
        """Set a measured, controller, or feedback signal with metadata."""
        self.signals[name] = SignalValue(
            name=name,
            value=value,
            unit=unit,
            category=category,
            quality=quality,
            timestamp_s=timestamp_s,
            source=source,
        )

    def get_signal_value(self, name: str, default: Any = None) -> Any:
        """Return the stored signal object by name."""
        return self.signals.get(name, default)

    def get_signal_numeric(self, name: str, default: float = 0.0) -> float:
        """Return a numeric signal value, unwrapping SignalValue when needed."""
        signal = self.signals.get(name)
        if signal is None:
            return default
        value = signal.value if isinstance(signal, SignalValue) else signal
        if isinstance(value, bool):
            return float(value)
        if isinstance(value, int | float):
            return float(value)
        return default

    def set_stream(self, connection_id: str, stream) -> None:
        """Store a material stream for a physical connection."""
        from virtual_factory.balance.stream import Stream  # noqa: F811  # lazy import, breaks circular dep
        if not isinstance(stream, Stream):
            raise TypeError(f"Expected Stream, got {type(stream).__name__}")
        self.streams[connection_id] = stream

    def get_stream(self, connection_id: str):
        """Return the material stream on a connection, or None."""
        return self.streams.get(connection_id)

    def snapshot(self) -> dict[str, object]:
        """Return a shallow serializable snapshot of the current state."""
        return {
            "truth": dict(self.truth),
            "signals": dict(self.signals),
            "commands": dict(self.commands),
            "diagnostics": dict(self.diagnostics),
        }
