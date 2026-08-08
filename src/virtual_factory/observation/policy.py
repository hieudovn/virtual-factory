"""ObservationPolicy — consumer-neutral observation category control.

M5-S02: Generalizes existing OutputPolicy ideas.
Controls what categories are observable under which mode.
Does NOT decide who consumes or which projection receives data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


# ═══════════════════════════════════════════════════
# ObservationMode
# ═══════════════════════════════════════════════════

class ObservationMode(str, Enum):
    """Supported observation policy modes."""
    INDUSTRIAL = "industrial"
    DEBUG = "debug"
    BENCHMARK = "benchmark"


# Categories compatible with existing OutputPolicy
_INDUSTRIAL_ALLOWED: frozenset[str] = frozenset({
    "industrial_signal",
    "controller_signal",
    "actuator_feedback",
    "industrial_event",
})

_ALWAYS_DENIED: frozenset[str] = frozenset({
    "internal_truth",
})


@dataclass(frozen=True, slots=True)
class ObservationPolicy:
    """Controls what observation categories / field classes are allowed.

    Consumer-neutral — does not decide who consumes or which
    projection/gateway is used.

    Aligns with existing ``OutputPolicy`` invariants:
    industrial mode → internal_truth denied.
    """

    mode: ObservationMode = ObservationMode.INDUSTRIAL
    allowed_categories: frozenset[str] = field(default_factory=lambda: _INDUSTRIAL_ALLOWED)
    denied_categories: frozenset[str] = field(default_factory=lambda: _ALWAYS_DENIED)

    def __post_init__(self) -> None:
        if not isinstance(self.mode, ObservationMode):
            raise ValueError(
                f"mode must be ObservationMode, "
                f"got {type(self.mode).__name__}"
            )

    @classmethod
    def industrial(cls) -> "ObservationPolicy":
        """Factory: standard industrial mode policy."""
        return cls(mode=ObservationMode.INDUSTRIAL)

    @classmethod
    def debug(cls) -> "ObservationPolicy":
        """Factory: debug mode — allows internal_truth."""
        return cls(
            mode=ObservationMode.DEBUG,
            allowed_categories=frozenset({
                "industrial_signal",
                "controller_signal",
                "actuator_feedback",
                "industrial_event",
                "internal_truth",
            }),
            denied_categories=frozenset(),
        )

    @classmethod
    def benchmark(cls) -> "ObservationPolicy":
        """Factory: benchmark mode — allows all including internal_truth."""
        return cls(
            mode=ObservationMode.BENCHMARK,
            allowed_categories=frozenset({
                "industrial_signal",
                "controller_signal",
                "actuator_feedback",
                "industrial_event",
                "internal_truth",
            }),
            denied_categories=frozenset(),
        )

    def is_allowed(self, category: str) -> bool:
        """Return True if *category* may be observed under this policy.

        Denied categories always win over allowed.
        """
        if category in self.denied_categories:
            return False
        if self.mode == ObservationMode.INDUSTRIAL and category == "internal_truth":
            return False
        return category in self.allowed_categories
