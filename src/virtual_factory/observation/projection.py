"""Projection protocol and neutral result types.

M5-S04: ProjectionProtocol, ProjectedMessage.
Consumer-neutral projection contract.
No gateway/transport/network fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Protocol, runtime_checkable

from virtual_factory.observation.envelope import ObservationEnvelope


# ═══════════════════════════════════════════════════
# ProjectionProtocol
# ═══════════════════════════════════════════════════

@runtime_checkable
class ProjectionProtocol(Protocol):
    """Minimal consumer projection contract.

    Input: ObservationEnvelope.
    Output: ProjectedMessage | None.
    Side-effect-free.  No gateway/network/transport.
    """

    projection_id: str

    def project(self, envelope: ObservationEnvelope) -> ProjectedMessage | None:
        ...


# ═══════════════════════════════════════════════════
# ProjectedMessage
# ═══════════════════════════════════════════════════

@dataclass(frozen=True, slots=True)
class ProjectedMessage:
    """Consumer-neutral projected message.

    Carries projection identity, schema metadata, and payload.
    No transport addressing (topic, URL, broker, queue).
    """

    projection_id: str
    message_type: str                   # e.g. "mes.execution_event", "iiot.signal"
    schema_name: str                    # e.g. "vf.mes.execution_event"
    schema_version: str = "1.0"
    key: str = ""                       # logical message key (idempotency_key)
    headers: Mapping[str, str] = field(default_factory=dict)
    payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.projection_id or not isinstance(self.projection_id, str):
            raise ValueError("projection_id must be a non-empty str")
        if not self.message_type or not isinstance(self.message_type, str):
            raise ValueError("message_type must be a non-empty str")
        if not self.schema_name or not isinstance(self.schema_name, str):
            raise ValueError("schema_name must be a non-empty str")
        if not self.schema_version or not isinstance(self.schema_version, str):
            raise ValueError("schema_version must be a non-empty str")
        # Immutability
        object.__setattr__(self, "headers", MappingProxyType(dict(self.headers)))
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))
