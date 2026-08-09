"""ObservationService — runtime observation collection bridge.

M5-S03: Evaluates ObservationPoints against reality inputs,
applies policies, and produces consumer-neutral ObservationEnvelopes.

One reality event → 0, 1, or N envelopes (from multiple matching points).
Does NOT route to consumers or projections (that is S04).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

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
from virtual_factory.observation.policy import (
    ObservationMode,
    ObservationPolicy,
)


# ═══════════════════════════════════════════════════
# Neutral reality input
# ═══════════════════════════════════════════════════

@dataclass(frozen=True, slots=True)
class RealityInput:
    """Neutral reality input for observation collection.

    Consumer-neutral.  No MES/assembly-specific fields.
    """

    run_id: str
    model_id: str
    source_event_id: str
    source_type: str
    source_domain: str
    source_path: str
    simulation_time_s: float
    category: str = "industrial_event"
    occurred_at: str | None = None
    source_data: dict[str, Any] = field(default_factory=dict)
    subject_type: str | None = None
    subject_id: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    correlation_id: str | None = None
    causation_id: str | None = None


# ═══════════════════════════════════════════════════
# ObservationService
# ═══════════════════════════════════════════════════

@dataclass
class ObservationService:
    """Evaluates ObservationPoints against reality inputs.

    Owns minimal trigger runtime state (last-fire simulation time
    for PERIODIC, previous snapshots for ON_CHANGE).

    Returns zero, one, or multiple ObservationEnvelopes.
    Does NOT route to consumers or projections.
    """

    points: list[ObservationPoint] = field(default_factory=list)
    policy: ObservationPolicy = field(default_factory=ObservationPolicy.industrial)

    # ── Trigger runtime state ──
    _periodic_last_s: dict[str, float | None] = field(default_factory=dict)
    _onchange_prev: dict[str, dict[str, Any]] = field(default_factory=dict)

    # ── Configuration ──

    def add_point(self, point: ObservationPoint) -> None:
        """Register an observation point."""
        if not isinstance(point, ObservationPoint):
            raise TypeError(
                f"expected ObservationPoint, got {type(point).__name__}"
            )
        self.points.append(point)

    # ── Collection ──

    def collect(self, reality: RealityInput) -> list[ObservationEnvelope]:
        """Evaluate all points against *reality*, return envelopes.

        One reality event → 0..N envelopes.
        Multiple envelopes come from multiple matching ObservationPoints,
        NOT from consumer routing.
        """
        envelopes: list[ObservationEnvelope] = []

        for point in self.points:
            if not point.enabled:
                continue

            # Layer 1: category/mode policy
            if not self.policy.is_allowed(reality.category):
                continue

            # Layer 2: source type match
            if not self._source_matches(point, reality):
                continue

            # Layer 3: trigger eligibility
            if not self._trigger_eligible(point, reality):
                continue

            # Layer 4: build envelope
            envelope = self._build_envelope(point, reality)
            envelopes.append(envelope)

        return envelopes

    def collect_manual(
        self, reality: RealityInput, point_id: str
    ) -> list[ObservationEnvelope]:
        """Explicitly collect for a MANUAL-trigger point."""
        for point in self.points:
            if point.point_id == point_id:
                if point.trigger.kind != TriggerKind.MANUAL:
                    raise ValueError(
                        f"Point {point_id} is not MANUAL, "
                        f"got {point.trigger.kind.value}"
                    )
                if not point.enabled:
                    return []
                if not self.policy.is_allowed(reality.category):
                    return []
                if not self._source_matches(point, reality):
                    return []
                return [self._build_envelope(point, reality)]
        return []

    # ── Internal helpers ──

    def _source_matches(
        self, point: ObservationPoint, reality: RealityInput
    ) -> bool:
        """Check if reality source matches point's source_filter."""
        if point.source_type != reality.source_type:
            return False
        for key, expected in point.source_filter.items():
            actual = reality.source_data.get(key)
            if actual != expected:
                return False
        return True

    def _trigger_eligible(
        self, point: ObservationPoint, reality: RealityInput
    ) -> bool:
        """Evaluate trigger eligibility with runtime state."""
        tp = point.trigger

        if tp.kind == TriggerKind.ON_EVENT:
            event_type = reality.source_data.get("event_type", "")
            target_id = reality.source_data.get("target_id", "")
            return tp.matches_event(event_type, target_id)

        if tp.kind == TriggerKind.PERIODIC:
            last_s = self._periodic_last_s.get(point.point_id)
            if last_s is None:
                return True  # first-fire: no prior state → eligible
            elapsed = reality.simulation_time_s - last_s
            return elapsed >= tp.interval_s

        if tp.kind == TriggerKind.ON_CHANGE:
            key = _onchange_key(point.point_id, reality)
            prev = self._onchange_prev.get(key)
            current = reality.source_data
            changed = tp.has_changed(prev, current)
            return changed

        # MANUAL — not eligible via automatic collect()
        return False

    def _build_envelope(
        self, point: ObservationPoint, reality: RealityInput
    ) -> ObservationEnvelope:
        """Build an ObservationEnvelope from point + reality."""

        # Update trigger runtime state
        self._update_trigger_state(point, reality)

        # Field selection
        payload = point.fields.select(reality.source_data)

        # Context extraction
        ctx = self._extract_context(point, reality)

        return ObservationEnvelope(
            observation_id=str(uuid4()),
            idempotency_key=make_idempotency_key(
                run_id=reality.run_id,
                source_event_id=reality.source_event_id,
                point_id=point.point_id,
                schema_version="1.0",
            ),
            observation_type=point.observation_type,
            run_id=reality.run_id,
            model_id=reality.model_id,
            simulation_time_s=reality.simulation_time_s,
            occurred_at=reality.occurred_at,
            emitted_at=datetime.now(timezone.utc).isoformat(),
            source_domain=reality.source_domain,
            source_path=reality.source_path,
            subject_type=reality.subject_type,
            subject_id=reality.subject_id,
            context=ctx,
            payload=payload,
            correlation_id=reality.correlation_id,
            causation_id=reality.causation_id,
        )

    def _extract_context(
        self, point: ObservationPoint, reality: RealityInput
    ) -> dict[str, Any]:
        """Extract context from reality using context_map."""
        ctx: dict[str, Any] = dict(reality.context)
        for ctx_key, source_key in point.context_map.items():
            if source_key in reality.source_data:
                ctx[ctx_key] = reality.source_data[source_key]
        return ctx

    def _update_trigger_state(
        self, point: ObservationPoint, reality: RealityInput
    ) -> None:
        """Update runtime trigger state after envelope creation."""
        tp = point.trigger
        if tp.kind == TriggerKind.PERIODIC:
            self._periodic_last_s[point.point_id] = reality.simulation_time_s
        elif tp.kind == TriggerKind.ON_CHANGE:
            key = _onchange_key(point.point_id, reality)
            self._onchange_prev[key] = dict(reality.source_data)


def _onchange_key(point_id: str, reality: RealityInput) -> str:
    """Build a stable ON_CHANGE state key from point + subject.

    Subject-less input uses a sentinel to avoid cross-contamination
    between different realities going through the same point.
    """
    st = reality.subject_type or "_nosubject"
    si = reality.subject_id or "_nosubject"
    return f"{point_id}|{st}|{si}"
