import csv
import json
import tempfile
from pathlib import Path

from virtual_factory.core.config_loader import load_plant_config
from virtual_factory.core.simulation_engine import SimulationEngine
from virtual_factory.telemetry.export import append_csv, append_jsonl, frame_to_records
from virtual_factory.telemetry.signal_value import SignalValue


def test_export_frame_to_csv_and_jsonl() -> None:
    """Telemetry export should write the common record fields."""
    frame = [
        SignalValue(
            name="LT102_LEVEL", value=1.25, unit="m",
            category="industrial_signal", quality="GOOD",
            timestamp_s=2.0, source="LT102",
        )
    ]
    records = frame_to_records(frame)
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        csv_path = tmp / "telemetry.csv"
        jsonl_path = tmp / "telemetry.jsonl"
        append_csv(csv_path, records)
        append_jsonl(jsonl_path, records)

        with csv_path.open("r", encoding="utf-8", newline="") as f:
            csv_records = list(csv.DictReader(f))
        jsonl_records = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines()]

        assert csv_records[0]["name"] == "LT102_LEVEL"
        assert csv_records[0]["category"] == "industrial_signal"
        assert jsonl_records[0]["timestamp_s"] == 2.0
        assert set(records[0]) == {"timestamp_s", "name", "value", "unit", "category", "quality", "source"}


def test_normal_engine_frame_export_contains_no_internal_truth() -> None:
    """Exporting a normal engine frame should not include internal_truth."""
    config = load_plant_config(Path("configs/plants/continuous_mvp_01.yaml"))
    engine = SimulationEngine(config)
    snapshot = engine.step()
    records = frame_to_records(snapshot["telemetry_latest"])
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        csv_path = tmp / "engine.csv"
        jsonl_path = tmp / "engine.jsonl"
        append_csv(csv_path, records)
        append_jsonl(jsonl_path, records)

        assert all(record["category"] != "internal_truth" for record in records)
        assert "T102_LEVEL_TRUE" not in csv_path.read_text(encoding="utf-8")
        assert "T102_LEVEL_TRUE" not in jsonl_path.read_text(encoding="utf-8")
