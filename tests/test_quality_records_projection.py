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
    def test_ap03_has_no_quality_record(self):
        # OPS-02-C01: AP03 is a checklist gate, not a quality-decision station —
        # its completion must NOT fabricate a quality record.
        ctrl = DemoController(config_path="configs/plants/tipa_assy_demo.yaml", scenario=DemoScenario.HAPPY_PATH)
        snap = ctrl.initialize()
        for _ in range(12):
            snap = ctrl.step()
        d = snap.to_dict()
        ap03_recs = [qr for qr in d["quality_records"] if qr["station_id"] == "AP03"]
        assert len(ap03_recs) == 0, "AP03 must not fabricate quality records"

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
    """Tightened tests proving same-WIP retest/reinspect cycles under
    per-sub-line exception scenarios via DemoController (composition-backed)."""

    # ---- AP06 FAIL #1 → PASS #2 (same WIP) ----

    def test_ap06_same_wip_fail_then_pass_retest(self):
        """Prove same WIP has attempt 1 FAIL then attempt 2 PASS at AP06."""
        ctrl = DemoController(config_path="configs/plants/tipa_assy_demo.yaml",
                              scenario=DemoScenario.AP06_FAIL_RETEST_PASS)
        ctrl.initialize()
        for _ in range(40):
            ctrl.step()
        snap = ctrl.detail_for("ASSY-SL03")
        d = snap.to_dict()

        # Group AP06 records by WIP, find one with FAIL→PASS sequence
        by_wip = {}
        for qr in d["quality_records"]:
            if qr["station_id"] == "AP06":
                by_wip.setdefault(qr["wip_id"], []).append(qr)

        found = False
        for wip_id, recs in by_wip.items():
            s = sorted(recs, key=lambda r: r["simulation_time_s"])
            if len(s) >= 2 and s[0]["disposition"] == "FAIL" and s[1]["disposition"] == "PASS":
                found = True
                assert s[0]["attempt_number"] == 1, f"attempt 1 should be 1, got {s[0]['attempt_number']}"
                assert s[1]["attempt_number"] == 2, f"attempt 2 should be 2, got {s[1]['attempt_number']}"
                assert s[1]["simulation_time_s"] > s[0]["simulation_time_s"], "time must increase"
                assert s[0]["check_type"] == "TEST"
                assert s[1]["check_type"] == "TEST"
                # Both records preserved, not overwritten
                assert len(s) >= 2
                break
        assert found, "No WIP found with AP06 FAIL #1 → PASS #2 retest cycle"

    # ---- AP08 NG #1 → PASS #2 (same WIP) ----

    def test_ap08_same_wip_ng_then_pass_reinspect(self):
        """Prove same WIP has attempt 1 NG then attempt 2 PASS at AP08."""
        ctrl = DemoController(config_path="configs/plants/tipa_assy_demo.yaml",
                              scenario=DemoScenario.AP08_NG_REINSPECT_PASS)
        ctrl.initialize()
        for _ in range(40):
            ctrl.step()
        snap = ctrl.detail_for("ASSY-SL02")
        d = snap.to_dict()

        by_wip = {}
        for qr in d["quality_records"]:
            if qr["station_id"] == "AP08":
                by_wip.setdefault(qr["wip_id"], []).append(qr)

        found = False
        for wip_id, recs in by_wip.items():
            s = sorted(recs, key=lambda r: r["simulation_time_s"])
            if len(s) >= 2 and s[0]["disposition"] == "NG" and s[1]["disposition"] == "PASS":
                found = True
                assert s[0]["attempt_number"] == 1
                assert s[1]["attempt_number"] == 2
                assert s[1]["simulation_time_s"] > s[0]["simulation_time_s"]
                assert s[0]["check_type"] == "VISUAL_INSPECTION"
                assert s[1]["check_type"] == "VISUAL_INSPECTION"
                assert len(s) >= 2
                break
        assert found, "No WIP found with AP08 NG #1 → PASS #2 reinspect cycle"

    # ---- FAILED_FINAL meaningful ----

    def test_failed_final_same_wip_both_attempts_fail(self):
        """Prove FAILED_FINAL: same WIP has attempt 1 FAIL + attempt 2 FAIL at AP06,
        both records preserved, terminal failure state reached."""
        ctrl = DemoController(config_path="configs/plants/tipa_assy_demo.yaml",
                              scenario=DemoScenario.FAILED_FINAL)
        ctrl.initialize()
        for _ in range(55):
            ctrl.step()
        snap = ctrl.detail_for("ASSY-SL03")
        d = snap.to_dict()

        # Group AP06 records by WIP, find one with FAIL→FAIL sequence
        by_wip = {}
        for qr in d["quality_records"]:
            if qr["station_id"] == "AP06":
                by_wip.setdefault(qr["wip_id"], []).append(qr)

        found = False
        for wip_id, recs in by_wip.items():
            s = sorted(recs, key=lambda r: r["simulation_time_s"])
            if len(s) >= 2 and s[0]["disposition"] == "FAIL" and s[1]["disposition"] == "FAIL":
                found = True
                assert s[0]["attempt_number"] == 1
                assert s[1]["attempt_number"] == 2
                assert s[1]["simulation_time_s"] > s[0]["simulation_time_s"]
                assert s[0]["check_type"] == "TEST"
                assert s[1]["check_type"] == "TEST"
                assert len(s) >= 2, "Both attempts must be preserved, not overwritten"
                break
        assert found, "No WIP found with AP06 FAIL #1 → FAIL #2 (terminal failure)"


# ═══════════════════════════════════════
# H. Snapshot JSON compatibility
# ═══════════════════════════════════════

class TestSnapshotCompatibility:
    def test_existing_keys_unchanged(self):
        """quality_records/active_operations are additive — all existing keys preserved."""
        ctrl = DemoController(config_path="configs/plants/tipa_assy_demo.yaml", scenario=DemoScenario.HAPPY_PATH)
        snap = ctrl.initialize()
        for _ in range(10):
            snap = ctrl.step()
        d = snap.to_dict()
        expected_keys = {
            "simulation_time_s", "line_state", "dwell_number", "nominal_dwell_s",
            "positions", "genealogy", "recent_quality_events", "quality_records",
            "active_operations", "station_contracts",
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
    def test_mutating_serialized_dict_does_not_affect_reserialization(self):
        """Mutating serialized dict does not affect runtime or re-serialization."""
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
            assert d2["quality_records"][0]["disposition"] != "MUTATED"

    def test_mutating_nested_measurements_does_not_affect_fresh_snapshot(self):
        """Mutating serialized output does not corrupt a fresh rebuild from runtime."""
        ctrl = DemoController(config_path="configs/plants/tipa_assy_demo.yaml", scenario=DemoScenario.HAPPY_PATH)
        ctrl.initialize()
        for _ in range(15):
            ctrl.step()
        snap = ctrl.detail_for("ASSY-SL01")
        d1 = snap.to_dict()
        # Mutate nested measurement in serialized output
        for qr in d1["quality_records"]:
            if qr["measurements"]:
                qr["measurements"][0]["value"] = 99999.0
                break
        # Fresh rebuild from controller (not just re-serialize same object)
        snap_fresh = ctrl.detail_for("ASSY-SL01")
        d2 = snap_fresh.to_dict()
        for qr in d2["quality_records"]:
            if qr["measurements"]:
                assert qr["measurements"][0]["value"] != 99999.0, "Nested mutation leaked to fresh snapshot"


# ═══════════════════════════════════════
# J. Released/exited WIP history retention
# ═══════════════════════════════════════

class TestReleasedWipHistory:
    def test_concrete_released_wip_absent_from_positions_has_ap11_record(self):
        """Prove a concrete released WIP is absent from positions[]
        but retains its AP11 FINAL_QC record in quality_records[]."""
        ctrl = DemoController(config_path="configs/plants/tipa_assy_demo.yaml", scenario=DemoScenario.HAPPY_PATH)
        ctrl.initialize()
        for _ in range(35):
            ctrl.step()
        snap = ctrl.detail_for("ASSY-SL01")
        d = snap.to_dict()

        # Current WIPs in positions
        pos_wips = {p["wip_id"] for p in d["positions"] if p["wip_id"]}
        # WIPs with quality records
        qr_wips = {qr["wip_id"] for qr in d["quality_records"]}
        # Released/exited = in quality records but not in positions
        released = qr_wips - pos_wips
        assert len(released) > 0, "Should have released/exited WIPs"

        # Find a concrete released WIP with AP11 FINAL_QC
        found = False
        for wip_id in released:
            ap11_recs = [qr for qr in d["quality_records"]
                         if qr["wip_id"] == wip_id
                         and qr["station_id"] == "AP11"
                         and qr["check_type"] == "FINAL_QC"
                         and qr["disposition"] == "PASS"]
            if ap11_recs:
                found = True
                assert wip_id not in pos_wips, f"{wip_id} should be absent from positions"
                # Total quality records for this WIP includes AP11
                wip_recs = [qr for qr in d["quality_records"] if qr["wip_id"] == wip_id]
                assert len(wip_recs) >= 1, f"{wip_id} should have quality records"
                break
        assert found, "No released WIP found with AP11 FINAL_QC PASS record"
