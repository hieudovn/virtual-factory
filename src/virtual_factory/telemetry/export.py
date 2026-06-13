"""Local telemetry export helpers for publishable signal frames."""

import csv
import json
from dataclasses import asdict
from pathlib import Path

from virtual_factory.telemetry.signal_value import SignalValue

EXPORT_FIELDS = ["timestamp_s", "name", "value", "unit", "category", "quality", "source"]


def frame_to_records(frame: list[SignalValue]) -> list[dict]:
    """Convert a telemetry frame into flat export records."""
    return [{field: asdict(signal).get(field) for field in EXPORT_FIELDS} for signal in frame]


def append_csv(path: str | Path, records: list[dict], write_header_if_missing: bool = True) -> None:
    """Append telemetry records to a CSV file."""
    if not records:
        return
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = write_header_if_missing and (not output_path.exists() or output_path.stat().st_size == 0)
    with output_path.open("a", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=EXPORT_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerows(records)


def append_jsonl(path: str | Path, records: list[dict]) -> None:
    """Append telemetry records to a JSON Lines file."""
    if not records:
        return
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
