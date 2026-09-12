"""VF-vNEXT-G14A — SH-WTP T106->T108 runtime projection contract (F01 only).

Creates the smallest explicit, evidence-traceable, INERT runtime projection for
exactly one accepted PIM relationship:

    REL-SHW-F01:  PROC-SHW-L1-T106-OUT-FLOW --FLOWS_TO--> PROC-SHW-L1-T108-IN-FLOW
    evidence:     DocumentConfirmed

Frozen architecture (this module implements only the explicit projection arrow):

    PIM semantic fact
    -> G12A/B ReferenceConnectivityGraph
    -> G14A explicit runtime projection decision
    -> VF BoundaryPort + G4 CompositionBinding
    -> future G14B coordinator/federated execution

Why F01 only (no auto-projection): the projection is justified by the conjunction
of (1) PIM F01 DocumentConfirmed, (2) G12C T106 filtered-water output-flow fact,
(3) G12C T108 filtered-water input-flow fact, (4) G13B T106 ``output_flow_m3_s``,
(5) G13 T108 ``inflow_m3_s``, and (6) identical volumetric-flow unit semantics.
No generic ``FLOWS_TO => material binding`` rule exists anywhere.

This module does NOT:

- execute the binding, transfer any value, advance the coordinator, share a clock,
  or orchestrate run-control;
- project F02/F03 (ambiguous/warning-bearing) or F04-F07 (not authorized);
- reference T110 (blocked);
- modify T106/T108 behavior, G4 semantics, G7, or PIM;
- enable workspace/container execution or plant-wide runtime.

``vf_runtime_authorization = NOT_AUTHORIZED`` and
``site_authorized_execution = NOT_AUTHORIZED`` remain unchanged; G14A authorizes
only this synthetic/reference projection contract for a future bounded gate.
"""

from __future__ import annotations

from dataclasses import dataclass

from virtual_factory.composition import (
    BoundaryPort,
    CompositionBinding,
    CompositionGraph,
    PortCategory,
    PortDirection,
    PortRef,
    check_port_compatibility,
)
from virtual_factory.shwtp.connectivity import (
    SHWTP_PIM_AUTHORITY,
    SHWTP_PIM_MAIN_SHA,
    SHWTP_SELECTED_RELATIONSHIPS,
    PimReferenceRelation,
)
from virtual_factory.shwtp.logical_runtime import (
    SHWTP_T106_CANONICAL_ID,
    SHWTP_T106_SCOPE_PATH,
)
from virtual_factory.shwtp.runtime import (
    SHWTP_T108_CANONICAL_ID,
    SHWTP_T108_SCOPE_PATH,
)
from virtual_factory.shwtp.structural import SHWTP_WORKSPACE_ID

# --- Frozen F01 projection pins ----------------------------------------------
SHWTP_F01_PROJECTION_ID = "PROJ-SHW-F01-T106-T108"
SHWTP_F01_RELATION_ID = "REL-SHW-F01"
SHWTP_F01_RELATION_TYPE = "FLOWS_TO"
SHWTP_F01_PIM_SOURCE = "PROC-SHW-L1-T106-OUT-FLOW"
SHWTP_F01_PIM_TARGET = "PROC-SHW-L1-T108-IN-FLOW"
SHWTP_F01_EVIDENCE_STATUS = "DocumentConfirmed"

# VF-local port/binding identities (never PIM canonical ids).
SHWTP_T106_OUT_PORT_ID = "out_flow"
SHWTP_T108_IN_PORT_ID = "in_flow"
SHWTP_F01_BINDING_ID = "BIND-SHW-F01-T106-OUT-T108-IN"

SHWTP_F01_PORT_UNIT = "m3/s"
SHWTP_F01_PORT_DESCRIPTOR = "volumetric_flow"

SHWTP_F01_AUTHORIZATION_SCOPE = (
    "CANDIDATE_SCOPED synthetic/reference federation projection only; "
    "no runtime execution in G14A; no site-faithful execution."
)
SHWTP_F01_DISCLAIMER = (
    "This projection is an explicit synthetic/reference interpretation of PIM "
    "REL-SHW-F01. It does NOT authorize site-faithful execution. "
    "vf_runtime_authorization remains NOT_AUTHORIZED and "
    "site_authorized_execution remains NOT_AUTHORIZED."
)


class ShwtpProjectionError(ValueError):
    """Raised when the F01 projection invariant is violated (fail closed)."""


def _f01_relation() -> PimReferenceRelation:
    """Cross-check the accepted G12B connectivity slice for REL-SHW-F01."""
    for rel in SHWTP_SELECTED_RELATIONSHIPS:
        if rel.relationship_id == SHWTP_F01_RELATION_ID:
            return rel
    raise ShwtpProjectionError(
        f"{SHWTP_F01_RELATION_ID} not present in accepted G12B connectivity slice"
    )


def t106_out_port_ref() -> PortRef:
    """VF-local source boundary endpoint identity (T106 filtered-water output)."""
    return PortRef(owner_scope=SHWTP_T106_SCOPE_PATH, port_id=SHWTP_T106_OUT_PORT_ID)


def t108_in_port_ref() -> PortRef:
    """VF-local target boundary endpoint identity (T108 filtered-water input)."""
    return PortRef(owner_scope=SHWTP_T108_SCOPE_PATH, port_id=SHWTP_T108_IN_PORT_ID)


def t106_out_port() -> BoundaryPort:
    return BoundaryPort(
        ref=t106_out_port_ref(),
        direction=PortDirection.OUT,
        category=PortCategory.MATERIAL,
        unit=SHWTP_F01_PORT_UNIT,
        descriptor=SHWTP_F01_PORT_DESCRIPTOR,
    )


def t108_in_port() -> BoundaryPort:
    return BoundaryPort(
        ref=t108_in_port_ref(),
        direction=PortDirection.IN,
        category=PortCategory.MATERIAL,
        unit=SHWTP_F01_PORT_UNIT,
        descriptor=SHWTP_F01_PORT_DESCRIPTOR,
    )


def f01_binding() -> CompositionBinding:
    return CompositionBinding(
        edge_id=SHWTP_F01_BINDING_ID,
        source=t106_out_port_ref(),
        target=t108_in_port_ref(),
    )


@dataclass(frozen=True, slots=True)
class ProjectionRecord:
    """Immutable, evidence-traceable description of the single F01 projection."""

    projection_id: str
    relation_id: str
    relation_type: str
    pim_source_endpoint: str
    pim_target_endpoint: str
    evidence_status: str
    vf_source_path: str
    vf_target_path: str
    source_port_ref: str
    target_port_ref: str
    source_direction: str
    target_direction: str
    category: str
    unit: str
    descriptor: str
    authorization_scope: str
    disclaimer: str
    pim_authority: str
    pim_main_sha: str

    def to_dict(self) -> dict:
        return {
            "projection_id": self.projection_id,
            "relation_id": self.relation_id,
            "relation_type": self.relation_type,
            "pim_source_endpoint": self.pim_source_endpoint,
            "pim_target_endpoint": self.pim_target_endpoint,
            "evidence_status": self.evidence_status,
            "vf_source_path": self.vf_source_path,
            "vf_target_path": self.vf_target_path,
            "source_port_ref": self.source_port_ref,
            "target_port_ref": self.target_port_ref,
            "source_direction": self.source_direction,
            "target_direction": self.target_direction,
            "category": self.category,
            "unit": self.unit,
            "descriptor": self.descriptor,
            "authorization_scope": self.authorization_scope,
            "disclaimer": self.disclaimer,
            "pim_authority": self.pim_authority,
            "pim_main_sha": self.pim_main_sha,
        }


@dataclass(frozen=True, slots=True)
class ShwtpF01Projection:
    """The single inert F01 projection: record + 2 ports + 1 binding + graph."""

    record: ProjectionRecord
    ports: tuple[BoundaryPort, BoundaryPort]
    binding: CompositionBinding
    graph: CompositionGraph

    def serialize(self) -> dict:
        """Deterministic inspection proving PIM -> VF boundary -> G4 binding."""
        return {
            "schema": "vf.vnext.g14a.shwtp.f01.projection.v1",
            "projection": self.record.to_dict(),
            "ports": [
                {
                    "ref": p.ref.as_string(),
                    "direction": p.direction.value,
                    "category": p.category.value,
                    "unit": p.unit,
                    "descriptor": p.descriptor,
                }
                for p in self.ports
            ],
            "bindings": [
                {
                    "edge_id": self.binding.edge_id,
                    "source": self.binding.source.as_string(),
                    "target": self.binding.target.as_string(),
                }
            ],
        }


def build_shwtp_f01_projection() -> ShwtpF01Projection:
    """Build the exact inert F01 projection (fail closed on any pin mismatch)."""
    rel = _f01_relation()

    # Fail closed: F01 pins must exactly match the pinned accepted values.
    if rel.relation_type != SHWTP_F01_RELATION_TYPE:
        raise ShwtpProjectionError(
            f"F01 relation_type must be {SHWTP_F01_RELATION_TYPE!r}, "
            f"got {rel.relation_type!r}"
        )
    if rel.source_id != SHWTP_F01_PIM_SOURCE:
        raise ShwtpProjectionError(
            f"F01 source endpoint must be {SHWTP_F01_PIM_SOURCE!r}, "
            f"got {rel.source_id!r}"
        )
    if rel.target_id != SHWTP_F01_PIM_TARGET:
        raise ShwtpProjectionError(
            f"F01 target endpoint must be {SHWTP_F01_PIM_TARGET!r}, "
            f"got {rel.target_id!r}"
        )
    if rel.evidence_status != SHWTP_F01_EVIDENCE_STATUS:
        raise ShwtpProjectionError(
            f"F01 evidence_status must be {SHWTP_F01_EVIDENCE_STATUS!r}, "
            f"got {rel.evidence_status!r}"
        )

    source_port = t106_out_port()
    target_port = t108_in_port()

    # Fail closed on direction/category/unit/descriptor compatibility.
    check_port_compatibility(source_port, target_port)

    binding = f01_binding()
    graph = CompositionGraph(
        workspace_id=SHWTP_WORKSPACE_ID,
        bindings=[binding],
        ports=[source_port, target_port],
    )

    record = ProjectionRecord(
        projection_id=SHWTP_F01_PROJECTION_ID,
        relation_id=SHWTP_F01_RELATION_ID,
        relation_type=SHWTP_F01_RELATION_TYPE,
        pim_source_endpoint=SHWTP_F01_PIM_SOURCE,
        pim_target_endpoint=SHWTP_F01_PIM_TARGET,
        evidence_status=SHWTP_F01_EVIDENCE_STATUS,
        vf_source_path=SHWTP_T106_SCOPE_PATH.as_string(),
        vf_target_path=SHWTP_T108_SCOPE_PATH.as_string(),
        source_port_ref=t106_out_port_ref().as_string(),
        target_port_ref=t108_in_port_ref().as_string(),
        source_direction=source_port.direction.value,
        target_direction=target_port.direction.value,
        category=source_port.category.value,
        unit=source_port.unit or "",
        descriptor=source_port.descriptor or "",
        authorization_scope=SHWTP_F01_AUTHORIZATION_SCOPE,
        disclaimer=SHWTP_F01_DISCLAIMER,
        pim_authority=SHWTP_PIM_AUTHORITY,
        pim_main_sha=SHWTP_PIM_MAIN_SHA,
    )

    return ShwtpF01Projection(
        record=record,
        ports=(source_port, target_port),
        binding=binding,
        graph=graph,
    )
