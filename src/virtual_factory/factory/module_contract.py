"""Typed module contract for side-effect-free factory proposals."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum, IntEnum
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from virtual_factory.factory.run_context import SimTick, coerce_tick

if TYPE_CHECKING:
    from virtual_factory.factory.event_ledger import CommittedEvent, ReadSnapshot


class ModuleContractError(ValueError):
    """Raised when a module contract invariant is violated."""


class UnsupportedCapabilityError(ModuleContractError):
    """Raised when a module lacks a capability required by the coordinator."""


class ProposalError(ModuleContractError):
    """Raised when a proposal is malformed or violates isolation."""


class ModuleCapability(str, Enum):
    PROPOSE = "propose"
    APPLY = "apply"
    SNAPSHOT = "snapshot"
    RESTORE = "restore"


class CausalPhase(IntEnum):
    INTAKE = 10
    PROCESS = 20
    FINISH = 30
    RECEIPT = 40


SOURCE_KINDS = frozenset({"SIMULATED", "REPLAYED_SOURCE"})
DEFINITION_PROVENANCES = frozenset(
    {
        "PDF_EXPLICIT",
        "VF_ACCEPTED_BASELINE",
        "MES_AS_BUILT",
        "SA_INFERENCE",
        "SYNTHETIC_ASSUMPTION",
        "PENDING_TIPA",
    }
)


def freeze_payload(value: Any, path: str = "payload") -> Any:
    """Return a deeply immutable JSON-compatible copy of *value*."""
    if callable(value):
        raise ModuleContractError(f"{path}: callables are not allowed")
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise ModuleContractError(f"{path}: non-finite float is not allowed")
        return value
    if isinstance(value, (list, tuple)):
        return tuple(
            freeze_payload(item, f"{path}[{index}]")
            for index, item in enumerate(value)
        )
    if isinstance(value, Mapping):
        items: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ModuleContractError(
                    f"{path}: mapping keys must be str, got {type(key).__name__}"
                )
            items[key] = freeze_payload(item, f"{path}.{key}")
        return MappingProxyType(items)
    raise ModuleContractError(
        f"{path}: unsupported type {type(value).__name__}"
    )


def thaw_payload(value: Any) -> Any:
    """Return a detached plain-data copy of a frozen payload."""
    if isinstance(value, Mapping):
        return {key: thaw_payload(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [thaw_payload(item) for item in value]
    return value


def _require_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ModuleContractError(f"{name} must be a non-empty str")
    return value


@dataclass(frozen=True, slots=True)
class PortSpec:
    port_id: str
    data_type: str

    def __post_init__(self) -> None:
        _require_text(self.port_id, "port_id")
        _require_text(self.data_type, "data_type")


def _normalize_ports(ports: tuple[PortSpec, ...], name: str) -> tuple[PortSpec, ...]:
    normalized: list[PortSpec] = []
    seen: set[str] = set()
    for index, port in enumerate(ports):
        if not isinstance(port, PortSpec):
            raise ModuleContractError(
                f"{name}[{index}] must be PortSpec, got {type(port).__name__}"
            )
        if port.port_id in seen:
            raise ModuleContractError(f"{name}: duplicate port_id {port.port_id!r}")
        seen.add(port.port_id)
        normalized.append(port)
    return tuple(normalized)


@dataclass(frozen=True, slots=True)
class ModuleManifest:
    module_id: str
    version: str
    fidelity: str
    input_ports: tuple[PortSpec, ...]
    output_ports: tuple[PortSpec, ...]
    capabilities: frozenset[ModuleCapability]
    ownership: str

    def __post_init__(self) -> None:
        _require_text(self.module_id, "module_id")
        _require_text(self.version, "version")
        _require_text(self.fidelity, "fidelity")
        _require_text(self.ownership, "ownership")
        if not isinstance(self.input_ports, tuple):
            object.__setattr__(self, "input_ports", tuple(self.input_ports))
        if not isinstance(self.output_ports, tuple):
            object.__setattr__(self, "output_ports", tuple(self.output_ports))
        object.__setattr__(
            self, "input_ports", _normalize_ports(self.input_ports, "input_ports")
        )
        object.__setattr__(
            self, "output_ports", _normalize_ports(self.output_ports, "output_ports")
        )
        try:
            capabilities = frozenset(
                ModuleCapability(item) for item in self.capabilities
            )
        except ValueError as exc:
            raise ModuleContractError(f"invalid capability: {exc}") from exc
        object.__setattr__(self, "capabilities", capabilities)

    def supports(self, capability: ModuleCapability) -> bool:
        return capability in self.capabilities


@dataclass(frozen=True, slots=True)
class EventProposal:
    tick: SimTick
    causal_phase: CausalPhase
    module_id: str
    local_sequence: int
    event_id: str
    event_type: str
    definition_digest: str
    payload: Any = None
    causation_id: str | None = None
    correlation_id: str | None = None
    source_id: str | None = None
    source_kind: str = "SIMULATED"
    definition_provenance: str = "SYNTHETIC_ASSUMPTION"

    def __post_init__(self) -> None:
        object.__setattr__(self, "tick", coerce_tick(self.tick))
        if not isinstance(self.causal_phase, CausalPhase):
            try:
                object.__setattr__(
                    self, "causal_phase", CausalPhase(self.causal_phase)
                )
            except ValueError as exc:
                raise ProposalError(
                    f"invalid causal_phase: {self.causal_phase!r}"
                ) from exc
        _require_text(self.module_id, "module_id")
        if isinstance(self.local_sequence, bool):
            raise ProposalError("local_sequence must be int, not bool")
        if not isinstance(self.local_sequence, int) or self.local_sequence < 0:
            raise ProposalError("local_sequence must be int >= 0")
        _require_text(self.event_id, "event_id")
        _require_text(self.event_type, "event_type")
        _require_text(self.definition_digest, "definition_digest")
        _require_text(self.source_kind, "source_kind")
        _require_text(self.definition_provenance, "definition_provenance")
        if self.source_kind not in SOURCE_KINDS:
            raise ProposalError(
                f"source_kind must be one of {sorted(SOURCE_KINDS)}, "
                f"got {self.source_kind!r}"
            )
        if self.definition_provenance not in DEFINITION_PROVENANCES:
            raise ProposalError(
                "definition_provenance must be one of "
                f"{sorted(DEFINITION_PROVENANCES)}, "
                f"got {self.definition_provenance!r}"
            )
        for name, value in (
            ("causation_id", self.causation_id),
            ("correlation_id", self.correlation_id),
            ("source_id", self.source_id),
        ):
            if value is not None:
                _require_text(value, name)
        object.__setattr__(self, "payload", freeze_payload(self.payload))

    def sort_key(self) -> tuple[int, int, str, int, str]:
        return (
            self.tick.tick_us,
            int(self.causal_phase),
            self.module_id,
            self.local_sequence,
            self.event_id,
        )


class ISimulationModule(ABC):
    """Synthetic module protocol; proposals never mutate committed state."""

    manifest: ModuleManifest

    @abstractmethod
    def initialize(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def next_event_time(self, horizon: SimTick) -> SimTick | None:
        raise NotImplementedError

    @abstractmethod
    def propose(
        self, horizon: SimTick, read_snapshot: ReadSnapshot
    ) -> tuple[EventProposal, ...]:
        raise NotImplementedError

    @abstractmethod
    def apply_committed(
        self, event: CommittedEvent, read_snapshot: ReadSnapshot
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def snapshot(self) -> Mapping[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def restore(self, state: Mapping[str, Any]) -> None:
        raise NotImplementedError
