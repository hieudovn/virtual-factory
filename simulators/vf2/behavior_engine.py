"""Generic behavior engine — pattern-based signal generators for VF-2.

Unlike VF-1's WTP-specific stage formulas, this engine reads signal
metadata from the ``SignalRegistry`` and applies the appropriate pattern
at each tick.  Supported patterns:

* ``constant`` — fixed value
* ``random_walk`` — random walk with bounds + mean reversion
* ``sine`` — sinusoidal oscillation
* ``degradation`` — slow linear drift
* ``dependent`` — expression-based (via ``transform_evaluator``)
"""

from __future__ import annotations

import math
import random
from typing import Any

from .models import clamp
from .signal_registry import SignalRegistry
from .transform_evaluator import evaluate_transform


# ======================================================================
# Per-signal mutable state
# ======================================================================


class BehaviorState:
    """Mutable state carried across ticks for one signal."""

    __slots__ = ("signal_id", "current_value", "phase", "accumulated_drift",
                 "rw_position")

    def __init__(self, signal_id: str) -> None:
        self.signal_id = signal_id
        self.current_value: float = 0.0
        self.phase: float = 0.0
        self.accumulated_drift: float = 0.0
        self.rw_position: float = 0.0


# ======================================================================
# BehaviorEngine
# ======================================================================


class BehaviorEngine:
    """Pattern-based signal value generator.

    Args:
        sig_reg: Signal registry (used to look up default behaviours).
        rng: Optional random generator (defaults to ``Random(42)``).
    """

    def __init__(
        self,
        sig_reg: SignalRegistry | None,
        rng: random.Random | None = None,
    ) -> None:
        self.sig_reg = sig_reg
        self.rng = rng or random.Random(42)
        self._state: dict[str, BehaviorState] = {}

    # ──────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────

    def step(
        self,
        dt_s: float,
        signal_values: dict[str, float],
    ) -> dict[str, float]:
        """Generate values for **all** signals for one tick.

        Args:
            dt_s: Tick duration in seconds.
            signal_values: Current values of all signals (for dependent
                resolution).

        Returns:
            ``{signal_id: new_value}`` for all registered signals.
        """
        if self.sig_reg is None:
            return {}

        results: dict[str, float] = {}
        for sid in self.sig_reg.all_signal_ids:
            sig = self.sig_reg.get(sid)
            if sig is None:
                continue
            behavior = self.sig_reg.get_default_behavior(sig)
            results[sid] = self.step_one(sid, dt_s, behavior, signal_values)

        return results

    def step_one(
        self,
        signal_id: str,
        dt_s: float,
        behavior: dict[str, Any],
        signal_values: dict[str, float],
    ) -> float:
        """Generate one signal value based on its behaviour config."""
        btype = behavior.get("type", "constant")

        if btype == "constant":
            return self._constant(behavior)
        if btype == "random_walk":
            return self._random_walk(signal_id, behavior, dt_s)
        if btype == "sine":
            return self._sine(signal_id, behavior, dt_s)
        if btype == "degradation":
            return self._degradation(signal_id, behavior, dt_s)
        if btype == "dependent":
            return self._dependent(behavior, signal_values)

        # Fallback
        return float(behavior.get("value", behavior.get("baseline", 0.0)))

    # ──────────────────────────────────────────────────────────────────
    # Pattern implementations
    # ──────────────────────────────────────────────────────────────────

    def _constant(self, behavior: dict[str, Any]) -> float:
        return float(behavior.get("value", 0.0))

    def _random_walk(
        self,
        signal_id: str,
        behavior: dict[str, Any],
        dt_s: float,
    ) -> float:
        state = self._get_state(signal_id)
        baseline = float(behavior.get("baseline", 0.0))
        noise_std = float(behavior.get("noise_std", 0.02))
        bounds_min = float(behavior.get("bounds_min", -1e9))
        bounds_max = float(behavior.get("bounds_max", 1e9))

        # Step with mean reversion
        step = self.rng.gauss(0, noise_std * math.sqrt(dt_s))
        reversion = 0.01 * (baseline - state.rw_position) * dt_s
        state.rw_position += step + reversion
        state.rw_position = clamp(state.rw_position, bounds_min, bounds_max)
        return state.rw_position

    def _sine(
        self,
        signal_id: str,
        behavior: dict[str, Any],
        dt_s: float,
    ) -> float:
        state = self._get_state(signal_id)
        baseline = float(behavior.get("baseline", 0.0))
        amplitude = float(behavior.get("amplitude", 1.0))
        freq = float(behavior.get("frequency_hz", 0.1))
        noise_std = float(behavior.get("noise_std", 0.0))

        state.phase += 2.0 * math.pi * freq * dt_s
        value = baseline + amplitude * math.sin(state.phase)
        value += self.rng.gauss(0, noise_std)
        return value

    def _degradation(
        self,
        signal_id: str,
        behavior: dict[str, Any],
        dt_s: float,
    ) -> float:
        state = self._get_state(signal_id)
        baseline = float(behavior.get("baseline", 0.0))
        drift_rate = float(behavior.get("drift_rate_per_s", 0.0))
        noise_std = float(behavior.get("noise_std", 0.0))

        state.accumulated_drift += drift_rate * dt_s
        value = baseline + state.accumulated_drift
        value += self.rng.gauss(0, noise_std)
        return value

    def _dependent(
        self,
        behavior: dict[str, Any],
        signal_values: dict[str, float],
    ) -> float:
        transform: str = behavior.get("transform", "input")
        depends_on: list[str] = list(behavior.get("depends_on", []))

        # Build namespace from upstream signal values
        namespace: dict[str, float] = {
            sid: signal_values.get(sid, 0.0) for sid in depends_on
        }
        if depends_on:
            namespace["input"] = signal_values.get(depends_on[0], 0.0)

        return evaluate_transform(transform, namespace, self.rng)

    # ──────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────

    def _get_state(self, signal_id: str) -> BehaviorState:
        """Return (or create) the mutable state for a signal."""
        state = self._state.get(signal_id)
        if state is None:
            state = BehaviorState(signal_id)
            self._state[signal_id] = state
        return state
