"""Tests for the Benchmark Manager and Export Utilities."""

import json
import os
import tempfile

import pytest

from virtual_factory.benchmark.benchmark_manager import (
    BenchmarkManager,
    BenchmarkLabels,
    BenchmarkPackage,
    BenchmarkMode,
)
from virtual_factory.benchmark.export_utils import BenchmarkExporter
from virtual_factory.faults.fault_engine import FaultEngine, FaultScheduler
from virtual_factory.faults.fault_models import FaultLibrary
from virtual_factory.faults.fault_models import FaultConfig
from virtual_factory.operating_states.state_machine import (
    OperatingStateMachine,
    OperatingState,
    StateTransition,
)


class TestBenchmarkLabels:
    def test_to_dict(self):
        label = BenchmarkLabels(
            timestamp_s=100.0,
            equipment_id="COMP01",
            operating_state="steady_running",
            active_faults=["bearing_wear"],
            fault_severities={"bearing_wear": 0.35},
            health_index=0.65,
            expected_anomaly=True,
            expected_diagnosis="bearing_wear",
            expected_severity_label="developing",
        )
        d = label.to_dict()
        assert d["timestamp_s"] == 100.0
        assert d["equipment_id"] == "COMP01"
        assert d["operating_state"] == "steady_running"
        assert d["health_index"] == 0.65
        assert d["expected_anomaly"] is True
        assert d["expected_diagnosis"] == "bearing_wear"


class TestBenchmarkManager:
    def test_industrial_mode_skips_labels(self):
        mgr = BenchmarkManager(mode=BenchmarkMode.INDUSTRIAL)
        label = mgr.record_labels(0.0, "EQ01")
        assert len(mgr.labels) == 0
        assert label.timestamp_s == 0.0

    def test_benchmark_mode_records_labels(self):
        mgr = BenchmarkManager(mode=BenchmarkMode.BENCHMARK)
        mgr.record_labels(0.0, "EQ01", operating_state="steady_running")
        assert len(mgr.labels) == 1
        assert mgr.labels[0].operating_state == "steady_running"

    def test_record_from_engine(self):
        lib = FaultLibrary()
        lib.register(FaultConfig(
            fault_id="test_fault", category="test",
            display_name="Test", severity_curve="linear",
            growth_rate=0.01,
        ))
        engine = FaultEngine(library=lib)
        engine.inject_fault("test_fault", "EQ01", 0.0, 0.4)

        sm = OperatingStateMachine("EQ01", initial=OperatingState.STEADY_RUNNING)

        mgr = BenchmarkManager(mode=BenchmarkMode.BENCHMARK)
        mgr.record_from_engine(100.0, "EQ01", sm, engine)
        assert len(mgr.labels) == 1
        label = mgr.labels[0]
        assert label.operating_state == "steady_running"
        assert "test_fault" in label.active_faults
        assert label.expected_anomaly is True
        assert label.expected_diagnosis == "test_fault"

    def test_healthy_equipment(self):
        lib = FaultLibrary()
        engine = FaultEngine(library=lib)
        sm = OperatingStateMachine("EQ01", initial=OperatingState.STOPPED)
        mgr = BenchmarkManager(mode=BenchmarkMode.BENCHMARK)
        mgr.record_from_engine(0.0, "EQ01", sm, engine)
        label = mgr.labels[0]
        assert label.health_index == 1.0
        assert label.expected_anomaly is False
        assert label.expected_diagnosis == "healthy"

    def test_reset(self):
        mgr = BenchmarkManager(mode=BenchmarkMode.BENCHMARK)
        mgr.record_labels(0.0, "EQ01")
        mgr.reset()
        assert len(mgr.labels) == 0

    def test_build_package(self):
        mgr = BenchmarkManager(mode=BenchmarkMode.BENCHMARK)
        mgr.record_labels(0.0, "COMP01", operating_state="steady_running")

        package = mgr.build_package(
            telemetry_records=[{"timestamp_s": 0.0, "name": "TAG1", "value": 42.0}],
            asset_metadata={"plant": "test"},
            alarm_records=[{"alarm": "HIGH"}],
            maintenance_records=[{"event": "repair"}],
            fault_timeline_records=[{"fault": "bearing_wear"}],
        )
        assert len(package.telemetry_records) == 1
        assert len(package.operating_state_records) == 1
        assert len(package.alarm_records) == 1
        assert len(package.maintenance_records) == 1
        assert len(package.fault_timeline_records) == 1
        assert len(package.benchmark_labels) == 1


class TestBenchmarkExporter:
    def test_export_jsonl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = BenchmarkExporter(output_dir=tmpdir)
            exporter.add_records("telemetry", [
                {"timestamp_s": 0.0, "name": "TAG1", "value": 42.0},
                {"timestamp_s": 1.0, "name": "TAG1", "value": 43.0},
            ])
            results = exporter.export_all(format="jsonl")
            assert "telemetry" in results
            assert os.path.exists(results["telemetry"])

            # Verify content
            with open(results["telemetry"]) as f:
                lines = f.readlines()
                assert len(lines) == 2
                assert "TAG1" in lines[0]

    def test_export_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = BenchmarkExporter(output_dir=tmpdir)
            path = exporter.export_metadata({"plant": "test", "tags": 50})
            assert os.path.exists(path)

    def test_write_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = BenchmarkExporter(output_dir=tmpdir)
            exporter.add_records("telemetry", [{"a": 1}])
            results = exporter.export_all(format="jsonl")
            manifest_path = exporter.write_manifest(results)
            assert os.path.exists(manifest_path)

            with open(manifest_path) as f:
                manifest = json.load(f)
                assert "run_id" in manifest
                assert "datasets" in manifest
                assert "telemetry" in manifest["datasets"]
