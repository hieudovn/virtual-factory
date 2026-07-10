"""Simulation loop & frame builder for VF-2.

This is the **integration point** — it combines package loader, validator,
registries, topology, behaviour engine, and scenario engine into a single
``step()`` call that produces measurement frames.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .behavior_engine import BehaviorEngine
from .config import Vf2Config
from .object_registry import ObjectRegistry
from .scenario_engine import ScenarioEngine
from .signal_registry import SignalRegistry
from .topology_engine import TopologyEngine


# ======================================================================
# Data structures
# ======================================================================


@dataclass
class Measurement:
    """One signal measurement at a point in time."""

    timestamp: str
    signal_id: str
    value: float | bool
    quality: str
    source: str


@dataclass
class SimulationState:
    """Mutable state accumulated across simulation ticks."""

    time_s: float = 0.0
    step_count: int = 0
    signal_values: dict[str, float] = field(default_factory=dict)
    latest_measurements: list[Measurement] = field(default_factory=list)


# ======================================================================
# Vf2SimulationLoop
# ======================================================================


class Vf2SimulationLoop:
    """Orchestrates one simulation tick through all VF-2 sub-systems.

    Flow per tick::

        1. BehaviourEngine.step(dt)  → raw signal values
        2. Resolve dependent signals in topological order
        3. ScenarioEngine.step(dt)   → apply scenario overrides
        4. Build measurement frame   → list[Measurement]
    """

    def __init__(
        self,
        pkg: Any,           # VF2Package — avoid circular import at runtime
        config: Vf2Config | None = None,
    ) -> None:
        # Defer imports to avoid circular dependency during testing
        from .models import VF2Package

        if not isinstance(pkg, VF2Package):
            # Allow duck-typing for tests
            pass

        self.pkg = pkg
        self.config = config or Vf2Config()

        # Build all sub-systems
        self.obj_reg = ObjectRegistry(pkg)
        self.sig_reg = SignalRegistry(pkg)
        self.topology = TopologyEngine(pkg, self.obj_reg, self.sig_reg)
        self.behavior = BehaviorEngine(self.sig_reg)
        self.scenario = ScenarioEngine(pkg, self.config.transition_s)

        # Build topology graph once
        self.graph = self.topology.build()

        self.state = SimulationState()
        self.rng = random.Random(42)

    # ──────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────

    def step(self, dt_s: float = 1.0) -> list[Measurement]:
        """Execute one full simulation tick.

        Args:
            dt_s: Tick duration in seconds (default 1.0).

        Returns:
            List of ``Measurement`` objects, one per registered signal.
        """
        self.state.time_s += dt_s
        self.state.step_count += 1

        # Phase 1: Behaviour engine generates raw values
        raw_values = self.behavior.step(dt_s, self.state.signal_values)
        self.state.signal_values.update(raw_values)

        # Phase 2: Resolve dependent signals in topological order
        for sig_id in self.graph.eval_order:
            sig = self.sig_reg.get(sig_id)
            if sig is None:
                continue
            if sig_id in raw_values:
                continue  # Already computed by behaviour engine
            behavior = self.sig_reg.get_default_behavior(sig)
            if behavior.get("type") == "dependent":
                val = self.behavior.step_one(
                    sig_id, dt_s, behavior, self.state.signal_values,
                )
                self.state.signal_values[sig_id] = val

        # Phase 3: Apply scenario overrides
        scenario_overrides = self.scenario.step(dt_s)
        for sid, val in scenario_overrides.items():
            self.state.signal_values[sid] = val

        # Phase 4: Build measurement frame
        frame = self._build_frame()
        self.state.latest_measurements = frame
        return frame

    def run(self, steps: int, dt_s: float = 1.0) -> list[list[Measurement]]:
        """Run *steps* ticks and return all frames."""
        return [self.step(dt_s) for _ in range(steps)]

    def activate_scenario(self, scenario_id: str) -> dict[str, Any]:
        """Activate a fault scenario by ID.

        Delegates to ``ScenarioEngine.activate()``.
        """
        return self.scenario.activate(scenario_id)

    # ──────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────

    def _build_frame(self) -> list[Measurement]:
        """Collect all signal values into ``Measurement`` objects."""
        ts = (
            datetime.now(timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%S.") + "000Z"
        )

        frame: list[Measurement] = []
        for sig_id in self.sig_reg.all_signal_ids:
            val = self.state.signal_values.get(sig_id, 0.0)
            sig = self.sig_reg.get(sig_id)

            # Basic quality heuristic
            quality = "GOOD"
            if sig and sig.behavior.signal_type.value == "alarm":
                quality = "GOOD"

            frame.append(Measurement(
                timestamp=ts,
                signal_id=sig_id,
                value=val,
                quality=quality,
                source=self.config.source,
            ))

        return frame
