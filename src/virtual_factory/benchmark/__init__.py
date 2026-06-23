"""Ground Truth & Benchmark Layer.

Generates hidden labels for analytics validation:
- Operating state
- Fault type, start time, severity
- Asset health, remaining useful life (simulated)
- Failure probability, expected diagnosis

These labels exist only for analytics benchmarking, never published as
industrial telemetry.
"""

from virtual_factory.benchmark.benchmark_manager import (
    BenchmarkManager,
    BenchmarkLabels,
    BenchmarkPackage,
    BenchmarkMode,
)
from virtual_factory.benchmark.export_utils import (
    BenchmarkExporter,
    export_benchmark_package,
)

__all__ = [
    "BenchmarkManager",
    "BenchmarkLabels",
    "BenchmarkPackage",
    "BenchmarkMode",
    "BenchmarkExporter",
    "export_benchmark_package",
]
