"""ObservationPoint, TriggerPolicy, FieldPolicy — declaration layer.

M5-S02: Defines WHAT may be observed, WHEN, and HOW fields are selected.
Consumer-neutral. No routing, projection, gateway, or runtime orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from virtual_factory.observation.envelope import ObservationType


# ═══════════════════════════════════════════════════
# TriggerKind
# ═══════════════════════════════════════════════════

class TriggerKind(str, Enum):
    """When an ObservationPoint is eligible to fire.

    Stable serialized values. No speculative extra kinds.
    """

    ON_EVENT = "on_event"
    PERIODIC = "periodic"
    ON_CHANGE = "on_change"
    MANUAL = "manual"


# ═══════════════════════════════════════════════════
# TriggerPolicy
# ═══════════════════════════════════════════════════

@dataclass(frozen=True, slots=True)
class TriggerPolicy:
    """Declares when an ObservationPoint becomes eligible.

    Kind-specific fields are validated in __post_init__.
    No scheduler, timer, or runtime state.
    """

    kind: TriggerKind

    # ON_EVENT
    event_types: tuple[str, ...] = ()
    target_ids: tuple[str, ...] = ()

    # PERIODIC
    interval_s: float = 0.0

    # ON_CHANGE
    change_field: str = ""
    change_threshold: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.kind, TriggerKind):
            raise ValueError(
                f"kind must be TriggerKind, "
                f"got {type(self.kind).__name__}"
            )
        if self.kind == TriggerKind.PERIODIC:
            if self.interval_s <= 0:
                raise ValueError(
                    f"PERIODIC trigger requires positive interval_s, "
                    f"got {self.interval_s}"
                )
        if self.kind == TriggerKind.ON_CHANGE:
            if not self.change_field:
                raise ValueError(
                    "ON_CHANGE trigger requires non-empty change_field"
                )
            if self.change_threshold < 0:
                raise ValueError(
                    f"ON_CHANGE trigger requires non-negative threshold, "
                    f"got {self.change_threshold}"
                )

    # ── Pure evaluation (no runtime state) ──

    def matches_event(self, event_type: str, target_id: str) -> bool:
        """Return True if this trigger matches a discrete reality event.

        Pure function — no side effects, no runtime state.
        Only meaningful for ON_EVENT triggers.
        """
        if self.kind != TriggerKind.ON_EVENT:
            return False
        if self.event_types and event_type not in self.event_types:
            return False
        if self.target_ids and target_id not in self.target_ids:
            return False
        return True

    def is_periodic_eligible(self, elapsed_s: float) -> bool:
        """Return True if enough simulation time has elapsed.

        Pure function.  Caller manages last-fire tracking (S03).
        """
        if self.kind != TriggerKind.PERIODIC:
            return False
        return elapsed_s >= self.interval_s

    def has_changed(
        self, previous: dict[str, Any] | None, current: dict[str, Any]
    ) -> bool:
        """Return True if the change_field crossed the threshold.

        Pure function.  Caller manages previous state (S03).
        """
        if self.kind != TriggerKind.ON_CHANGE:
            return False
        if previous is None:
            return True  # first observation always qualifies
        prev_val = previous.get(self.change_field)
        curr_val = current.get(self.change_field)
        if prev_val is None or curr_val is None:
            return False
        try:
            return abs(float(curr_val) - float(prev_val)) >= self.change_threshold
        except (TypeError, ValueError):
            return False


# ═══════════════════════════════════════════════════
# FieldPolicy — DEFAULT DENY + EXPLICIT ALLOW-LIST
# ═══════════════════════════════════════════════════

@dataclass(frozen=True, slots=True)
class FieldPolicy:
    """Controls what fields are selectable from a reality source.

    PRIMARY DEFENSE: explicit allow-list (``extract``).
    Only fields named in ``extract`` are selectable.

    DEFENSE-IN-DEPTH: ``deny`` blocks specific fields even if
    they appear in ``extract`` (deny wins).

    A field NOT in ``extract`` is invisible — no configuration
    change is needed when reality models gain new internal fields.
    """

    extract: tuple[str, ...] = ()
    deny: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in self.extract:
            if not field_name or not isinstance(field_name, str):
                raise ValueError(
                    f"extract field names must be non-empty str, "
                    f"got {field_name!r}"
                )
        for field_name in self.deny:
            if not field_name or not isinstance(field_name, str):
                raise ValueError(
                    f"deny field names must be non-empty str, "
                    f"got {field_name!r}"
                )

    def select(self, source: dict[str, Any]) -> dict[str, Any]:
        """Return only explicitly allowed fields from *source*.

        Rules (in order):
        1. Only fields in ``extract`` are candidates.
        2. Fields in ``deny`` are removed (deny wins).
        3. *source* is never mutated (returns a new dict).
        4. New/unknown fields in *source* are invisible by default.
        """
        result: dict[str, Any] = {}
        deny_set = frozenset(self.deny)
        for field_name in self.extract:
            if field_name in deny_set:
                continue
            if field_name in source:
                result[field_name] = source[field_name]
        return result


# ═══════════════════════════════════════════════════
# ObservationPoint
# ═══════════════════════════════════════════════════

@dataclass(frozen=True, slots=True)
class ObservationPoint:
    """Declares an observable boundary.

    Defines WHAT reality source to observe, WHEN via trigger,
    and HOW fields are selected via FieldPolicy.

    Effectively immutable: ``source_filter`` and ``context_map`` are
    stored as ``MappingProxyType`` (read-only views).

    Does NOT declare:
    - consumer / target projection
    - gateway / protocol / destination
    - MES / IIoT / MQTT / REST endpoint
    """

    point_id: str
    observation_type: ObservationType
    label: str
    source_type: str
    source_filter: Mapping[str, Any] = field(default_factory=dict)
    trigger: TriggerPolicy = field(
        default_factory=lambda: TriggerPolicy(kind=TriggerKind.ON_EVENT)
    )
    fields: FieldPolicy = field(default_factory=FieldPolicy)
    context_map: Mapping[str, str] = field(default_factory=dict)
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.point_id or not isinstance(self.point_id, str):
            raise ValueError("point_id must be a non-empty str")
        if not isinstance(self.observation_type, ObservationType):
            raise ValueError(
                f"observation_type must be ObservationType, "
                f"got {type(self.observation_type).__name__}"
            )
        if not self.source_type or not isinstance(self.source_type, str):
            raise ValueError("source_type must be a non-empty str")
        if not isinstance(self.trigger, TriggerPolicy):
            raise ValueError("trigger must be a TriggerPolicy")
        if not isinstance(self.fields, FieldPolicy):
            raise ValueError("fields must be a FieldPolicy")
        if not isinstance(self.enabled, bool):
            raise ValueError(
                f"enabled must be bool, got {type(self.enabled).__name__}"
            )
        if not isinstance(self.source_filter, dict):
            raise ValueError("source_filter must be a dict")
        if not isinstance(self.context_map, dict):
            raise ValueError("context_map must be a dict")
        for k, v in self.context_map.items():
            if not isinstance(k, str) or not isinstance(v, str):
                raise ValueError(
                    f"context_map keys and values must be str, "
                    f"got {type(k).__name__}: {type(v).__name__}"
                )

        # ── Immutability: wrap mutable fields in read-only proxy ──
        object.__setattr__(
            self, "source_filter", MappingProxyType(dict(self.source_filter))
        )
        object.__setattr__(
            self, "context_map", MappingProxyType(dict(self.context_map))
        )
