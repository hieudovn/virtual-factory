"""Run context — frozen metadata for one discrete simulation run.

No domain logic.  Pure data in a frozen dataclass.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any


class RunContextError(ValueError):
    """Raised when a RunContext invariant is violated."""


@dataclass(frozen=True, slots=True)
class RunContext:
    """Immutable metadata describing a single discrete simulation run.

    Attributes:
        run_id: Non-empty unique run identifier (required).
        model_id: Non-empty model identifier (required).
        engine_kind: Fixed to ``"discrete_manufacturing"``.
        model_version: Optional model version string.
        scenario_id: Optional scenario identifier.
        scenario_version: Optional scenario version string.
        random_seed: Non-negative integer seed (not bool).
        environment: Non-empty environment namespace (e.g. ``"demo"``).
        source_kind: Fixed to ``"simulation"``.
    """

    run_id: str
    model_id: str
    engine_kind: str = "discrete_manufacturing"
    model_version: str | None = None
    scenario_id: str | None = None
    scenario_version: str | None = None
    random_seed: int = 42
    environment: str = "demo"
    source_kind: str = "simulation"

    def __post_init__(self) -> None:
        # --- run_id ---
        if not isinstance(self.run_id, str) or not self.run_id.strip():
            raise RunContextError("run_id must be a non-empty str")

        # --- model_id ---
        if not isinstance(self.model_id, str) or not self.model_id.strip():
            raise RunContextError("model_id must be a non-empty str")

        # --- engine_kind ---
        if self.engine_kind != "discrete_manufacturing":
            raise RunContextError(
                f"engine_kind must be 'discrete_manufacturing', "
                f"got {self.engine_kind!r}"
            )

        # --- model_version ---
        if self.model_version is not None:
            if not isinstance(self.model_version, str) or not self.model_version.strip():
                raise RunContextError(
                    "model_version must be a non-empty str if provided"
                )

        # --- scenario_id ---
        if self.scenario_id is not None:
            if not isinstance(self.scenario_id, str) or not self.scenario_id.strip():
                raise RunContextError(
                    "scenario_id must be a non-empty str if provided"
                )

        # --- scenario_version ---
        if self.scenario_version is not None:
            if not isinstance(self.scenario_version, str) or not self.scenario_version.strip():
                raise RunContextError(
                    "scenario_version must be a non-empty str if provided"
                )

        # --- random_seed ---
        if isinstance(self.random_seed, bool):
            raise RunContextError("random_seed must be int, not bool")
        if not isinstance(self.random_seed, int):
            raise RunContextError(
                f"random_seed must be int, got {type(self.random_seed).__name__}"
            )
        if self.random_seed < 0:
            raise RunContextError(
                f"random_seed must be non-negative, got {self.random_seed}"
            )

        # --- environment ---
        if not isinstance(self.environment, str) or not self.environment.strip():
            raise RunContextError("environment must be a non-empty str")

        # --- source_kind ---
        if self.source_kind != "simulation":
            raise RunContextError(
                f"source_kind must be 'simulation', got {self.source_kind!r}"
            )

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Return a detached plain dictionary representation."""
        return {
            "run_id": self.run_id,
            "model_id": self.model_id,
            "engine_kind": self.engine_kind,
            "model_version": self.model_version,
            "scenario_id": self.scenario_id,
            "scenario_version": self.scenario_version,
            "random_seed": self.random_seed,
            "environment": self.environment,
            "source_kind": self.source_kind,
        }
