"""VF-vNEXT-G11 — SH-WTP structural Workspace construction (structural only).

Materializes the SH-WTP Workspace structural hierarchy from the accepted, frozen
G10 plan (``configs/vnext/shwtp/shwtp_readiness_scope.json``) using ONLY the
accepted generic G1 Workspace/Scope/Object foundation
(``virtual_factory.workspace``). No parallel SH-WTP structural framework is
introduced.

Frozen semantics preserved (Issue #56 / G10):

- PIM stays canonical/evidence authority; VF local StructuralPath/identity stays
  local. PIM canonical IDs are referenced (read-only metadata), never renamed
  into VF identity.
- Containment is a structural tree (exactly one containment parent per node
  except the Workspace root) and is NOT a connectivity/flow graph.
- G11 is structural construction ONLY: ``structural_construction =
  AUTHORIZED_IN_G11``. ``synthetic_reference_execution =
  PENDING_LATER_PIM_REVIEW`` and ``site_authorized_execution =
  NOT_AUTHORIZED`` remain unauthorized.
- ``vf_runtime_authorization = NOT_AUTHORIZED`` is preserved.
- T106/T108/T110 are ``executable_candidate`` classification only (the only
  ``ScopeMode.EXECUTABLE_CAPABLE`` scopes, capability not runtime); every other
  materialized node is ``ScopeMode.CONTAINER_ONLY``. No engine, bridge,
  coordinator participant, run-control participant, solver, behavior, or state
  advancement is created.
- No connectivity/composition graph edge is materialized in G11.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from virtual_factory.workspace import (
    ScopeMode,
    ScopeSpec,
    StructuralPath,
    Workspace,
    build_workspace,
)

SHWTP_WORKSPACE_ID = "shwtp"
SHWTP_PLANT_CANONICAL_ID = "PLANT-SHW"
SHWTP_RUNTIME_AUTHORIZATION = "NOT_AUTHORIZED"
SHWTP_STRUCTURAL_AUTHORIZED_IN_G11 = "AUTHORIZED_IN_G11"
SHWTP_SYNTHETIC_PENDING_LATER_PIM_REVIEW = "PENDING_LATER_PIM_REVIEW"
SHWTP_SITE_AUTHORIZED_EXECUTION = "NOT_AUTHORIZED"

# Executable candidates (classification only, first VF-readiness slice).
SHWTP_EXECUTABLE_CANDIDATE_CANONICAL_IDS = frozenset(
    {"UNIT-SHW-L1-T106", "UNIT-SHW-L1-T108", "UNIT-SHW-WASH-T110"}
)

DEFAULT_PLAN_PATH = (
    Path(__file__).resolve().parents[3]
    / "configs"
    / "vnext"
    / "shwtp"
    / "shwtp_readiness_scope.json"
)

# Containment layout keyed by PIM canonical id (parent -> children). The
# workspace root (None) contains every top-level Area plus the plant-level unit
# UNIT-SHW-DIST-P108. Containment follows the pinned PIM skeleton
# ``plant_wide_skeleton_ph03.yaml`` ``units_by_area`` / ``plant_level_units``:
# UNIT-SHW-WASH-T110 is homed under AREA-SHW-LINE1 for the slice scope; every
# other unit is homed under its area. This is PIM/G10 evidence, NOT invention.
_CONTAINMENT_BY_CANONICAL: dict[str | None, list[str]] = {
    None: [
        "AREA-SHW-RAW-WATER",
        "AREA-SHW-LINE1",
        "AREA-SHW-LINE2",
        "AREA-SHW-CHEMICAL",
        "AREA-SHW-SLUDGE",
        "AREA-SHW-ELECTRICAL",
        "AREA-SHW-AUTOMATION",
        "UNIT-SHW-DIST-P108",
    ],
    "AREA-SHW-RAW-WATER": ["UNIT-SHW-RAW-INTAKE", "UNIT-SHW-T100"],
    "AREA-SHW-LINE1": [
        "UNIT-SHW-L1-T101",
        "UNIT-SHW-L1-T102",
        "UNIT-SHW-L1-T103",
        "UNIT-SHW-L1-T104",
        "UNIT-SHW-L1-T105",
        "UNIT-SHW-L1-T106",
        "UNIT-SHW-L1-T107",
        "UNIT-SHW-L1-T108",
        "UNIT-SHW-L1-T109",
        "UNIT-SHW-WASH-T110",
    ],
    "AREA-SHW-LINE2": [
        "UNIT-SHW-L2-T101",
        "UNIT-SHW-L2-T105",
        "UNIT-SHW-L2-T106",
        "UNIT-SHW-L2-T108",
    ],
    "AREA-SHW-CHEMICAL": ["UNIT-SHW-CHEM-DOSING"],
    "AREA-SHW-SLUDGE": ["UNIT-SHW-SLUDGE-T201"],
    "AREA-SHW-ELECTRICAL": ["UNIT-SHW-ELEC-MCC"],
    "AREA-SHW-AUTOMATION": ["UNIT-SHW-AUTO-PLC"],
}


class ShwtpStructuralError(ValueError):
    """Raised when the SH-WTP structural materialization violates an invariant."""


def vf_local_id(canonical_id: str) -> str:
    """Deterministic VF-local scope id derived from a PIM canonical id.

    The VF local id is a lowercase alias (prefix stripped, ``-`` -> ``_``); it is
    NEVER equal to the PIM canonical id. The canonical id itself is preserved as
    read-only reference metadata on the node.
    """
    for prefix in ("AREA-SHW-", "UNIT-SHW-"):
        if canonical_id.startswith(prefix):
            tail = canonical_id[len(prefix) :]
            return tail.lower().replace("-", "_")
    raise ShwtpStructuralError(
        f"cannot derive a VF local scope id from canonical id {canonical_id!r}"
    )


@dataclass(frozen=True, slots=True)
class ShwtpNodeMeta:
    """Read-only G10-derived metadata for one materialized SH-WTP scope node.

    This is a reference relationship to the frozen G10 inventory / PIM canonical
    id, NOT an authority transfer and NOT a runtime capability.
    """

    path: StructuralPath
    scope_id: str
    role: str  # container_only | executable_candidate | object_only | reference_only
    fidelity_ceiling: str
    evidence_status: str
    confidence: str
    gaps: tuple[str, ...]
    inventory_id: str
    canonical_id: str
    pim_reference: str
    note: str
    runtime_authorization: str = SHWTP_RUNTIME_AUTHORIZATION

    @property
    def is_executable_candidate(self) -> bool:
        return self.role == "executable_candidate"

    @property
    def scope_path_string(self) -> str:
        return self.path.as_string()


@dataclass(frozen=True, slots=True)
class ShwtpPlantMeta:
    """Read-only G10-derived metadata for the SH-WTP Workspace (plant) root."""

    inventory_id: str
    canonical_id: str
    role: str
    fidelity_ceiling: str
    evidence_status: str
    confidence: str
    gaps: tuple[str, ...]
    pim_reference: str
    note: str
    runtime_authorization: str = SHWTP_RUNTIME_AUTHORIZATION


def _role_for(entry: dict) -> str:
    return entry["vf_scope_role"]


def _scope_mode_for(role: str) -> ScopeMode:
    if role == "executable_candidate":
        return ScopeMode.EXECUTABLE_CAPABLE
    return ScopeMode.CONTAINER_ONLY


def _load_plan(plan_path: Path) -> dict:
    if not plan_path.exists():
        raise ShwtpStructuralError(f"frozen G10 plan not found: {plan_path}")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if not isinstance(plan, dict) or "inventory" not in plan:
        raise ShwtpStructuralError(
            f"frozen G10 plan {plan_path} has no inventory"
        )
    return plan


def _inventory_by_canonical(plan: dict) -> dict[str, dict]:
    mapping: dict[str, dict] = {}
    for entry in plan["inventory"]:
        cid = entry.get("pim_canonical_id")
        if not cid:
            raise ShwtpStructuralError(f"inventory entry missing canonical id: {entry}")
        if cid in mapping:
            raise ShwtpStructuralError(f"duplicate canonical id in inventory: {cid}")
        mapping[cid] = entry
    return mapping


class ShwtpWorkspace:
    """Deterministic SH-WTP structural Workspace + read-only node metadata.

    ``workspace`` is the generic G1 :class:`Workspace`. ``meta_by_path`` maps
    every materialized scope StructuralPath to its G10-derived metadata.
    """

    __slots__ = ("_workspace", "_plan_path", "_meta_by_path", "_plant_meta")

    def __init__(
        self,
        workspace: Workspace,
        plan_path: str,
        meta_by_path: Mapping[StructuralPath, ShwtpNodeMeta],
        plant_meta: ShwtpPlantMeta,
    ) -> None:
        self._workspace = workspace
        self._plan_path = plan_path
        self._meta_by_path = dict(meta_by_path)
        self._plant_meta = plant_meta

    @property
    def workspace(self) -> Workspace:
        return self._workspace

    @property
    def workspace_id(self) -> str:
        return self._workspace.workspace_id

    @property
    def plan_path(self) -> str:
        return self._plan_path

    @property
    def plant_meta(self) -> ShwtpPlantMeta:
        return self._plant_meta

    @property
    def meta_by_path(self) -> Mapping[StructuralPath, ShwtpNodeMeta]:
        return self._meta_by_path

    @property
    def scope_count(self) -> int:
        return len(self._meta_by_path)

    def node_meta(self, path: StructuralPath) -> ShwtpNodeMeta | None:
        """Metadata for a scope node, or None when absent."""
        return self._meta_by_path.get(path)

    def iter_scope_metas(self):
        """Yield node metadata in deterministic pre-order (tree order)."""
        for scope in self._workspace.top_level_scopes:
            for nested in scope.iter_scopes():
                meta = self._meta_by_path.get(nested.path)
                if meta is not None:
                    yield meta

    def serialize(self) -> dict:
        """Deterministic machine-readable structural inspection."""
        nodes: list[dict] = []
        for meta in self.iter_scope_metas():
            nodes.append(
                {
                    "path": meta.scope_path_string,
                    "scope_id": meta.scope_id,
                    "mode": _scope_mode_for(meta.role).value,
                    "role": meta.role,
                    "fidelity_ceiling": meta.fidelity_ceiling,
                    "evidence_status": meta.evidence_status,
                    "confidence": meta.confidence,
                    "gaps": sorted(meta.gaps),
                    "inventory_id": meta.inventory_id,
                    "canonical_id": meta.canonical_id,
                    "pim_reference": meta.pim_reference,
                    "note": meta.note,
                    "runtime_authorization": meta.runtime_authorization,
                    "children": [
                        c.scope_id
                        for c in self._workspace.find_scope_by_path(meta.path).children  # type: ignore[union-attr]
                    ],
                }
            )
        return {
            "schema": "vf.vnext.g11.shwtp.structural.v1",
            "workspace_id": self._workspace.workspace_id,
            "display_name": self._workspace.display_name,
            "plan_path": self._plan_path,
            "plant": {
                "inventory_id": self._plant_meta.inventory_id,
                "canonical_id": self._plant_meta.canonical_id,
                "role": self._plant_meta.role,
                "fidelity_ceiling": self._plant_meta.fidelity_ceiling,
                "evidence_status": self._plant_meta.evidence_status,
                "confidence": self._plant_meta.confidence,
                "gaps": sorted(self._plant_meta.gaps),
                "pim_reference": self._plant_meta.pim_reference,
                "runtime_authorization": self._plant_meta.runtime_authorization,
            },
            "authorization": {
                "vf_runtime_authorization": SHWTP_RUNTIME_AUTHORIZATION,
                "structural_construction": SHWTP_STRUCTURAL_AUTHORIZED_IN_G11,
                "synthetic_reference_execution": SHWTP_SYNTHETIC_PENDING_LATER_PIM_REVIEW,
                "site_authorized_execution": SHWTP_SITE_AUTHORIZED_EXECUTION,
            },
            "node_count": len(nodes),
            "nodes": nodes,
        }


def build_shwtp_workspace(
    plan_path: str | Path = DEFAULT_PLAN_PATH,
    *,
    display_name: str | None = "SH-WTP Water Treatment Plant",
    description: str | None = None,
) -> ShwtpWorkspace:
    """Deterministically materialize the SH-WTP structural Workspace tree.

    Reads the frozen G10 plan, validates that every canonical id declared in the
    containment layout exists in the G10 inventory and that every inventory
    entry (except the PLANT root) materializes exactly one scope, then builds the
    generic G1 Workspace. Fail-closed on any gap.
    """
    path = Path(plan_path)
    plan = _load_plan(path)
    inventory_by_cid = _inventory_by_canonical(plan)

    declared = {
        cid
        for children in _CONTAINMENT_BY_CANONICAL.values()
        for cid in children
    }
    if SHWTP_PLANT_CANONICAL_ID not in inventory_by_cid:
        raise ShwtpStructuralError(
            f"frozen G10 plan has no plant root {SHWTP_PLANT_CANONICAL_ID!r}"
        )
    inventory_cids = set(inventory_by_cid) - {SHWTP_PLANT_CANONICAL_ID}
    if declared != inventory_cids:
        missing = sorted(inventory_cids - declared)
        extra = sorted(declared - inventory_cids)
        raise ShwtpStructuralError(
            f"containment layout does not match G10 inventory exactly "
            f"(unrepresented inventory entries={missing}, "
            f"undeclared canonical ids={extra})"
        )

    for parent_cid, children in _CONTAINMENT_BY_CANONICAL.items():
        for cid in children:
            entry = inventory_by_cid.get(cid)
            if entry is None:
                raise ShwtpStructuralError(
                    f"canonical id {cid!r} (parent {parent_cid!r}) not in G10 inventory"
                )

    specs: list[ScopeSpec] = []
    # top-level scopes (under the workspace root)
    for cid in _CONTAINMENT_BY_CANONICAL[None]:
        role = _role_for(inventory_by_cid[cid])
        specs.append(
            ScopeSpec(
                scope_id=vf_local_id(cid),
                mode=_scope_mode_for(role),
                parent_path=None,
            )
        )
    # unit scopes nested under their Area
    for parent_cid, children in _CONTAINMENT_BY_CANONICAL.items():
        if parent_cid is None:
            continue
        parent_local = vf_local_id(parent_cid)
        parent_path = StructuralPath((SHWTP_WORKSPACE_ID, parent_local))
        for cid in children:
            role = _role_for(inventory_by_cid[cid])
            specs.append(
                ScopeSpec(
                    scope_id=vf_local_id(cid),
                    mode=_scope_mode_for(role),
                    parent_path=parent_path,
                )
            )

    workspace = build_workspace(
        SHWTP_WORKSPACE_ID,
        specs,
        display_name=display_name,
        description=description
        or "SH-WTP structural Workspace (Song Hong Water Treatment Plant) "
        "materialized from the frozen G10 readiness/scope plan. Structural "
        "construction only: containment tree; PIM canonical ids are read-only "
        "references; NOT_AUTHORIZED; no connectivity graph and no runtime.",
    )

    meta_by_path: dict[StructuralPath, ShwtpNodeMeta] = {}
    for scope in workspace.top_level_scopes:
        for nested in scope.iter_scopes():
            cid = _canonical_id_for_local(nested.scope_id)
            entry = inventory_by_cid[cid]
            meta_by_path[nested.path] = ShwtpNodeMeta(
                path=nested.path,
                scope_id=nested.scope_id,
                role=_role_for(entry),
                fidelity_ceiling=entry["fidelity_ceiling"],
                evidence_status=entry["evidence"]["status"],
                confidence=entry["evidence"]["confidence"],
                gaps=tuple(sorted(entry.get("gaps", []))),
                inventory_id=entry["id"],
                canonical_id=cid,
                pim_reference=entry.get("pim_reference", ""),
                note=entry.get("note", ""),
            )

    plant_entry = inventory_by_cid[SHWTP_PLANT_CANONICAL_ID]
    plant_meta = ShwtpPlantMeta(
        inventory_id=plant_entry["id"],
        canonical_id=SHWTP_PLANT_CANONICAL_ID,
        role=_role_for(plant_entry),
        fidelity_ceiling=plant_entry["fidelity_ceiling"],
        evidence_status=plant_entry["evidence"]["status"],
        confidence=plant_entry["evidence"]["confidence"],
        gaps=tuple(sorted(plant_entry.get("gaps", []))),
        pim_reference=plant_entry.get("pim_reference", ""),
        note=plant_entry.get("note", ""),
    )

    return ShwtpWorkspace(workspace, str(path), meta_by_path, plant_meta)


def _canonical_id_for_local(scope_id: str) -> str:
    """Invert the deterministic local-id derivation to recover the canonical id.

    Only used to re-link a built scope back to its G10 inventory entry; the
    canonical id is still stored as reference metadata and never used as VF
    identity.
    """
    for cid, local in _LOCAL_ID_BY_CANONICAL.items():
        if local == scope_id:
            return cid
    raise ShwtpStructuralError(f"no canonical id maps to local scope id {scope_id!r}")


_LOCAL_ID_BY_CANONICAL: dict[str, str] = {
    cid: vf_local_id(cid)
    for children in _CONTAINMENT_BY_CANONICAL.values()
    for cid in children
}
