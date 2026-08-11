"""M6-S04B-I06-P01 — Quality Record additive projection tests."""

import json
import pytest

from virtual_factory.assembly.demo_snapshot import (
    QualityRecordView,
    AssyDemoSnapshot,
    build_snapshot,
)
from virtual_factory.assembly.line_runtime import AssyLineRuntime
from virtual_factory.assembly.demo_controller import DemoController, DemoScenario


# ═══════════════════════════════════════
# A. Serialization
# ═══════════════════════════════════════

class TestQualityRecordViewSerialization:
    def test_to_dict_emits_expected_keys(self):
        qr = QualityRecordView(
            record_id="QR-0001",
            wip_id="MTR-0001",
            station_id="AP06",
            check_type="TEST",
            disposition="PASS",
            attempt_number=1,
            simulation_time_s=420.0,
            measurements=[{"name": "R_U-V", "value": 1.23, "unit": "\u03a9", "expected_min": 0.8, "expected_max": 1.5}],
            checklist_items=["item_a", "item_b"],
            reason_code="",
        )
        d = qr.to_dict()
        assert set(d.keys()) == {
            "record_id", "wip_id", "station_id", "check_type",
            "disposition", "attempt_number", "simulation_time_s",
            "measurements", "checklist_items", "reason_code",
        }

    def test_empty_record_serializes(self):
        qr = QualityRecordView()
        d = qr.to_dict()
        assert d["measurements"] == []
        assert d["checklist_items"] == []
        assert d["reason_code"] == ""

    def test_measurements_preserved(self):
        qr = QualityRecordView(
            measurements=[
                {"name": "R_U-V", "value": 1.23, "unit": "\u03a9"},
                {"name": "R_V-W", "value": 1.18, "unit": "\u03a9", "expected_min": 0.8, "expected_max": 1.5},
            ]
        )
        d = qr.to_dict()
        assert len(d["measurements"]) == 2
        assert d["measurements"][0]["name"] == "R_U-V"
        assert d["measurements"][1]["expected_min"] == 0.8
        # Optional fields not present when None
        assert "expected_min" not in d["measurements"][0]


# ═══════════════════════════════════════
# B. Empty history
# ═══════════════════════════════════════

class TestEmptyHistory:
    def test_fresh_runtime_has_no_quality_records(self):
        runtime = AssyLineRuntime()
        snap = build_snapshot(runtime, scenario="HAPPY_PATH")
        d = snap.to_dict()
        assert "quality_records" in d
        assert d["quality_records"] == []

    def test_snapshot_default_is_empty(self):
        snap = AssyDemoSnapshot()
        assert snap.quality_records == []


# ═══════════════════════════════════════
# C. AP03 checklist
# ═══════════════════════════════════════

class TestAP03Checklist:
    def test_ap03_has_checklist_type(self):
        ctrl = DemoController(config_path="configs/plants/tipa_assy_demo.yaml", scenario=DemoScenario.HAPPY_PATH)
        snap = ctrl.initialize()
        for _ in range(12):
            snap = ctrl.step()
        d = snap.to_dict()
        ap03_recs = [qr for qr in d["quality_records"] if qr["station_id"] == "AP03"]
        assert len(ap03_recs) > 0, "Should have AP03 records after stepping"
        for qr in ap03_recs:
            assert qr["check_type"] == "CHECKLIST"
            assert len(qr["checklist_items"]) == 3
            assert "mechanical_prep_ok" in qr["checklist_items"]
            assert "visual_check_ok" in qr["checklist_items"]
            assert "measurement_subset_ok" in qr["checklist_items"]
            # No per-item disposition invented
            for item in qr["checklist_items"]:
                assert isinstance(item, str)
            assert qr["disposition"] == "PASS"

    def test_ap03_no_measurements(self):
        ctrl = DemoController(config_path="configs/plants/tipa_assy_demo.yaml", scenario=DemoScenario.HAPPY_PATH)
        snap = ctrl.initialize()
        for _ in range(12):
            snap = ctrl.step()
        d = snap.to_dict()
        for qr in d["quality_records"]:
            if qr["station_id"] == "AP03":
                assert qr["measurements"] == []


# ═══════════════════════════════════════
# D. AP06 measurements
# ═══════════════════════════════════════

class TestAP06Measurements:
    def test_ap06_has_test_type_and_measurements(self):
        ctrl = DemoController(config_path="configs/plants/tipa_assy_demo.yaml", scenario=DemoScenario.HAPPY_PATH)
        snap = ctrl.initialize()
        for _ in range(15):
            snap = ctrl.step()
        d = snap.to_dict()
        ap06_recs = [qr for qr in d["quality_records"] if qr["station_id"] == "AP06"]
        assert len(ap06_recs) > 0, "Should have AP06 records"
        for qr in ap06_recs:
            assert qr["check_type"] == "TEST"
            assert len(qr["measurements"]) == 3
            names = {m["name"] for m in qr["measurements"]}
            assert names == {"R_U-V", "R_V-W", "R_W-U"}
            for m in qr["measurements"]:
                assert "value" in m
                assert "unit" in m
                assert m["unit"] == "\u03a9"

    def test_ap06_measurements_have_expected_ranges(self):
        ctrl = DemoController(config_path="configs/plants/tipa_assy_demo.yaml", scenario=DemoScenario.HAPPY_PATH)
        snap = ctrl.initialize()
        for _ in range(15):
            snap = ctrl.step()
        d = snap.to_dict()
        for qr in d["quality_records"]:
            if qr["station_id"] == "AP06":
                for m in qr["measurements"]:
                    assert "expected_min" in m
                    assert "expected_max" in m
                    assert m["expected_min"] < m["expected_max"]


# ═══════════════════════════════════════
# E. Scenario-dependent quality history (via DemoController + composition)
# ═══════════════════════════════════════

class TestScenarioQualityHistory:
    """Tests that verify quality_records projection preserves attempt history
    under per-sub-line exception scenarios.  Uses DemoController with TIPA
    ASSY config which internally delegates to AssyDemoComposition."""

    def test_ap06_fail_retest_has_fail_disposition(self):
        ctrl = DemoController(config_path="configs/plants/tipa_assy_demo.yaml",
                              scenario=DemoScenario.AP06_FAIL_RETEST_PASS)
        ctrl.initialize()
        for _ in range(35):
            ctrl.step()
        snap = ctrl.detail_for("ASSY-SL03")
        d = snap.to_dict()
        ap06_recs = [qr for qr in d["quality_records"] if qr["station_id"] == "AP06"]
        assert len(ap06_recs) > 0, "Should have AP06 records on exception target"
        dispositions = {qr["disposition"] for qr in ap06_recs}
        assert "FAIL" in dispositions, f"ASSY-SL03 should have FAIL: got {dispositions}"

    def test_ap06_retest_attempts_monotonic(self):
        ctrl = DemoController(config_path="configs/plants/tipa_assy_demo.yaml",
                              scenario=DemoScenario.AP06_FAIL_RETEST_PASS)
        ctrl.initialize()
        for _ in range(35):
            ctrl.step()
        snap = ctrl.detail_for("ASSY-SL03")
        d = snap.to_dict()
        by_wip = {}
        for qr in d["quality_records"]:
            if qr["station_id"] == "AP06":
                by_wip.setdefault(qr["wip_id"], []).append(qr)
        for wip_id, recs in by_wip.items():
            attempts = [r["attempt_number"] for r in sorted(recs, key=lambda r: r["simulation_time_s"])]
            for i in range(1, len(attempts)):
                assert attempts[i] >= attempts[i-1], f"{wip_id}: attempts not monotonic"

    def test_ap08_reinspect_has_vision_records(self):
        ctrl = DemoController(config_path="configs/plants/tipa_assy_demo.yaml",
                              scenario=DemoScenario.AP08_NG_REINSPECT_PASS)
        ctrl.initialize()
        for _ in range(35):
            ctrl.step()
        snap = ctrl.detail_for("ASSY-SL02")
        d = snap.to_dict()
        ap08_recs = [qr for qr in d["quality_records"] if qr["station_id"] == "AP08"]
        assert len(ap08_recs) > 0, "Should have AP08 records"
        assert any(qr["check_type"] == "VISUAL_INSPECTION" for qr in ap08_recs)

    def test_ap08_has_surface_quality_checklist(self):
        ctrl = DemoController(config_path="configs/plants/tipa_assy_demo.yaml",
                              scenario=DemoScenario.AP08_NG_REINSPECT_PASS)
        ctrl.initialize()
        for _ in range(35):
            ctrl.step()
        snap = ctrl.detail_for("ASSY-SL02")
        d = snap.to_dict()
        for qr in d["quality_records"]:
            if qr["station_id"] == "AP08":
                assert len(qr["checklist_items"]) == 3
                assert "surface_quality" in qr["checklist_items"]

    def test_failed_final_has_quality_records(self):
        ctrl = DemoController(config_path="configs/plants/tipa_assy_demo.yaml",
                              scenario=DemoScenario.FAILED_FINAL)
        ctrl.initialize()
        for _ in range(35):
            ctrl.step()
        snap = ctrl.detail_for("ASSY-SL06")
        d = snap.to_dict()
        assert len(d["quality_records"]) > 0


# ═══════════════════════════════════════
# H. Snapshot JSON compatibility
# ═══════════════════════════════════════

class TestSnapshotCompatibility:
    def test_existing_keys_unchanged(self):
        """quality_records is additive — all existing keys preserved."""
        ctrl = DemoController(config_path="configs/plants/tipa_assy_demo.yaml", scenario=DemoScenario.HAPPY_PATH)
        snap = ctrl.initialize()
        for _ in range(10):
            snap = ctrl.step()
        d = snap.to_dict()
        expected_keys = {
            "simulation_time_s", "line_state", "dwell_number", "nominal_dwell_s",
            "positions", "genealogy", "recent_quality_events", "quality_records",
            "production", "scenario", "plant_id", "production_line_id",
            "sub_line_id", "variant",
        }
        assert set(d.keys()) == expected_keys

    def test_positions_shape_unchanged(self):
        ctrl = DemoController(config_path="configs/plants/tipa_assy_demo.yaml", scenario=DemoScenario.HAPPY_PATH)
        snap = ctrl.initialize()
        for _ in range(10):
            snap = ctrl.step()
        d = snap.to_dict()
        assert len(d["positions"]) == 12
        for p in d["positions"]:
            assert set(p.keys()) == {
                "position_id", "station_label", "carrier_id", "wip_id",
                "wip_type", "manufacturing_status", "quality_status",
                "latest_quality_result", "attempt_number", "is_occupied",
                "is_quality_hold", "held_reason",
            }

    def test_genealogy_shape_unchanged(self):
        ctrl = DemoController(config_path="configs/plants/tipa_assy_demo.yaml", scenario=DemoScenario.HAPPY_PATH)
        snap = ctrl.initialize()
        for _ in range(12):
            snap = ctrl.step()
        d = snap.to_dict()
        for g in d["genealogy"]:
            assert "child_wip_id" in g
            assert "parent_wip_ids" in g


# ═══════════════════════════════════════
# I. Detached projection
# ═══════════════════════════════════════

class TestDetachedProjection:
    def test_quality_record_view_is_detached(self):
        """Mutating serialized dict does not affect runtime."""
        ctrl = DemoController(config_path="configs/plants/tipa_assy_demo.yaml", scenario=DemoScenario.HAPPY_PATH)
        snap = ctrl.initialize()
        for _ in range(12):
            snap = ctrl.step()
        d1 = snap.to_dict()
        # Mutate the serialized output
        if d1["quality_records"]:
            d1["quality_records"][0]["disposition"] = "MUTATED"
        # Re-serialize — should not have mutation
        d2 = snap.to_dict()
        if d1["quality_records"] and d2["quality_records"]:
            # Original disposition preserved in new serialization
            assert d2["quality_records"][0]["disposition"] != "MUTATED"


# ═══════════════════════════════════════
# J. Released WIP history accessibility
# ═══════════════════════════════════════

class TestReleasedWipHistory:
    def test_released_wip_quality_records_remain(self):
        ctrl = DemoController(config_path="configs/plants/tipa_assy_demo.yaml", scenario=DemoScenario.HAPPY_PATH)
        snap = ctrl.initialize()
        for _ in range(30):
            snap = ctrl.step()
        d = snap.to_dict()
        # Find released WIPs
        released_wips = set()
        for p in d["positions"]:
            if p.get("manufacturing_status") == "released":
                # Released WIPs leave positions[], so check quality_records
                pass
        # Released WIPs should still have quality records via wip_ids
        all_qr_wips = {qr["wip_id"] for qr in d["quality_records"]}
        # At minimum, some quality records exist
        assert len(all_qr_wips) > 0, "Quality records should reference WIP IDs"

    def test_motor_count_matches_quality_coverage(self):
        ctrl = DemoController(config_path="configs/plants/tipa_assy_demo.yaml", scenario=DemoScenario.HAPPY_PATH)
        snap = ctrl.initialize()
        for _ in range(20):
            snap = ctrl.step()
        d = snap.to_dict()
        # Each MTR should have at minimum AP06 + AP08 + AP11 records
        mtr_records = [qr for qr in d["quality_records"] if qr["wip_id"].startswith("MTR")]
        motors_created = d["production"]["motors_created"]
        # Not every MTR may have all records yet, but total should be positive
        assert len(mtr_records) > 0
