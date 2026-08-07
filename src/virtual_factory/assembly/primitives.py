"""Assembly domain primitives — Source, Buffer, Processor, Router, Sink, QualityGate.

M3-S01: Lightweight domain vocabulary. Each primitive has a deterministic ID
and a type tag.  No runtime behavior, no topology, no TIPA coupling.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass


class PrimitiveType(str, enum.Enum):
    """Kind of assembly domain primitive."""
    SOURCE = "source"
    BUFFER = "buffer"
    PROCESSOR = "processor"
    ROUTER = "router"
    SINK = "sink"
    QUALITY_GATE = "quality_gate"


class AssemblyPrimitiveError(ValueError):
    """Raised when an assembly primitive invariant is violated."""


@dataclass(frozen=True, slots=True)
class AssemblyPrimitive:
    """Base for all assembly domain primitives.

    Every primitive has a stable, deterministic ``primitive_id`` and a
    ``primitive_type`` tag.  Subclasses provide domain-specific fields.
    """

    primitive_id: str
    primitive_type: PrimitiveType
    label: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.primitive_id, str) or not self.primitive_id.strip():
            raise AssemblyPrimitiveError("primitive_id must be non-empty str")
        if not isinstance(self.primitive_type, PrimitiveType):
            raise AssemblyPrimitiveError(
                f"primitive_type must be PrimitiveType, got {type(self.primitive_type).__name__}"
            )


# ──────────────────────────────────────────────
# Source
# ──────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class Source(AssemblyPrimitive):
    """Entry of WIP/material into the modeled system.

    Not procurement.  Not ERP inventory.
    """

    primitive_type: PrimitiveType = PrimitiveType.SOURCE


# ──────────────────────────────────────────────
# Buffer
# ──────────────────────────────────────────────

class BufferError(AssemblyPrimitiveError):
    """Raised when a buffer invariant is violated."""


@dataclass(frozen=True, slots=True)
class Buffer(AssemblyPrimitive):
    """Bounded waiting/storage between processing steps.

    Capacity enforcement is a domain concern — no silent loss.
    """

    primitive_type: PrimitiveType = PrimitiveType.BUFFER
    capacity: int = 256

    def __post_init__(self) -> None:
        AssemblyPrimitive.__post_init__(self)
        if isinstance(self.capacity, bool):
            raise BufferError("capacity must be int, not bool")
        if not isinstance(self.capacity, int) or self.capacity <= 0:
            raise BufferError(f"capacity must be int > 0, got {self.capacity!r}")


# ──────────────────────────────────────────────
# Processor
# ──────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class Processor(AssemblyPrimitive):
    """Processing capability / station abstraction.

    No machine-specific physics embedded.
    """

    primitive_type: PrimitiveType = PrimitiveType.PROCESSOR
    processing_time_s: float = 1.0

    def __post_init__(self) -> None:
        AssemblyPrimitive.__post_init__(self)
        import math
        if isinstance(self.processing_time_s, bool):
            raise AssemblyPrimitiveError("processing_time_s must be numeric, not bool")
        if not isinstance(self.processing_time_s, (int, float)):
            raise AssemblyPrimitiveError(
                f"processing_time_s must be numeric, got {type(self.processing_time_s).__name__}"
            )
        if self.processing_time_s < 0 or math.isnan(self.processing_time_s) or math.isinf(self.processing_time_s):
            raise AssemblyPrimitiveError(
                f"processing_time_s must be finite >= 0, got {self.processing_time_s!r}"
            )


# ──────────────────────────────────────────────
# Router
# ──────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class Router(AssemblyPrimitive):
    """Choice of next domain destination.

    Routing expression language belongs to later M3 slices.
    This primitive carries the identity needed for handler wiring.
    """

    primitive_type: PrimitiveType = PrimitiveType.ROUTER


# ──────────────────────────────────────────────
# Sink
# ──────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class Sink(AssemblyPrimitive):
    """Terminal successful / other disposition from the modeled flow."""

    primitive_type: PrimitiveType = PrimitiveType.SINK


# ──────────────────────────────────────────────
# QualityGate
# ──────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class QualityGate(AssemblyPrimitive):
    """Inspection / quality decision point.

    Produces a domain disposition (pass, fail, rework, scrap).
    """

    primitive_type: PrimitiveType = PrimitiveType.QUALITY_GATE
