"""ObservationGateway protocol and DeliveryResult.

M5-S05: Transport boundary. Gateway accepts ProjectedMessage only.
No Engine/runtime/truth access. No MES/Odoo semantics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Protocol, runtime_checkable


# ═══════════════════════════════════════════════════
# DeliveryStatus
# ═══════════════════════════════════════════════════

class DeliveryStatus(str, Enum):
    DELIVERED = "delivered"
    FAILED = "failed"
    SKIPPED = "skipped"


# ═══════════════════════════════════════════════════
# DeliveryResult
# ═══════════════════════════════════════════════════

@dataclass(frozen=True, slots=True)
class DeliveryResult:
    """Immutable delivery outcome for one ProjectedMessage.

    Gateway failure must not mutate the message or simulation state.
    """

    gateway_id: str
    message_key: str
    status: DeliveryStatus
    attempts: int = 1
    delivered_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    error_code: str | None = None
    error_message: str | None = None
    transport_metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.gateway_id:
            raise ValueError("gateway_id must be non-empty")
        if not self.message_key:
            raise ValueError("message_key must be non-empty")
        object.__setattr__(
            self, "transport_metadata",
            MappingProxyType(dict(self.transport_metadata)),
        )


# ═══════════════════════════════════════════════════
# ObservationGateway protocol
# ═══════════════════════════════════════════════════

@runtime_checkable
class ObservationGatewayProtocol(Protocol):
    """Transport boundary for ProjectedMessage delivery.

    Input: ProjectedMessage (not ObservationEnvelope, not runtime state).
    Output: DeliveryResult.
    """

    gateway_id: str

    def send(self, message: Any) -> DeliveryResult:
        ...

    def send_many(self, messages: list[Any]) -> list[DeliveryResult]:
        ...
