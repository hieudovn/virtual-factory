"""VF-SHW-X1 — SH-WTP whole-plant CONTRACT LAYER (loader + fail-closed validator).

This module materialises the frozen X0 design into a machine-readable contract
layer and validates it. It is **contract-only**: it constructs NO runtime, NO
session, NO bridge, NO engine and NO controller — it reads JSON contracts,
cross-checks them against the accepted PIM-derived inventory and raises
``ShwtpContractError`` on any inconsistency (fail-closed, never defaulted).

Artefacts (configs/vnext/shwtp/):
  * ``shwtp_whole_plant_graph_v1.json``      whole-plant process graph (nodes/edges/assumptions)
  * ``shwtp_process_contracts_v1.json``      per-scope process + fidelity contracts
  * ``shwtp_control_contracts_v1.json``      C0/C1/C2 control contracts
  * ``shwtp_x2_admission_manifest_v1.json``  the authoritative X2 admission boundary

Authority: PIM owns canonical semantics; VF references them read-only. New PIM
canonical ids are FORBIDDEN here; VF-local identity uses the reserved
``vf-shw-`` namespace. Runtime authorization remains NOT_AUTHORIZED.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

_CONFIG_DIR = Path(__file__).resolve().parents[3] / "configs" / "vnext" / "shwtp"

DEFAULT_GRAPH_PATH = _CONFIG_DIR / "shwtp_whole_plant_graph_v1.json"
DEFAULT_PROCESS_CONTRACTS_PATH = _CONFIG_DIR / "shwtp_process_contracts_v1.json"
DEFAULT_CONTROL_CONTRACTS_PATH = _CONFIG_DIR / "shwtp_control_contracts_v1.json"
DEFAULT_X2_ADMISSION_PATH = _CONFIG_DIR / "shwtp_x2_admission_manifest_v1.json"
DEFAULT_INVENTORY_PATH = _CONFIG_DIR / "shwtp_readiness_scope.json"

GRAPH_SCHEMA = "vf.vnext.x1.shwtp.whole_plant_graph.v1"
PROCESS_SCHEMA = "vf.vnext.x1.shwtp.process_contracts.v1"
CONTROL_SCHEMA = "vf.vnext.x1.shwtp.control_contracts.v1"
ADMISSION_SCHEMA = "vf.vnext.x1.shwtp.x2_admission_manifest.v1"

EDGE_CATEGORIES = ("pim_known", "vf_scenario_assumption", "reference_only")
#: provenance vocabulary for VF-assumed graph edges (mirrors the scenario overlay)
ASSUMED_SOURCE_KIND = "vf_scenario_assumption"
ASSUMED_STATUS = "assumed/synthetic"
CONTROL_CLASSES = ("C0", "C1", "C2")
IMPLEMENTATION_GATES = ("X2", "X3", "X4", "n/a")
FIDELITY_CLASSES = ("reference_only", "logical_only", "synthetic_reference", "first_order")

VF_LOCAL_PREFIX = "vf-shw-"
#: A full PIM canonical id shape (a bare prefix such as ``AREA-SHW`` is not an id).
PIM_ID_PATTERN = re.compile(r"\b(?:PLANT|AREA|UNIT|REL|PROC|GAP)-SHW(?:-[A-Z0-9]+)+\b")

AUTHORITY_MARKERS = {
    "vf_runtime_authorization": "NOT_AUTHORIZED",
    "site_authorized_execution": "NOT_AUTHORIZED",
    "whole_plant_runtime": "NOT_AUTHORIZED / NOT_IMPLEMENTED",
    "site_truth": False,
}

REQUIRED_PROCESS_FIELDS = (
    "scope_id",
    "process_role",
    "fidelity_class",
    "inputs",
    "outputs",
    "state",
    "parameters",
    "constraints",
    "conservation",
    "update_rule_family",
    "init_reset",
    "invalid_state",
    "site_truth",
)

REQUIRED_CONTROL_FIELDS = (
    "controller_id",
    "owning_scope",
    "controller_type",
    "control_class",
    "implementation_gate",
    "active_in_x2",
    "auto_manual",
    "permissives",
    "interlocks",
    "alarms",
    "reset_init",
    "anti_windup",
    "synthetic_tuning_status",
    "provenance",
    "evidence_status",
)

PI_PID_TYPES = ("PI", "PID")
PI_PID_GATES = ("X3", "X4")

#: X1-C01: how an X2 process input is produced inside X2.
X2_PRODUCER_CLASSES = (
    "process_node",
    "x2_active_controller",
    "x2_fallback_default",
    "scenario",
    "boundary",
)
#: X1-C01: an explicit X2 fallback/default must declare one of these modes.
X2_FALLBACK_MODES = (
    "fixed_speed_synthetic_reference",
    "fixed_position_synthetic_reference",
    "discrete_open_closed_position",
    "scenario_reference",
    "rule_based_synthetic_reference",
)
X2_FALLBACK_REQUIRED_KEYS = ("mode", "value", "rule", "provenance")

#: X1-C01: level actions must name the direction they protect.
LEVEL_ACTION_DIRECTIONS = {
    "downstream": ("downstream", "outlet", "withdrawal"),
    "upstream": ("upstream", "intake", "inflow", "refill"),
}
LEVEL_ACTION_REQUIRED_KEYS = ("condition", "action", "target_scope", "target_signal")
ACTUATOR_OWNERSHIP_REQUIRED_KEYS = ("upstream_actuator", "downstream_actuator")
ACTUATOR_REQUIRED_KEYS = ("scope", "signal", "direction")
CONTROL_ID_PREFIX = VF_LOCAL_PREFIX + "ctrl-"
NODE_ID_PREFIX = VF_LOCAL_PREFIX + "node-"
NON_NODE_INPUT_SOURCES = ("scenario",)


class ShwtpContractError(ValueError):
    """A SH-WTP whole-plant contract is missing, malformed or inconsistent."""


# ── loading helpers ────────────────────────────────────────────────────────

def _load_json(path: Path, label: str) -> dict:
    if not path.exists():
        raise ShwtpContractError(f"{label} contract not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise ShwtpContractError(f"{label} contract is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ShwtpContractError(f"{label} contract must be a JSON object")
    return payload


def _require(payload: Mapping[str, Any], key: str, label: str) -> Any:
    if key not in payload:
        raise ShwtpContractError(f"{label} contract is missing required key {key!r}")
    return payload[key]


def _check_authority(payload: Mapping[str, Any], label: str) -> None:
    authority = payload.get("authority")
    if not isinstance(authority, dict):
        raise ShwtpContractError(f"{label} contract is missing an authority block")
    for key, expected in AUTHORITY_MARKERS.items():
        if key not in authority:
            raise ShwtpContractError(f"{label} authority is missing {key!r}")
        if authority[key] != expected:
            raise ShwtpContractError(
                f"{label} authority {key!r} must be {expected!r}, got {authority[key]!r}"
            )


def _check_schema(payload: Mapping[str, Any], expected: str, label: str) -> None:
    schema = _require(payload, "schema", label)
    if schema != expected:
        raise ShwtpContractError(f"{label} schema must be {expected!r}, got {schema!r}")
    if not payload.get("version"):
        raise ShwtpContractError(f"{label} contract must carry a version")
    if payload.get("gate") != "VF-SHW-X1":
        raise ShwtpContractError(f"{label} contract gate must be 'VF-SHW-X1'")


# ── dataclasses (frozen, sorted, contract-only) ────────────────────────────

@dataclass(frozen=True)
class GraphNode:
    node_id: str
    canonical_id: str | None
    vf_path: str | None
    area_canonical_id: str | None
    process_role: str
    kind: str
    evidence_status: str | None
    fidelity_ceiling: str | None
    proposed_vf_fidelity: str | None
    x2_eligible: bool
    canonical_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class GraphEdge:
    edge_id: str
    source: str
    target: str
    flow: str
    category: str
    pim_relation_id: str | None
    evidence_status: str | None
    assumption_id: str | None
    reversible: bool | None
    x2_eligible: bool


@dataclass(frozen=True)
class ScopeContract:
    scope_id: str
    canonical_id: str | None
    process_role: str
    fidelity_class: str
    pim_ceiling: str | None
    x2_admitted: bool
    control_level: str
    control_ids: tuple[str, ...]
    update_rule_family: str
    conservation_kind: str
    site_truth: bool
    raw: Mapping[str, Any]


@dataclass(frozen=True)
class ControlContract:
    controller_id: str
    owning_scope: str
    controller_type: str
    control_class: str
    implementation_gate: str
    active_in_x2: bool
    anti_windup: str
    synthetic_tuning_status: str
    evidence_status: str
    raw: Mapping[str, Any]


@dataclass(frozen=True)
class X2Admission:
    executable_scope_ids: tuple[str, ...]
    reference_only_scope_ids: tuple[str, ...]
    c1_active_ids: tuple[str, ...]
    c2_deferred: tuple[tuple[str, str], ...]
    assumed_edges_used: tuple[str, ...]
    assumed_edges_excluded: tuple[str, ...]
    pim_known_edges_used: tuple[str, ...]
    invariants: tuple[str, ...]
    not_authorized: tuple[str, ...]


@dataclass(frozen=True)
class WholePlantContracts:
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]
    assumption_ids: tuple[str, ...]
    scopes: tuple[ScopeContract, ...]
    reference_only_scopes: tuple[str, ...]
    controls: tuple[ControlContract, ...]
    admission: X2Admission
    signature: str
    source_paths: Mapping[str, str]


# ── canonical identity checks ──────────────────────────────────────────────

def accepted_canonical_ids(inventory_path: Path | None = None) -> frozenset[str]:
    """The accepted PIM-derived canonical identity set (read-only).

    Sources: the frozen readiness inventory (ids + pim canonical ids), the
    structural containment keys and the selected PIM relations. Nothing is
    constructed; only frozen data is read.
    """
    path = Path(inventory_path) if inventory_path is not None else DEFAULT_INVENTORY_PATH
    payload = _load_json(path, "readiness inventory")
    ids: set[str] = set()

    def _collect(obj: Any) -> None:
        if isinstance(obj, dict):
            for value in obj.values():
                _collect(value)
        elif isinstance(obj, list):
            for item in obj:
                _collect(item)
        elif isinstance(obj, str):
            ids.update(PIM_ID_PATTERN.findall(obj))

    _collect(payload)

    structural = _load_structural_containment()
    ids.update(structural)
    ids.update(_selected_relation_ids_and_endpoints())
    ids.add("PLANT-SHW")
    return frozenset(ids)


def _load_structural_containment() -> frozenset[str]:
    from virtual_factory.shwtp import structural

    ids: set[str] = {structural.SHWTP_PLANT_CANONICAL_ID}
    for parent, children in structural._CONTAINMENT_BY_CANONICAL.items():  # noqa: SLF001
        ids.add(parent)
        ids.update(children)
    ids.update(structural.SHWTP_EXECUTABLE_CANDIDATE_CANONICAL_IDS)
    return frozenset(ids)


def _selected_relation_ids_and_endpoints() -> frozenset[str]:
    from virtual_factory.shwtp import connectivity

    ids: set[str] = set()
    for relation in connectivity.SHWTP_SELECTED_RELATIONSHIPS:
        ids.add(relation.relationship_id)
        ids.add(relation.source_id)
        ids.add(relation.target_id)
    return frozenset(ids)


def referenced_pim_ids(payload: Any) -> set[str]:
    """Every PIM-shaped id appearing in a contract payload (any nesting)."""
    found: set[str] = set()
    if isinstance(payload, dict):
        for value in payload.values():
            found |= referenced_pim_ids(value)
    elif isinstance(payload, list):
        for item in payload:
            found |= referenced_pim_ids(item)
    elif isinstance(payload, str):
        found |= set(PIM_ID_PATTERN.findall(payload))
    return found


def referenced_vf_local_ids(payload: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(payload, dict):
        for value in payload.values():
            found |= referenced_vf_local_ids(value)
    elif isinstance(payload, list):
        for item in payload:
            found |= referenced_vf_local_ids(item)
    elif isinstance(payload, str):
        found |= set(re.findall(r"\bvf-shw-[a-z0-9-]+\b", payload))
    return found


# ── graph validation ───────────────────────────────────────────────────────

def _validate_graph(payload: dict) -> tuple[tuple[GraphNode, ...], tuple[GraphEdge, ...], tuple[str, ...]]:
    nodes_raw = _require(payload, "nodes", "graph")
    edges_raw = _require(payload, "edges", "graph")
    registry = _require(payload, "assumption_registry", "graph")
    if not isinstance(nodes_raw, list) or not nodes_raw:
        raise ShwtpContractError("graph must declare a non-empty node list")
    if not isinstance(edges_raw, list) or not edges_raw:
        raise ShwtpContractError("graph must declare a non-empty edge list")

    nodes: list[GraphNode] = []
    seen_nodes: set[str] = set()
    for node in nodes_raw:
        node_id = _require(node, "node_id", "graph node")
        if node_id in seen_nodes:
            raise ShwtpContractError(f"duplicate graph node id {node_id!r}")
        seen_nodes.add(node_id)
        if not str(node_id).startswith(VF_LOCAL_PREFIX):
            raise ShwtpContractError(
                f"graph node id {node_id!r} must use the reserved {VF_LOCAL_PREFIX!r} namespace"
            )
        nodes.append(
            GraphNode(
                node_id=node_id,
                canonical_id=node.get("canonical_id"),
                vf_path=node.get("vf_path"),
                area_canonical_id=node.get("area_canonical_id"),
                process_role=_require(node, "process_role", f"node {node_id}"),
                kind=node.get("kind", "process"),
                evidence_status=node.get("evidence_status"),
                fidelity_ceiling=node.get("fidelity_ceiling"),
                proposed_vf_fidelity=node.get("proposed_vf_fidelity"),
                x2_eligible=bool(node.get("x2_eligible")),
                canonical_refs=tuple(node.get("canonical_refs", ())),
            )
        )
    nodes_sorted = tuple(sorted(nodes, key=lambda n: n.node_id))
    node_ids = {node.node_id for node in nodes_sorted}

    edges: list[GraphEdge] = []
    seen_edges: set[str] = set()
    logic_keys: dict[tuple[str, str, str], str] = {}
    for edge in edges_raw:
        edge_id = _require(edge, "edge_id", "graph edge")
        if edge_id in seen_edges:
            raise ShwtpContractError(f"duplicate graph edge id {edge_id!r}")
        seen_edges.add(edge_id)
        source = _require(edge, "from", f"edge {edge_id}")
        target = _require(edge, "to", f"edge {edge_id}")
        if source not in node_ids or target not in node_ids:
            raise ShwtpContractError(f"edge {edge_id!r} references an unknown node")
        category = _require(edge, "category", f"edge {edge_id}")
        if category not in EDGE_CATEGORIES:
            raise ShwtpContractError(
                f"edge {edge_id!r} category {category!r} must be one of {EDGE_CATEGORIES}"
            )
        flow = edge.get("flow", "water")
        logic_key = (source, target, flow)
        if logic_key in logic_keys:
            raise ShwtpContractError(
                f"edge {edge_id!r} duplicates {logic_keys[logic_key]!r} under the same logical "
                f"identity; an edge must not be simultaneously PIM-known and VF-assumed"
            )
        logic_keys[logic_key] = edge_id

        assumption_id: str | None = None
        reversible: bool | None = None
        if category == "pim_known":
            if not edge.get("pim_relation_id"):
                raise ShwtpContractError(f"pim_known edge {edge_id!r} must cite a pim_relation_id")
            if edge.get("assumption") is not None:
                raise ShwtpContractError(f"pim_known edge {edge_id!r} must not carry an assumption")
        elif category == "vf_scenario_assumption":
            assumption = edge.get("assumption")
            if not isinstance(assumption, dict):
                raise ShwtpContractError(
                    f"assumed edge {edge_id!r} must carry explicit assumption provenance"
                )
            for key in ("assumption_id", "source_kind", "status", "reversible", "rationale"):
                if key not in assumption:
                    raise ShwtpContractError(
                        f"assumed edge {edge_id!r} assumption is missing {key!r}"
                    )
            if assumption["source_kind"] != ASSUMED_SOURCE_KIND:
                raise ShwtpContractError(
                    f"assumed edge {edge_id!r} source_kind must be {ASSUMED_SOURCE_KIND!r}"
                )
            if assumption["status"] != ASSUMED_STATUS:
                raise ShwtpContractError(
                    f"assumed edge {edge_id!r} status must be {ASSUMED_STATUS!r}"
                )
            if assumption["reversible"] is not True:
                raise ShwtpContractError(f"assumed edge {edge_id!r} must be reversible")
            assumption_id = assumption["assumption_id"]
            reversible = True
        else:  # reference_only
            if edge.get("assumption") is not None:
                raise ShwtpContractError(
                    f"reference_only edge {edge_id!r} must not carry an assumption"
                )
            if edge.get("x2_eligible"):
                raise ShwtpContractError(
                    f"reference_only edge {edge_id!r} must not be X2-eligible"
                )

        edges.append(
            GraphEdge(
                edge_id=edge_id,
                source=source,
                target=target,
                flow=flow,
                category=category,
                pim_relation_id=edge.get("pim_relation_id"),
                evidence_status=edge.get("evidence_status"),
                assumption_id=assumption_id,
                reversible=reversible,
                x2_eligible=bool(edge.get("x2_eligible")),
            )
        )
    edges_sorted = tuple(sorted(edges, key=lambda e: e.edge_id))

    if not isinstance(registry, list):
        raise ShwtpContractError("assumption_registry must be a list")
    registry_ids = tuple(sorted(str(entry["assumption_id"]) for entry in registry))
    edge_assumption_ids = tuple(sorted(e.assumption_id for e in edges_sorted if e.assumption_id))
    if registry_ids != edge_assumption_ids:
        raise ShwtpContractError(
            "assumption_registry must list exactly the assumption ids used by assumed edges"
        )
    if len(set(registry_ids)) != len(registry_ids):
        raise ShwtpContractError("assumption_registry contains duplicate assumption ids")
    return nodes_sorted, edges_sorted, registry_ids


# ── process / control / admission validation ───────────────────────────────

def _validate_scopes(payload: dict) -> tuple[tuple[ScopeContract, ...], tuple[str, ...]]:
    contracts_raw = _require(payload, "contracts", "process contracts")
    if not isinstance(contracts_raw, list) or not contracts_raw:
        raise ShwtpContractError("process contracts must declare a non-empty contract list")

    scopes: list[ScopeContract] = []
    for entry in contracts_raw:
        scope_id = _require(entry, "scope_id", "process contract")
        for field in REQUIRED_PROCESS_FIELDS:
            if field not in entry:
                raise ShwtpContractError(f"process contract {scope_id!r} is missing {field!r}")
        if entry["site_truth"] is not False:
            raise ShwtpContractError(f"process contract {scope_id!r} must set site_truth=false")
        fidelity = entry["fidelity_class"]
        if fidelity not in FIDELITY_CLASSES:
            raise ShwtpContractError(
                f"process contract {scope_id!r} fidelity_class {fidelity!r} is not in the frozen vocabulary"
            )
        conservation = entry["conservation"]
        if not isinstance(conservation, dict) or not conservation.get("kind"):
            raise ShwtpContractError(
                f"process contract {scope_id!r} must declare a conservation/balance kind"
            )
        invalid = entry["invalid_state"]
        if not isinstance(invalid, dict) or invalid.get("fail_closed") is not True:
            raise ShwtpContractError(
                f"process contract {scope_id!r} must define fail-closed invalid-state behaviour"
            )
        for field in ("inputs", "outputs", "state", "parameters", "constraints"):
            if not isinstance(entry[field], list):
                raise ShwtpContractError(
                    f"process contract {scope_id!r} field {field!r} must be a list"
                )
        scopes.append(
            ScopeContract(
                scope_id=scope_id,
                canonical_id=entry.get("canonical_id"),
                process_role=entry["process_role"],
                fidelity_class=fidelity,
                pim_ceiling=entry.get("pim_ceiling"),
                x2_admitted=bool(entry.get("x2_admitted")),
                control_level=entry.get("control_level", "C0"),
                control_ids=tuple(entry.get("control_ids", ())),
                update_rule_family=entry["update_rule_family"],
                conservation_kind=conservation["kind"],
                site_truth=False,
                raw=entry,
            )
        )

    reference_only_raw = payload.get("reference_only_scopes", [])
    if not isinstance(reference_only_raw, list):
        raise ShwtpContractError("reference_only_scopes must be a list")
    reference_only = tuple(sorted(str(entry["scope_id"]) for entry in reference_only_raw))
    admitted = {scope.scope_id for scope in scopes if scope.x2_admitted}
    overlap = admitted & set(reference_only)
    if overlap:
        raise ShwtpContractError(
            f"scope(s) {sorted(overlap)} are both X2-admitted and reference-only"
        )
    if len({scope.scope_id for scope in scopes}) != len(scopes):
        raise ShwtpContractError("process contracts contain duplicate scope ids")
    return tuple(sorted(scopes, key=lambda s: s.scope_id)), reference_only


def _validate_controls(payload: dict) -> tuple[ControlContract, ...]:
    controls_raw = _require(payload, "controls", "control contracts")
    if not isinstance(controls_raw, list) or not controls_raw:
        raise ShwtpContractError("control contracts must declare a non-empty control list")

    controls: list[ControlContract] = []
    for entry in controls_raw:
        controller_id = _require(entry, "controller_id", "control contract")
        for field in REQUIRED_CONTROL_FIELDS:
            if field not in entry:
                raise ShwtpContractError(f"control contract {controller_id!r} is missing {field!r}")
        control_class = entry["control_class"]
        if control_class not in CONTROL_CLASSES:
            raise ShwtpContractError(
                f"control contract {controller_id!r} class {control_class!r} must be one of {CONTROL_CLASSES}"
            )
        gate = entry["implementation_gate"]
        if gate not in IMPLEMENTATION_GATES:
            raise ShwtpContractError(
                f"control contract {controller_id!r} implementation_gate {gate!r} is invalid"
            )
        active = bool(entry["active_in_x2"])
        if active and control_class == "C2":
            raise ShwtpContractError(
                f"C2 control {controller_id!r} must not be active in X2 (dynamic PI/PID is X3/X4)"
            )
        if active and gate != "X2":
            raise ShwtpContractError(
                f"control {controller_id!r} is active in X2 but its gate is {gate!r}"
            )
        if not active and gate == "X2" and control_class != "C0":
            raise ShwtpContractError(
                f"control {controller_id!r} has gate X2 but is not active in X2"
            )
        if entry["controller_type"] in PI_PID_TYPES:
            if control_class != "C2":
                raise ShwtpContractError(
                    f"PI/PID control {controller_id!r} must be class C2"
                )
            if entry["anti_windup"] == "n/a":
                raise ShwtpContractError(
                    f"PI/PID control {controller_id!r} must declare an anti-windup strategy"
                )
            if not entry.get("pv") or not entry.get("mv"):
                raise ShwtpContractError(f"PI/PID control {controller_id!r} must declare PV and MV")
        if not entry["synthetic_tuning_status"]:
            raise ShwtpContractError(
                f"control {controller_id!r} must declare its synthetic tuning status"
            )
        controls.append(
            ControlContract(
                controller_id=controller_id,
                owning_scope=entry["owning_scope"],
                controller_type=entry["controller_type"],
                control_class=control_class,
                implementation_gate=gate,
                active_in_x2=active,
                anti_windup=entry["anti_windup"],
                synthetic_tuning_status=entry["synthetic_tuning_status"],
                evidence_status=entry["evidence_status"],
                raw=entry,
            )
        )
    ids = [control.controller_id for control in controls]
    if len(set(ids)) != len(ids):
        raise ShwtpContractError("control contracts contain duplicate controller ids")
    for control in controls:
        if not control.controller_id.startswith(VF_LOCAL_PREFIX):
            raise ShwtpContractError(
                f"controller id {control.controller_id!r} must use the {VF_LOCAL_PREFIX!r} namespace"
            )
    return tuple(sorted(controls, key=lambda c: c.controller_id))


# ── X1-C01: X2 input resolution (no C2 dependency) ────────────────────────

def _water_adjacency(edges: tuple[GraphEdge, ...]) -> dict[str, set[str]]:
    """Directed water-flow adjacency over non-reference graph edges."""
    adjacency: dict[str, set[str]] = {}
    for edge in edges:
        if edge.category == "reference_only" or edge.flow != "water":
            continue
        adjacency.setdefault(edge.source, set()).add(edge.target)
        adjacency.setdefault(edge.target, set())
    return adjacency


def _reaches(adjacency: Mapping[str, set[str]], start: str, target: str, limit: int = 64) -> bool:
    if start == target:
        return False
    seen = {start}
    queue = [start]
    while queue and len(seen) <= limit:
        node = queue.pop(0)
        for nxt in sorted(adjacency.get(node, ())):
            if nxt == target:
                return True
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return False


def _resolve_x2_input(scope: ScopeContract, entry: Mapping[str, Any], nodes_by_id, controls_by_id) -> dict:
    """Resolve one input of an X2-admitted scope to its X2 producer (fail-closed)."""
    signal = entry.get("signal")
    if not signal:
        raise ShwtpContractError(
            f"process contract {scope.scope_id!r} declares an input without a signal name"
        )
    source = entry.get("source")
    declared = entry.get("x2_producer_class")
    if declared is not None and declared not in X2_PRODUCER_CLASSES:
        raise ShwtpContractError(
            f"process contract {scope.scope_id!r} input {signal!r} declares x2_producer_class "
            f"{declared!r} which is not in {X2_PRODUCER_CLASSES}"
        )

    if isinstance(source, str) and source.startswith(CONTROL_ID_PREFIX):
        control = controls_by_id.get(source)
        if control is None:
            raise ShwtpContractError(
                f"process contract {scope.scope_id!r} input {signal!r} references unknown controller {source!r}"
            )
        if control.control_class == "C2":
            fallback = entry.get("x2_fallback")
            if declared != "x2_fallback_default" or not isinstance(fallback, Mapping):
                raise ShwtpContractError(
                    f"X2-admitted scope {scope.scope_id!r} input {signal!r} is sourced from the C2 "
                    f"controller {source!r} without an explicit X2 fallback/default; X2 must not "
                    f"require a C2 controller output"
                )
            for key in X2_FALLBACK_REQUIRED_KEYS:
                if key not in fallback:
                    raise ShwtpContractError(
                        f"X2 fallback for {scope.scope_id!r} input {signal!r} is missing {key!r}"
                    )
            if fallback["mode"] not in X2_FALLBACK_MODES:
                raise ShwtpContractError(
                    f"X2 fallback mode {fallback['mode']!r} for {scope.scope_id!r} input {signal!r} "
                    f"must be one of {X2_FALLBACK_MODES}"
                )
            if fallback["value"] is None or not str(fallback.get("rule", "")).strip():
                raise ShwtpContractError(
                    f"X2 fallback for {scope.scope_id!r} input {signal!r} must declare a deterministic "
                    f"value and rule"
                )
            if not str(fallback["provenance"]).startswith("synthetic_reference"):
                raise ShwtpContractError(
                    f"X2 fallback for {scope.scope_id!r} input {signal!r} must be labelled synthetic_reference"
                )
            producer_class = "x2_fallback_default"
        else:
            if not (control.active_in_x2 and control.implementation_gate == "X2"):
                raise ShwtpContractError(
                    f"X2-admitted scope {scope.scope_id!r} input {signal!r} is sourced from controller "
                    f"{source!r} which is not X2-active (class {control.control_class}, gate "
                    f"{control.implementation_gate!r}, active_in_x2={control.active_in_x2}) and declares no "
                    f"explicit X2 fallback/default"
                )
            producer_class = "x2_active_controller"
    elif isinstance(source, str) and source.startswith(NODE_ID_PREFIX):
        node = nodes_by_id.get(source)
        if node is None:
            raise ShwtpContractError(
                f"process contract {scope.scope_id!r} input {signal!r} references unknown graph node {source!r}"
            )
        if not node.x2_eligible:
            raise ShwtpContractError(
                f"process contract {scope.scope_id!r} input {signal!r} is sourced from graph node {source!r} "
                f"which is not X2-eligible"
            )
        producer_class = "process_node"
    elif source in NON_NODE_INPUT_SOURCES:
        producer_class = "scenario"
    else:
        raise ShwtpContractError(
            f"X2-admitted scope {scope.scope_id!r} input {signal!r} has the unresolved producer {source!r}; "
            f"declare a process node, an X2-active C1 controller or an explicit x2_fallback"
        )

    if declared is not None and declared != producer_class:
        raise ShwtpContractError(
            f"process contract {scope.scope_id!r} input {signal!r} declares x2_producer_class {declared!r} "
            f"but resolves as {producer_class!r}"
        )

    deferred = entry.get("deferred_modulator")
    if deferred is not None:
        if not isinstance(deferred, Mapping):
            raise ShwtpContractError(
                f"process contract {scope.scope_id!r} input {signal!r} deferred_modulator must be a mapping"
            )
        deferred_control = controls_by_id.get(deferred.get("controller_id"))
        if deferred_control is None:
            raise ShwtpContractError(
                f"process contract {scope.scope_id!r} input {signal!r} names an unknown deferred modulator "
                f"{deferred.get('controller_id')!r}"
            )
        if deferred_control.control_class != "C2" or deferred_control.implementation_gate not in PI_PID_GATES:
            raise ShwtpContractError(
                f"deferred modulator {deferred_control.controller_id!r} must be a C2 control in a later gate "
                f"(got class {deferred_control.control_class!r}, gate {deferred_control.implementation_gate!r})"
            )
        if deferred_control.active_in_x2:
            raise ShwtpContractError(
                f"deferred modulator {deferred_control.controller_id!r} must stay inactive in X2"
            )
        if deferred.get("modulates") != signal or deferred.get("gate") != deferred_control.implementation_gate:
            raise ShwtpContractError(
                f"process contract {scope.scope_id!r} input {signal!r} deferred_modulator annotation must "
                f"restate the controller gate and the modulated signal"
            )
    return {
        "scope_id": scope.scope_id,
        "signal": signal,
        "unit": entry.get("unit"),
        "declared_source": source,
        "x2_producer_class": producer_class,
        "x2_active_in_x2": producer_class == "x2_active_controller",
        "deferred_modulator": deferred.get("controller_id") if isinstance(deferred, Mapping) else None,
        "deferred_modulator_gate": deferred.get("gate") if isinstance(deferred, Mapping) else None,
        "x2_fallback_mode": entry.get("x2_fallback", {}).get("mode") if isinstance(entry.get("x2_fallback"), Mapping) else None,
    }


def _validate_x2_io_resolution(
    scopes: tuple[ScopeContract, ...],
    nodes: tuple[GraphNode, ...],
    edges: tuple[GraphEdge, ...],
    controls: tuple[ControlContract, ...],
) -> tuple[dict, ...]:
    """Every X2-admitted input must resolve to an X2 producer; never to a C2 output."""
    nodes_by_id = {node.node_id: node for node in nodes}
    controls_by_id = {control.controller_id: control for control in controls}
    rows: list[dict] = []
    for scope in scopes:
        if not scope.x2_admitted:
            continue
        inputs = scope.raw.get("inputs", [])
        if not inputs:
            raise ShwtpContractError(f"X2-admitted scope {scope.scope_id!r} declares no inputs")
        for entry in inputs:
            rows.append(_resolve_x2_input(scope, entry, nodes_by_id, controls_by_id))
    if not rows:
        raise ShwtpContractError("no X2 input resolution could be derived from the process contracts")
    return tuple(rows)


def _validate_level_action_direction(
    scopes: tuple[ScopeContract, ...],
    nodes: tuple[GraphNode, ...],
    edges: tuple[GraphEdge, ...],
    controls: tuple[ControlContract, ...],
) -> tuple[dict, ...]:
    """Level actions must name the correct upstream/downstream actuator (X1-C01)."""
    adjacency = _water_adjacency(edges)
    nodes_by_id = {node.node_id: node for node in nodes}
    rows: list[dict] = []
    for control in controls:
        policy = control.raw.get("level_action_policy")
        ownership = control.raw.get("actuator_ownership")
        has_level_alarm = any(str(alarm).startswith("level_") for alarm in control.raw.get("alarms", []))
        if policy is None and ownership is None:
            if has_level_alarm and control.active_in_x2 and control.control_class == "C1":
                raise ShwtpContractError(
                    f"X2-active C1 control {control.controller_id!r} declares level alarms and must define "
                    f"both level_action_policy and actuator_ownership"
                )
            continue
        if policy is None or ownership is None:
            raise ShwtpContractError(
                f"control {control.controller_id!r} must declare level_action_policy and actuator_ownership together"
            )
        for key in ACTUATOR_OWNERSHIP_REQUIRED_KEYS:
            if key not in ownership:
                raise ShwtpContractError(
                    f"control {control.controller_id!r} actuator_ownership is missing {key!r}"
                )
        for direction in ("upstream", "downstream"):
            block = ownership[f"{direction}_actuator"]
            if not isinstance(block, Mapping):
                raise ShwtpContractError(
                    f"control {control.controller_id!r} {direction}_actuator must be a mapping"
                )
            for key in ACTUATOR_REQUIRED_KEYS:
                if key not in block:
                    raise ShwtpContractError(
                        f"control {control.controller_id!r} {direction}_actuator is missing {key!r}"
                    )
            if block["direction"] != direction:
                raise ShwtpContractError(
                    f"control {control.controller_id!r} {direction}_actuator must declare direction {direction!r}"
                )
            if block["scope"] not in nodes_by_id:
                raise ShwtpContractError(
                    f"control {control.controller_id!r} {direction}_actuator references unknown scope {block['scope']!r}"
                )
        if not isinstance(policy, list) or not policy:
            raise ShwtpContractError(f"control {control.controller_id!r} level_action_policy must be a non-empty list")

        for entry in policy:
            for key in LEVEL_ACTION_REQUIRED_KEYS:
                if key not in entry:
                    raise ShwtpContractError(
                        f"control {control.controller_id!r} level_action_policy entry is missing {key!r}"
                    )
            action = str(entry["action"])
            matched = [
                direction
                for direction, words in LEVEL_ACTION_DIRECTIONS.items()
                if any(word in action for word in words)
            ]
            if len(matched) != 1:
                raise ShwtpContractError(
                    f"control {control.controller_id!r} level action {action!r} must name exactly one "
                    f"direction (upstream or downstream)"
                )
            direction = matched[0]
            target = entry["target_scope"]
            if target not in nodes_by_id:
                raise ShwtpContractError(
                    f"control {control.controller_id!r} level action {action!r} targets unknown scope {target!r}"
                )
            expected_signal = ownership[f"{direction}_actuator"]["signal"]
            if entry["target_signal"] != expected_signal:
                raise ShwtpContractError(
                    f"control {control.controller_id!r} level action {action!r} must act on the "
                    f"{direction} actuator signal {expected_signal!r} (got {entry['target_signal']!r})"
                )
            owner = control.owning_scope
            if direction == "downstream" and not _reaches(adjacency, owner, target):
                raise ShwtpContractError(
                    f"control {control.controller_id!r} downstream level action must target a scope reachable "
                    f"downstream of {owner!r} (got {target!r})"
                )
            if direction == "upstream" and not _reaches(adjacency, target, owner):
                raise ShwtpContractError(
                    f"control {control.controller_id!r} upstream level action must target a scope that feeds "
                    f"{owner!r} (got {target!r})"
                )
            rows.append(
                {
                    "controller_id": control.controller_id,
                    "owning_scope": owner,
                    "condition": entry["condition"],
                    "action": action,
                    "direction": direction,
                    "target_scope": target,
                    "target_signal": entry["target_signal"],
                }
            )

        for group in ("permissives", "interlocks"):
            for text in control.raw.get(group, []):
                lowered = str(text).lower()
                low_level = any(token in lowered for token in ("lal", "low level", "low-low"))
                blocks_upstream = any(
                    token in lowered
                    for token in ("stop intake", "stop the intake", "intake pump", "stop upstream")
                )
                # a statement that explicitly denies the upstream trip is not a trip
                negated = lowered.lstrip().startswith(("no ", "not ", "never ")) or any(
                    token in lowered for token in ("no low-level", "not implied", "must not", "never trips")
                )
                if low_level and blocks_upstream and not negated and "permitted" not in lowered:
                    raise ShwtpContractError(
                        f"control {control.controller_id!r} {group} entry {text!r} lets a low level trip the "
                        f"upstream intake; a low level must protect DOWNSTREAM withdrawal while upstream "
                        f"refill stays permitted"
                    )
    return tuple(rows)


def _validate_admission(
    payload: dict,
    scopes: tuple[ScopeContract, ...],
    reference_only: tuple[str, ...],
    edges: tuple[GraphEdge, ...],
    controls: tuple[ControlContract, ...],
) -> X2Admission:
    executable_raw = _require(payload, "x2_executable_scopes", "admission manifest")
    c1_raw = _require(payload, "x2_c1_controls_active", "admission manifest")
    c2_raw = _require(payload, "x2_c2_controls_deferred", "admission manifest")
    assumed_raw = _require(payload, "x2_assumed_edges_used", "admission manifest")
    assumed_excluded_raw = payload.get("x2_assumed_edges_excluded", [])
    known_raw = _require(payload, "x2_pim_known_edges_used", "admission manifest")
    invariants = _require(payload, "x2_invariants_must_prove", "admission manifest")
    not_authorized = _require(payload, "x2_not_authorized", "admission manifest")

    for name, value in (
        ("x2_executable_scopes", executable_raw),
        ("x2_c1_controls_active", c1_raw),
        ("x2_c2_controls_deferred", c2_raw),
        ("x2_assumed_edges_used", assumed_raw),
        ("x2_pim_known_edges_used", known_raw),
        ("x2_invariants_must_prove", invariants),
        ("x2_not_authorized", not_authorized),
    ):
        if not isinstance(value, list) or not value:
            raise ShwtpContractError(f"admission manifest {name!r} must be a non-empty list")

    executable_ids = tuple(sorted(str(entry["scope_id"]) for entry in executable_raw))
    if not isinstance(payload.get("x2_reference_or_container_only"), list):
        raise ShwtpContractError("admission manifest must declare reference/container-only scopes")
    reference_ids = tuple(
        sorted(
            {
                str(entry["scope_id"])
                for entry in payload["x2_reference_or_container_only"]
                if "scope_id" in entry
            }
            | set(reference_only)
        )
    )
    overlap = set(executable_ids) & set(reference_ids)
    if overlap:
        raise ShwtpContractError(f"scopes {sorted(overlap)} are both executable and reference-only")

    admitted = {scope.scope_id for scope in scopes if scope.x2_admitted}
    missing_contracts = sorted(set(executable_ids) - admitted)
    if missing_contracts:
        raise ShwtpContractError(
            f"X2-admitted scopes without a complete process contract: {missing_contracts}"
        )
    extra = sorted(admitted - set(executable_ids))
    if extra:
        raise ShwtpContractError(
            f"scopes marked X2-admitted in the process contracts but absent from the manifest: {extra}"
        )

    control_by_id = {control.controller_id: control for control in controls}
    c1_ids: list[str] = []
    for entry in c1_raw:
        controller_id = str(entry["controller_id"])
        control = control_by_id.get(controller_id)
        if control is None:
            raise ShwtpContractError(f"admission lists unknown C1 control {controller_id!r}")
        if not control.active_in_x2 or control.implementation_gate != "X2":
            raise ShwtpContractError(
                f"admission lists {controller_id!r} as active in X2 but its contract disagrees"
            )
        if control.control_class != "C1":
            raise ShwtpContractError(f"admission lists non-C1 control {controller_id!r} as C1")
        c1_ids.append(controller_id)

    c2_pairs: list[tuple[str, str]] = []
    for entry in c2_raw:
        controller_id = str(entry["controller_id"])
        control = control_by_id.get(controller_id)
        if control is None:
            raise ShwtpContractError(f"admission lists unknown deferred control {controller_id!r}")
        if control.active_in_x2:
            raise ShwtpContractError(
                f"deferred control {controller_id!r} is marked active in X2"
            )
        gate = str(entry.get("gate"))
        if gate not in ("X3", "X4"):
            raise ShwtpContractError(
                f"deferred control {controller_id!r} must be deferred to X3 or X4, got {gate!r}"
            )
        if control.implementation_gate != gate:
            raise ShwtpContractError(
                f"deferred control {controller_id!r} gate disagrees with its contract"
            )
        c2_pairs.append((controller_id, gate))

    active_c1 = {
        control.controller_id
        for control in controls
        if control.active_in_x2 and control.control_class == "C1"
    }
    if active_c1 != set(c1_ids):
        raise ShwtpContractError(
            "admission C1 list must equal the set of X2-active C1 control contracts"
        )

    assumed_by_id = {edge.edge_id: edge for edge in edges if edge.category == "vf_scenario_assumption"}
    for entry in assumed_raw:
        edge_id = str(entry["edge_id"])
        edge = assumed_by_id.get(edge_id)
        if edge is None:
            raise ShwtpContractError(f"admission uses unknown/ non-assumed edge {edge_id!r}")
        if entry.get("assumption_id") != edge.assumption_id:
            raise ShwtpContractError(
                f"admission assumption id for {edge_id!r} disagrees with the graph"
            )
    for entry in assumed_excluded_raw:
        edge_id = str(entry["edge_id"])
        edge = assumed_by_id.get(edge_id)
        if edge is None:
            raise ShwtpContractError(f"admission excludes unknown assumed edge {edge_id!r}")
        if edge.x2_eligible:
            raise ShwtpContractError(f"edge {edge_id!r} is X2-eligible but listed as excluded")
    used = {str(entry["edge_id"]) for entry in assumed_raw}
    for edge in assumed_by_id.values():
        if edge.x2_eligible and edge.edge_id not in used:
            raise ShwtpContractError(
                f"X2-eligible assumed edge {edge.edge_id!r} is not listed as used in the admission manifest"
            )

    for entry in known_raw:
        edge_id = str(entry["edge_id"])
        edge = next((e for e in edges if e.edge_id == edge_id), None)
        if edge is None or edge.category != "pim_known":
            raise ShwtpContractError(
                f"admission cites {edge_id!r} as PIM-known but the graph disagrees"
            )

    for control in controls:
        if control.active_in_x2 and control.owning_scope not in set(executable_ids):
            raise ShwtpContractError(
                f"active control {control.controller_id!r} owns non-executable scope "
                f"{control.owning_scope!r}"
            )

    return X2Admission(
        executable_scope_ids=executable_ids,
        reference_only_scope_ids=reference_ids,
        c1_active_ids=tuple(sorted(c1_ids)),
        c2_deferred=tuple(sorted(c2_pairs)),
        assumed_edges_used=tuple(sorted(used)),
        assumed_edges_excluded=tuple(sorted(str(e["edge_id"]) for e in assumed_excluded_raw)),
        pim_known_edges_used=tuple(sorted(str(e["edge_id"]) for e in known_raw)),
        invariants=tuple(invariants),
        not_authorized=tuple(not_authorized),
    )


# ── public API ─────────────────────────────────────────────────────────────

def load_whole_plant_contracts(
    graph_path: Path | str | None = None,
    process_contracts_path: Path | str | None = None,
    control_contracts_path: Path | str | None = None,
    x2_admission_path: Path | str | None = None,
    inventory_path: Path | str | None = None,
) -> WholePlantContracts:
    """Load, validate and freeze the X1 contract layer (fail-closed)."""
    paths = {
        "graph": Path(graph_path) if graph_path else DEFAULT_GRAPH_PATH,
        "process": Path(process_contracts_path) if process_contracts_path else DEFAULT_PROCESS_CONTRACTS_PATH,
        "control": Path(control_contracts_path) if control_contracts_path else DEFAULT_CONTROL_CONTRACTS_PATH,
        "admission": Path(x2_admission_path) if x2_admission_path else DEFAULT_X2_ADMISSION_PATH,
    }

    graph = _load_json(paths["graph"], "whole-plant graph")
    process = _load_json(paths["process"], "process contracts")
    control = _load_json(paths["control"], "control contracts")
    admission_raw = _load_json(paths["admission"], "X2 admission manifest")

    _check_schema(graph, GRAPH_SCHEMA, "graph")
    _check_schema(process, PROCESS_SCHEMA, "process contracts")
    _check_schema(control, CONTROL_SCHEMA, "control contracts")
    _check_schema(admission_raw, ADMISSION_SCHEMA, "X2 admission manifest")
    for label, payload in (
        ("graph", graph),
        ("process contracts", process),
        ("control contracts", control),
        ("X2 admission manifest", admission_raw),
    ):
        _check_authority(payload, label)

    nodes, edges, assumption_ids = _validate_graph(graph)
    scopes, reference_only = _validate_scopes(process)
    controls = _validate_controls(control)
    # X1-C01: X2 I/O resolution (never a C2 dependency) + level-action actuator direction
    _validate_x2_io_resolution(scopes, nodes, edges, controls)
    _validate_level_action_direction(scopes, nodes, edges, controls)
    admission = _validate_admission(admission_raw, scopes, reference_only, edges, controls)

    # identity: no invented PIM id, VF-local namespace only
    allowed = accepted_canonical_ids(Path(inventory_path) if inventory_path else None)
    for label, payload in (
        ("graph", graph),
        ("process contracts", process),
        ("control contracts", control),
        ("X2 admission manifest", admission_raw),
    ):
        unknown = sorted(referenced_pim_ids(payload) - allowed)
        if unknown:
            raise ShwtpContractError(
                f"{label} references PIM id(s) that do not exist in the accepted inventory: {unknown}"
            )

    signature = _signature(
        {
            "nodes": [
                (n.node_id, n.canonical_id, n.process_role, n.x2_eligible)
                for n in nodes
            ],
            "edges": [
                (e.edge_id, e.source, e.target, e.flow, e.category, e.assumption_id, e.x2_eligible)
                for e in edges
            ],
            "scopes": [
                (s.scope_id, s.canonical_id, s.fidelity_class, s.x2_admitted, s.update_rule_family)
                for s in scopes
            ],
            "controls": [
                (c.controller_id, c.owning_scope, c.control_class, c.implementation_gate, c.active_in_x2)
                for c in controls
            ],
            "admission": admission,
        }
    )

    return WholePlantContracts(
        nodes=nodes,
        edges=edges,
        assumption_ids=assumption_ids,
        scopes=scopes,
        reference_only_scopes=reference_only,
        controls=controls,
        admission=admission,
        signature=signature,
        source_paths={key: str(value) for key, value in paths.items()},
    )


def x2_io_resolution_audit(contracts: WholePlantContracts) -> tuple[dict, ...]:
    """Read-only audit of how every X2-admitted input is produced inside X2."""
    return _validate_x2_io_resolution(contracts.scopes, contracts.nodes, contracts.edges, contracts.controls)


def level_action_audit(contracts: WholePlantContracts) -> tuple[dict, ...]:
    """Read-only audit of level-action actuator ownership and direction."""
    return _validate_level_action_direction(contracts.scopes, contracts.nodes, contracts.edges, contracts.controls)


def _signature(payload: Mapping[str, Any]) -> str:
    def _normalise(value: Any) -> Any:
        if isinstance(value, Mapping):
            return {str(k): _normalise(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
        if isinstance(value, (list, tuple)):
            return [_normalise(item) for item in value]
        if hasattr(value, "__dataclass_fields__"):
            return _normalise({f: getattr(value, f) for f in value.__dataclass_fields__})
        return value

    blob = json.dumps(_normalise(payload), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def pim_ids_referenced_by_contracts(contracts: WholePlantContracts) -> tuple[str, ...]:
    """Sorted PIM ids referenced anywhere in the frozen contract layer."""
    found: set[str] = set()
    for scope in contracts.scopes:
        found |= referenced_pim_ids(scope.raw)
    for control in contracts.controls:
        found |= referenced_pim_ids(control.raw)
    for node in contracts.nodes:
        found |= referenced_pim_ids(
            {"canonical_id": node.canonical_id, "area": node.area_canonical_id,
             "refs": list(node.canonical_refs)}
        )
    for edge in contracts.edges:
        found |= referenced_pim_ids({"rel": edge.pim_relation_id})
    found |= referenced_pim_ids(list(contracts.admission.invariants) + list(contracts.admission.not_authorized))
    return tuple(sorted(found))


def iter_vf_local_ids(contracts: WholePlantContracts) -> Iterable[str]:
    found: set[str] = set()
    for scope in contracts.scopes:
        found |= referenced_vf_local_ids(scope.raw)
    for control in contracts.controls:
        found |= referenced_vf_local_ids(control.raw)
    for node in contracts.nodes:
        found.add(node.node_id)
    return tuple(sorted(found))
