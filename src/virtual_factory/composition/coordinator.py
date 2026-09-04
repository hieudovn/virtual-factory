"""Deterministic composition coordinator (G4).

The Coordinator is a composition service — NOT a domain simulation engine. It
owns composition sequencing/context only; child runtimes keep their domain truth.
It never reaches into participant domain state except through the participant/
boundary contract.

Frozen phase semantics (validated in tests):

    validate -> advance participants -> stage outputs -> validate transfers
             -> commit inputs -> finalize window outcome

- deterministic participant/transfer ordering independent of registration or
  declaration order (ordered by structural identity);
- fail closed: graph/port/binding problems detectable before execution stop the
  window; participant advance failure stops the window before later exchange/
  commit; transfer validation failure prevents boundary commit; commit failure
  stops further commits (one explicit deterministic policy);
- no claim of transactional rollback of already-advanced child runtime state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from virtual_factory.composition.graph import CompositionGraph
from virtual_factory.composition.participant import ExecutableParticipant
from virtual_factory.composition.ports import (
    PortError,
    PortRef,
    check_port_compatibility,
)
from virtual_factory.composition.transfer import BoundaryTransfer
from virtual_factory.workspace.identity import StructuralPath
from virtual_factory.workspace.model import Workspace


class CoordinationError(ValueError):
    """Raised when a coordination invariant is violated."""


@dataclass(frozen=True, slots=True)
class WindowOutcome:
    """The outcome of one authorized coordination boundary."""

    window_id: str
    target_time_s: float
    participants: tuple[str, ...]  # deterministic scope-path order
    committed: tuple[str, ...]     # transfer ids committed (deterministic)
    status: str                    # "completed" | "failed"
    failure: str | None = None


def _failure(
    window_id: str,
    target_time_s: float,
    participants: tuple[str, ...],
    committed: tuple[str, ...],
    failure: str,
) -> WindowOutcome:
    return WindowOutcome(
        window_id=window_id,
        target_time_s=target_time_s,
        participants=participants,
        committed=committed,
        status="failed",
        failure=failure,
    )


class Coordinator:
    """Composition service that advances registered executable participants
    through one authorized coordination boundary at a time."""

    def __init__(self, workspace: Workspace, graph: CompositionGraph) -> None:
        if not isinstance(workspace, Workspace):
            raise CoordinationError("workspace must be a G1 Workspace")
        if not isinstance(graph, CompositionGraph):
            raise CoordinationError("graph must be a CompositionGraph")
        if graph.workspace_id != workspace.workspace_id:
            raise CoordinationError(
                f"graph workspace {graph.workspace_id!r} does not match "
                f"workspace {workspace.workspace_id!r}"
            )
        self._workspace = workspace
        self._graph = graph
        self._participants: dict[str, ExecutableParticipant] = {}

    @property
    def graph(self) -> CompositionGraph:
        return self._graph

    @property
    def participants(self) -> tuple[str, ...]:
        """Registered participant scope paths in deterministic order."""
        return tuple(sorted(self._participants.keys()))

    def register(self, participant: ExecutableParticipant) -> None:
        """Register one executable participant.

        The owning scope must exist and be executable-capable; container-only
        scopes cannot be registered; duplicate registration fails closed.
        """
        scope_path = getattr(participant, "scope_path", None)
        if not isinstance(scope_path, StructuralPath):
            raise CoordinationError(
                "participant must expose a StructuralPath scope_path"
            )
        try:
            scope = self._workspace.resolve_scope(scope_path)  # dangling -> fail
        except Exception as exc:  # noqa: BLE001
            raise CoordinationError(
                f"participant scope {scope_path.as_string()!r} cannot be "
                f"resolved in workspace {self._workspace.workspace_id!r}: {exc}"
            ) from exc
        if scope.is_container_only:
            raise CoordinationError(
                f"container-only scope {scope_path.as_string()!r} cannot be "
                f"registered as an executable participant"
            )
        for attr in ("advance_to", "commit_transfers"):
            if not callable(getattr(participant, attr, None)):
                raise CoordinationError(
                    f"participant for {scope_path.as_string()!r} must expose "
                    f"callable {attr}"
                )
        key = scope_path.as_string()
        if key in self._participants:
            raise CoordinationError(
                f"duplicate participant registration for scope {key!r}"
            )
        self._participants[key] = participant

    def run_window(
        self, window_id: str, target_time_s: float
    ) -> WindowOutcome:
        """Execute one coordination boundary deterministically and fail-closed."""
        if not isinstance(window_id, str) or not window_id.strip():
            raise CoordinationError("window_id must be a non-empty str")
        if isinstance(target_time_s, bool) or not isinstance(
            target_time_s, (int, float)
        ):
            raise CoordinationError("target_time_s must be numeric, not bool")
        if target_time_s < 0:
            raise CoordinationError("target_time_s must be >= 0")

        order = tuple(sorted(self._participants.keys()))

        # 1. validate graph/bindings before execution
        try:
            self._validate_graph_bindings()
        except CoordinationError as exc:
            return _failure(
                window_id, target_time_s, order, (), f"graph validation failed: {exc}"
            )

        # 2. advance participants (deterministic order) + stage outputs
        staged: dict[str, BoundaryTransfer] = {}
        for key in order:
            participant = self._participants[key]
            try:
                outputs = participant.advance_to(target_time_s)
            except Exception as exc:  # noqa: BLE001 — fail closed on any advance failure
                return _failure(
                    window_id,
                    target_time_s,
                    order,
                    (),
                    f"participant advance failed for {key}: {exc}",
                )
            if not isinstance(outputs, (tuple, list)):
                return _failure(
                    window_id,
                    target_time_s,
                    order,
                    (),
                    f"advance_to for {key} must return a sequence of transfers",
                )
            for transfer in outputs:
                if not isinstance(transfer, BoundaryTransfer):
                    return _failure(
                        window_id,
                        target_time_s,
                        order,
                        (),
                        f"advance_to for {key} returned a non-BoundaryTransfer",
                    )
                if transfer.transfer_id in staged:
                    return _failure(
                        window_id,
                        target_time_s,
                        order,
                        (),
                        f"duplicate transfer id {transfer.transfer_id!r}",
                    )
                staged[transfer.transfer_id] = transfer

        # 3. validate all staged transfers
        try:
            self._validate_transfers(staged)
        except CoordinationError as exc:
            return _failure(
                window_id,
                target_time_s,
                order,
                (),
                f"transfer validation failed: {exc}",
            )

        # 4. commit inputs deterministically (grouped by target scope path,
        #    then transfer id). A commit failure stops further commits.
        committed: list[str] = []
        inbound_by_target: dict[str, list[BoundaryTransfer]] = {}
        for transfer in sorted(
            staged.values(),
            key=lambda t: (t.target.owner_scope.as_string(), t.transfer_id),
        ):
            inbound_by_target.setdefault(
                transfer.target.owner_scope.as_string(), []
            ).append(transfer)
        for target_key in sorted(inbound_by_target):
            transfers = tuple(inbound_by_target[target_key])
            try:
                self._participants[target_key].commit_transfers(transfers)
            except Exception as exc:  # noqa: BLE001
                return _failure(
                    window_id,
                    target_time_s,
                    order,
                    tuple(committed),
                    f"commit failure for {target_key}: {exc}",
                )
            committed.extend(t.transfer_id for t in transfers)

        return WindowOutcome(
            window_id=window_id,
            target_time_s=target_time_s,
            participants=order,
            committed=tuple(committed),
            status="completed",
        )

    # ── internal validation ──────────────────────────────────────

    def _validate_graph_bindings(self) -> None:
        """Every declared binding must be port-compatible (detected pre-advance)."""
        for binding in self._graph.bindings:
            source_port = self._graph.registry.require(binding.source)
            target_port = self._graph.registry.require(binding.target)
            try:
                check_port_compatibility(source_port, target_port)
            except PortError as exc:
                raise CoordinationError(
                    f"invalid binding {binding.edge_id!r}: {exc}"
                ) from exc

    def _validate_transfers(self, staged: dict[str, BoundaryTransfer]) -> None:
        """Fail-closed transfer validation before any boundary commit."""
        for transfer in staged.values():
            if transfer.workspace_id != self._graph.workspace_id:
                raise CoordinationError(
                    f"transfer {transfer.transfer_id!r} workspace "
                    f"{transfer.workspace_id!r} does not match graph workspace "
                    f"{self._graph.workspace_id!r}"
                )
            if not self._graph.has_binding(transfer.source, transfer.target):
                raise CoordinationError(
                    f"undeclared port exchange {transfer.source.as_string()!r} "
                    f"-> {transfer.target.as_string()!r}"
                )
            binding = self._binding_for(transfer.binding_id, transfer.source, transfer.target)
            if binding is None:
                raise CoordinationError(
                    f"transfer {transfer.transfer_id!r} references unknown/ "
                    f"mismatched binding {transfer.binding_id!r}"
                )
            source_port = self._graph.registry.require(transfer.source)
            target_port = self._graph.registry.require(transfer.target)
            try:
                check_port_compatibility(source_port, target_port)
            except PortError as exc:
                raise CoordinationError(
                    f"transfer {transfer.transfer_id!r}: {exc}"
                ) from exc
            for ref in (transfer.source, transfer.target):
                key = ref.owner_scope.as_string()
                if key not in self._participants:
                    raise CoordinationError(
                        f"transfer endpoint scope {key!r} is not a registered "
                        f"participant"
                    )

        # Baseline input has at most one producer; reject implicit many-to-one.
        producers_by_target: dict[str, set[str]] = {}
        for transfer in staged.values():
            producers_by_target.setdefault(
                transfer.target.as_string(), set()
            ).add(transfer.source.as_string())
        for target, sources in sorted(producers_by_target.items()):
            if len(sources) > 1:
                raise CoordinationError(
                    f"implicit multi-producer input at {target!r}: "
                    f"{sorted(sources)}"
                )

    def _binding_for(self, edge_id: str, source: PortRef, target: PortRef):
        for binding in self._graph.bindings:
            if binding.edge_id == edge_id:
                if binding.source == source and binding.target == target:
                    return binding
                return None
        return None
