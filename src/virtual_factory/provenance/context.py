"""Generic, mechanism-neutral, immutable runtime/run context (G2).

A single platform-level representation of "one simulation run" that continuous,
discrete, batch and composed/hybrid execution mechanisms can share. It carries
IDENTITY and PROVENANCE-INPUT only — no domain logic, no execution state.

Identity separation (frozen, PH00 B1–B3 / ARCH-01):

- ``workspace_id``    — G1 Workspace identity.
- ``scope_path``      — full G1 ``StructuralPath`` of the owning/effective
                        executable scope (optional for legacy/workspace-level runs).
- ``run_id``          — identity of one simulation execution.
- ``scenario_id``     — identity of the selected scenario (one effective scenario
                        authority per run), with optional ``scenario_version``.
- ``model_id``        — model/profile identity where repo conventions require it
                        (optional at platform level; required by discrete).
- ``profile``         — informational execution/profile descriptor (e.g. the PH00
                        ``runtime.engine`` compatibility field). NOT an
                        engine-cardinality authority (ARCH-06 C01).
- ``source_run_id``   — optional lineage to a prior run (restart/new attempt),
                        metadata only — G2 does NOT implement replay/reset
                        orchestration.

PIM canonical ids are NOT part of this model and are never fabricated here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from virtual_factory.workspace.identity import StructuralPath


class RunContextV2Error(ValueError):
    """Raised when a generic run-context invariant is violated."""


@dataclass(frozen=True, slots=True)
class RunContextV2:
    """Immutable mechanism-neutral description of one simulation run."""

    workspace_id: str
    run_id: str
    scope_path: StructuralPath | None = None
    scenario_id: str | None = None
    scenario_version: str | None = None
    model_id: str | None = None
    model_version: str | None = None
    profile: str | None = None
    random_seed: int | None = None
    environment: str | None = None
    source_run_id: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty_str(self.workspace_id, "workspace_id")
        _require_non_empty_str(self.run_id, "run_id")
        if self.scope_path is not None:
            if not isinstance(self.scope_path, StructuralPath):
                raise RunContextV2Error(
                    f"scope_path must be StructuralPath, got {type(self.scope_path).__name__}"
                )
            if self.scope_path.workspace_id != self.workspace_id:
                raise RunContextV2Error(
                    f"scope_path workspace_id {self.scope_path.workspace_id!r} must "
                    f"match workspace_id {self.workspace_id!r}"
                )
        for name in ("scenario_id", "scenario_version", "model_id", "model_version",
                     "profile", "environment", "source_run_id"):
            value = getattr(self, name)
            if value is not None:
                _require_non_empty_str(value, name)
        if self.random_seed is not None:
            if isinstance(self.random_seed, bool):
                raise RunContextV2Error("random_seed must be int, not bool")
            if not isinstance(self.random_seed, int) or self.random_seed < 0:
                raise RunContextV2Error(
                    f"random_seed must be a non-negative int, got {self.random_seed!r}"
                )

    def to_dict(self) -> dict[str, Any]:
        """Deterministic, detached, key-stable serialization."""
        return {
            "workspace_id": self.workspace_id,
            "run_id": self.run_id,
            "scope_path": self.scope_path.as_string() if self.scope_path is not None else None,
            "scenario_id": self.scenario_id,
            "scenario_version": self.scenario_version,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "profile": self.profile,
            "random_seed": self.random_seed,
            "environment": self.environment,
            "source_run_id": self.source_run_id,
        }


def _require_non_empty_str(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise RunContextV2Error(f"{name} must be a non-empty str")
