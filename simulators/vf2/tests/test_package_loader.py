"""Tests for the VF-2 package loader (ST01)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from simulators.vf2.models import VF2Package
from simulators.vf2.package_loader import load_package

GOLDEN_FIXTURE = (
    Path(__file__).resolve().parent.parent / "examples" / "sample_pim_package.json"
)


class TestPackageLoader:

    def test_load_golden_fixture(self):
        """Golden fixture must load without error."""
        pkg = load_package(GOLDEN_FIXTURE)
        assert isinstance(pkg, VF2Package)
        assert pkg.package_id == "VF2-PKG-UNIT-REF-PUMP-STATION-01"
        assert pkg.package_type == "vf2_simulation_package"
        assert pkg.schema_version == "1.0"

    def test_source_model(self):
        pkg = load_package(GOLDEN_FIXTURE)
        assert pkg.source_model.system == "PIM"
        assert pkg.source_model.model_version == "PIM-PH04-v0.1"
        assert pkg.source_model.unit_id == "UNIT-REF-PUMP-STATION-01"

    def test_objects_count(self):
        pkg = load_package(GOLDEN_FIXTURE)
        assert len(pkg.objects) == 8

    def test_objects_have_required_fields(self):
        pkg = load_package(GOLDEN_FIXTURE)
        for obj in pkg.objects:
            assert obj.simulation_object_id  # not empty
            assert obj.canonical_id          # not empty
            assert obj.object_type           # valid enum
            assert obj.name                  # not empty
            assert obj.unit_id               # not empty
            assert obj.source.canonical_id   # provenance back-reference

    def test_object_types(self):
        pkg = load_package(GOLDEN_FIXTURE)
        types = {obj.object_type for obj in pkg.objects}
        assert "centrifugal_pump" in types
        assert "electric_motor" in types
        assert "gate_valve" in types
        assert "check_valve" in types

    def test_signals_count(self):
        pkg = load_package(GOLDEN_FIXTURE)
        assert len(pkg.signals) == 4

    def test_signals_have_required_fields(self):
        pkg = load_package(GOLDEN_FIXTURE)
        for sig in pkg.signals:
            assert sig.simulation_signal_id.startswith("VF2.")
            assert sig.canonical_asset_id
            assert sig.name
            assert sig.direction in ("VF2_INPUT", "VF2_OUTPUT")
            assert sig.behavior.signal_type in ("measurement", "status", "alarm", "setpoint", "feedback")

    def test_topology(self):
        pkg = load_package(GOLDEN_FIXTURE)
        assert len(pkg.topology.process_edges) >= 1
        edge = pkg.topology.process_edges[0]
        assert edge.from_simulation_object_id  # "from" mapped correctly
        assert edge.to_simulation_object_id    # "to" mapped correctly

    def test_scenarios_count(self):
        pkg = load_package(GOLDEN_FIXTURE)
        assert len(pkg.scenarios) == 6

    def test_pump_trip_scenario_has_affected_signals(self):
        pkg = load_package(GOLDEN_FIXTURE)
        trip = [s for s in pkg.scenarios if s.scenario_id == "SCN-PUMP-TRIP-002"]
        assert len(trip) == 1
        trip = trip[0]
        assert trip.scenario_type == "pump_trip"
        assert len(trip.affected_simulation_signal_ids) == 3
        assert len(trip.expected_effects) == 3

    def test_validation_rules(self):
        pkg = load_package(GOLDEN_FIXTURE)
        assert len(pkg.validation_rules) >= 1

    def test_rejects_invalid_schema_version(self):
        with open(GOLDEN_FIXTURE) as f:
            data = json.load(f)
        data["schema_version"] = "99.0"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            json.dump(data, tmp)
            tmp_path = tmp.name

        with pytest.raises(ValueError, match="Unsupported schema version"):
            load_package(tmp_path)

    def test_rejects_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_package("nonexistent.json")
