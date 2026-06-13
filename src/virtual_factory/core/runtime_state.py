"""Runtime state container for truth values, signals, commands, and diagnostics."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RuntimeState:
    """Stores mutable runtime values for a simulation assembly."""

    truth: dict[str, float | int | str | bool] = field(default_factory=dict)
    signals: dict[str, object] = field(default_factory=dict)
    commands: dict[str, object] = field(default_factory=dict)
    diagnostics: dict[str, object] = field(default_factory=dict)

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

    def snapshot(self) -> dict[str, dict[str, object]]:
        """Return a shallow serializable snapshot of the current state."""
        return {
            "truth": dict(self.truth),
            "signals": dict(self.signals),
            "commands": dict(self.commands),
            "diagnostics": dict(self.diagnostics),
        }
