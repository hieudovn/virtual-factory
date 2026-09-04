"""Immutable staged boundary transfer (G4).

Cross-scope data exchange uses detached transfer values/envelopes — never live
references to another runtime's mutable state. A transfer is produced (staged)
by a source participant and committed later to a consumer participant through
its declared boundary interface.

Frozen semantics:

- source/target are authoritative ``PortRef`` boundary endpoints;
- transfer carries the binding identity and coordination window/time;
- workspace identity must match both endpoint scopes (fail-closed);
- payload is DEEP-FROZEN and JSON-compatible — no callable, runtime object or
  mutable-state reference is allowed;
- the payload cannot retroactively mutate the producer runtime and the consumer
  cannot mutate the producer state through it;
- no PIM canonical identity is fabricated.
"""

from __future__ import annotations

import math
import types
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from virtual_factory.composition.ports import PortError, PortRef
from virtual_factory.workspace.identity import StructuralPath


class TransferError(ValueError):
    """Raised when a boundary-transfer invariant is violated."""


def _freeze(value: Any, path: str) -> Any:
    """Recursively validate/freeze a JSON-compatible payload (detached copy)."""
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise TransferError(f"{path}: non-finite float is not allowed")
        return value
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v, f"{path}[{i}]") for i, v in enumerate(value))
    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for k, v in value.items():
            if not isinstance(k, str):
                raise TransferError(f"{path}: mapping keys must be str")
            frozen[k] = _freeze(v, f"{path}.{k}")
        return types.MappingProxyType(frozen)
    if callable(value):
        raise TransferError(f"{path}: callables are not allowed in transfer payload")
    raise TransferError(
        f"{path}: unsupported payload type {type(value).__name__!r} "
        f"(only JSON-compatible data is allowed)"
    )


def _to_plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_to_plain(v) for v in value]
    return value


def _require_nonempty(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise TransferError(f"{name} must be a non-empty str")


@dataclass(frozen=True, slots=True)
class BoundaryTransfer:
    """One detached, immutable boundary exchange value."""

    transfer_id: str
    source: PortRef
    target: PortRef
    binding_id: str
    window_id: str
    simulation_time_s: float
    workspace_id: str
    run_id: str | None = None
    payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_nonempty(self.transfer_id, "transfer_id")
        _require_nonempty(self.binding_id, "binding_id")
        _require_nonempty(self.window_id, "window_id")
        _require_nonempty(self.workspace_id, "workspace_id")
        if not isinstance(self.source, PortRef):
            raise TransferError(f"source must be PortRef, got {type(self.source).__name__}")
        if not isinstance(self.target, PortRef):
            raise TransferError(f"target must be PortRef, got {type(self.target).__name__}")
        if self.run_id is not None:
            _require_nonempty(self.run_id, "run_id")
        if isinstance(self.simulation_time_s, bool) or not isinstance(
            self.simulation_time_s, (int, float)
        ):
            raise TransferError("simulation_time_s must be numeric, not bool")
        if self.simulation_time_s < 0:
            raise TransferError("simulation_time_s must be >= 0")
        # Identity/authority: both endpoints must live in this transfer's
        # workspace (fail closed; never fabricate or accept a mismatch).
        if self.source.owner_scope.workspace_id != self.workspace_id:
            raise TransferError(
                f"transfer source {self.source.as_string()!r} is outside "
                f"workspace {self.workspace_id!r}"
            )
        if self.target.owner_scope.workspace_id != self.workspace_id:
            raise TransferError(
                f"transfer target {self.target.as_string()!r} is outside "
                f"workspace {self.workspace_id!r}"
            )
        # Deep-freeze (detach) the payload so it cannot reference or retroactively
        # mutate any producer runtime state.
        object.__setattr__(self, "payload", _freeze(self.payload, "payload"))

    def to_dict(self) -> dict[str, Any]:
        """Deterministic, detached, key-stable serialization."""
        return {
            "transfer_id": self.transfer_id,
            "source": self.source.as_string(),
            "target": self.target.as_string(),
            "binding_id": self.binding_id,
            "window_id": self.window_id,
            "simulation_time_s": self.simulation_time_s,
            "workspace_id": self.workspace_id,
            "run_id": self.run_id,
            "payload": _to_plain(self.payload),
        }
