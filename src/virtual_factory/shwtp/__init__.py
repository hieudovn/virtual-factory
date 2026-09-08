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
- connectivity (G12B): :func:`build_shwtp_reference_connectivity`,
  :class:`ShwtpReferenceConnectivity`, :func:`build_shwtp_reference_graph`,
  :func:`source_pins`
- runtime (G13): :class:`T108Config`, :class:`T108TankRuntime`,
  :class:`T108State`, :class:`T108Step`, :class:`T108RuntimeError`,
  ``SHWTP_T108_CANONICAL_ID``, ``SHWTP_T108_SCOPE_PATH``
- logical runtime (G13B): :class:`T106Config`, :class:`T106LogicalRuntime`,
  :class:`T106State`, :class:`T106Step`, :class:`T106RuntimeError`,
  ``SHWTP_T106_CANONICAL_ID``, ``SHWTP_T106_SCOPE_PATH``
- projection (G14A): :class:`ProjectionRecord`, :class:`ShwtpF01Projection`,
  :func:`build_shwtp_f01_projection`, :func:`t106_out_port`, :func:`t108_in_port`,
  :func:`f01_binding`, :class:`ShwtpProjectionError`
- federation (G14B): :class:`ShwtpFederationConfig`, :class:`ShwtpFederation`,
  :class:`ShwtpT106Participant`, :class:`ShwtpT108Participant`,
  :class:`ShwtpFederationError`, ``SHWTP_FEDERATION_COUPLING_POLICY``,
  ``SHWTP_FEDERATION_PAYLOAD_KEY``
- evaluation (G15): :class:`ShwtpEvaluator`, :class:`ShwtpEvaluationRow`,
  :class:`ShwtpEvaluationSummary`, :func:`t108_mass_balance_residual`,
  :class:`ShwtpEvaluationError`, ``SHWTP_EVALUATION_LAG_WINDOWS``

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
from virtual_factory.shwtp.connectivity import (
    SHWTP_PIM_AUTHORITY,
    SHWTP_PIM_MAIN_SHA,
    SHWTP_SELECTED_RELATIONSHIPS,
    SHWTP_SYNTHETIC_REFERENCE_EXECUTION,
    PimReferenceRelation,
    ShwtpReferenceConnectivity,
    build_shwtp_reference_connectivity,
    build_shwtp_reference_graph,
    source_pins,
)
from virtual_factory.shwtp.runtime import (
    SHWTP_T108_CANONICAL_ID,
    SHWTP_T108_SCOPE_PATH,
    T108Config,
    T108RuntimeError,
    T108State,
    T108Step,
    T108TankRuntime,
)
from virtual_factory.shwtp.logical_runtime import (
    SHWTP_T106_CANONICAL_ID,
    SHWTP_T106_SCOPE_PATH,
    T106Config,
    T106LogicalRuntime,
    T106RuntimeError,
    T106State,
    T106Step,
)
from virtual_factory.shwtp.projection import (
    SHWTP_F01_PROJECTION_ID,
    ShwtpF01Projection,
    ShwtpProjectionError,
    ProjectionRecord,
    build_shwtp_f01_projection,
    f01_binding,
    t106_out_port,
    t108_in_port,
)
from virtual_factory.shwtp.federation import (
    SHWTP_FEDERATION_COUPLING_POLICY,
    SHWTP_FEDERATION_PAYLOAD_KEY,
    ShwtpFederation,
    ShwtpFederationConfig,
    ShwtpFederationError,
    ShwtpT106Participant,
    ShwtpT108Participant,
)
from virtual_factory.shwtp.evaluation import (
    SHWTP_EVALUATION_LAG_WINDOWS,
    ShwtpEvaluationError,
    ShwtpEvaluationRow,
    ShwtpEvaluationSummary,
    ShwtpEvaluator,
    t108_mass_balance_residual,
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
    "SHWTP_PIM_AUTHORITY",
    "SHWTP_PIM_MAIN_SHA",
    "SHWTP_SELECTED_RELATIONSHIPS",
    "SHWTP_SYNTHETIC_REFERENCE_EXECUTION",
    "PimReferenceRelation",
    "ShwtpReferenceConnectivity",
    "build_shwtp_reference_connectivity",
    "build_shwtp_reference_graph",
    "source_pins",
    "SHWTP_T108_CANONICAL_ID",
    "SHWTP_T108_SCOPE_PATH",
    "T108Config",
    "T108RuntimeError",
    "T108State",
    "T108Step",
    "T108TankRuntime",
    "SHWTP_T106_CANONICAL_ID",
    "SHWTP_T106_SCOPE_PATH",
    "T106Config",
    "T106LogicalRuntime",
    "T106RuntimeError",
    "T106State",
    "T106Step",
    "SHWTP_F01_PROJECTION_ID",
    "ShwtpF01Projection",
    "ShwtpProjectionError",
    "ProjectionRecord",
    "build_shwtp_f01_projection",
    "f01_binding",
    "t106_out_port",
    "t108_in_port",
    "SHWTP_FEDERATION_COUPLING_POLICY",
    "SHWTP_FEDERATION_PAYLOAD_KEY",
    "ShwtpFederation",
    "ShwtpFederationConfig",
    "ShwtpFederationError",
    "ShwtpT106Participant",
    "ShwtpT108Participant",
    "SHWTP_EVALUATION_LAG_WINDOWS",
    "ShwtpEvaluationError",
    "ShwtpEvaluationRow",
    "ShwtpEvaluationSummary",
    "ShwtpEvaluator",
    "t108_mass_balance_residual",
]
