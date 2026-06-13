"""Valve actuator skeleton."""

from dataclasses import dataclass

from virtual_factory.actuation.base_actuator import BaseActuator


@dataclass(slots=True)
class ValveActuator(BaseActuator):
    """Placeholder for mapping controller output to valve opening."""
