"""Tests for VF-2 package validator (ST02)."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from simulators.vf2.models import VF2ProcessEdge
from simulators.vf2.package_loader import load_package
from simulators.vf2.package_validator import validate_package, ValidationResult

GOLDEN = (
    Path(__file__).resolve().parent.parent
    / "examples"
    / "sample_pim_package.json"
)


# ──────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def golden_pkg():
    return load_package(GOLDEN)


# ──────────────────────────────────────────────────────────────────────
# AC-1: golden fixture passes
# ──────────────────────────────────────────────────────────────────────


class TestGoldenFixture:

    def test_golden_fixture_passes(self, golden_pkg):
        result = validate_package(golden_pkg)
        assert result.valid, f"Golden fixture should be valid, got: {result.errors}"
        assert len(result.errors) == 0


# ──────────────────────────────────────────────────────────────────────
# V1: package_id
# ──────────────────────────────────────────────────────────────────────


class TestPackageId:

    def test_missing_package_id(self, golden_pkg):
        pkg = deepcopy(golden_pkg)
        pkg.package_id = ""
        result = validate_package(pkg)
        assert not result.valid
        assert any("V1" in e for e in result.errors)


# ──────────────────────────────────────────────────────────────────────
# V2: source_model.system
# ──────────────────────────────────────────────────────────────────────


class TestSourceModel:

    def test_wrong_system(self, golden_pkg):
        pkg = deepcopy(golden_pkg)
        pkg.source_model.system = "NOT_PIM"
        result = validate_package(pkg)
        assert not result.valid
        assert any("V2" in e for e in result.errors)


# ──────────────────────────────────────────────────────────────────────
# V3 / V4 / V5: duplicates
# ──────────────────────────────────────────────────────────────────────


class TestDuplicates:

    def test_duplicate_object_id(self, golden_pkg):
        pkg = deepcopy(golden_pkg)
        # Duplicate the first object with the same ID
        dup = deepcopy(pkg.objects[0])
        pkg.objects = list(pkg.objects) + [dup]
        result = validate_package(pkg)
        assert not result.valid
        assert any("V3" in e for e in result.errors)

    def test_duplicate_signal_id(self, golden_pkg):
        pkg = deepcopy(golden_pkg)
        dup = deepcopy(pkg.signals[0])
        pkg.signals = list(pkg.signals) + [dup]
        result = validate_package(pkg)
        assert not result.valid
        assert any("V4" in e for e in result.errors)

    def test_duplicate_scenario_id(self, golden_pkg):
        pkg = deepcopy(golden_pkg)
        dup = deepcopy(pkg.scenarios[0])
        pkg.scenarios = list(pkg.scenarios) + [dup]
        result = validate_package(pkg)
        assert not result.valid
        assert any("V5" in e for e in result.errors)


# ──────────────────────────────────────────────────────────────────────
# V6: object identity fields
# ──────────────────────────────────────────────────────────────────────


class TestObjectIdentity:

    def test_object_missing_simulation_object_id(self, golden_pkg):
        pkg = deepcopy(golden_pkg)
        pkg.objects[0].simulation_object_id = ""
        result = validate_package(pkg)
        assert not result.valid
        assert any("V6" in e for e in result.errors)

    def test_object_missing_canonical_id(self, golden_pkg):
        pkg = deepcopy(golden_pkg)
        pkg.objects[0].canonical_id = ""
        result = validate_package(pkg)
        assert not result.valid
        assert any("V6" in e for e in result.errors)


# ──────────────────────────────────────────────────────────────────────
# V8: signal ID prefix
# ──────────────────────────────────────────────────────────────────────


class TestSignalPrefix:

    def test_signal_id_without_vf2_prefix(self, golden_pkg):
        pkg = deepcopy(golden_pkg)
        pkg.signals[0].simulation_signal_id = "BAD.PREFIX"
        result = validate_package(pkg)
        assert not result.valid
        assert any("V8" in e for e in result.errors)


# ──────────────────────────────────────────────────────────────────────
# V9 / V10: topology boundary endpoints
# ──────────────────────────────────────────────────────────────────────


class TestBoundaryEndpoints:

    def test_boundary_endpoint_warning_compat_mode(self, golden_pkg):
        pkg = deepcopy(golden_pkg)
        bogus_edge = VF2ProcessEdge(
            from_simulation_object_id="VF2-REF-PMP-101A",
            to_simulation_object_id="VF2-NONEXISTENT",
            relation_type="FLOWS_TO",
        )
        pkg.topology.process_edges = list(pkg.topology.process_edges) + [bogus_edge]
        result = validate_package(pkg, strict=False)
        assert result.valid, "Compat mode: boundary endpoints should be warnings only"
        assert any("Boundary endpoint" in w for w in result.warnings)

    def test_boundary_endpoint_error_strict_mode(self, golden_pkg):
        pkg = deepcopy(golden_pkg)
        bogus_edge = VF2ProcessEdge(
            from_simulation_object_id="VF2-REF-PMP-101A",
            to_simulation_object_id="VF2-NONEXISTENT",
            relation_type="FLOWS_TO",
        )
        pkg.topology.process_edges = list(pkg.topology.process_edges) + [bogus_edge]
        result = validate_package(pkg, strict=True)
        assert not result.valid, "Strict mode: boundary endpoints should be errors"
        assert any("V9/V10" in e for e in result.errors)


# ──────────────────────────────────────────────────────────────────────
# V11: scenario trigger
# ──────────────────────────────────────────────────────────────────────


class TestScenarioTrigger:

    def test_trigger_nonexistent_object(self, golden_pkg):
        pkg = deepcopy(golden_pkg)
        pkg.scenarios[0].trigger_simulation_object_id = "VF2-DOES-NOT-EXIST"
        result = validate_package(pkg)
        assert not result.valid
        assert any("V11" in e for e in result.errors)

    def test_trigger_none_is_ok(self, golden_pkg):
        """A scenario may have no trigger (e.g. normal_operation)."""
        pkg = deepcopy(golden_pkg)
        pkg.scenarios[0].trigger_simulation_object_id = None
        result = validate_package(pkg)
        assert result.valid


# ──────────────────────────────────────────────────────────────────────
# V12: affected signals
# ──────────────────────────────────────────────────────────────────────


class TestAffectedSignals:

    def test_affected_signal_nonexistent(self, golden_pkg):
        pkg = deepcopy(golden_pkg)
        pkg.scenarios[0].affected_simulation_signal_ids = ["NONEXISTENT.SIGNAL"]
        result = validate_package(pkg)
        assert result.valid  # V12 is warning-only
        assert any("V12" in w for w in result.warnings)


# ──────────────────────────────────────────────────────────────────────
# V7 / V13: orphan signals
# ──────────────────────────────────────────────────────────────────────


class TestOrphanSignals:

    def test_orphan_signal_warning(self, golden_pkg):
        pkg = deepcopy(golden_pkg)
        pkg.signals[0].canonical_asset_id = "NONEXISTENT-ASSET-ID"
        result = validate_package(pkg)
        assert result.valid  # V7/V13 is warning-only
        assert any("V7/V13" in w for w in result.warnings)


# ──────────────────────────────────────────────────────────────────────
# V14: schema_version
# ──────────────────────────────────────────────────────────────────────


class TestSchemaVersion:

    def test_wrong_schema_version(self, golden_pkg):
        pkg = deepcopy(golden_pkg)
        pkg.schema_version = "2.0"
        result = validate_package(pkg)
        assert not result.valid
        assert any("V14" in e for e in result.errors)


# ──────────────────────────────────────────────────────────────────────
# V15: validation rules completeness
# ──────────────────────────────────────────────────────────────────────


class TestValidationRules:

    def test_rule_missing_rule_id(self, golden_pkg):
        pkg = deepcopy(golden_pkg)
        pkg.validation_rules[0].rule_id = ""
        result = validate_package(pkg)
        assert result.valid  # V15 is warning-only
        assert any("V15" in w for w in result.warnings)

    def test_rule_missing_rule_name(self, golden_pkg):
        pkg = deepcopy(golden_pkg)
        pkg.validation_rules[0].rule_name = ""
        result = validate_package(pkg)
        assert result.valid
        assert any("V15" in w for w in result.warnings)


# ──────────────────────────────────────────────────────────────────────
# V16: expected effects signal reference
# ──────────────────────────────────────────────────────────────────────


class TestExpectedEffects:

    def test_effect_signal_nonexistent(self, golden_pkg):
        pkg = deepcopy(golden_pkg)
        pkg.scenarios[0].expected_effects[0].signal_id = "NONEXISTENT.SIG"
        result = validate_package(pkg)
        assert result.valid  # V16 is warning-only
        assert any("V16" in w for w in result.warnings)


# ──────────────────────────────────────────────────────────────────────
# Edge: empty objects
# ──────────────────────────────────────────────────────────────────────


class TestEmptyPackage:

    def test_empty_objects(self, golden_pkg):
        pkg = deepcopy(golden_pkg)
        pkg.objects = []
        result = validate_package(pkg)
        # With no objects, scenario triggers fail (V11) and topology edges
        # become boundary warnings. This is expected — empty objects is
        # invalid when scenarios and topology reference them.
        assert not result.valid
        assert any("V11" in e for e in result.errors)


# ──────────────────────────────────────────────────────────────────────
# Electrical edges boundary check
# ──────────────────────────────────────────────────────────────────────


class TestElectricalEdges:

    def test_electrical_edge_boundary_warning(self, golden_pkg):
        pkg = deepcopy(golden_pkg)
        bogus = VF2ProcessEdge(
            from_simulation_object_id="VF2-NONEXISTENT-MCC",
            to_simulation_object_id="VF2-REF-PMP-MTR-101A",
            relation_type="POWERS",
        )
        pkg.topology.electrical_edges = [bogus]
        result = validate_package(pkg, strict=False)
        assert result.valid
        assert any("Boundary endpoint" in w for w in result.warnings)
