"""Stdout logging output adapter."""

from __future__ import annotations

import logging

from simulators.vf2.simulation_loop import Measurement

from .base import OutputAdapter

logger = logging.getLogger("vf2.output")


class StdoutOutput(OutputAdapter):
    """Logs each measurement to ``stdout`` via the ``vf2.output`` logger.

    Args:
        log_level: Logging level (default ``logging.INFO``).
    """

    def __init__(self, log_level: int = logging.INFO) -> None:
        self.log_level = log_level

    def write(self, frame: list[Measurement]) -> None:
        for m in frame:
            logger.log(
                self.log_level,
                "%s | %s = %s %s",
                m.timestamp,
                m.signal_id,
                m.value,
                m.quality,
            )

    def close(self) -> None:
        pass
