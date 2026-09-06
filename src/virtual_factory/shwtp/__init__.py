"""VF-vNEXT-G11 — SH-WTP structural Workspace construction (structural only).

Materializes the SH-WTP Workspace structural hierarchy from the frozen G10 plan
using the accepted generic G1 Workspace/Scope/Object foundation.

Public API:

- constants: ``SHWTP_WORKSPACE_ID``, ``SHWTP_PLANT_CANONICAL_ID``,
  ``SHWTP_RUNTIME_AUTHORIZATION``, ``SHWTP_EXECUTABLE_CANDIDATE_CANONICAL_IDS``
- identity: :func:`vf_local_id`
- metadata: :class:`ShwtpNodeMeta`, :class:`ShwtpPlantMeta`
- view: :class:`ShwtpWorkspace`
- construction: :func:`build_shwtp_workspace`

Structural construction only (G11). No executable behavior, no runtime bridge,
no connectivity graph, no PIM authority transfer, no G12+ work.
"""

from __future__ import annotations

from virtual_factory.shwtp.structural import (
    SHWTP_EXECUTABLE_CANDIDATE_CANONICAL_IDS,
    SHWTP_PLANT_CANONICAL_ID,
    SHWTP_RUNTIME_AUTHORIZATION,
    SHWTP_SITE_AUTHORIZED_EXECUTION,
    SHWTP_STRUCTURAL_AUTHORIZED_IN_G11,
    SHWTP_SYNTHETIC_PENDING_LATER_PIM_REVIEW,
    SHWTP_WORKSPACE_ID,
    ShwtpNodeMeta,
    ShwtpPlantMeta,
    ShwtpStructuralError,
    ShwtpWorkspace,
    build_shwtp_workspace,
    vf_local_id,
)

__all__ = [
    "SHWTP_EXECUTABLE_CANDIDATE_CANONICAL_IDS",
    "SHWTP_PLANT_CANONICAL_ID",
    "SHWTP_RUNTIME_AUTHORIZATION",
    "SHWTP_SITE_AUTHORIZED_EXECUTION",
    "SHWTP_STRUCTURAL_AUTHORIZED_IN_G11",
    "SHWTP_SYNTHETIC_PENDING_LATER_PIM_REVIEW",
    "SHWTP_WORKSPACE_ID",
    "ShwtpNodeMeta",
    "ShwtpPlantMeta",
    "ShwtpStructuralError",
    "ShwtpWorkspace",
    "build_shwtp_workspace",
    "vf_local_id",
]
