"""Pressure transmitter skeleton."""

from dataclasses import dataclass

from virtual_factory.instrumentation.base_sensor import BaseSensor


@dataclass(slots=True)
class PressureTransmitter(BaseSensor):
    """Placeholder for converting true pressure into a measured pressure signal."""
