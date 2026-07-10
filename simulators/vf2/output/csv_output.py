"""CSV file output adapter."""

from __future__ import annotations

import csv
from pathlib import Path

from simulators.vf2.simulation_loop import Measurement

from .base import OutputAdapter


class CsvOutput(OutputAdapter):
    """Writes measurement frames to a CSV file.

    Args:
        path: File path for the CSV output.
        append: If ``True``, append to an existing file.
    """

    def __init__(self, path: str | Path, append: bool = False) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(self.path, "a" if append else "w", newline="")
        self._writer = csv.writer(self._file)
        self._header_written = False

    def write(self, frame: list[Measurement]) -> None:
        if not self._header_written:
            self._writer.writerow([
                "timestamp", "signal_id", "value", "quality", "source",
            ])
            self._header_written = True

        for m in frame:
            self._writer.writerow([
                m.timestamp, m.signal_id, m.value, m.quality, m.source,
            ])
        self._file.flush()

    def close(self) -> None:
        self._file.close()
