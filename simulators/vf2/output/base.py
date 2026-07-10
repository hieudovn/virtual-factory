"""Abstract output adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from simulators.vf2.simulation_loop import Measurement


class OutputAdapter(ABC):
    """Interface for all VF-2 output adapters."""

    @abstractmethod
    def write(self, frame: list[Measurement]) -> None:
        """Write one measurement frame."""

    @abstractmethod
    def close(self) -> None:
        """Flush and release resources."""
