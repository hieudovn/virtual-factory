"""Provenance v2 — immutable machine-readable origin/context envelope (G2).

Attaches immutable, deterministic provenance to a run/output WITHOUT replacing
runtime truth, evidence maturity, or PIM semantic identity.

Identity separation (frozen):

- ``workspace_id``, ``scope_path``, ``run_id``, ``scenario_id`` are VF structural/
  runtime identity;
- ``runtime_signal_id`` is a VF-internal execution key — DISTINCT from the
  PIM-owned ``canonical_signal_id`` (which G2 neither stores nor fabricates);
- ``origin_kind``/``fidelity``/``data_status`` are frozen simulation-truth labels.

G2 does NOT implement PIM semantic binding (G9). ``semantic_contract_version``
and ``semantic_contract_sha`` are optional, immutable, and serialized — never
validated against PIM here, and never used to fabricate canonical ids.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from virtual_factory.provenance.enums import DataStatus, Fidelity, OriginKind
from virtual_factory.workspace.identity import StructuralPath


class ProvenanceError(ValueError):
    """Raised when a provenance invariant is violated."""


@dataclass(frozen=True, slots=True)
class ProvenanceV2:
    """Immutable provenance envelope for one run/output."""

    workspace_id: str
    run_id: str
    scope_path: StructuralPath | None = None
    scenario_id: str | None = None
    origin_kind: OriginKind = OriginKind.SIMULATION
    fidelity: Fidelity | None = None
    data_status: DataStatus | None = None
    semantic_contract_version: str | None = None
    semantic_contract_sha: str | None = None
    evidence_note: str | None = None
    runtime_signal_id: str | None = None
    simulation_time_s: float | None = None
    step: int | None = None

    def __post_init__(self) -> None:
        _require_non_empty_str(self.workspace_id, "workspace_id")
        _require_non_empty_str(self.run_id, "run_id")
        if self.scope_path is not None and not isinstance(self.scope_path, StructuralPath):
            raise ProvenanceError(
                f"scope_path must be StructuralPath, got {type(self.scope_path).__name__}"
            )
        if self.scenario_id is not None:
            _require_non_empty_str(self.scenario_id, "scenario_id")

        # Simulation truth labels — fail closed.
        if self.origin_kind is not OriginKind.SIMULATION:
            raise ProvenanceError(
                f"origin_kind must be OriginKind.SIMULATION for VF-generated "
                f"output, got {self.origin_kind!r}"
            )
        if self.data_status is not None and self.data_status not in (
            DataStatus.SYNTHETIC,
            DataStatus.SIMULATED_GROUND_TRUTH,
        ):
            raise ProvenanceError(
                f"data_status must be synthetic or simulated_ground_truth, "
                f"got {self.data_status!r}"
            )
        if self.fidelity is not None and not isinstance(self.fidelity, Fidelity):
            raise ProvenanceError(
                f"fidelity must be a Fidelity enum, got {type(self.fidelity).__name__}"
            )

        for name in ("semantic_contract_version", "semantic_contract_sha",
                     "evidence_note", "runtime_signal_id"):
            value = getattr(self, name)
            if value is not None:
                _require_non_empty_str(value, name)

        if self.simulation_time_s is not None:
            if isinstance(self.simulation_time_s, bool) or not isinstance(
                self.simulation_time_s, (int, float)
            ):
                raise ProvenanceError("simulation_time_s must be a float")
            if self.simulation_time_s < 0:
                raise ProvenanceError("simulation_time_s must be >= 0")
        if self.step is not None:
            if isinstance(self.step, bool) or not isinstance(self.step, int) or self.step < 0:
                raise ProvenanceError(f"step must be a non-negative int, got {self.step!r}")

    def to_dict(self) -> dict[str, Any]:
        """Deterministic, detached, key-stable serialization."""
        return {
            "workspace_id": self.workspace_id,
            "run_id": self.run_id,
            "scope_path": self.scope_path.as_string() if self.scope_path is not None else None,
            "scenario_id": self.scenario_id,
            "origin_kind": self.origin_kind.value,
            "fidelity": self.fidelity.value if self.fidelity is not None else None,
            "data_status": self.data_status.value if self.data_status is not None else None,
            "semantic_contract_version": self.semantic_contract_version,
            "semantic_contract_sha": self.semantic_contract_sha,
            "evidence_note": self.evidence_note,
            "runtime_signal_id": self.runtime_signal_id,
            "simulation_time_s": self.simulation_time_s,
            "step": self.step,
        }


def _require_non_empty_str(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ProvenanceError(f"{name} must be a non-empty str")
