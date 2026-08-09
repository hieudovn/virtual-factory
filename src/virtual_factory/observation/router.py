"""ObservationRouter — consumer/projection fan-out.

M5-S04: Routes one ObservationEnvelope to 0..N registered projections.
First layer where consumer selection is allowed.
Does NOT invoke gateways or network I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from virtual_factory.observation.envelope import ObservationEnvelope, ObservationType
from virtual_factory.observation.projection import ProjectedMessage, ProjectionProtocol


# ═══════════════════════════════════════════════════
# ProjectionSubscription
# ═══════════════════════════════════════════════════

@dataclass(frozen=True, slots=True)
class ProjectionSubscription:
    """Declares which envelopes a projection should receive."""

    projection: ProjectionProtocol
    observation_types: tuple[ObservationType, ...] = ()
    source_domains: tuple[str, ...] = ()
    predicate: Callable[[ObservationEnvelope], bool] | None = None

    def matches(self, envelope: ObservationEnvelope) -> bool:
        if self.observation_types and envelope.observation_type not in self.observation_types:
            return False
        if self.source_domains and envelope.source_domain not in self.source_domains:
            return False
        if self.predicate is not None:
            return self.predicate(envelope)
        return True


# ═══════════════════════════════════════════════════
# ObservationRouter
# ═══════════════════════════════════════════════════

@dataclass
class ObservationRouter:
    """Routes ObservationEnvelopes to registered projections.

    One envelope → 0..N projection results.
    Consumer fan-out occurs HERE, not in ObservationPoint or Service.
    """

    _subscriptions: list[ProjectionSubscription] = field(default_factory=list)

    def subscribe(self, subscription: ProjectionSubscription) -> None:
        """Register a projection subscription."""
        if not isinstance(subscription, ProjectionSubscription):
            raise TypeError(
                f"expected ProjectionSubscription, got "
                f"{type(subscription).__name__}"
            )
        self._subscriptions.append(subscription)

    def route(self, envelope: ObservationEnvelope) -> list[ProjectedMessage]:
        """Route one envelope to matching projections.

        Returns 0..N ProjectedMessages.  Does NOT mutate the envelope.
        Does NOT invoke gateways.
        """
        results: list[ProjectedMessage] = []
        for sub in self._subscriptions:
            if not sub.matches(envelope):
                continue
            try:
                msg = sub.projection.project(envelope)
                if msg is not None:
                    results.append(msg)
            except Exception:
                # Fail-fast: projection errors propagate
                raise
        return results
