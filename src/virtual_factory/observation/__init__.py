"""M5 Observation Foundation — consumer-neutral observation types and envelopes.

M5-S01: ObservationType + ObservationEnvelope + idempotency helper.
M5-S02: ObservationPoint + TriggerPolicy + FieldPolicy + ObservationPolicy.
M5-S03: ObservationService + Identity model.
No Router, Projection, or Gateway logic.
"""

from virtual_factory.observation.envelope import (
    ObservationEnvelope,
    ObservationType,
    make_idempotency_key,
)
from virtual_factory.observation.identity import (
    EntityRef,
    ExternalIdentityRef,
    IdentityLink,
    IdentityResolver,
)
from virtual_factory.observation.point import (
    FieldPolicy,
    ObservationPoint,
    TriggerKind,
    TriggerPolicy,
)
from virtual_factory.observation.policy import ObservationMode, ObservationPolicy
from virtual_factory.observation.service import (
    ObservationService,
    RealityInput,
)

__all__ = [
    "EntityRef",
    "ExternalIdentityRef",
    "FieldPolicy",
    "IdentityLink",
    "IdentityResolver",
    "ObservationEnvelope",
    "ObservationMode",
    "ObservationPoint",
    "ObservationPolicy",
    "ObservationService",
    "ObservationType",
    "RealityInput",
    "TriggerKind",
    "TriggerPolicy",
    "make_idempotency_key",
]
