# Prompt for Coder — VF-2 ST08: Output Adapters

> **Parent:** VF-2 PIM-native Simulation Runtime  
> **Task:** VF2-ST08 — Output Adapters (Memory, CSV, Stdout)  
> **Prerequisite:** ST07 completed (simulator running end-to-end)

---

## Context

ST07 proved the simulator works — `loop.run(60)` produces measurement frames. ST08 adds output adapters so those frames go somewhere useful. Three adapters: memory (for API), CSV (for file export), stdout (for logging).

---

## What You're Building

### `output/base.py` — Abstract interface

```python
from abc import ABC, abstractmethod
from simulators.vf2.simulation_loop import Measurement

class OutputAdapter(ABC):
    @abstractmethod
    def write(self, frame: list[Measurement]) -> None: ...
    
    @abstractmethod
    def close(self) -> None: ...
```

### `output/memory_output.py`

```python
class MemoryOutput(OutputAdapter):
    """Stores frames in memory — used by API /telemetry/latest."""
    def __init__(self, max_frames: int = 3600):
        self.frames: list[list[Measurement]] = []
        self.max_frames = max_frames
    
    def write(self, frame): 
        self.frames.append(frame)
        if len(self.frames) > self.max_frames:
            self.frames.pop(0)
    
    def close(self): pass
    
    def get_latest(self) -> list[Measurement] | None:
        return self.frames[-1] if self.frames else None
    
    def get_all(self) -> list[list[Measurement]]:
        return list(self.frames)
```

### `output/csv_output.py`

```python
import csv
from pathlib import Path

class CsvOutput(OutputAdapter):
    """Writes frames to a CSV file."""
    def __init__(self, path: str | Path, append: bool = False):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(self.path, "a" if append else "w", newline="")
        self._writer = csv.writer(self._file)
        self._header_written = append and self.path.exists()
    
    def write(self, frame):
        if not self._header_written:
            self._writer.writerow(["timestamp", "signal_id", "value", "quality", "source"])
            self._header_written = True
        for m in frame:
            self._writer.writerow([m.timestamp, m.signal_id, m.value, m.quality, m.source])
        self._file.flush()
    
    def close(self):
        self._file.close()
```

### `output/stdout_output.py`

```python
import logging
logger = logging.getLogger("vf2.output")

class StdoutOutput(OutputAdapter):
    """Logs each frame to stdout via logger."""
    def __init__(self, log_level: int = logging.INFO):
        self.log_level = log_level
    
    def write(self, frame):
        for m in frame:
            logger.log(self.log_level, "%s | %s = %s %s", 
                      m.timestamp, m.signal_id, m.value, m.quality)
    
    def close(self): pass
```

### `tests/test_output_adapters.py`

```python
import tempfile, os
from pathlib import Path
from simulators.vf2.package_loader import load_package
from simulators.vf2.simulation_loop import Vf2SimulationLoop
from simulators.vf2.output.memory_output import MemoryOutput
from simulators.vf2.output.csv_output import CsvOutput
from simulators.vf2.output.stdout_output import StdoutOutput

GOLDEN = Path(__file__).resolve().parent.parent / "examples" / "sample_pim_package.json"

class TestMemoryOutput:
    def test_stores_frames(self):
        pkg = load_package(GOLDEN)
        loop = Vf2SimulationLoop(pkg)
        out = MemoryOutput(max_frames=100)
        frame = loop.step()
        out.write(frame)
        assert out.get_latest() is not None
        assert len(out.get_latest()) == 4
    
    def test_max_frames(self):
        out = MemoryOutput(max_frames=3)
        out.write([]); out.write([]); out.write([]); out.write([])
        assert len(out.frames) == 3

class TestCsvOutput:
    def test_writes_csv(self):
        pkg = load_package(GOLDEN)
        loop = Vf2SimulationLoop(pkg)
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tf:
            path = tf.name
        try:
            out = CsvOutput(path)
            out.write(loop.step())
            out.close()
            with open(path) as f:
                lines = f.readlines()
            assert len(lines) == 5  # header + 4 signals
            assert "timestamp" in lines[0]
        finally:
            os.unlink(path)

class TestStdoutOutput:
    def test_does_not_crash(self, caplog):
        out = StdoutOutput()
        out.write([])  # Should not crash
```

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC-1 | `MemoryOutput` stores frames, `get_latest()` returns last frame |
| AC-2 | `MemoryOutput` respects `max_frames` limit |
| AC-3 | `CsvOutput` writes valid CSV with header + data rows |
| AC-4 | `StdoutOutput` doesn't crash on write |
| AC-5 | All tests pass + VF-1 OK |
