"""Integration boundary — reverse control/context from external systems.

M5-S04: ControlBoundary translates external production context/commands
into neutral simulation control structures.
Does NOT call Engine, HandlerRegistry, or mutate runtime state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping


# ═══════════════════════════════════════════════════
# Command types
# ═══════════════════════════════════════════════════

class ControlCommandKind(str, Enum):
    START = "start"
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"


# ═══════════════════════════════════════════════════
# Inbound contracts
# ═══════════════════════════════════════════════════

@dataclass(frozen=True, slots=True)
class ProductionContext:
    """External production order / work context.

    References are business identifiers, not Odoo DB IDs.
    """

    production_order_ref: str
    product_ref: str
    routing_ref: str | None = None
    operation_ref: str | None = None
    quantity: int = 1
    priority: int = 0
    due_time: str | None = None
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.production_order_ref:
            raise ValueError("production_order_ref must be non-empty")
        if not self.product_ref:
            raise ValueError("product_ref must be non-empty")
        object.__setattr__(self, "attributes", MappingProxyType(dict(self.attributes)))


@dataclass(frozen=True, slots=True)
class ControlCommand:
    """External control command."""

    command_id: str
    command_type: ControlCommandKind
    target_ref: str
    subject_ref: str | None = None
    parameters: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.command_id:
            raise ValueError("command_id must be non-empty")
        if not self.target_ref:
            raise ValueError("target_ref must be non-empty")
        object.__setattr__(self, "parameters", MappingProxyType(dict(self.parameters)))


@dataclass(frozen=True, slots=True)
class MaterialContext:
    """External material release context."""

    release_id: str
    material_ref: str
    quantity: int = 1
    subject_ref: str | None = None
    source_ref: str | None = None

    def __post_init__(self) -> None:
        if not self.release_id:
            raise ValueError("release_id must be non-empty")
        if not self.material_ref:
            raise ValueError("material_ref must be non-empty")


@dataclass(frozen=True, slots=True)
class QualitySpecContext:
    """External quality requirement context."""

    requirement_id: str
    test_type: str = "inspection"
    min_value: float | None = None
    max_value: float | None = None
    target_value: float | None = None
    unit: str | None = None
    scope_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.requirement_id:
            raise ValueError("requirement_id must be non-empty")


# ═══════════════════════════════════════════════════
# Simulation control output
# ═══════════════════════════════════════════════════

@dataclass(frozen=True, slots=True)
class SimulationControlBatch:
    """Neutral simulation control context.

    Produced by ControlBoundary.  Does NOT call Engine.
    """

    run_id: str
    model_id: str
    production_context: ProductionContext | None = None
    commands: tuple[ControlCommand, ...] = ()
    material_contexts: tuple[MaterialContext, ...] = ()
    quality_specs: tuple[QualitySpecContext, ...] = ()
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("run_id must be non-empty")
        object.__setattr__(self, "attributes", MappingProxyType(dict(self.attributes)))


# ═══════════════════════════════════════════════════
# ControlBoundary
# ═══════════════════════════════════════════════════

class ControlBoundary:
    """Translates external context/commands into neutral control structures.

    Does NOT call Engine, HandlerRegistry, or mutate runtime state.
    Output is SimulationControlBatch — neutral, immutable.
    """

    def translate(
        self,
        run_id: str,
        model_id: str,
        production: ProductionContext | None = None,
        commands: tuple[ControlCommand, ...] = (),
        materials: tuple[MaterialContext, ...] = (),
        quality: tuple[QualitySpecContext, ...] = (),
        **attributes: Any,
    ) -> SimulationControlBatch:
        """Translate external inputs into a neutral control batch."""
        return SimulationControlBatch(
            run_id=run_id,
            model_id=model_id,
            production_context=production,
            commands=commands,
            material_contexts=materials,
            quality_specs=quality,
            attributes=attributes,
        )
