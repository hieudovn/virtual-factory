"""Topology & dependency engine for VF-2.

Builds a directed graph from package topology edges and infers signal
dependencies, replacing VF-1's hardcoded 8-stage WTP chain with a
generic graph-based resolver.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

from .models import VF2Package
from .object_registry import ObjectRegistry
from .signal_registry import SignalRegistry


# ======================================================================
# Data structures
# ======================================================================


@dataclass
class TopologyGraph:
    """Directed graph built from package topology + signal dependencies.

    Attributes:
        process_flow: Adjacency ``{object_id: [downstream_object_ids]}``.
        electrical: Electrical connectivity ``{feeder_id: [powered_ids]}``.
        signal_deps: Signal dependency DAG ``{signal_id: [upstream_signal_ids]}``.
        eval_order: Topological sort of ``signal_deps`` (independent first).
        boundary_endpoints: Object IDs referenced in topology but not in ``objects[]``.
    """

    process_flow: dict[str, list[str]] = field(default_factory=dict)
    electrical: dict[str, list[str]] = field(default_factory=dict)
    signal_deps: dict[str, list[str]] = field(default_factory=dict)
    eval_order: list[str] = field(default_factory=list)
    boundary_endpoints: set[str] = field(default_factory=set)


# ======================================================================
# TopologyEngine
# ======================================================================


class TopologyEngine:
    """Builds and queries the topology / dependency graph from a VF-2 package.

    Uses:

    1. ``package.topology.process_edges`` → process flow graph
    2. ``package.topology.electrical_edges`` → electrical graph
    3. Signal behaviour (direction, ``signal_type``) → dependency inference
    """

    def __init__(
        self,
        pkg: VF2Package,
        obj_reg: ObjectRegistry,
        sig_reg: SignalRegistry,
    ) -> None:
        self._pkg = pkg
        self._obj_reg = obj_reg
        self._sig_reg = sig_reg

    # ──────────────────────────────────────────────────────────────────
    # Build
    # ──────────────────────────────────────────────────────────────────

    def build(self) -> TopologyGraph:
        """Build the full topology graph.

        Steps:
        1. Process flow graph from ``process_edges``
        2. Electrical graph from ``electrical_edges``
        3. Signal dependency DAG (inferred from types + topology)
        4. Topological sort of signal deps for evaluation order
        5. Identify boundary endpoints
        """
        graph = TopologyGraph()

        # ── 1. Process flow ──────────────────────────────────────────
        object_ids = set(self._obj_reg.object_ids)
        for edge in self._pkg.topology.process_edges:
            frm = edge.from_simulation_object_id
            to = edge.to_simulation_object_id
            graph.process_flow.setdefault(frm, []).append(to)

            # Track boundary endpoints
            if frm not in object_ids:
                graph.boundary_endpoints.add(frm)
            if to not in object_ids:
                graph.boundary_endpoints.add(to)

        # ── 2. Electrical graph ──────────────────────────────────────
        for edge in self._pkg.topology.electrical_edges:
            frm = edge.from_simulation_object_id
            to = edge.to_simulation_object_id
            graph.electrical.setdefault(frm, []).append(to)

            if frm not in object_ids:
                graph.boundary_endpoints.add(frm)
            if to not in object_ids:
                graph.boundary_endpoints.add(to)

        # ── 3. Signal dependency DAG ──────────────────────────────────
        graph.signal_deps = _infer_signal_deps(
            self._sig_reg, self._obj_reg, graph.process_flow,
        )

        # ── 4. Topological sort ──────────────────────────────────────
        graph.eval_order = _topological_sort(graph.signal_deps)

        return graph

    # ──────────────────────────────────────────────────────────────────
    # Queries
    # ──────────────────────────────────────────────────────────────────

    def get_downstream_objects(self, object_id: str) -> list[str]:
        """Return objects downstream of *object_id* in the process flow."""
        visited: set[str] = set()
        result: list[str] = []
        queue: deque[str] = deque()

        # Build full process flow from all edges
        flow: dict[str, list[str]] = defaultdict(list)
        for edge in self._pkg.topology.process_edges:
            flow[edge.from_simulation_object_id].append(
                edge.to_simulation_object_id,
            )

        queue.append(object_id)
        while queue:
            oid = queue.popleft()
            for downstream in flow.get(oid, []):
                if downstream not in visited:
                    visited.add(downstream)
                    result.append(downstream)
                    queue.append(downstream)

        return result

    def get_affected_signals(
        self,
        object_id: str,
        sig_reg: SignalRegistry | None = None,
    ) -> list[str]:
        """Return all signal IDs affected if *object_id* fails.

        Includes:
        - Direct signals on the object (via ``canonical_asset_id``)
        - Signals on downstream objects (via process flow)
        """
        sr = sig_reg or self._sig_reg
        affected: list[str] = []

        # 1. Direct signals
        obj = self._obj_reg.get(object_id)
        if obj:
            for sig in sr.filter_by_asset(obj.canonical_id):
                affected.append(sig.simulation_signal_id)

        # 2. Downstream signals
        for down_id in self.get_downstream_objects(object_id):
            down_obj = self._obj_reg.get(down_id)
            if down_obj:
                for sig in sr.filter_by_asset(down_obj.canonical_id):
                    affected.append(sig.simulation_signal_id)

        return affected

    def resolve_order(self, signal_ids: list[str]) -> list[str]:
        """Topological sort of signals so dependencies are evaluated first.

        If a signal in *signal_ids* depends on another that is not in the
        list, the dependency is ignored (already evaluated or external).
        """
        # Build subgraph containing only the requested signals
        sub_deps: dict[str, list[str]] = {}
        for sid in signal_ids:
            deps = self._build_graph().signal_deps.get(sid, [])
            sub_deps[sid] = [d for d in deps if d in signal_ids]

        return _topological_sort(sub_deps)

    def _build_graph(self) -> TopologyGraph:
        """Convenience — build once and cache."""
        if not hasattr(self, "_graph"):
            self._graph = self.build()
        return self._graph


# ======================================================================
# Internal helpers
# ======================================================================


def _infer_signal_deps(
    sig_reg: SignalRegistry,
    obj_reg: ObjectRegistry,
    process_flow: dict[str, list[str]],
) -> dict[str, list[str]]:
    """Infer signal dependencies from signal types + topology.

    Rules
    -----
    1. Measurement signals on objects that *also* have a status signal
       depend on that status signal (e.g. flow depends on pump running).
    2. Feedback signals depend on setpoint signals for the same asset.
    3. Signals on downstream objects potentially depend on upstream
       object signals (via process flow).
    """
    deps: dict[str, list[str]] = {sid: [] for sid in sig_reg.all_signal_ids}

    # Build {canonical_asset_id: [signal_ids]} map
    asset_signals: dict[str, list[str]] = {}
    asset_signal_types: dict[str, dict[str, str]] = {}
    for sig in sig_reg.all_signal_ids:
        s = sig_reg.get(sig)
        if s is None:
            continue
        asset_signals.setdefault(s.canonical_asset_id, []).append(sig)
        asset_signal_types.setdefault(s.canonical_asset_id, {})[sig] = (
            s.behavior.signal_type.value
        )

    # Rule 1: measurements depend on status signals of the same asset
    for asset_id, sigs in asset_signals.items():
        status_sigs = [
            sid for sid, stype in asset_signal_types.get(asset_id, {}).items()
            if stype == "status"
        ]
        measurement_sigs = [
            sid for sid, stype in asset_signal_types.get(asset_id, {}).items()
            if stype == "measurement"
        ]
        for m_sig in measurement_sigs:
            for st_sig in status_sigs:
                if st_sig not in deps[m_sig]:
                    deps[m_sig].append(st_sig)

    # Rule 2: feedback depends on setpoint of the same asset
    for asset_id, sigs in asset_signals.items():
        setpoint_sigs = [
            sid for sid, stype in asset_signal_types.get(asset_id, {}).items()
            if stype == "setpoint"
        ]
        feedback_sigs = [
            sid for sid, stype in asset_signal_types.get(asset_id, {}).items()
            if stype == "feedback"
        ]
        for fb_sig in feedback_sigs:
            for sp_sig in setpoint_sigs:
                if sp_sig not in deps[fb_sig]:
                    deps[fb_sig].append(sp_sig)

    # Rule 3: downstream object measurement signals depend on upstream
    # object measurement signals (process flow chain)
    for upstream_id, downstream_ids in process_flow.items():
        up_obj = obj_reg.get(upstream_id)
        if up_obj is None:
            continue
        for down_id in downstream_ids:
            down_obj = obj_reg.get(down_id)
            if down_obj is None:
                continue

            up_meas = [
                sid for sid in asset_signals.get(up_obj.canonical_id, [])
                if asset_signal_types.get(up_obj.canonical_id, {}).get(sid) == "measurement"
            ]
            down_meas = [
                sid for sid in asset_signals.get(down_obj.canonical_id, [])
                if asset_signal_types.get(down_obj.canonical_id, {}).get(sid) == "measurement"
            ]
            for d_sig in down_meas:
                for u_sig in up_meas:
                    if u_sig not in deps[d_sig]:
                        deps[d_sig].append(u_sig)

    return deps


def _topological_sort(deps: dict[str, list[str]]) -> list[str]:
    """Kahn's algorithm — return signal IDs in dependency order.

    Raises ``ValueError`` if a cycle is detected.
    """
    # In-degree count
    in_degree: dict[str, int] = {sid: 0 for sid in deps}
    for _sid, upstream_ids in deps.items():
        for up_id in upstream_ids:
            if up_id in in_degree:
                in_degree[up_id] += 0  # ensure present
            # Count edge: dependency means the upstream must be evaluated
            # BEFORE the downstream. So downstream (the key) waits for upstream.
            # Actually: if A depends on B, B must come first.
            # So in-degree counts how many things A depends on.
            # in_degree[sid] counts upstream deps of sid
            pass  # handled below

    # Correct: in_degree[x] = number of things x depends on
    in_degree = {sid: len(upstream) for sid, upstream in deps.items()}

    # Queue of signals with no dependencies
    queue: deque[str] = deque(sid for sid, deg in in_degree.items() if deg == 0)

    order: list[str] = []
    while queue:
        sid = queue.popleft()
        order.append(sid)
        # Find all signals that depend on sid
        for maybe_downstream, upstream_ids in deps.items():
            if sid in upstream_ids:
                in_degree[maybe_downstream] -= 1
                if in_degree[maybe_downstream] == 0:
                    queue.append(maybe_downstream)

    if len(order) != len(deps):
        raise ValueError(
            f"Cycle detected in signal dependencies: "
            f"{len(order)} of {len(deps)} signals resolved"
        )

    return order
