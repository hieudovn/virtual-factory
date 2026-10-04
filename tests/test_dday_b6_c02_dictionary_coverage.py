"""DDAY-B6-C02 — selected dictionary coverage and timestamp semantics."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from virtual_factory.workspaces.bottled_water import BottledWaterFactory
from virtual_factory.workspaces.plantos_export import (
    TIMESTAMP_KIND,
    TIMESTAMP_SEMANTICS,
    UnmappedExportError,
    dictionary_summary,
    load_export_dictionary,
    lookup_signal_entry,
    map_snapshot,
    selected_signal_keys,
    unavailable_signal_entries,
    utc_timestamp,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = REPO_ROOT / "configs" / "workspaces" / "bottled-water-dday"
LINE_YAML = WORKSPACE / "line.yaml"
FACTORY_YAML = WORKSPACE / "factory.yaml"
FROZEN_C01_HASHES = {
    "src/virtual_factory/workspaces/capper_degradation.py":
        "c5b2883a9a5ca50878a9cc7bab850ad0a296df19e73c0a6fc62c56a499e0891b",
    "src/virtual_factory/workspaces/compressor_pressure.py":
        "f35a639aced026e497edb53174034b207b86a6d0fa12db63fe7c80f18ca1ac08",
    "src/virtual_factory/protocols/mqtt_gateway.py":
        "f540ef429dbcedfef4baeddbe2f5c41c152d547f057a4a3d93762c6406414872",
    "src/virtual_factory/ui/static/bottled_water_overview.html":
        "46ab475e5594014f0e2bd4384b0bb46e0623c6a8f2f4a453565346d1e961b8ae",
    "src/virtual_factory/ui/static/bottled_water_overview.js":
        "aba11b2b9c434da2c5aaec794904bd7e4278c9b2030188fccc53fe2cba093425",
    "src/virtual_factory/ui/static/bottled_water_overview.css":
        "8d4424b81772e591b8c5ce9ccb81fd5d03c4a9dd07517b942e877f94f4b21dc5",
}


def _factory() -> BottledWaterFactory:
    return BottledWaterFactory(LINE_YAML, FACTORY_YAML)


def _run(factory: BottledWaterFactory, steps: int = 8) -> dict:
    factory.start()
    for _ in range(steps):
        factory.step(1.0)
    return factory.snapshot()


def _current(factory: BottledWaterFactory) -> dict:
    return {
        (item["asset_id"], item["signal_or_event"]): item["payload"]
        for item in factory.plantos_export()["current_values"]
    }


def test_c02_01_capper_speed_cycle_torque_exported():
    factory = _factory()
    snapshot = _run(factory)
    current = _current(factory)
    for signal_id in ("speed", "cycle_time", "cap_torque"):
        payload = current[("BW-FP-CAP01", signal_id)]
        raw = snapshot["nodes"]["BW-FP-CAP01"]["signals"][signal_id]
        assert payload["value"] == raw["value"]
        assert payload["unit"] == raw["unit"]
        assert payload["source_id"] == "BW-FP-CAP01"


def test_c02_02_compressor_power_and_energy_exported():
    factory = _factory()
    snapshot = _run(factory)
    current = _current(factory)
    for signal_id in ("active_power", "energy_total"):
        payload = current[("BW-UT-CMP01", signal_id)]
        raw = snapshot["nodes"]["BW-UT-CMP01"]["signals"][signal_id]
        assert payload["value"] == raw["value"]
        assert payload["unit"] == raw["unit"]


def test_c02_03_fg_dispatch_count_exported():
    factory = _factory()
    snapshot = _run(factory)
    current = _current(factory)
    payload = current[("BW-WH-FG01", "dispatch_count")]
    raw = snapshot["nodes"]["BW-WH-FG01"]["signals"]["dispatch_count"]
    assert payload["value"] == raw["value"]


def test_c02_04_production_rate_and_cycle_facts_exported():
    factory = _factory()
    snapshot = _run(factory)
    current = _current(factory)
    fill = current[("BW-FP-FIL01", "fill_rate")]
    assert fill["value"] == snapshot["nodes"]["BW-FP-FIL01"]["signals"]["fill_rate"]["value"]
    assert current[("BW-FP-CAP01", "speed")]["semantic_role"] == "production_rate"
    assert current[("BW-FP-CAP01", "cycle_time")]["semantic_role"] == "production_cycle"
    keys = set(selected_signal_keys())
    assert ("BW-FP-FIL01", "fill_rate") in keys
    assert ("BW-FP-CAP01", "speed") in keys
    assert ("BW-FP-CAP01", "cycle_time") in keys


def test_c02_05_unavailable_items_are_declared_and_not_fabricated():
    unavailable = {
        (entry["source_id"], entry["signal_id"]): entry
        for entry in unavailable_signal_entries()
    }
    assert ("BW-UT-CMP01", "load") in unavailable
    assert ("BW-FP", "target_rate") in unavailable
    for entry in unavailable.values():
        assert entry["export_status"] == "UNAVAILABLE"
        assert entry["not_exported"] is True
        assert entry.get("reason")
    factory = _factory()
    snapshot = _run(factory)
    exported = {
        (item.asset_id, item.signal_or_event)
        for item in map_snapshot(snapshot)
        if item.kind == "signal"
    }
    assert ("BW-UT-CMP01", "load") not in exported
    assert ("BW-FP", "target_rate") not in snapshot["nodes"]["BW-FP"]["signals"]
    assert "load" not in snapshot["nodes"]["BW-UT-CMP01"]["signals"]
    with pytest.raises(UnmappedExportError):
        lookup_signal_entry("BW-UT-CMP01", "load")
    with pytest.raises(UnmappedExportError):
        lookup_signal_entry("BW-FP", "target_rate")
    summary = dictionary_summary()
    reasons = {item["signal_id"]: item["reason"] for item in summary["unavailable"]}
    assert "active_power" in reasons["load"]
    assert "CONFIGURED_TARGET" in reasons["target_rate"]


def test_c02_06_timestamp_is_simulated_source_utc_not_receipt_time():
    factory = _factory()
    _run(factory)
    bundle = factory.plantos_export()
    semantics = bundle["timestamp_semantics"]
    assert semantics["timestamp"] == TIMESTAMP_KIND == "simulated_source_utc"
    assert semantics["simulation_time_s"] == "simulation_elapsed_seconds"
    assert "not_generated_by_vf" in semantics["receipt_time"]
    assert "Not wall-clock receipt time" in TIMESTAMP_SEMANTICS["timestamp_meaning"]
    payload = bundle["current_values"][0]["payload"]
    assert payload["timestamp_kind"] == TIMESTAMP_KIND
    assert payload["timestamp"] == utc_timestamp(payload["simulation_time_s"])
    assert "receipt_time" not in payload
    assert "wall_clock" not in payload
    dictionary = load_export_dictionary()
    assert dictionary["timestamp_semantics"]["timestamp"] == TIMESTAMP_KIND


def test_c02_07_frozen_overview_scenarios_and_mqtt_unchanged():
    for rel, expected in FROZEN_C01_HASHES.items():
        digest = hashlib.sha256((REPO_ROOT / rel).read_bytes()).hexdigest()
        assert digest == expected, f"{rel} changed vs C01-closed content"
