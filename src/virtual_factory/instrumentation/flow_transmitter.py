"""Flow transmitter skeleton."""

from dataclasses import dataclass

from virtual_factory.instrumentation.base_sensor import BaseSensor


@dataclass(slots=True)
class FlowTransmitter(BaseSensor):
    """Placeholder for converting true flow into a measured flow signal."""
