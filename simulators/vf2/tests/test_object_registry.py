"""Tests for VF-2 dynamic ObjectRegistry (ST03)."""

from __future__ import annotations

from pathlib import Path

import pytest

from simulators.vf2.object_registry import ObjectRegistry
from simulators.vf2.package_loader import load_package

GOLDEN = (
    Path(__file__).resolve().parent.parent
    / "examples"
    / "sample_pim_package.json"
)


@pytest.fixture(scope="module")
def reg():
    return ObjectRegistry(load_package(GOLDEN))


class TestObjectRegistry:

    # AC-1
    def test_from_package(self, reg):
        assert reg.object_count == 8

    # AC-2
    def test_get_existing(self, reg):
        obj = reg.get("VF2-REF-PMP-101A")
        assert obj is not None
        assert obj.object_type == "centrifugal_pump"
        assert obj.name == "Main Pump A (duty)"

    def test_get_nonexistent(self, reg):
        assert reg.get("VF2-NONEXISTENT") is None

    # AC-3
    def test_filter_by_type(self, reg):
        pumps = reg.filter_by_type("centrifugal_pump")
        assert len(pumps) == 2
        motors = reg.filter_by_type("electric_motor")
        assert len(motors) == 2
        gate_valves = reg.filter_by_type("gate_valve")
        assert len(gate_valves) == 2
        check_valves = reg.filter_by_type("check_valve")
        assert len(check_valves) == 2

    def test_filter_by_unit(self, reg):
        objs = reg.filter_by_unit("UNIT-REF-PUMP-STATION-01")
        assert len(objs) == 8  # All objects are in this unit

    def test_get_by_canonical(self, reg):
        obj = reg.get_by_canonical("ASSET-REF-PMP-101A")
        assert obj is not None
        assert obj.simulation_object_id == "VF2-REF-PMP-101A"

    def test_get_by_canonical_nonexistent(self, reg):
        assert reg.get_by_canonical("NONEXISTENT") is None

    def test_object_ids(self, reg):
        ids = reg.object_ids
        assert "VF2-REF-PMP-101A" in ids
        assert "VF2-REF-PMP-MTR-101A" in ids
        assert "VF2-REF-PMP-VLV-102A" in ids
        assert len(ids) == 8

    def test_object_types(self, reg):
        types = reg.object_types
        assert "centrifugal_pump" in types
        assert "electric_motor" in types
        assert "gate_valve" in types
        assert "check_valve" in types

    def test_all_objects(self, reg):
        objs = reg.all_objects
        assert len(objs) == 8
