"""Discrete manufacturing simulation kernel and engine.

M2-S01: RunStatus, DiscreteRunState, RuntimeSnapshot,
         EventDispatcherProtocol, HandlerOutcome, DiscreteSimulationEngine
M2-S02: HandlerRegistry, EventHandlerFn
"""

from virtual_factory.discrete.state import DiscreteRunState, RunStatus
from virtual_factory.discrete.snapshot import RuntimeSnapshot
from virtual_factory.discrete.dispatcher import (
    EventDispatcherProtocol,
    HandlerOutcome,
    HandlerOutcomeError,
)
from virtual_factory.discrete.engine import (
    DiscreteSimulationEngine,
    DiscreteSimulationEngineError,
)
from virtual_factory.discrete.handler_registry import (
    DuplicateHandlerError,
    HandlerRegistrationError,
    HandlerRegistry,
    HandlerRegistryError,
)

__all__ = [
    "DiscreteRunState",
    "RunStatus",
    "RuntimeSnapshot",
    "EventDispatcherProtocol",
    "HandlerOutcome",
    "HandlerOutcomeError",
    "DiscreteSimulationEngine",
    "DiscreteSimulationEngineError",
    "HandlerRegistry",
    "HandlerRegistryError",
    "HandlerRegistrationError",
    "DuplicateHandlerError",
]
