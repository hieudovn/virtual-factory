"""Generic multi-participant federation proof (VF-vNEXT-G19).

An additive, mechanism-level, REUSABLE harness that drives the existing G4
``Coordinator`` / ``ExecutableParticipant`` / ``BoundaryTransfer`` seams with
3+ SYNTHETIC participants exchanging detached boundary values over 2+ bindings
in one deterministic coordination window. It proves the G4 mechanism scales
beyond the two-scope SH-WTP proof WITHOUT any plant semantics.

Frozen invariants preserved:

- G4 semantics are reused, never redesigned (no change to Coordinator, graph,
  ports, transfers, or participant protocol).
- ``CompositionGraph != execution order``: the graph is a declared connectivity
  set; the coordinator's participant/transfer ordering is deterministic by
  structural identity and never a topological sort of the graph.
- Coupling policy remains an ORCHESTRATION policy. This harness applies
  one-window-lag (``explicit_lagged``) semantics at the orchestration level only
  — participants produce from their COMMITTED state (one window behind) and the
  coordinator commits only after every participant advanced. No coupling-policy
  field is added to the graph / binding / port / transfer.
- Transfers are detached and immutable (G4 ``BoundaryTransfer`` deep-freezes the
  payload; no live reference to another participant's state).
- Identity/workspace mismatch fails closed (G4 graph/transfer/coordinator rules).
- A failed window is never reported ``completed`` (coordinator returns
  ``status="failed"`` and stops commits).
- Identical inputs produce identical results (deterministic ordering + exact
  arithmetic only; no hidden state).
- No SH-WTP authority broadening: this module never touches PIM or SH-WTP
  runtimes.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Sequence

from virtual_factory.composition import (
    BoundaryPort,
    BoundaryTransfer,
    CompositionBinding,
    CompositionGraph,
    Coordinator,
    ParticipantError,
    PortCategory,
    PortDirection,
    PortRef,
    WindowOutcome,
)
from virtual_factory.workspace import (
    ScopeMode,
    ScopeSpec,
    StructuralPath,
    Workspace,
    build_workspace,
)

# Orchestration-level coupling policy applied by THIS harness (same frozen
# one-window-lag semantics as G14B). It is deliberately NOT a property of the
# composition graph, ports, bindings, or transfers.
GENERIC_FEDERATION_COUPLING_POLICY = "explicit_lagged"


class GenericFederationError(ValueError):
    """Raised when a generic multi-participant federation invariant is violated."""


def _require_number(value, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GenericFederationError(f"{name} must be a finite number, got {value!r}")
    if not math.isfinite(float(value)):
        raise GenericFederationError(f"{name} must be a finite number, got {value!r}")
    return float(value)


def _require_nonempty(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GenericFederationError(f"{name} must be a non-empty str")
    return value


@dataclass
class SyntheticParticipant:
    """A synthetic, mechanism-neutral G4 ``ExecutableParticipant``.

    Emits exactly one detached transfer per window from its CURRENT committed
    state (one window behind by construction — explicit_lagged applied at the
    orchestration level) and records inbound commits for the NEXT window.

    - pure source: ``in_port is None`` (rejects any inbound transfer);
    - pure sink:   ``out_port is None`` (emits nothing);
    - interior:    consumes one inbound and re-emits ``gain * value``.
    """

    scope_path: StructuralPath
    workspace_id: str
    run_id: str
    out_port: PortRef | None
    in_port: PortRef | None
    binding_id: str | None
    target_ref: PortRef | None
    initial_value: float
    gain: float = 1.0
    source_values: tuple[float, ...] | None = None

    _time_s: float = 0.0
    _active_window_id: str | None = None
    _output_value: float = field(init=False)
    _latest_inbound: float | None = None
    _committed_values: list[float] = field(default_factory=list)
    _last_emitted: float | None = None
    _emit_index: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.scope_path, StructuralPath):
            raise GenericFederationError(
                f"scope_path must be StructuralPath, got {type(self.scope_path).__name__}"
            )
        if self.scope_path.is_workspace_root:
            raise GenericFederationError("participant requires a scope, not the workspace root")
        _require_nonempty(self.workspace_id, "workspace_id")
        _require_nonempty(self.run_id, "run_id")
        _require_number(self.initial_value, "initial_value")
        _require_number(self.gain, "gain")
        if self.out_port is None and self.in_port is None:
            raise GenericFederationError(
                "participant must expose at least one of out_port / in_port"
            )
        if self.source_values is not None:
            if self.in_port is not None:
                raise GenericFederationError(
                    "source_values is only valid for a pure source (in_port=None)"
                )
            if not self.source_values:
                raise GenericFederationError("source_values must not be empty")
            for v in self.source_values:
                _require_number(v, "source_values entry")
        self._output_value = self.initial_value

    # -- G4 participant surface -------------------------------------------
    @property
    def current_time_s(self) -> float:
        return self._time_s

    def prepare_window(self, window_id: str) -> None:
        """Provide the active window context before the coordinator runs it."""
        _require_nonempty(window_id, "window_id")
        self._active_window_id = window_id

    def advance_to(self, target_time_s: float) -> tuple[BoundaryTransfer, ...]:
        """Advance local time (never backward) and emit one detached transfer.

        The emitted value is the participant's CURRENT committed state — one
        window behind by construction. No same-window feed-through.
        """
        if isinstance(target_time_s, bool) or not isinstance(target_time_s, (int, float)):
            raise GenericFederationError("advance_to target must be numeric")
        if not math.isfinite(float(target_time_s)):
            raise GenericFederationError("advance_to target must be finite")
        if target_time_s < self._time_s:
            raise GenericFederationError(
                f"cannot advance backward: {self._time_s!r} -> {target_time_s!r}"
            )
        if self._active_window_id is None:
            raise GenericFederationError("prepare_window must be called before advance_to")

        self._time_s = float(target_time_s)

        if self.out_port is None:
            return ()

        if self.binding_id is None or self.target_ref is None:
            raise GenericFederationError(
                "an emitting participant requires binding_id and target_ref"
            )

        value = self._output_value
        if self.in_port is None and self.source_values is not None:
            index = min(self._emit_index, len(self.source_values) - 1)
            value = self.source_values[index]
            self._emit_index += 1
        transfer = BoundaryTransfer(
            transfer_id=f"{self._active_window_id}::{self.scope_path.as_string()}",
            source=self.out_port,
            target=self.target_ref,
            binding_id=self.binding_id,
            window_id=self._active_window_id,
            simulation_time_s=float(target_time_s),
            workspace_id=self.workspace_id,
            run_id=self.run_id,
            payload={"value": value},
        )
        self._last_emitted = value
        return (transfer,)

    def commit_transfers(
        self, inbound: Sequence[BoundaryTransfer]
    ) -> None:
        """Commit inbound transfers and update the NEXT window's output value.

        A pure source must receive nothing (fail closed). A sink/interior
        participant records the latest committed value and applies its gain for
        the next window (one-window lag).
        """
        if self.in_port is None:
            if inbound:
                raise GenericFederationError(
                    f"pure source {self.scope_path.as_string()!r} received "
                    f"unexpected inbound transfers"
                )
            return

        values: list[float] = []
        for transfer in inbound:
            if not isinstance(transfer, BoundaryTransfer):
                raise GenericFederationError(
                    f"inbound must be BoundaryTransfer, got {type(transfer).__name__}"
                )
            payload = transfer.payload
            if not isinstance(payload, Mapping) or "value" not in payload:
                raise GenericFederationError(
                    f"inbound transfer {transfer.transfer_id!r} payload missing 'value'"
                )
            values.append(float(payload["value"]))

        self._committed_values.extend(values)
        if values:
            self._latest_inbound = values[-1]
            self._output_value = self.gain * self._latest_inbound


class SyntheticFederation:
    """A built generic multi-participant federation (workspace + graph +
    coordinator + participants)."""

    def __init__(
        self,
        workspace: Workspace,
        graph: CompositionGraph,
        coordinator: Coordinator,
        participants: tuple[SyntheticParticipant, ...],
    ) -> None:
        self._workspace = workspace
        self._graph = graph
        self._coordinator = coordinator
        self._participants = participants

    @property
    def workspace(self) -> Workspace:
        return self._workspace

    @property
    def graph(self) -> CompositionGraph:
        return self._graph

    @property
    def coordinator(self) -> Coordinator:
        return self._coordinator

    @property
    def participants(self) -> tuple[SyntheticParticipant, ...]:
        return self._participants

    def run_window(self, window_id: str, target_time_s: float) -> WindowOutcome:
        """Prepare every participant for the window, then run one boundary."""
        for participant in self._participants:
            participant.prepare_window(window_id)
        return self._coordinator.run_window(window_id, target_time_s)


def build_synthetic_federation(
    workspace_id: str,
    participant_ids: tuple[str, ...],
    initial_values: tuple[float, ...],
    *,
    communication_step_s: float = 1.0,
    gain: float = 1.0,
    run_id: str = "run-synthetic-g19",
    source_values: tuple[float, ...] | None = None,
    registration_order: tuple[str, ...] | None = None,
) -> SyntheticFederation:
    """Build a linear-chain synthetic federation of 3+ participants.

    Topology: ``p0 -> p1 -> ... -> pN-1`` with ``N-1`` bindings. Each interior
    participant has one ``in`` port and one ``out`` port; ``p0`` is a pure
    source; ``pN-1`` is a pure sink. All participants share one communication
    step and apply ``explicit_lagged`` at the orchestration level.

    ``source_values`` (optional) makes the source emit a per-window sequence so
    tests can prove no same-window feed-through across consecutive windows.

    ``registration_order`` (optional) is a permutation of ``participant_ids``
    controlling the order participants are registered with the coordinator; it
    lets tests prove outcomes are independent of registration order.
    """
    _require_nonempty(workspace_id, "workspace_id")
    _require_nonempty(run_id, "run_id")
    if len(participant_ids) < 3:
        raise GenericFederationError(
            f"need at least 3 participants, got {len(participant_ids)}"
        )
    if len(initial_values) != len(participant_ids):
        raise GenericFederationError(
            f"initial_values length {len(initial_values)} must match "
            f"participant_ids length {len(participant_ids)}"
        )
    if len(set(participant_ids)) != len(participant_ids):
        raise GenericFederationError("participant_ids must be unique")
    _require_number(communication_step_s, "communication_step_s")
    if communication_step_s <= 0:
        raise GenericFederationError("communication_step_s must be > 0")
    _require_number(gain, "gain")
    if source_values is not None and len(source_values) < 2:
        raise GenericFederationError(
            "source_values must provide at least 2 values for a meaningful "
            "multi-window feed-through proof"
        )
    if registration_order is None:
        registration_order = participant_ids
    else:
        if set(registration_order) != set(participant_ids):
            raise GenericFederationError(
                "registration_order must be a permutation of participant_ids"
            )
        if len(set(registration_order)) != len(registration_order):
            raise GenericFederationError("registration_order must not contain duplicates")

    # G1 Workspace: every participant is an executable-capable scope.
    workspace = build_workspace(
        workspace_id,
        [
            ScopeSpec(scope_id=pid, mode=ScopeMode.EXECUTABLE_CAPABLE)
            for pid in participant_ids
        ],
    )

    paths = [StructuralPath((workspace_id, pid)) for pid in participant_ids]

    ports: list[BoundaryPort] = []
    bindings: list[CompositionBinding] = []
    n = len(participant_ids)
    for i in range(n - 1):
        out_ref = PortRef(owner_scope=paths[i], port_id="out")
        in_ref = PortRef(owner_scope=paths[i + 1], port_id="in")
        ports.append(BoundaryPort(
            ref=out_ref,
            direction=PortDirection.OUT,
            category=PortCategory.MATERIAL,
            unit="value",
        ))
        ports.append(BoundaryPort(
            ref=in_ref,
            direction=PortDirection.IN,
            category=PortCategory.MATERIAL,
            unit="value",
        ))
        bindings.append(CompositionBinding(
            edge_id=f"b{i}",
            source=out_ref,
            target=in_ref,
        ))

    graph = CompositionGraph(
        workspace_id=workspace_id,
        bindings=bindings,
        ports=ports,
    )

    participants: list[SyntheticParticipant] = []
    for i, pid in enumerate(participant_ids):
        if i == 0:
            out_ref = PortRef(owner_scope=paths[0], port_id="out")
            participants.append(SyntheticParticipant(
                scope_path=paths[0],
                workspace_id=workspace_id,
                run_id=run_id,
                out_port=out_ref,
                in_port=None,
                binding_id="b0",
                target_ref=PortRef(owner_scope=paths[1], port_id="in"),
                initial_value=float(initial_values[0]),
                gain=gain,
                source_values=source_values,
            ))
        elif i == n - 1:
            participants.append(SyntheticParticipant(
                scope_path=paths[i],
                workspace_id=workspace_id,
                run_id=run_id,
                out_port=None,
                in_port=PortRef(owner_scope=paths[i], port_id="in"),
                binding_id=None,
                target_ref=None,
                initial_value=float(initial_values[i]),
                gain=gain,
            ))
        else:
            participants.append(SyntheticParticipant(
                scope_path=paths[i],
                workspace_id=workspace_id,
                run_id=run_id,
                out_port=PortRef(owner_scope=paths[i], port_id="out"),
                in_port=PortRef(owner_scope=paths[i], port_id="in"),
                binding_id=f"b{i}",
                target_ref=PortRef(owner_scope=paths[i + 1], port_id="in"),
                initial_value=float(initial_values[i]),
                gain=gain,
            ))

    coordinator = Coordinator(workspace=workspace, graph=graph)
    by_path = {p.scope_path.as_string(): p for p in participants}
    for pid in registration_order:
        coordinator.register(by_path[StructuralPath((workspace_id, pid)).as_string()])

    return SyntheticFederation(
        workspace=workspace,
        graph=graph,
        coordinator=coordinator,
        participants=tuple(participants),
    )
