"""Composition seam (G4) — cross-scope composition graph, typed boundary ports,
immutable staged transfers, mechanism-neutral participants, and a deterministic
coordinator.

G4 does NOT implement G5+ (ASSY federation, UI, run-control, semantic binding,
SH-WTP), no numerical coupling solver, no historian, and no AssyLineRuntime
rewrite. The Coordinator is a composition service, not a domain simulation
engine.
"""

from __future__ import annotations

from virtual_factory.composition.ports import (
    BoundaryPort,
    PortCategory,
    PortDirection,
    PortError,
    PortRef,
    PortRegistry,
    check_port_compatibility,
)
from virtual_factory.composition.graph import (
    CompositionBinding,
    CompositionError,
    CompositionGraph,
)
from virtual_factory.composition.transfer import (
    BoundaryTransfer,
    TransferError,
)
from virtual_factory.composition.participant import (
    ExecutableParticipant,
    ParticipantError,
)
from virtual_factory.composition.coordinator import (
    CoordinationError,
    Coordinator,
    WindowOutcome,
)

__all__ = [
    "BoundaryPort",
    "PortCategory",
    "PortDirection",
    "PortError",
    "PortRef",
    "PortRegistry",
    "check_port_compatibility",
    "CompositionBinding",
    "CompositionError",
    "CompositionGraph",
    "BoundaryTransfer",
    "TransferError",
    "ExecutableParticipant",
    "ParticipantError",
    "CoordinationError",
    "Coordinator",
    "WindowOutcome",
]
