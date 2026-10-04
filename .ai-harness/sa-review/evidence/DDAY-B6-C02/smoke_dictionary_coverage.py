#!/usr/bin/env python3
"""DDAY-B6-C02 — dictionary coverage and timestamp-semantics smoke."""

from __future__ import annotations

import sys
from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "src" / "virtual_factory").is_dir():
            return candidate
    raise RuntimeError("repository root not found")


REPO_ROOT = _find_repo_root(Path(__file__).resolve())
sys.path.insert(0, str(REPO_ROOT / "src"))

from virtual_factory.workspaces.bottled_water import BottledWaterFactory
from virtual_factory.workspaces.plantos_export import (
    COMPLETE_EXPORT_METADATA_FIELDS,
    TIMESTAMP_KIND,
    UnmappedExportError,
    dictionary_summary,
    exported_signal_entries,
    lookup_signal_entry,
    review_set_entries,
    utc_timestamp,
)

WORKSPACE = REPO_ROOT / "configs" / "workspaces" / "bottled-water-dday"
_failures: list[str] = []


def claim(condition: bool, description: str) -> None:
    print(f"  [{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        _failures.append(description)


def main() -> int:
    print("=" * 72)
    print("DDAY-B6-C02 — selected dictionary coverage + timestamp semantics")
    print("=" * 72)

    factory = BottledWaterFactory(WORKSPACE / "line.yaml", WORKSPACE / "factory.yaml")
    factory.start()
    for _ in range(8):
        factory.step(1.0)
    snapshot = factory.snapshot()
    bundle = factory.plantos_export()
    current = {
        (item["asset_id"], item["signal_or_event"]): item["payload"]
        for item in bundle["current_values"]
    }

    for key in (
        ("BW-FP-CAP01", "speed"),
        ("BW-FP-CAP01", "cycle_time"),
        ("BW-FP-CAP01", "cap_torque"),
        ("BW-UT-CMP01", "active_power"),
        ("BW-UT-CMP01", "energy_total"),
        ("BW-WH-FG01", "dispatch_count"),
        ("BW-FP-FIL01", "fill_rate"),
    ):
        claim(key in current, f"exports {key[0]}.{key[1]}")
        if key in current:
            claim(
                current[key]["value"] == snapshot["nodes"][key[0]]["signals"][key[1]]["value"],
                f"{key[0]}.{key[1]} equals factory raw fact",
            )

    closed = False
    try:
        lookup_signal_entry("BW-UT-CMP01", "load")
    except UnmappedExportError:
        closed = True
    claim(closed, "compressor load is UNAVAILABLE / not exported")
    summary = dictionary_summary()
    unavailable = {item["signal_id"] for item in summary["unavailable"]}
    claim(unavailable == {"load", "target_rate"}, f"unavailable set {unavailable}")

    payload = bundle["current_values"][0]["payload"]
    claim(payload["timestamp_kind"] == TIMESTAMP_KIND, "timestamp_kind is simulated_source_utc")
    claim(payload["timestamp"] == utc_timestamp(payload["simulation_time_s"]),
          "timestamp is epoch + simulation_time_s")
    claim("receipt_time" not in payload, "VF does not generate receipt time")
    claim(bundle["timestamp_semantics"]["timestamp"] == TIMESTAMP_KIND,
          "bundle discloses timestamp semantics")
    claim("wall-clock" in bundle["timestamp_semantics"]["timestamp_meaning"].lower()
          or "Not wall-clock" in bundle["timestamp_semantics"]["timestamp_meaning"],
          "semantics say timestamp is not wall-clock receipt time")
    review = review_set_entries()
    claim(len(review) >= 9, "review-set dispositions are machine-readable")
    claim(all(item.get("disposition") in {"EXPORTED", "UNAVAILABLE"} for item in review),
          "every review-set fact has EXPORTED or UNAVAILABLE")
    meta_ok = all(
        all(entry.get(field) for field in COMPLETE_EXPORT_METADATA_FIELDS)
        for entry in exported_signal_entries()
    )
    claim(meta_ok, "every exported dictionary item has complete metadata")

    print()
    if _failures:
        print(f"SMOKE FAILED ({len(_failures)} claim(s))")
        for item in _failures:
            print(f"  - {item}")
        return 1
    print("SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
