"""Benchmark export utilities for analytics datasets.

Generates the standard benchmark package:
- telemetry.parquet
- asset_metadata.yaml
- operating_states.parquet
- alarm_events.parquet
- maintenance_events.parquet
- fault_timeline.parquet
- benchmark_labels.parquet
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# Optional pyarrow import for Parquet support
try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    HAS_PYARROW = True
except ImportError:
    HAS_PYARROW = False


@dataclass
class BenchmarkExporter:
    """Exports benchmark datasets in structured formats.

    Supports Parquet (via pyarrow) and CSV/JSONL fallback.
    """

    output_dir: str = "output/benchmark"
    run_id: str = ""
    _records: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.run_id:
            self.run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self._records = {}

    # ------------------------------------------------------------------
    # Data collection
    # ------------------------------------------------------------------

    def add_records(self, dataset: str, records: list[dict[str, Any]]) -> None:
        """Add records for a dataset (e.g. 'telemetry', 'alarm_events')."""
        self._records.setdefault(dataset, []).extend(records)

    def set_records(self, dataset: str, records: list[dict[str, Any]]) -> None:
        """Set (replace) records for a dataset."""
        self._records[dataset] = list(records)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_all(self, format: str = "parquet") -> dict[str, str]:
        """Export all collected datasets.

        Returns a dict mapping dataset name -> output file path.
        """
        os.makedirs(self.output_dir, exist_ok=True)
        results: dict[str, str] = {}

        for dataset, records in self._records.items():
            if not records:
                continue

            if format == "parquet" and HAS_PYARROW:
                path = self._export_parquet(dataset, records)
            else:
                path = self._export_jsonl(dataset, records)
            results[dataset] = path

        return results

    def export_metadata(self, metadata: dict[str, Any]) -> str:
        """Export asset metadata as YAML."""
        import yaml
        os.makedirs(self.output_dir, exist_ok=True)
        path = os.path.join(self.output_dir, "asset_metadata.yaml")
        with open(path, "w") as f:
            yaml.dump(metadata, f, default_flow_style=False, sort_keys=False)
        return path

    def _export_parquet(self, dataset: str, records: list[dict[str, Any]]) -> str:
        """Export records as Parquet file."""
        if not HAS_PYARROW:
            return self._export_jsonl(dataset, records)

        # Infer schema from first record
        table = pa.Table.from_pylist(records)
        path = os.path.join(self.output_dir, f"{dataset}.parquet")
        pq.write_table(table, path, compression="snappy")
        return path

    def _export_jsonl(self, dataset: str, records: list[dict[str, Any]]) -> str:
        """Export records as JSONL (fallback)."""
        path = os.path.join(self.output_dir, f"{dataset}.jsonl")
        with open(path, "w") as f:
            for rec in records:
                # Convert non-serializable values
                clean = {}
                for k, v in rec.items():
                    if isinstance(v, float):
                        clean[k] = round(v, 6)
                    elif isinstance(v, (int, str, bool, type(None))):
                        clean[k] = v
                    else:
                        clean[k] = str(v)
                f.write(json.dumps(clean) + "\n")
        return path

    def _export_csv(self, dataset: str, records: list[dict[str, Any]]) -> str:
        """Export records as CSV (fallback)."""
        import csv
        path = os.path.join(self.output_dir, f"{dataset}.csv")
        if not records:
            return path
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
            writer.writeheader()
            writer.writerows(records)
        return path

    # ------------------------------------------------------------------
    # Manifest
    # ------------------------------------------------------------------

    def write_manifest(self, exported_files: dict[str, str]) -> str:
        """Write a manifest file describing the exported datasets."""
        manifest = {
            "run_id": self.run_id,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "format": "parquet" if HAS_PYARROW else "jsonl",
            "datasets": {
                name: {
                    "file": os.path.basename(path),
                    "record_count": len(self._records.get(name, [])),
                }
                for name, path in exported_files.items()
            },
        }
        path = os.path.join(self.output_dir, "manifest.json")
        with open(path, "w") as f:
            json.dump(manifest, f, indent=2)
        return path


def export_benchmark_package(
    package,  # BenchmarkPackage
    output_dir: str = "output/benchmark",
    run_id: str = "",
) -> dict[str, str]:
    """Export a complete BenchmarkPackage to the output directory.

    Produces:
    - telemetry.parquet
    - asset_metadata.yaml
    - operating_states.parquet
    - alarm_events.parquet
    - maintenance_events.parquet
    - fault_timeline.parquet
    - benchmark_labels.parquet
    - manifest.json
    """
    exporter = BenchmarkExporter(output_dir=output_dir, run_id=run_id)

    exporter.set_records("telemetry", package.telemetry_records)
    exporter.set_records("operating_states", package.operating_state_records)
    exporter.set_records("alarm_events", package.alarm_records)
    exporter.set_records("maintenance_events", package.maintenance_records)
    exporter.set_records("fault_timeline", package.fault_timeline_records)
    exporter.set_records("benchmark_labels", package.benchmark_labels)

    results = exporter.export_all()
    meta_path = exporter.export_metadata(package.asset_metadata)
    results["asset_metadata"] = meta_path

    manifest_path = exporter.write_manifest(results)
    results["manifest"] = manifest_path

    return results
