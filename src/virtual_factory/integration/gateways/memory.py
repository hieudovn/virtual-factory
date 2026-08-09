"""In-memory observation gateway for testing and demo.

M5-S05: Stores ProjectedMessages in memory.  Optional failure injection.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from virtual_factory.integration.gateway import DeliveryResult, DeliveryStatus
from virtual_factory.observation.projection import ProjectedMessage


@dataclass
class InMemoryObsGateway:
    """Stores delivered messages in memory.  No network I/O."""

    gateway_id: str = "inmemory"
    _messages: list[ProjectedMessage] = field(default_factory=list)
    _fail_next: int = 0  # number of next calls to fail, 0 = no failure

    def set_fail_next(self, count: int) -> None:
        """Configure the next *count* send() calls to return FAILED."""
        self._fail_next = max(0, count)

    def send(self, message: ProjectedMessage) -> DeliveryResult:
        if self._fail_next > 0:
            self._fail_next -= 1
            return DeliveryResult(
                gateway_id=self.gateway_id,
                message_key=message.key,
                status=DeliveryStatus.FAILED,
                error_code="injected_failure",
                error_message="Simulated gateway failure",
            )
        self._messages.append(message)
        return DeliveryResult(
            gateway_id=self.gateway_id,
            message_key=message.key,
            status=DeliveryStatus.DELIVERED,
        )

    def send_many(self, messages: list[ProjectedMessage]) -> list[DeliveryResult]:
        return [self.send(m) for m in messages]

    @property
    def messages(self) -> tuple[ProjectedMessage, ...]:
        return tuple(self._messages)
