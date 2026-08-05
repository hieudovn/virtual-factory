"""Discrete manufacturing simulation kernel and engine.

M2-S01 public contracts:
- RunStatus, DiscreteRunState
- RuntimeSnapshot
- EventDispatcherProtocol, HandlerOutcome
- DiscreteSimulationEngine
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

__all__ = [
    "DiscreteRunState",
    "RunStatus",
    "RuntimeSnapshot",
    "EventDispatcherProtocol",
    "HandlerOutcome",
    "HandlerOutcomeError",
    "DiscreteSimulationEngine",
    "DiscreteSimulationEngineError",
]
