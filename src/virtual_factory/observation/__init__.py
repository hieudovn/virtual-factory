"""M5 Observation Foundation — consumer-neutral observation types and envelopes.

M5-S01: ObservationType + ObservationEnvelope + idempotency helper.
M5-S02: ObservationPoint + TriggerPolicy + FieldPolicy + ObservationPolicy.
No Router, Projection, or Gateway logic.
"""

from virtual_factory.observation.envelope import (
    ObservationEnvelope,
    ObservationType,
    make_idempotency_key,
)
from virtual_factory.observation.point import (
    FieldPolicy,
    ObservationPoint,
    TriggerKind,
    TriggerPolicy,
)
from virtual_factory.observation.policy import ObservationPolicy

__all__ = [
    "FieldPolicy",
    "ObservationEnvelope",
    "ObservationPoint",
    "ObservationPolicy",
    "ObservationType",
    "TriggerKind",
    "TriggerPolicy",
    "make_idempotency_key",
]
