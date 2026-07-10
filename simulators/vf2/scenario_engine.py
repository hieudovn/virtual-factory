"""Scenario engine for VF-2 — activates fault scenarios with signal overrides.

Per SA C4, PIM scenarios have ``expected_effects`` (human-readable) +
``affected_simulation_signal_ids`` (machine-readable).  VF-2 maps these
to runtime signal overrides with smooth linear interpolation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import VF2Package, VF2Scenario


# ======================================================================
# ScenarioTransition
# ======================================================================


@dataclass
class ScenarioTransition:
    """Smooth transition between scenarios.

    Attributes:
        active: Whether a transition is in progress.
        from_scenario: Name of the previous scenario (or ``""``).
        to_scenario: Name of the target scenario.
        duration_s: Total duration of the transition.
        elapsed_s: How long the transition has been running.
        signal_overrides_start: Override values at the start of transition.
        signal_overrides_target: Override values at the end of transition.
    """

    active: bool = False
    from_scenario: str = ""
    to_scenario: str = ""
    duration_s: float = 30.0
    elapsed_s: float = 0.0
    signal_overrides_start: dict[str, float] = field(default_factory=dict)
    signal_overrides_target: dict[str, float] = field(default_factory=dict)


# ======================================================================
# ScenarioEngine
# ======================================================================


class ScenarioEngine:
    """Activates fault scenarios with signal overrides.

    Scenario types supported:

    * ``pump_trip`` — all affected measurement signals → 0.0
    * ``valve_fault`` — all affected measurement signals → 0.0
      (defaults to empty overrides when no affected signals given)

    Smooth transition: linear interpolation over *transition_s* seconds.
    """

    def __init__(
        self,
        pkg: VF2Package,
        transition_s: float = 30.0,
    ) -> None:
        self.scenarios: dict[str, VF2Scenario] = {
            s.scenario_id: s for s in pkg.scenarios
        }
        self.active_scenario: VF2Scenario | None = None
        self.transition: ScenarioTransition | None = None
        self.transition_duration_s = transition_s

    # ──────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────

    def activate(self, scenario_id: str) -> dict[str, Any]:
        """Activate a scenario.

        Args:
            scenario_id: The scenario to activate.

        Returns:
            A status dict::

                {"status": "transitioning" | "error",
                 "from_scenario": "...",
                 "to_scenario": "...",
                 "transition_duration_s": ...}
        """
        if scenario_id not in self.scenarios:
            return {
                "status": "error",
                "message": f"Scenario '{scenario_id}' not found",
            }

        scn = self.scenarios[scenario_id]
        old = self.active_scenario.scenario_id if self.active_scenario else ""

        # Capture current active overrides as the starting point
        start_overrides = self._get_active_overrides()

        # Build target overrides from the scenario
        target_overrides = self._build_overrides(scn)

        self.active_scenario = scn
        self.transition = ScenarioTransition(
            active=True,
            from_scenario=old,
            to_scenario=scenario_id,
            duration_s=self.transition_duration_s,
            signal_overrides_start=start_overrides,
            signal_overrides_target=target_overrides,
        )

        return {
            "status": "transitioning",
            "from_scenario": old,
            "to_scenario": scenario_id,
            "transition_duration_s": self.transition_duration_s,
        }

    def step(self, dt_s: float) -> dict[str, float]:
        """Advance any active transition by *dt_s*.

        Returns the current signal overrides — linearly interpolated
        if a transition is in progress, or the final overrides once
        the transition has completed.
        """
        if self.transition is None or not self.transition.active:
            return self._get_active_overrides()

        self.transition.elapsed_s += dt_s
        progress = min(1.0, self.transition.elapsed_s / max(self.transition_duration_s, 0.01))

        # Linear interpolation
        overrides: dict[str, float] = {}
        for sid, target in self.transition.signal_overrides_target.items():
            start = self.transition.signal_overrides_start.get(sid, target)
            overrides[sid] = start + (target - start) * progress

        if progress >= 1.0:
            # Transition complete — freeze final values
            self.transition.active = False
            self.transition.signal_overrides_start = dict(self.transition.signal_overrides_target)

        return overrides

    # ──────────────────────────────────────────────────────────────────
    # Queries
    # ──────────────────────────────────────────────────────────────────

    def get_current(self) -> str:
        """Return the active scenario ID (or ``""`` if none)."""
        return self.active_scenario.scenario_id if self.active_scenario else ""

    def list_scenarios(self) -> list[dict[str, str]]:
        """Return metadata for all registered scenarios."""
        return [
            {
                "scenario_id": s.scenario_id,
                "scenario_type": s.scenario_type,
                "description": s.description or "",
            }
            for s in self.scenarios.values()
        ]

    # ──────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────

    def _build_overrides(self, scn: VF2Scenario) -> dict[str, float]:
        """Map scenario type + affected signals to runtime overrides.

        * ``pump_trip`` — all affected measurement signals → 0.0
        * ``valve_fault`` — all affected measurement signals → 0.0
        * Others — affected signals → 0.0 (generic fallback)
        """
        overrides: dict[str, float] = {}

        if scn.scenario_type in ("pump_trip", "valve_fault"):
            for sid in scn.affected_simulation_signal_ids:
                overrides[sid] = 0.0
        else:
            for sid in scn.affected_simulation_signal_ids:
                overrides[sid] = 0.0

        return overrides

    def _get_active_overrides(self) -> dict[str, float]:
        """Return the final overrides (after transition has completed)."""
        if self.transition and not self.transition.active:
            return dict(self.transition.signal_overrides_target)
        return {}
