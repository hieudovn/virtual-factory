"""Federation seam (G5) — migrate TIPA Workspace / ASSY federation onto G1–G4.

G5 hosts the EXISTING ``AssyLineRuntime`` inside the accepted G1
Workspace/Scope structural foundation and the G4 executable-participant/
coordinator seams WITHOUT rewriting ``AssyLineRuntime`` and WITHOUT inventing a
new synchronization policy.

Public API:

- tipa_workspace: :func:`build_tipa_workspace`, :func:`sub_line_path`,
  :func:`assy_scope_path`, canonical constants, :class:`FederationStructuralError`
- assy_participant: :class:`AssySubLineAdapter` (G4 participant over one runtime)
- assy_host: :class:`TipaAssyFederation`, :class:`FederatedAssySubLine`,
  :class:`FederationError`

G5 does NOT implement G6 UI, G7 run-control/replay, G8+, G9 semantic binding,
G10 SH-WTP, or any hidden cross-sub-line synchronization policy.
"""

from __future__ import annotations

from virtual_factory.federation.assy_host import (
    FederatedAssySubLine,
    FederationError,
    TipaAssyFederation,
)
from virtual_factory.federation.assy_participant import AssySubLineAdapter
from virtual_factory.federation.tipa_workspace import (
    PLANT_ID,
    PRODUCTION_LINE_ID,
    SUB_LINE_IDS,
    FederationStructuralError,
    assy_scope_path,
    build_tipa_workspace,
    sub_line_path,
)
from virtual_factory.federation.generic import (
    GENERIC_FEDERATION_COUPLING_POLICY,
    GenericFederationError,
    SyntheticFederation,
    SyntheticParticipant,
    build_synthetic_federation,
)

__all__ = [
    "AssySubLineAdapter",
    "FederatedAssySubLine",
    "FederationError",
    "TipaAssyFederation",
    "PLANT_ID",
    "PRODUCTION_LINE_ID",
    "SUB_LINE_IDS",
    "FederationStructuralError",
    "assy_scope_path",
    "build_tipa_workspace",
    "sub_line_path",
    "GENERIC_FEDERATION_COUPLING_POLICY",
    "GenericFederationError",
    "SyntheticFederation",
    "SyntheticParticipant",
    "build_synthetic_federation",
]
