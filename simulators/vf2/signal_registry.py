"""Dynamic signal registry — built from a VF-2 PIM package at load time.

NO hardcoded signal IDs.  Everything comes from the package.

Default behaviors are assigned dynamically based on the PIM ``signal_type``,
following the SA C2 convention:

================  =============  ========================================
PIM signal_type   Default type   Details
================  =============  ========================================
``measurement``   random_walk    baseline = initial_value, noise_std 0.02
``status``        constant       value = initial_value
``alarm``         constant       value = False
``setpoint``      constant       value = initial_value
``feedback``      dependent      depends_on inferred, transform "input"
================  =============  ========================================
"""

from __future__ import annotations

from .models import (
    VF2Package,
    VF2SimulationSignal,
    VF2SignalDirection,
    VF2SignalType,
)


class SignalRegistry:
    """Dynamic registry of VF-2 simulation signals, built from a package.

    NO hardcoded signal IDs.  EVERYTHING comes from the package.
    """

    def __init__(self, pkg: VF2Package) -> None:
        self._by_id: dict[str, VF2SimulationSignal] = {}
        for sig in pkg.signals:
            self._by_id[sig.simulation_signal_id] = sig

    # ──────────────────────────────────────────────────────────────────
    # Basic lookup
    # ──────────────────────────────────────────────────────────────────

    def get(self, signal_id: str) -> VF2SimulationSignal | None:
        """Get a signal by its ``simulation_signal_id``, or ``None``."""
        return self._by_id.get(signal_id)

    @property
    def all_signal_ids(self) -> list[str]:
        return list(self._by_id.keys())

    @property
    def signal_count(self) -> int:
        return len(self._by_id)

    # ──────────────────────────────────────────────────────────────────
    # Filter by PIM fields
    # ──────────────────────────────────────────────────────────────────

    def filter_by_direction(
        self, direction: VF2SignalDirection,
    ) -> list[VF2SimulationSignal]:
        """Return all signals with the given ``direction``."""
        return [s for s in self._by_id.values() if s.direction == direction]

    def filter_by_signal_type(
        self, signal_type: VF2SignalType,
    ) -> list[VF2SimulationSignal]:
        """Return all signals with the given ``behavior.signal_type``."""
        return [s for s in self._by_id.values() if s.behavior.signal_type == signal_type]

    def filter_by_asset(
        self, canonical_asset_id: str,
    ) -> list[VF2SimulationSignal]:
        """Return all signals attached to a given canonical asset."""
        return [
            s for s in self._by_id.values()
            if s.canonical_asset_id == canonical_asset_id
        ]

    def filter_by_instrument(
        self, canonical_instrument_id: str,
    ) -> list[VF2SimulationSignal]:
        """Return all signals attached to a given canonical instrument."""
        return [
            s for s in self._by_id.values()
            if s.canonical_instrument_id == canonical_instrument_id
        ]

    # ──────────────────────────────────────────────────────────────────
    # Default behavior assignment  (SA C2)
    # ──────────────────────────────────────────────────────────────────

    def get_default_behavior(self, signal: VF2SimulationSignal) -> dict:
        """Return a default behavior template based on the PIM ``signal_type``.

        Args:
            signal: A loaded VF-2 signal.

        Returns:
            A dict describing the default simulation behavior, e.g.::

                {"type": "random_walk", "baseline": 0.0, "noise_std": 0.02}
        """
        st = signal.behavior.signal_type
        initial = signal.behavior.initial_value

        if st == VF2SignalType.MEASUREMENT:
            return {
                "type": "random_walk",
                "baseline": float(initial) if initial is not None else 0.0,
                "noise_std": 0.02,
            }

        if st == VF2SignalType.STATUS:
            return {
                "type": "constant",
                "value": bool(initial) if initial is not None else False,
            }

        if st == VF2SignalType.ALARM:
            return {
                "type": "constant",
                "value": False,
            }

        if st == VF2SignalType.SETPOINT:
            return {
                "type": "constant",
                "value": float(initial) if initial is not None else 0.0,
            }

        if st == VF2SignalType.FEEDBACK:
            return {
                "type": "dependent",
                "depends_on": [],  # inferred from topology at a later stage
                "transform": "input",
            }

        # Fallback
        return {
            "type": "random_walk",
            "baseline": float(initial) if initial is not None else 0.0,
            "noise_std": 0.02,
        }

    # ──────────────────────────────────────────────────────────────────
    # Grouped signal sets  (convenience properties)
    # ──────────────────────────────────────────────────────────────────

    @property
    def input_signals(self) -> list[VF2SimulationSignal]:
        return self.filter_by_direction(VF2SignalDirection.VF2_INPUT)

    @property
    def output_signals(self) -> list[VF2SimulationSignal]:
        return self.filter_by_direction(VF2SignalDirection.VF2_OUTPUT)

    @property
    def measurement_signals(self) -> list[VF2SimulationSignal]:
        return self.filter_by_signal_type(VF2SignalType.MEASUREMENT)

    @property
    def status_signals(self) -> list[VF2SimulationSignal]:
        return self.filter_by_signal_type(VF2SignalType.STATUS)

    @property
    def alarm_signals(self) -> list[VF2SimulationSignal]:
        return self.filter_by_signal_type(VF2SignalType.ALARM)

    @property
    def setpoint_signals(self) -> list[VF2SimulationSignal]:
        return self.filter_by_signal_type(VF2SignalType.SETPOINT)

    @property
    def feedback_signals(self) -> list[VF2SimulationSignal]:
        return self.filter_by_signal_type(VF2SignalType.FEEDBACK)
