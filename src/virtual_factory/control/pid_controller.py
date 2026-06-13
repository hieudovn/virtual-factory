"""PID controller skeleton."""

from dataclasses import dataclass

from virtual_factory.control.base_controller import BaseController


@dataclass(slots=True)
class PIDController(BaseController):
    """PID controller placeholder; tuning logic will be added later."""
