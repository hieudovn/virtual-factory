"""Engine contract — structural protocol for simulation engines.

Defines the minimal interface that any simulation engine must satisfy
to be used by the CLI, API server and runtime service.

Per SA-ADR-017: legacy configurations default to continuous-process.

This module does NOT introduce a mandatory ABC hierarchy.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SimulationEngineProtocol(Protocol):
    """Structural contract satisfied by any simulation engine.

    Reflects the actual runtime usage in ``main.py`` and
    ``ui/runtime_service.py``, not a future design.
    """

    initialized: bool
    dt_s: float

    def initialize(self) -> None:
        """Lazily build the runtime assembly and prepare for stepping."""
        ...

    def step(self) -> dict[str, Any]:
        """Advance the simulation by one tick and return a snapshot."""
        ...
