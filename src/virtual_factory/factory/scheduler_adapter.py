"""Serial deterministic factory coordinator and checkpoint adapter."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from virtual_factory.factory.event_ledger import (
    CommittedEvent,
    EventLedger,
    LedgerError,
    ReadSnapshot,
    canonical_digest,
    thaw_payload,
)
from virtual_factory.factory.module_contract import (
    CausalPhase,
    EventProposal,
    ISimulationModule,
    ModuleCapability,
    ModuleContractError,
    ModuleManifest,
    ProposalError,
    UnsupportedCapabilityError,
    freeze_payload,
)
from virtual_factory.factory.run_context import (
    FactoryRunContext,
    LifecycleState,
    SimTick,
    coerce_tick,
)

_REQUIRED_CAPABILITIES = (
    ModuleCapability.PROPOSE,
    ModuleCapability.APPLY,
    ModuleCapability.SNAPSHOT,
    ModuleCapability.RESTORE,
)


class CoordinatorError(RuntimeError):
    """Base error for coordinator failures."""


class ModuleRegistrationError(CoordinatorError):
    """Raised when a module cannot be registered."""


class SchedulerError(CoordinatorError):
    """Raised when coordinator scheduling invariants are violated."""


class PastEventError(SchedulerError):
    """Raised when a module proposes or schedules an event in the past."""


class SameTickBoundError(SchedulerError):
    """Raised when a same-tick fixed point exceeds its bound."""


class CausalCycleError(SchedulerError):
    """Raised when same-tick events cannot be causally satisfied."""


class CommitError(CoordinatorError):
    """Raised when applying a committed event fails."""


class CheckpointError(CoordinatorError):
    """Raised when a checkpoint is malformed or incompatible."""


def _require_mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CheckpointError(f"{name} must be a mapping")
    return value


def _require_int(value: object, name: str, minimum: int = 0) -> int:
    if isinstance(value, bool):
        raise CheckpointError(f"{name} must be int, not bool")
    if not isinstance(value, int) or value < minimum:
        raise CheckpointError(f"{name} must be int >= {minimum}")
    return value


def _require_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CheckpointError(f"{name} must be a non-empty str")
    return value


class SerialFactoryCoordinator:
    """One serial coordinator with commit authority over registered modules."""

    def __init__(
        self, context: FactoryRunContext, *, max_events_per_tick: int = 1000
    ) -> None:
        if not isinstance(context, FactoryRunContext):
            raise CoordinatorError("context must be a FactoryRunContext")
        if isinstance(max_events_per_tick, bool):
            raise CoordinatorError("max_events_per_tick must be int, not bool")
        if (
            not isinstance(max_events_per_tick, int)
            or max_events_per_tick <= 0
        ):
            raise CoordinatorError("max_events_per_tick must be int > 0")
        self._context = context
        self._max_events_per_tick = max_events_per_tick
        self._modules: dict[str, ISimulationModule] = {}
        self._ledger = EventLedger(factory_run_id=context.run_id)

    @property
    def context(self) -> FactoryRunContext:
        return self._context

    @property
    def ledger(self) -> EventLedger:
        return self._ledger

    @property
    def module_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._modules))

    def register_module(self, module: ISimulationModule) -> str:
        if not isinstance(module, ISimulationModule):
            raise ModuleRegistrationError(
                f"module must be ISimulationModule, got {type(module).__name__}"
            )
        manifest = getattr(module, "manifest", None)
        if not isinstance(manifest, ModuleManifest):
            raise ModuleRegistrationError("module must expose a ModuleManifest")
        if manifest.module_id in self._modules:
            raise ModuleRegistrationError(
                f"duplicate module_id: {manifest.module_id!r}"
            )
        missing = [
            capability.value
            for capability in _REQUIRED_CAPABILITIES
            if not manifest.supports(capability)
        ]
        if missing:
            raise UnsupportedCapabilityError(
                f"module {manifest.module_id!r} lacks capabilities: {missing}"
            )
        self._modules[manifest.module_id] = module
        return manifest.module_id

    def initialize(self) -> None:
        if self._context.state is not LifecycleState.INITIALIZED:
            raise CoordinatorError(
                f"coordinator initialize requires INITIALIZED, "
                f"got {self._context.state.value}"
            )
        for module_id in sorted(self._modules):
            self._modules[module_id].initialize()

    def read_snapshot(self) -> ReadSnapshot:
        return self._ledger.read_snapshot(
            self._context.tick, self._context.generation
        )

    def _mark_failed(self, reason: str) -> None:
        if self._context.state in (
            LifecycleState.RUNNING,
            LifecycleState.PAUSED,
        ):
            try:
                self._context.fail(reason)
            except Exception:
                pass

    def _detached_snapshot(
        self, module_id: str, module: ISimulationModule
    ) -> dict[str, Any]:
        raw = module.snapshot()
        if not isinstance(raw, Mapping):
            raise ProposalError(
                f"module {module_id!r} snapshot must be a mapping"
            )
        try:
            return thaw_payload(freeze_payload(dict(raw)))
        except ModuleContractError as exc:
            raise ProposalError(
                f"module {module_id!r} snapshot is not canonical: {exc}"
            ) from exc

    def _proposal_from_module(
        self,
        module_id: str,
        module: ISimulationModule,
        horizon: SimTick,
        snapshot: ReadSnapshot,
    ) -> tuple[EventProposal, ...]:
        before = self._detached_snapshot(module_id, module)
        before_digest = canonical_digest(before)
        try:
            raw = module.propose(horizon, snapshot)
        except Exception as exc:
            try:
                module.restore(before)
            except Exception as restore_exc:
                self._mark_failed(
                    f"module {module_id!r} propose and restore failed"
                )
                raise ProposalError(
                    f"module {module_id!r} propose failed: {exc}; "
                    f"restore also failed: {restore_exc}"
                ) from exc
            raise ProposalError(
                f"module {module_id!r} propose failed: {exc}"
            ) from exc
        try:
            after = self._detached_snapshot(module_id, module)
        except ProposalError as exc:
            try:
                module.restore(before)
            except Exception as restore_exc:
                self._mark_failed(
                    f"module {module_id!r} post-propose snapshot/restore failed"
                )
                raise ProposalError(
                    f"module {module_id!r} post-propose snapshot failed: {exc}; "
                    f"restore also failed: {restore_exc}"
                ) from exc
            raise
        if canonical_digest(after) != before_digest:
            try:
                module.restore(before)
            except Exception as restore_exc:
                self._mark_failed(
                    f"module {module_id!r} propose mutation/restore failed"
                )
                raise ProposalError(
                    f"module {module_id!r} propose mutated state and restore "
                    f"failed: {restore_exc}"
                ) from restore_exc
            raise ProposalError(
                f"module {module_id!r} propose mutated module state"
            )
        if not isinstance(raw, (tuple, list)):
            raise ProposalError(
                f"module {module_id!r} propose must return a tuple/list"
            )
        proposals: list[EventProposal] = []
        for index, proposal in enumerate(raw):
            if not isinstance(proposal, EventProposal):
                raise ProposalError(
                    f"module {module_id!r} proposal[{index}] is not EventProposal"
                )
            if proposal.module_id != module_id:
                raise ProposalError(
                    f"module {module_id!r} proposed for {proposal.module_id!r}"
                )
            if proposal.tick < self._context.tick:
                raise PastEventError(
                    f"module {module_id!r} proposed past tick "
                    f"{proposal.tick.tick_us} < {self._context.tick.tick_us}"
                )
            if proposal.tick > horizon:
                raise ProposalError(
                    f"module {module_id!r} proposed beyond horizon: "
                    f"{proposal.tick.tick_us} > {horizon.tick_us}"
                )
            proposals.append(proposal)
        return tuple(proposals)

    def _next_candidate(
        self, horizon: SimTick
    ) -> SimTick | None:
        candidates: list[SimTick] = []
        for module_id in sorted(self._modules):
            module = self._modules[module_id]
            try:
                value = module.next_event_time(horizon)
            except Exception as exc:
                raise ProposalError(
                    f"module {module_id!r} next_event_time failed: {exc}"
                ) from exc
            if value is None:
                continue
            tick = coerce_tick(value)
            if tick < self._context.tick:
                raise PastEventError(
                    f"module {module_id!r} next event is in the past: "
                    f"{tick.tick_us} < {self._context.tick.tick_us}"
                )
            if tick <= horizon:
                candidates.append(tick)
        if not candidates:
            return None
        return min(candidates)

    def _gather_same_tick(
        self, horizon: SimTick
    ) -> list[EventProposal]:
        snapshot = self.read_snapshot()
        proposals: list[EventProposal] = []
        for module_id in sorted(self._modules):
            module = self._modules[module_id]
            next_tick = module.next_event_time(horizon)
            if next_tick is None:
                continue
            next_tick = coerce_tick(next_tick)
            if next_tick < self._context.tick:
                raise PastEventError(
                    f"module {module_id!r} next event is in the past: "
                    f"{next_tick.tick_us} < {self._context.tick.tick_us}"
                )
            if next_tick > horizon:
                continue
            for proposal in self._proposal_from_module(
                module_id, module, horizon, snapshot
            ):
                if proposal.tick == self._context.tick:
                    proposals.append(proposal)
        return proposals

    def _commit(self, proposal: EventProposal) -> CommittedEvent:
        module = self._modules[proposal.module_id]
        event = CommittedEvent(
            factory_run_id=self._context.run_id,
            generation=self._context.generation,
            module_id=proposal.module_id,
            local_sequence=proposal.local_sequence,
            tick=proposal.tick,
            event_id=proposal.event_id,
            event_type=proposal.event_type,
            sequence=self._ledger.cursor + 1,
            causal_phase=proposal.causal_phase,
            definition_digest=proposal.definition_digest,
            payload=proposal.payload,
            causation_id=proposal.causation_id,
            correlation_id=proposal.correlation_id,
            source_id=proposal.source_id,
            source_kind=proposal.source_kind,
            definition_provenance=proposal.definition_provenance,
        )
        self._ledger.check_append(event)
        before = self._detached_snapshot(proposal.module_id, module)
        try:
            module.apply_committed(event, self.read_snapshot())
        except Exception as exc:
            try:
                module.restore(before)
            except Exception as restore_exc:
                self._mark_failed(
                    f"module {proposal.module_id!r} apply and restore failed"
                )
                raise CommitError(
                    f"module {proposal.module_id!r} apply_committed failed: "
                    f"{exc}; restore also failed: {restore_exc}"
                ) from exc
            raise CommitError(
                f"module {proposal.module_id!r} apply_committed failed: {exc}"
            ) from exc
        try:
            self._ledger.append(event)
        except Exception as exc:
            try:
                module.restore(before)
            except Exception as restore_exc:
                self._mark_failed(
                    f"module {proposal.module_id!r} ledger append and restore failed"
                )
                raise CommitError(
                    f"ledger append failed: {exc}; module restore also failed: "
                    f"{restore_exc}"
                ) from exc
            raise
        return event

    def run_until(self, horizon: SimTick | int) -> tuple[CommittedEvent, ...]:
        target = coerce_tick(horizon)
        if self._context.state is not LifecycleState.RUNNING:
            raise CoordinatorError(
                f"run_until requires RUNNING, got {self._context.state.value}"
            )
        if target < self._context.tick:
            raise PastEventError(
                f"horizon {target.tick_us} < current {self._context.tick.tick_us}"
            )

        committed: list[CommittedEvent] = []
        while True:
            candidate = self._next_candidate(target)
            if candidate is None:
                break
            if candidate < self._context.tick:
                raise PastEventError(
                    f"candidate {candidate.tick_us} is in the past"
                )
            if candidate > self._context.tick:
                self._context.advance_to(candidate)

            committed_this_tick = 0
            while True:
                same_tick = self._gather_same_tick(target)
                if not same_tick:
                    break
                eligible = [
                    proposal
                    for proposal in same_tick
                    if proposal.causation_id is None
                    or self._ledger.has_event_id(proposal.causation_id)
                ]
                if not eligible:
                    raise CausalCycleError(
                        "same-tick proposals cannot satisfy causal ordering at "
                        f"tick {self._context.tick.tick_us}"
                    )
                eligible.sort(key=EventProposal.sort_key)
                for proposal in eligible:
                    if committed_this_tick >= self._max_events_per_tick:
                        raise SameTickBoundError(
                            "same-tick fixed point exceeded "
                            f"{self._max_events_per_tick} events at tick "
                            f"{self._context.tick.tick_us}"
                        )
                    committed.append(self._commit(proposal))
                    committed_this_tick += 1
            if committed_this_tick == 0:
                raise SchedulerError(
                    "no same-tick progress at tick "
                    f"{self._context.tick.tick_us}"
                )

        return tuple(committed)

    def _header_payload(self) -> dict[str, Any]:
        header = self._context.header
        return {
            "workspace_digest": header.workspace_digest,
            "config_digest": header.config_digest,
            "seed": header.seed,
            "model_revision": header.model_revision,
            "epoch_utc": header.epoch_utc.isoformat(),
            "mode": header.mode.value,
            "shift_timezone": header.shift_timezone,
        }

    def checkpoint(self) -> dict[str, Any]:
        if self._context.state is LifecycleState.RUNNING:
            raise CheckpointError("checkpoint requires a non-RUNNING safe point")
        module_snapshots: dict[str, Any] = {}
        for module_id in sorted(self._modules):
            raw = self._modules[module_id].snapshot()
            if not isinstance(raw, Mapping):
                raise CheckpointError(
                    f"module {module_id!r} snapshot must be a mapping"
                )
            module_snapshots[module_id] = thaw_payload(
                freeze_payload(dict(raw))
            )
        return {
            "schema_version": "1.0",
            "factory_run_id": self._context.run_id,
            "header": self._header_payload(),
            "generation": self._context.generation,
            "run_state": self._context.state.value,
            "tick_us": self._context.tick.tick_us,
            "pending_events": [],
            "ledger": [event.to_dict() for event in self._ledger.events],
            "ledger_cursor": self._ledger.cursor,
            "ledger_digest": self._ledger.digest(),
            "module_snapshots": module_snapshots,
        }

    def restore(self, checkpoint: Mapping[str, Any]) -> None:
        data = _require_mapping(checkpoint, "checkpoint")
        if data.get("schema_version") != "1.0":
            raise CheckpointError("unsupported checkpoint schema_version")
        if data.get("factory_run_id") != self._context.run_id:
            raise CheckpointError("checkpoint factory_run_id mismatch")
        expected_header = self._header_payload()
        header_data = _require_mapping(data.get("header"), "header")
        if set(header_data) != set(expected_header):
            raise CheckpointError("checkpoint header fields mismatch")
        for field, expected in expected_header.items():
            if header_data.get(field) != expected:
                raise CheckpointError(
                    f"checkpoint header {field} mismatch"
                )
        generation = _require_int(data.get("generation"), "generation")
        if generation != self._context.generation:
            raise CheckpointError("checkpoint generation mismatch")
        state_value = _require_text(data.get("run_state"), "run_state")
        try:
            state = LifecycleState(state_value)
        except ValueError as exc:
            raise CheckpointError(f"invalid run_state: {state_value!r}") from exc
        tick = SimTick(_require_int(data.get("tick_us"), "tick_us"))

        pending_events = data.get("pending_events")
        if not isinstance(pending_events, list):
            raise CheckpointError("checkpoint pending_events must be a list")
        if pending_events:
            raise CheckpointError(
                "checkpoint pending_events are not supported and must be empty"
            )
        ledger_cursor = _require_int(
            data.get("ledger_cursor"), "ledger_cursor"
        )
        ledger_data = data.get("ledger")
        if not isinstance(ledger_data, list):
            raise CheckpointError("checkpoint ledger must be a list")
        if ledger_cursor != len(ledger_data):
            raise CheckpointError("checkpoint ledger_cursor mismatch")
        temp = EventLedger(factory_run_id=self._context.run_id)
        try:
            for item in ledger_data:
                if not isinstance(item, Mapping):
                    raise CheckpointError("ledger entry must be a mapping")
                temp.append(CommittedEvent.from_dict(item))
        except (LedgerError, TypeError, ValueError) as exc:
            raise CheckpointError(f"invalid ledger: {exc}") from exc

        expected_digest = _require_text(
            data.get("ledger_digest"), "ledger_digest"
        )
        if temp.digest() != expected_digest:
            raise CheckpointError("checkpoint ledger digest mismatch")

        snapshots = _require_mapping(
            data.get("module_snapshots"), "module_snapshots"
        )
        if set(snapshots) != set(self._modules):
            raise CheckpointError("checkpoint module set mismatch")

        current_snapshots = {
            module_id: self._modules[module_id].snapshot()
            for module_id in sorted(self._modules)
        }
        try:
            for module_id in sorted(self._modules):
                module_snapshot = _require_mapping(
                    snapshots[module_id],
                    f"module_snapshots[{module_id!r}]",
                )
                self._modules[module_id].restore(dict(module_snapshot))
        except Exception as exc:
            for module_id in sorted(current_snapshots):
                self._modules[module_id].restore(current_snapshots[module_id])
            if isinstance(exc, CheckpointError):
                raise
            raise CheckpointError(f"module restore failed: {exc}") from exc

        self._context = FactoryRunContext(
            self._context.run_id,
            self._context.header,
            generation=generation,
            state=state,
            tick=tick,
        )
        self._ledger = temp

    def trace_digest(self) -> str:
        return canonical_digest([event.to_dict() for event in self._ledger.events])
