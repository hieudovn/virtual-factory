"""Operating State Model.

Explicit operating states for equipment and plants, including state
transitions, entry/exit conditions, and benchmark truth export.
"""

from virtual_factory.operating_states.state_machine import (
    OperatingState,
    OperatingStateMachine,
    StateTransition,
    OPERATING_STATES,
    VALID_TRAINING_STATES,
)

__all__ = [
    "OperatingState",
    "OperatingStateMachine",
    "StateTransition",
    "OPERATING_STATES",
    "VALID_TRAINING_STATES",
]
