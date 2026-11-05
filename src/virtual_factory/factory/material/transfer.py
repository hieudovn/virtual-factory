"""Transfer state machine and declared simulated latency policy."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from virtual_factory.factory.material.models import (
    MaterialValidationError,
    TransferError,
    TransferState,
)


_ALLOWED_TRANSITIONS: dict[TransferState, frozenset[TransferState]] = {
    TransferState.REQUESTED: frozenset(
        {TransferState.SHIPPED, TransferState.CANCELLED}
    ),
    TransferState.SHIPPED: frozenset(
        {TransferState.IN_TRANSIT, TransferState.CANCELLED}
    ),
    TransferState.IN_TRANSIT: frozenset(
        {TransferState.RECEIVED, TransferState.RETURNED, TransferState.LOST}
    ),
    TransferState.RECEIVED: frozenset(),
    TransferState.RETURNED: frozenset(),
    TransferState.CANCELLED: frozenset(),
    TransferState.LOST: frozenset(),
}


def in_transit_location(transfer_id: str) -> str:
    if not isinstance(transfer_id, str) or not transfer_id:
        raise MaterialValidationError("transfer_id must be a non-empty str")
    return f"in_transit:{transfer_id}"


def validate_transition(current: TransferState, target: TransferState) -> None:
    if target not in _ALLOWED_TRANSITIONS[current]:
        raise TransferError(
            f"invalid transfer transition {current.value} -> {target.value}"
        )


@dataclass(frozen=True)
class TransferPolicy:
    default_latency_us: int = 0
    routes: Mapping[tuple[str, str], int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.default_latency_us, bool) or not isinstance(
            self.default_latency_us, int
        ):
            raise MaterialValidationError(
                "default transfer latency must be int"
            )
        if self.default_latency_us < 0:
            raise MaterialValidationError(
                "default transfer latency must be >= 0"
            )
        normalized: dict[tuple[str, str], int] = {}
        for route, latency in self.routes.items():
            if (
                not isinstance(route, tuple)
                or len(route) != 2
                or not all(isinstance(item, str) and item for item in route)
            ):
                raise MaterialValidationError(
                    "transfer route keys must be non-empty string pairs"
                )
            if isinstance(latency, bool) or not isinstance(latency, int):
                raise MaterialValidationError(
                    "transfer route latency must be int"
                )
            if latency < 0:
                raise MaterialValidationError(
                    "transfer route latency must be >= 0"
                )
            normalized[route] = latency
        object.__setattr__(self, "routes", normalized)

    def latency_us(self, sender_location: str, destination_location: str) -> int:
        return self.routes.get(
            (sender_location, destination_location),
            self.default_latency_us,
        )
