"""M6-S04B-I01 — Context Identity + Config Extension Tests.

Tests identity model, validation, config parsing, and ensures additive
YAML section does not break existing AssyLineConfig loading.
"""

from __future__ import annotations

import copy
import tempfile
import os
from pathlib import Path

import pytest
import yaml

from virtual_factory.assembly.sub_line_identity import (
    AssySubLineIdentity,
    AssyProductionLineIdentity,
    SubLineIdentityError,
    load_assy_demo_identity_from_yaml,
    CANONICAL_TIPA_SUB_LINE_IDS,
)

from virtual_factory.assembly.line_runtime import (
    load_assy_config_from_yaml,
)


# ═══════════════════════════════════════════════════════════
# YAML fixture helpers
# ═══════════════════════════════════════════════════════════

REAL_CONFIG = (
    Path(__file__).resolve().parent.parent
    / "configs" / "plants" / "tipa_assy_demo.yaml"
)


def _write_temp_yaml(content: dict) -> str:
    """Write a dict to a temp YAML file, return path."""
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    yaml.safe_dump(content, tmp)
    tmp.close()
    return tmp.name


MINIMAL_VALID_EXTRA = {
    "production_line": {
        "plant_id": "TIPA",
        "id": "ASSY",
        "label": "ASSY Line",
        "sub_lines": [
            {"id": "ASSY-SL01", "variant": "hydraulic", "label": "ASSY-SL01 — Hydraulic"},
            {"id": "ASSY-SL02", "variant": "hydraulic", "label": "ASSY-SL02 — Hydraulic"},
            {"id": "ASSY-SL03", "variant": "hydraulic", "label": "ASSY-SL03 — Hydraulic"},
            {"id": "ASSY-SL04", "variant": "thermal", "label": "ASSY-SL04 — Thermal"},
            {"id": "ASSY-SL05", "variant": "thermal", "label": "ASSY-SL05 — Thermal"},
            {"id": "ASSY-SL06", "variant": "thermal", "label": "ASSY-SL06 — Thermal"},
        ],
        "demo": {"target_sub_line_for_exception": "ASSY-SL03"},
    }
}


# ═══════════════════════════════════════════════════════════
# Identity parsing tests
# ═══════════════════════════════════════════════════════════

class TestIdentityParsing:
    """Tests for loading and parsing the identity model."""

    def test_real_config_parses(self):
        """The real tipa_assy_demo.yaml must parse correctly."""
        identity = load_assy_demo_identity_from_yaml(str(REAL_CONFIG))
        assert identity.plant_id == "TIPA"
        assert identity.production_line_id == "ASSY"
        assert identity.label == "ASSY Line"
        assert len(identity.sub_lines) == 6

    def test_all_six_canonical_ids_present(self):
        """All six canonical sub_line_ids must be present."""
        identity = load_assy_demo_identity_from_yaml(str(REAL_CONFIG))
        ids = {sl.sub_line_id for sl in identity.sub_lines}
        assert ids == CANONICAL_TIPA_SUB_LINE_IDS

    def test_hydraulic_thermal_mapping(self):
        """SL01-SL03 = hydraulic, SL04-SL06 = thermal."""
        identity = load_assy_demo_identity_from_yaml(str(REAL_CONFIG))
        hyd = {sl.sub_line_id for sl in identity.hydraulic_sub_lines}
        thm = {sl.sub_line_id for sl in identity.thermal_sub_lines}
        assert hyd == {"ASSY-SL01", "ASSY-SL02", "ASSY-SL03"}
        assert thm == {"ASSY-SL04", "ASSY-SL05", "ASSY-SL06"}

    def test_exception_target_is_sl03(self):
        """Default exception target is ASSY-SL03."""
        identity = load_assy_demo_identity_from_yaml(str(REAL_CONFIG))
        assert identity.target_sub_line_for_exception == "ASSY-SL03"

    def test_production_line_id_on_sub_lines(self):
        """Every sub-line must have production_line_id == ASSY."""
        identity = load_assy_demo_identity_from_yaml(str(REAL_CONFIG))
        for sl in identity.sub_lines:
            assert sl.production_line_id == "ASSY", sl

    def test_get_sub_line(self):
        """get_sub_line lookup works."""
        identity = load_assy_demo_identity_from_yaml(str(REAL_CONFIG))
        sl = identity.get_sub_line("ASSY-SL01")
        assert sl is not None
        assert sl.variant == "hydraulic"
        assert identity.get_sub_line("NONEXISTENT") is None

    def test_minimal_valid_yaml_parses(self):
        """A minimal valid YAML should parse."""
        path = _write_temp_yaml({"plant": {"id": "TIPA"}, **MINIMAL_VALID_EXTRA})
        try:
            identity = load_assy_demo_identity_from_yaml(path)
            assert len(identity.sub_lines) == 6
        finally:
            os.unlink(path)

    def test_identity_immutable(self):
        """AssySubLineIdentity and AssyProductionLineIdentity are frozen."""
        with pytest.raises(Exception):
            AssySubLineIdentity("ASSY", "ASSY-SL01", "hydraulic", "label").sub_line_id = "x"  # type: ignore


# ═══════════════════════════════════════════════════════════
# Validation tests
# ═══════════════════════════════════════════════════════════

class TestValidation:
    """Tests for identity validation rules."""

    def test_missing_production_line_section(self):
        """Config without production_line section must raise."""
        path = _write_temp_yaml({})
        try:
            with pytest.raises(SubLineIdentityError, match="production_line"):
                load_assy_demo_identity_from_yaml(path)
        finally:
            os.unlink(path)

    def test_wrong_plant_id_rejected(self):
        """Non-'TIPA' plant_id must be rejected."""
        cfg = copy.deepcopy(MINIMAL_VALID_EXTRA)
        cfg["production_line"]["plant_id"] = "SOME_OTHER_PLANT"
        path = _write_temp_yaml(cfg)
        try:
            with pytest.raises(SubLineIdentityError, match="plant_id"):
                load_assy_demo_identity_from_yaml(path)
        finally:
            os.unlink(path)

    def test_wrong_production_line_id_rejected(self):
        """Non-'ASSY' production_line_id must be rejected."""
        cfg = copy.deepcopy(MINIMAL_VALID_EXTRA)
        cfg["production_line"]["id"] = "NOT_ASSY"
        path = _write_temp_yaml(cfg)
        try:
            with pytest.raises(SubLineIdentityError, match="production_line_id"):
                load_assy_demo_identity_from_yaml(path)
        finally:
            os.unlink(path)

    def test_duplicate_sub_line_id_rejected(self):
        """Duplicate sub-line IDs must be rejected."""
        cfg = copy.deepcopy(MINIMAL_VALID_EXTRA)
        # Duplicate SL03
        cfg["production_line"]["sub_lines"][2] = cfg["production_line"]["sub_lines"][1]
        path = _write_temp_yaml({"plant": {"id": "TIPA"}, **cfg})
        try:
            with pytest.raises(SubLineIdentityError, match="Duplicate"):
                load_assy_demo_identity_from_yaml(path)
        finally:
            os.unlink(path)

    def test_wrong_count_rejected(self):
        """Fewer or more than 6 sub-lines must be rejected."""
        cfg = copy.deepcopy(MINIMAL_VALID_EXTRA)
        cfg["production_line"]["sub_lines"] = cfg["production_line"]["sub_lines"][:5]
        path = _write_temp_yaml({"plant": {"id": "TIPA"}, **cfg})
        try:
            with pytest.raises(SubLineIdentityError, match="Expected exactly 6"):
                load_assy_demo_identity_from_yaml(path)
        finally:
            os.unlink(path)

    def test_unknown_sub_line_id_rejected(self):
        """Sub-line ID not in canonical set must be rejected."""
        cfg = copy.deepcopy(MINIMAL_VALID_EXTRA)
        cfg["production_line"]["sub_lines"][0]["id"] = "ASSY-SL99"
        path = _write_temp_yaml({"plant": {"id": "TIPA"}, **cfg})
        try:
            with pytest.raises(SubLineIdentityError, match="Unknown sub_line_id"):
                load_assy_demo_identity_from_yaml(path)
        finally:
            os.unlink(path)

    def test_invalid_variant_rejected(self):
        """Unknown variant must be rejected."""
        cfg = copy.deepcopy(MINIMAL_VALID_EXTRA)
        cfg["production_line"]["sub_lines"][0]["variant"] = "pneumatic"
        path = _write_temp_yaml({"plant": {"id": "TIPA"}, **cfg})
        try:
            with pytest.raises(SubLineIdentityError, match="unknown variant"):
                load_assy_demo_identity_from_yaml(path)
        finally:
            os.unlink(path)

    def test_hydraulic_with_thermal_variant_rejected(self):
        """ASSY-SL01 with thermal variant must be rejected."""
        cfg = copy.deepcopy(MINIMAL_VALID_EXTRA)
        cfg["production_line"]["sub_lines"][0]["variant"] = "thermal"  # SL01
        path = _write_temp_yaml({"plant": {"id": "TIPA"}, **cfg})
        try:
            with pytest.raises(SubLineIdentityError, match="must have variant 'hydraulic'"):
                load_assy_demo_identity_from_yaml(path)
        finally:
            os.unlink(path)

    def test_thermal_with_hydraulic_variant_rejected(self):
        """ASSY-SL04 with hydraulic variant must be rejected."""
        cfg = copy.deepcopy(MINIMAL_VALID_EXTRA)
        cfg["production_line"]["sub_lines"][3]["variant"] = "hydraulic"  # SL04
        path = _write_temp_yaml({"plant": {"id": "TIPA"}, **cfg})
        try:
            with pytest.raises(SubLineIdentityError, match="must have variant 'thermal'"):
                load_assy_demo_identity_from_yaml(path)
        finally:
            os.unlink(path)

    def test_missing_target_rejected(self):
        """Empty target must be rejected."""
        cfg = copy.deepcopy(MINIMAL_VALID_EXTRA)
        cfg["production_line"]["demo"]["target_sub_line_for_exception"] = ""
        path = _write_temp_yaml({"plant": {"id": "TIPA"}, **cfg})
        try:
            with pytest.raises(SubLineIdentityError, match="target_sub_line_for_exception"):
                load_assy_demo_identity_from_yaml(path)
        finally:
            os.unlink(path)

    def test_unknown_target_rejected(self):
        """Target referencing non-existent sub-line must be rejected."""
        cfg = copy.deepcopy(MINIMAL_VALID_EXTRA)
        cfg["production_line"]["demo"]["target_sub_line_for_exception"] = "ASSY-SL99"
        path = _write_temp_yaml({"plant": {"id": "TIPA"}, **cfg})
        try:
            with pytest.raises(SubLineIdentityError, match="target_sub_line_for_exception"):
                load_assy_demo_identity_from_yaml(path)
        finally:
            os.unlink(path)

    def test_sub_line_production_line_id_matches(self):
        """Every sub-line's production_line_id must equal the line's id."""
        identity = load_assy_demo_identity_from_yaml(str(REAL_CONFIG))
        for sl in identity.sub_lines:
            assert sl.production_line_id == identity.production_line_id, (
                f"{sl.sub_line_id}: {sl.production_line_id} != {identity.production_line_id}"
            )


# ═══════════════════════════════════════════════════════════
# Compatibility tests — existing config loader unchanged
# ═══════════════════════════════════════════════════════════

class TestExistingLoaderCompatibility:
    """Prove the additive YAML section does NOT break existing loading."""

    def test_load_assy_config_from_yaml_still_works(self):
        """Existing loader must produce correct AssyLineConfig."""
        config = load_assy_config_from_yaml(str(REAL_CONFIG))
        assert config.conveyor.nominal_line_dwell_time_s == 120.0
        assert config.conveyor.index_movement_duration_s == 0.0
        assert "PRE-ASSY" in config.conveyor.positions
        assert "AP11" in config.conveyor.positions
        assert len(config.conveyor.positions) == 12

    def test_station_durations_unchanged(self):
        """Station durations must be unchanged."""
        config = load_assy_config_from_yaml(str(REAL_CONFIG))
        assert config.station_durations["PRE-ASSY"] == 30.0
        assert config.station_durations["AP06"] == 60.0
        assert config.station_durations["AP11"] == 30.0

    def test_quality_config_unchanged(self):
        """Quality config must be unchanged."""
        config = load_assy_config_from_yaml(str(REAL_CONFIG))
        assert config.quality.ap06.max_attempts == 2
        assert config.quality.ap06.scenario == "FAIL_FIRST_THEN_PASS"
        assert config.quality.ap11.scenario == "PASS"

    def test_upstream_config_unchanged(self):
        """Upstream config must be unchanged."""
        config = load_assy_config_from_yaml(str(REAL_CONFIG))
        assert config.upstream.sso2_wip_prefix == "SSO2"
        assert config.upstream.rso2_wip_prefix == "RSO2"
        assert config.upstream.sso2_production_interval_s == 120.0

    def test_identity_prefix_unchanged(self):
        """Motor WIP prefix must be unchanged."""
        config = load_assy_config_from_yaml(str(REAL_CONFIG))
        assert config.motor_wip_prefix == "MTR"

    def test_ap04_config_unchanged(self):
        """AP04 join config must be unchanged."""
        config = load_assy_config_from_yaml(str(REAL_CONFIG))
        assert "SSO2" in config.ap04_required_parent_sources
        assert "RSO2" in config.ap04_required_parent_sources
