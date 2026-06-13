"""Level transmitter skeleton."""

from dataclasses import dataclass

from virtual_factory.instrumentation.base_sensor import BaseSensor


@dataclass(slots=True)
class LevelTransmitter(BaseSensor):
    """Placeholder for converting true level into a measured level signal."""
