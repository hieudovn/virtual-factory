"""Provenance v2 — generic runtime context + provenance envelope + namespace + adapters.

G2 delivers ONE generic, mechanism-neutral run-context/provenance seam that later
gates attach to executable Simulation Scopes and shared outputs. It does NOT
duplicate run identity, does NOT fabricate PIM canonical ids, and does NOT
implement replay/reset orchestration or semantic binding.
"""

from __future__ import annotations

from virtual_factory.provenance.enums import DataStatus, Fidelity, OriginKind
from virtual_factory.provenance.context import RunContextV2, RunContextV2Error
from virtual_factory.provenance.envelope import ProvenanceV2, ProvenanceError
from virtual_factory.provenance.namespace import (
    OutputNamespaceError,
    derive_output_namespace,
)
from virtual_factory.provenance.adapter import (
    from_discrete_run_context,
    to_provenance_v2,
)

__all__ = [
    "DataStatus",
    "Fidelity",
    "OriginKind",
    "RunContextV2",
    "RunContextV2Error",
    "ProvenanceV2",
    "ProvenanceError",
    "OutputNamespaceError",
    "derive_output_namespace",
    "from_discrete_run_context",
    "to_provenance_v2",
]
