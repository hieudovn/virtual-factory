"""VF-vNEXT-G12B — SH-WTP PIM reference connectivity materialization.

Materializes the exact pinned SH-WTP PIM connectivity relationship facts
(the F01-F07 process/connectivity slice) into the accepted generic G12A
:class:`~virtual_factory.connectivity.ReferenceConnectivityGraph`.

Frozen architecture (this module implements only the first arrow):

    PIM semantic relationships -> VF ReferenceConnectivityGraph
        -> later explicit interpretation/projection -> Boundary Contracts/Ports
        -> G4 CompositionGraph -> Runtime

Frozen rules (Issue #59):

- Raw PIM relation types are preserved verbatim: ``FLOWS_TO`` stays
  ``FLOWS_TO``, ``DISCHARGES_TO`` stays ``DISCHARGES_TO``, ``CONNECTED_TO``
  stays ``CONNECTED_TO``. No reclassification into the six G10 runtime
  planning classes (``material_flow`` / ``chemical_flow`` /
  ``sludge_waste_flow`` / ``utility_energy_flow`` / ``control_information_flow``
  / ``dependency_constraint``).
- ``PROC-*`` / ProcessConnection entities are allowed as
  :class:`~virtual_factory.connectivity.ReferenceEndpoint` without being G11
  Scopes. They are NOT materialized into containment, NOT mapped to Unit/Scope
  via ``PART_OF``, and no runtime owner is inferred.
- Ambiguous/review-required relations remain present (PIM asserts them) but
  their warning/status metadata is preserved exactly and no stronger
  interpretation is added.
- Every edge is inert: ``runtime_effect = none``.
- No BoundaryPort / PortDirection / PortCategory / CompositionBinding /
  coordinator / run-control / state propagation.
- ``vf_runtime_authorization = NOT_AUTHORIZED`` and
  ``synthetic_reference_execution = PENDING_LATER_PIM_REVIEW`` are unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass

from virtual_factory.connectivity import (
    ReferenceConnectivityGraph,
    ReferenceEdge,
    ReferenceEndpoint,
)

# --- Frozen PIM authority pins (repo-first, Issue #59) ---------------------
SHWTP_PIM_AUTHORITY = "hieudovn/plant-intelligence-model"
SHWTP_PIM_MAIN_SHA = "ec7f1266d4a19e5201b689874a2a7a75a022fc5c"
SHWTP_PIM_PACKAGE = "SHW-PIM-VF-EXPORT-v0.1"
SHWTP_PIM_VERSION = "v0.1"
SHWTP_PIM_SOURCE_MODEL = "SHW-PH03-v0.1"
SHWTP_PIM_SEMANTIC_IDENTITY_SHA = "f23f3c4614f50a1a2e3805f7e887433feb934915"
SHWTP_PIM_ARTIFACT_HASH_SHA = "ea3361a4aca9d25927a4a76c792f3af184e1aabb"
SHWTP_PIM_COMPATIBILITY = "compatible_with_constraints"

# Frozen runtime authorization state (Issue #59 point 10) — unchanged.
SHWTP_RUNTIME_AUTHORIZATION = "NOT_AUTHORIZED"
SHWTP_SYNTHETIC_REFERENCE_EXECUTION = "PENDING_LATER_PIM_REVIEW"
SHWTP_SITE_AUTHORIZED_EXECUTION = "NOT_AUTHORIZED"

SHWTP_PIM_MODEL_FIXTURE = "examples/song-hong-wtp/model_fixture/model.yaml"
SHWTP_PIM_MODEL_FIXTURE_SHA256 = (
    "e9c6703fd0c50a58ccb481aa952eddbeddd4b94b5206103b8c472836e0729ea6"
)

# PIM declares every flow-path entity with entity_type/category
# ``ProcessConnection`` (repo-first inspection of model.yaml).
SHWTP_PROCESS_ENTITY_KIND = "ProcessConnection"


@dataclass(frozen=True, slots=True)
class PimReferenceRelation:
    """One exact pinned PIM relationship fact (verbatim fields)."""

    relationship_id: str
    relation_type: str
    source_id: str
    target_id: str
    evidence_status: str
    warnings: tuple[str, ...] = ()


# Exact selected process/connectivity slice F01-F07 from the pinned PIM model
# fixture (repo-first inspection). Raw relation types and evidence status are
# verbatim. F02 (DISCHARGES_TO) and F03 (CONNECTED_TO) carry the PIM
# "known-but-unconstrained" warning (REL-006) preserved as-is.
SHWTP_SELECTED_RELATIONSHIPS: tuple[PimReferenceRelation, ...] = (
    PimReferenceRelation(
        relationship_id="REL-SHW-F01",
        relation_type="FLOWS_TO",
        source_id="PROC-SHW-L1-T106-OUT-FLOW",
        target_id="PROC-SHW-L1-T108-IN-FLOW",
        evidence_status="DocumentConfirmed",
    ),
    PimReferenceRelation(
        relationship_id="REL-SHW-F02",
        relation_type="DISCHARGES_TO",
        source_id="PROC-SHW-L1-T106-WASH-OUT",
        target_id="PROC-SHW-WASH-T110-RECOVERY-RETURN",
        evidence_status="PatternInferred",
        warnings=(
            "known-but-unconstrained in C04 (REL-006 WARNING; linked to GAP register)",
        ),
    ),
    PimReferenceRelation(
        relationship_id="REL-SHW-F03",
        relation_type="CONNECTED_TO",
        source_id="PROC-SHW-WASH-T110-RECOVERY-RETURN",
        target_id="PROC-SHW-L1-T106-OUT-FLOW",
        evidence_status="PatternInferred",
        warnings=(
            "known-but-unconstrained in C04 (REL-006 WARNING; linked to GAP register)",
        ),
    ),
    PimReferenceRelation(
        relationship_id="REL-SHW-F04",
        relation_type="FLOWS_TO",
        source_id="PROC-SHW-RAW-TO-T100",
        target_id="PROC-SHW-T100-TO-L1",
        evidence_status="DocumentConfirmed",
    ),
    PimReferenceRelation(
        relationship_id="REL-SHW-F05",
        relation_type="FLOWS_TO",
        source_id="PROC-SHW-T100-TO-L1",
        target_id="PROC-SHW-L1-TO-DIST",
        evidence_status="DocumentConfirmed",
    ),
    PimReferenceRelation(
        relationship_id="REL-SHW-F06",
        relation_type="FLOWS_TO",
        source_id="PROC-SHW-L1-SLUDGE-OUT",
        target_id="PROC-SHW-SLUDGE-T201-IN",
        evidence_status="PatternInferred",
    ),
    PimReferenceRelation(
        relationship_id="REL-SHW-F07",
        relation_type="FLOWS_TO",
        source_id="PROC-SHW-CHEM-DOSING-LINE",
        target_id="PROC-SHW-T100-TO-L1",
        evidence_status="PatternInferred",
    ),
)


def _endpoint(canonical_id: str) -> ReferenceEndpoint:
    """A PIM canonical semantic reference endpoint (never a VF Scope)."""
    return ReferenceEndpoint(
        authority=SHWTP_PIM_AUTHORITY,
        entity_id=canonical_id,
        entity_kind=SHWTP_PROCESS_ENTITY_KIND,
    )


def build_shwtp_reference_graph() -> ReferenceConnectivityGraph:
    """Build the deterministic inert SH-WTP PIM reference connectivity graph.

    Exactly the F01-F07 connectivity facts, raw relation types preserved, no
    runtime interpretation, no containment coupling.
    """
    edges = [
        ReferenceEdge(
            edge_id=rel.relationship_id,
            source=_endpoint(rel.source_id),
            target=_endpoint(rel.target_id),
            relation_type=rel.relation_type,
            evidence_ref=f"{SHWTP_PIM_MODEL_FIXTURE}#{rel.relationship_id}",
            status=rel.evidence_status,
            gaps=rel.warnings,
        )
        for rel in SHWTP_SELECTED_RELATIONSHIPS
    ]
    return ReferenceConnectivityGraph(edges)


def source_pins() -> dict:
    """Deterministic PIM source provenance for the materialized slice."""
    return {
        "repository": SHWTP_PIM_AUTHORITY,
        "main_sha": SHWTP_PIM_MAIN_SHA,
        "package": SHWTP_PIM_PACKAGE,
        "version": SHWTP_PIM_VERSION,
        "source_model_version": SHWTP_PIM_SOURCE_MODEL,
        "semantic_identity_sha": SHWTP_PIM_SEMANTIC_IDENTITY_SHA,
        "artifact_hash_sha": SHWTP_PIM_ARTIFACT_HASH_SHA,
        "compatibility": SHWTP_PIM_COMPATIBILITY,
        "runtime_authorization": SHWTP_RUNTIME_AUTHORIZATION,
        "model_fixture": SHWTP_PIM_MODEL_FIXTURE,
        "model_fixture_sha256": SHWTP_PIM_MODEL_FIXTURE_SHA256,
        "selected_relationship_ids": tuple(
            rel.relationship_id for rel in SHWTP_SELECTED_RELATIONSHIPS
        ),
    }


@dataclass(frozen=True, slots=True)
class ShwtpReferenceConnectivity:
    """SH-WTP PIM reference connectivity view (graph + source provenance)."""

    graph: ReferenceConnectivityGraph
    pins: dict
    selected_relationship_ids: tuple[str, ...]

    def serialize(self) -> dict:
        """Deterministic machine-readable summary + graph serialization."""
        return {
            "schema": "vf.vnext.g12b.shwtp.reference_connectivity.v1",
            "pim_source": {
                key: value
                for key, value in self.pins.items()
                if key != "selected_relationship_ids"
            },
            "selected_relationship_ids": list(self.selected_relationship_ids),
            "selected_count": len(self.selected_relationship_ids),
            "runtime_authorization": SHWTP_RUNTIME_AUTHORIZATION,
            "synthetic_reference_execution": SHWTP_SYNTHETIC_REFERENCE_EXECUTION,
            "site_authorized_execution": SHWTP_SITE_AUTHORIZED_EXECUTION,
            "graph": self.graph.serialize(),
        }


def build_shwtp_reference_connectivity() -> ShwtpReferenceConnectivity:
    """Build the SH-WTP PIM reference connectivity view."""
    return ShwtpReferenceConnectivity(
        graph=build_shwtp_reference_graph(),
        pins=source_pins(),
        selected_relationship_ids=tuple(
            rel.relationship_id for rel in SHWTP_SELECTED_RELATIONSHIPS
        ),
    )
