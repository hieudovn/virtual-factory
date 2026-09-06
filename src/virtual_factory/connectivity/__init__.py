"""Reference Connectivity Graph foundation (G12A).

Generic, immutable, deterministic, inert representation of externally sourced
semantic/topology relation facts. This is the ``ReferenceConnectivityGraph``
layer of the frozen architecture and is intentionally separate from G1
containment, G4 composition, run-control, and any plant-specific vocabulary.

Public API:

- :class:`ReferenceEndpoint` — generic external semantic node reference;
- :class:`ReferenceEdge` — immutable, provenance-rich, inert relation fact;
- :class:`ReferenceConnectivityGraph` — deterministic graph with fail-closed
  invariants and deterministic serialization.

No runtime semantics, no ports, no state propagation, no SH-WTP materialization.
"""

from __future__ import annotations

from virtual_factory.connectivity.reference_graph import (
    NO_RUNTIME_EFFECT,
    SCHEMA,
    ReferenceConnectivityGraph,
    ReferenceEdge,
    ReferenceEndpoint,
    ReferenceGraphError,
)

__all__ = [
    "NO_RUNTIME_EFFECT",
    "SCHEMA",
    "ReferenceConnectivityGraph",
    "ReferenceEdge",
    "ReferenceEndpoint",
    "ReferenceGraphError",
]
