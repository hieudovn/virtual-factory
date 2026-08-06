"""Discrete manufacturing simulation kernel and engine.

M2-S01: RunStatus, DiscreteRunState, RuntimeSnapshot,
         EventDispatcherProtocol, HandlerOutcome, DiscreteSimulationEngine
M2-S02: HandlerRegistry, EventHandlerFn
M2-S04: ExecutionMode, RunControlCommand, ControlCommandResult,
         ControlCommandQueue, ControllerPacingPolicy, DiscreteRunController
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
    EventHandlerFn,
    HandlerRegistrationError,
    HandlerRegistry,
    HandlerRegistryError,
)
from virtual_factory.discrete.trace import (
    EventTraceBuffer,
    EventTraceBufferError,
    EventTraceEntry,
    EventTraceEntryError,
    RuntimeDiagnostics,
    RuntimeDiagnosticsError,
)
from virtual_factory.discrete.commands import (
    ControlCommandQueue,
    ControlCommandQueueError,
    ControlCommandResult,
    ControlCommandResultError,
    ControlCommandType,
    RunControlCommand,
    RunControlCommandError,
)
from virtual_factory.discrete.controller import (
    ControllerPacingPolicy,
    ControllerPacingPolicyError,
    DiscreteRunController,
    DiscreteRunControllerError,
    ExecutionMode,
    SafePointOutcome,
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
    "EventHandlerFn",
    "EventTraceEntry",
    "EventTraceEntryError",
    "EventTraceBuffer",
    "EventTraceBufferError",
    "RuntimeDiagnostics",
    "RuntimeDiagnosticsError",
    "ExecutionMode",
    "ControlCommandType",
    "RunControlCommand",
    "RunControlCommandError",
    "ControlCommandResult",
    "ControlCommandResultError",
    "ControlCommandQueue",
    "ControlCommandQueueError",
    "ControllerPacingPolicy",
    "ControllerPacingPolicyError",
    "DiscreteRunController",
    "DiscreteRunControllerError",
    "SafePointOutcome",
]
