"""M5 Observation Foundation — consumer-neutral observation types and envelopes.

M5-S01: ObservationType + ObservationEnvelope + idempotency helper.
No ObservationPoint, Router, Projection, or Gateway logic.
"""

from virtual_factory.observation.envelope import (
    ObservationEnvelope,
    ObservationType,
    make_idempotency_key,
)

__all__ = [
    "ObservationEnvelope",
    "ObservationType",
    "make_idempotency_key",
]
