"""SH-WTP X3 conservative transfer allocation + hydraulic/energy feasibility.

Implements the physical core of the SA design freeze (Issue #97):

- **D4** a model-level allocation stage over the frozen tick snapshot: immutable
  per-edge budgets, aggregate shared-trunk and source totals (no source water
  allocated twice), receiver headroom that reserves ALL queued unconsumed inbound
  water, source availability of held + committed water only (never newly emitted
  same-tick inflow), deterministic priority (existing safety/backwash path first,
  then normal delivery, ties by edge id), non-storage paths propagating their
  downstream budget upstream, and bounded queues. Withheld water stays in the
  source storage; nothing here mutates another participant's water state.
- **D6** simplified hydraulic/energy feasibility for the declared powered pumps:
  descending curve ``H(n,Q) = H0*n^2 - k*Q^2`` against the system requirement
  ``Hreq = Hstatic + R*Q^2``, motor rating, hydraulic power ``P_hyd = rho*g*Q*H``
  and ``P_elec = P_hyd/eta_total + no_load``. The nonnegative excess head above
  the system requirement is recorded as equivalent throttling/dissipation, never
  as unexplained pressure or useful energy. A zero-speed pump forwards no flow
  (no passive bypass in the one-way pumped-path abstraction).

Units: everything here is SI (m3, s, m3/s, m, Pa, W, J). Mappings to the existing
m3/h and % interfaces happen at the named boundaries of :mod:`x3_profile`.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from virtual_factory.shwtp.x3_profile import (
    X3EdgeRating,
    X3Profile,
    X3Pump,
    X3Units,
)

#: Deterministic allocation priority: the existing safety/backwash path is served
#: before normal delivery; ties are broken by binding id (D4).
SAFETY_FIRST_BINDINGS: tuple[str, ...] = (
    "vf-shw-edge-t106-wash",
    "vf-shw-edge-wash-t106",
    "vf-shw-edge-t105-sludge",
)


class X3BudgetError(ValueError):
    """Raised when the allocation stage cannot produce a valid budget set."""


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise X3BudgetError(f"{name} must be a finite number, got {value!r}")
    out = float(value)
    if not math.isfinite(out):
        raise X3BudgetError(f"{name} must be a finite number, got {value!r}")
    return out


def _nonneg(value: Any, name: str) -> float:
    out = _finite(value, name)
    if out < 0.0:
        raise X3BudgetError(f"{name} must be >= 0, got {out!r}")
    return out


# ── D6: pump hydraulics / energy ─────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class PumpOperatingPoint:
    """One evaluated pump operating point (all SI)."""

    pump_id: str
    speed_fraction: float
    requested_flow_m3_s: float
    flow_m3_s: float
    head_m: float
    required_head_m: float
    throttle_head_m: float
    hydraulic_w: float
    electric_w: float
    motor_rating_w: float
    feasible: bool
    reason: str

    @property
    def flow_m3h(self) -> float:
        return self.flow_m3_s * 3600.0

    @property
    def off(self) -> bool:
        return self.flow_m3_s <= 0.0


class PumpModel:
    """Declared synthetic pump curve + motor/energy feasibility (D6)."""

    def __init__(self, pump: X3Pump, units: X3Units) -> None:
        self.pump = pump
        self.units = units

    # curve -----------------------------------------------------------------
    def head_m(self, speed_fraction: float, flow_m3_s: float) -> float:
        speed = _nonneg(speed_fraction, "speed_fraction")
        flow = _nonneg(flow_m3_s, "flow_m3_s")
        return self.pump.h0_m * speed * speed - self.pump.k_s2_m5 * flow * flow

    def required_head_m(self, flow_m3_s: float) -> float:
        flow = _nonneg(flow_m3_s, "flow_m3_s")
        return self.pump.h_static_m + self.pump.r_s2_m5 * flow * flow

    def hydraulic_power_w(self, flow_m3_s: float, head_m: float) -> float:
        return self.units.rho_kg_m3 * self.units.g_m_s2 * _nonneg(flow_m3_s, "flow_m3_s") * _nonneg(head_m, "head_m")

    def electric_power_w(self, hydraulic_w: float) -> float:
        return hydraulic_w / self.pump.eta_total + self.pump.no_load_w

    # feasibility -----------------------------------------------------------
    def _feasible_at(self, speed_fraction: float, flow_m3_s: float) -> bool:
        if flow_m3_s <= 0.0:
            return True
        head = self.head_m(speed_fraction, flow_m3_s)
        required = self.required_head_m(flow_m3_s)
        if head < required:
            return False
        power = self.electric_power_w(self.hydraulic_power_w(flow_m3_s, head))
        return power <= self.pump.motor_rating_w

    def max_feasible_flow_m3_s(self, speed_fraction: float) -> float:
        """Largest admissible flow honouring the system head and the motor rating."""
        speed = _nonneg(speed_fraction, "speed_fraction")
        if speed <= 0.0:
            return 0.0
        high = min(self.pump.q_rated_m3_s * speed, self.pump.q_rated_m3_s)
        if high <= 0.0:
            return 0.0
        if self._feasible_at(speed, high):
            return high
        low = 0.0
        for _ in range(60):  # deterministic bisection on a monotone-in-Q feasibility
            mid = (low + high) / 2.0
            if self._feasible_at(speed, mid):
                low = mid
            else:
                high = mid
        return low

    def operating_point(self, speed_pct: float, requested_flow_m3_s: float) -> PumpOperatingPoint:
        """Evaluate the achievable operating point for a commanded speed."""
        speed_pct = _finite(speed_pct, "speed_pct")
        if not 0.0 <= speed_pct <= 100.0:
            raise X3BudgetError(f"{self.pump.pump_id}: speed {speed_pct!r} % is outside [0, 100]")
        requested = _nonneg(requested_flow_m3_s, "requested_flow_m3_s")
        speed = speed_pct / 100.0
        reason = "ok"
        if speed <= 0.0:
            return PumpOperatingPoint(
                pump_id=self.pump.pump_id,
                speed_fraction=0.0,
                requested_flow_m3_s=requested,
                flow_m3_s=0.0,
                head_m=0.0,
                required_head_m=self.required_head_m(0.0),
                throttle_head_m=0.0,
                hydraulic_w=0.0,
                electric_w=0.0,
                motor_rating_w=self.pump.motor_rating_w,
                feasible=True,
                reason="pump_off_no_flow_no_energy",
            )
        cap = self.max_feasible_flow_m3_s(speed)
        flow = min(requested, cap)
        if flow <= 0.0:
            reason = "insufficient_head_or_motor_overload"
        elif flow < requested - 1e-15:
            reason = "limited_by_head_or_motor_rating"
        head = max(0.0, self.head_m(speed, flow))
        required = self.required_head_m(flow)
        hydraulic = self.hydraulic_power_w(flow, head)
        electric = self.electric_power_w(hydraulic) if flow > 0.0 else 0.0
        return PumpOperatingPoint(
            pump_id=self.pump.pump_id,
            speed_fraction=speed,
            requested_flow_m3_s=requested,
            flow_m3_s=flow,
            head_m=head,
            required_head_m=required,
            throttle_head_m=max(0.0, head - required),
            hydraulic_w=hydraulic,
            electric_w=electric,
            motor_rating_w=self.pump.motor_rating_w,
            feasible=electric <= self.pump.motor_rating_w + 1e-9,
            reason=reason,
        )

    def energy_step_j(self, point: PumpOperatingPoint, dt_s: float) -> float:
        """E = P_elec * dt; an OFF pump integrates exactly zero energy."""
        if point.off:
            return 0.0
        return _nonneg(point.electric_w, "electric_w") * _nonneg(dt_s, "dt_s")


# ── D4: conservative transfer allocation ─────────────────────────────────

@dataclass(frozen=True, slots=True)
class EdgeBudget:
    """The immutable per-edge budget of one tick."""

    binding_id: str
    source_scope: str
    target_scope: str
    requested_m3_s: float
    budget_m3_s: float
    limiting_factor: str

    @property
    def budget_m3h(self) -> float:
        return self.budget_m3_s * 3600.0

    @property
    def limited(self) -> bool:
        return self.budget_m3_s < self.requested_m3_s - 1e-15


@dataclass(frozen=True, slots=True)
class TickAllocation:
    """The complete, validated budget set for one coordination tick."""

    tick_index: int
    dt_s: float
    budgets: Mapping[str, EdgeBudget]
    source_available_m3_s: Mapping[str, float]
    receiver_headroom_m3_s: Mapping[str, float]
    trunk_used_m3_s: Mapping[str, float]
    queued_volume_m3: float
    diagnostics: tuple[str, ...] = ()
    conduit_remaining_m3_s: Mapping[str, float] = field(default_factory=dict)

    def budget_m3h_by_scope_port(self) -> dict[str, dict[str, float]]:
        """Budgets in the processor interface (m3/h) keyed by scope and source port."""
        return dict(self._by_scope_port)

    _by_scope_port: Mapping[str, Mapping[str, float]] = field(default_factory=dict)


def _topological_order(
    scope_ids: Sequence[str],
    edges: Sequence[tuple[str, str]],
) -> tuple[str, ...]:
    """Deterministic topological order of the declared edges (source before target).

    The ordering graph contains every edge that must be "fed before it can
    forward": a cycle there is a modelling error. Storage-internal loops (for
    example the declared wash loop between two tanks) contribute no such edge and
    are deliberately outside this graph.
    """
    nodes = sorted(scope_ids)
    outgoing: dict[str, list[str]] = {node: [] for node in nodes}
    indegree: dict[str, int] = {node: 0 for node in nodes}
    for source, target in edges:
        outgoing[source].append(target)
        indegree[target] += 1
    ready = sorted(node for node in nodes if indegree[node] == 0)
    order: list[str] = []
    while ready:
        node = ready.pop(0)
        order.append(node)
        for target in sorted(outgoing[node]):
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
                ready.sort()
    if len(order) != len(nodes):
        raise X3BudgetError(
            "the pass-through propagation graph contains a cycle; the X3 allocation "
            "stage requires an acyclic non-storage path"
        )
    return tuple(order)


def allocate_tick(
    *,
    profile: X3Profile,
    tick_index: int,
    scope_state: Mapping[str, Mapping[str, Any]],
    requested_m3_s: Mapping[str, float],
    bindings: Sequence[Mapping[str, str]],
    source_ports: Mapping[str, str],
    priority_bindings: Sequence[str] = SAFETY_FIRST_BINDINGS,
) -> TickAllocation:
    """Compute the conservative per-edge budgets for one tick (D4).

    ``scope_state[scope_id]`` must provide ``volume_m3`` (0 for non-storage
    scopes), ``capacity_m3`` (None/absent for non-storage scopes) and
    ``queued_inbound_m3`` (water committed but not yet consumed this tick).
    ``requested_m3_s`` is the process law's unbounded request per binding.
    """
    dt_s = profile.tick_s
    scope_ids = sorted(scope_state)
    pass_through = {
        scope_id: scope_state[scope_id].get("capacity_m3") in (None, 0)
        for scope_id in scope_ids
    }
    # 1) source availability: held water + water already committed for this tick
    source_available: dict[str, float] = {}
    declared_inflow: dict[str, float] = {}
    for scope_id in scope_ids:
        state = scope_state[scope_id]
        declared = state.get("source_availability_m3_s")
        declared_inflow[scope_id] = 0.0
        if declared is not None and not pass_through[scope_id]:
            source_available[scope_id] = _nonneg(declared, f"{scope_id}.source_availability_m3_s")
            continue
        held = _nonneg(state.get("volume_m3", 0.0), f"{scope_id}.volume_m3")
        due = _nonneg(state.get("queued_inbound_m3", 0.0), f"{scope_id}.queued_inbound_m3")
        if pass_through[scope_id]:
            if declared is None:
                source_available[scope_id] = math.inf
            else:
                source_available[scope_id] = _nonneg(
                    declared, f"{scope_id}.source_availability_m3_s"
                )
                declared_inflow[scope_id] = source_available[scope_id]
        else:
            source_available[scope_id] = (held + due) / dt_s
    # 2) receiver headroom: reserve ALL queued unconsumed inbound water
    headroom: dict[str, float] = {}
    for scope_id in scope_ids:
        state = scope_state[scope_id]
        capacity = state.get("capacity_m3")
        if capacity in (None, 0):
            headroom[scope_id] = math.inf
            continue
        volume = _nonneg(state.get("volume_m3", 0.0), f"{scope_id}.volume_m3")
        queued = _nonneg(state.get("queued_inbound_m3", 0.0), f"{scope_id}.queued_inbound_m3")
        headroom[scope_id] = max(0.0, float(capacity) - volume - queued) / dt_s
    ordered = _topological_order(
        scope_ids,
        [
            (binding["source_scope"], binding["target_scope"])
            for binding in bindings
            if pass_through[binding["source_scope"]] or pass_through[binding["target_scope"]]
        ],
    )
    # 3) CONDUIT model: every capacity component on a pass-through path (edge
    # rating and the declared throughput of its control element) is reserved ONCE
    # -- at the entry into the conduit -- and shared by every parallel branch that
    # feeds it. The water enters the conduit once, so charging every hop again
    # would either starve the chain or silently drop water at a hop that cannot
    # forward. ``conduit[X]`` is the set of components a flow entering X must
    # still traverse.
    component_cap: dict[str, float] = {
        binding["binding_id"]: min(
            profile.edge(binding["binding_id"]).max_flow_m3_s,
            _nonneg(
                requested_m3_s.get(binding["binding_id"], profile.edge(binding["binding_id"]).max_flow_m3_s),
                f"{binding['binding_id']}.requested_m3_s",
            ),
        )
        for binding in bindings
    }
    outbound: dict[str, list[str]] = {scope_id: [] for scope_id in scope_ids}
    for binding in bindings:
        outbound[binding["source_scope"]].append(binding["binding_id"])
    for key in outbound:
        outbound[key].sort()
    edge_target = {binding["binding_id"]: binding["target_scope"] for binding in bindings}
    conduit: dict[str, tuple[str, ...]] = {}
    for scope_id in reversed(ordered):
        if not pass_through[scope_id]:
            conduit[scope_id] = ()
            continue
        members: set[str] = set()
        downstream = outbound[scope_id]
        if len(downstream) == 1:
            # a SERIES conduit: the same water traverses every hop, so all hops
            # are components of one shared reservation
            members.add(downstream[0])
            members.update(conduit[edge_target[downstream[0]]])
        # a SPLITTING pass-through scope (or a terminal boundary sink) declares no
        # conduit of its own: each branch is then bounded by its own component
        # capacity and by its own receiver, which is conservative by construction
        conduit[scope_id] = tuple(sorted(members))
    # 4) allocate deterministically: safety/backwash path first, then by id, and
    # every binding is evaluated only after the scopes that feed it
    priority = {binding_id: index for index, binding_id in enumerate(priority_bindings)}
    rank = {scope_id: index for index, scope_id in enumerate(ordered)}
    ordered_bindings = sorted(
        bindings,
        key=lambda binding: (
            rank[binding["source_scope"]],
            priority.get(binding["binding_id"], len(priority)),
            binding["binding_id"],
        ),
    )
    source_remaining = dict(source_available)
    receiver_remaining = dict(headroom)
    conduit_remaining = dict(component_cap)
    # D4 trunk semantics: one shared trunk meters the SIMULTANEOUS draw from the
    # SAME source (parallel branches fed by one header). The series segments of a
    # single process line carry the SAME water, so their per-edge limit is the
    # trunk rating itself and never a shared sum (a shared sum would forbid the
    # second segment of a chain from carrying the water the first one discharged).
    trunk_remaining: dict[str, float] = {
        f"{trunk_id}|{source_scope}": trunk_rating
        for trunk_id, trunk_rating in profile.trunks.items()
        for source_scope in scope_ids
    }
    received: dict[str, float] = {scope_id: 0.0 for scope_id in scope_ids}
    budgets: dict[str, EdgeBudget] = {}
    diagnostics: list[str] = []
    for binding in ordered_bindings:
        binding_id = binding["binding_id"]
        source = binding["source_scope"]
        target = binding["target_scope"]
        rating: X3EdgeRating = profile.edge(binding_id)
        requested = _nonneg(requested_m3_s.get(binding_id, 0.0), f"{binding_id}.requested_m3_s")
        if pass_through[source]:
            # a conduit carries what it received, never more; its own component
            # capacity was already reserved at the entry of the conduit
            request_eff = min(requested, received[source] + declared_inflow[source])
            source_cap = source_remaining.get(source, math.inf)
        else:
            request_eff = requested
            source_cap = source_remaining.get(source, math.inf)
        receiver_cap = receiver_remaining.get(target, math.inf)
        # a conduit is reserved exactly ONCE, at the moment water ENTERS it: a
        # pass-through source merely carries forward water whose whole path was
        # already reserved, so it is never charged the same hop twice
        if pass_through[target] and not pass_through[source]:
            keys = conduit[target]
            if keys:
                receiver_cap = min(receiver_cap, min(conduit_remaining[key] for key in keys))
        trunk_key = f"{rating.trunk_id}|{source}" if rating.trunk_id is not None else None
        trunk_cap = math.inf
        if trunk_key is not None:
            trunk_cap = trunk_remaining.get(trunk_key, math.inf)
        limit, factor = min(
            (rating.max_flow_m3_s, "edge_rating"),
            (source_cap, "source_availability"),
            (receiver_cap, "shared_conduit_capacity"),
            (trunk_cap, "shared_trunk"),
            key=lambda pair: pair[0],
        )
        budget = max(0.0, min(request_eff, limit))
        if request_eff < requested - 1e-15 and budget >= request_eff - 1e-15:
            factor = "pass_through_conduit_intake"
        if budget < requested - 1e-15:
            diagnostics.append(f"{binding_id}:{factor}")
        budgets[binding_id] = EdgeBudget(
            binding_id=binding_id,
            source_scope=source,
            target_scope=target,
            requested_m3_s=requested,
            budget_m3_s=budget,
            limiting_factor=factor if budget < requested - 1e-15 else "none",
        )
        if math.isfinite(source_remaining.get(source, math.inf)):
            source_remaining[source] = max(0.0, source_remaining[source] - budget)
        if pass_through[target]:
            received[target] += budget
            if not pass_through[source]:
                for key in conduit[target]:
                    conduit_remaining[key] = max(0.0, conduit_remaining[key] - budget)
        elif math.isfinite(receiver_remaining.get(target, math.inf)):
            receiver_remaining[target] = max(0.0, receiver_remaining[target] - budget)
        if trunk_key is not None and math.isfinite(trunk_remaining.get(trunk_key, math.inf)):
            trunk_remaining[trunk_key] = max(0.0, trunk_remaining[trunk_key] - budget)
    queued_volume = round(
        sum(
            _nonneg(state.get("queued_inbound_m3", 0.0), "queued_inbound_m3")
            for state in scope_state.values()
        ),
        12,
    )
    if queued_volume > profile.queue.max_queued_volume_m3 + 1e-9:
        raise X3BudgetError(
            f"queued in-transit water {queued_volume!r} m3 exceeds the declared bounded "
            f"queue limit {profile.queue.max_queued_volume_m3!r} m3"
        )
    by_scope_port: dict[str, dict[str, float]] = {}
    for binding_id, budget in budgets.items():
        port = source_ports.get(binding_id)
        if port is None:
            continue
        by_scope_port.setdefault(budget.source_scope, {})[port] = budget.budget_m3h
    return TickAllocation(
        tick_index=tick_index,
        dt_s=dt_s,
        budgets=budgets,
        source_available_m3_s=source_available,
        receiver_headroom_m3_s=headroom,
        trunk_used_m3_s=trunk_remaining,
        conduit_remaining_m3_s=conduit_remaining,
        queued_volume_m3=queued_volume,
        diagnostics=tuple(diagnostics),
        _by_scope_port=by_scope_port,
    )


def overflow_beyond_rounding(*, created_m3: float, tolerance_m3: float) -> bool:
    """True when created water exceeds the justified float-rounding tolerance (D4)."""
    return _nonneg(created_m3, "created_m3") > _nonneg(tolerance_m3, "tolerance_m3") + 1e-15


def require_valid_state(*, values: Mapping[str, float], tolerance_m3: float = 1e-9) -> None:
    """Reject nonfinite/negative states before stepping (SA clarification to D6)."""
    for name, value in values.items():
        number = _finite(value, name)
        if number < -tolerance_m3:
            raise X3BudgetError(f"invalid state before stepping: {name}={number!r}")
