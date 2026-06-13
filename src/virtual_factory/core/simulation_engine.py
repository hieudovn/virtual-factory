"""Simulation engine skeleton.

The engine will execute plant configurations loaded from YAML/JSON. It must not
hard-code a specific plant, including the first continuous-process MVP.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SimulationEngine:
    """Coordinates time, plant graph, models, and telemetry policies."""

    plant_config: dict[str, Any]
    state: dict[str, Any] = field(default_factory=dict)

    def initialize(self) -> None:
        """Prepare runtime state from configuration without running physics."""
        self.state["initialized"] = True

    def step(self) -> None:
        """Advance the simulation by one tick.

        Detailed physics, controller execution, and telemetry generation are
        intentionally deferred to later implementation phases.
        """
        raise NotImplementedError("Simulation stepping is not implemented yet.")
