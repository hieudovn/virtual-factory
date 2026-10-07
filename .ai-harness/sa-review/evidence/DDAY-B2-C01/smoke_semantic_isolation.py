#!/usr/bin/env python3
"""DDAY-B2-C01-A — semantic isolation smoke check.

Task: DDAY-B2-C01 (SA Issue #103 / parent Issue #102 / PR #101).
Contract: .ai-harness/tasks/DDAY-B2-C01.json

Proves, against the real reused discrete runtime (no mocks), that Bottled Water
outward runtime facts carry no legacy-domain lifecycle semantics at:

  entry          -> in_line
  in progress    -> in_line (station not yet complete)
  station done   -> completed_station
  route done     -> released
  rejected       -> rejected

and that the legacy indexed-line profile keeps its frozen ``in_assy`` semantics.

Exit code 0 = every claim proven. Any failed claim exits non-zero.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "src" / "virtual_factory").is_dir():
            return candidate
    raise RuntimeError("repository root not found")


REPO_ROOT = _find_repo_root(Path(__file__).resolve())
sys.path.insert(0, str(REPO_ROOT / "src"))

from virtual_factory.assembly.line_runtime import (  # noqa: E402
    AssyLineRuntime,
    WipLifecycle,
    load_assy_config_from_yaml,
)
from virtual_factory.assembly.station_contracts import CompletionMode  # noqa: E402

CONFIG_PATH = (
    REPO_ROOT / "configs" / "workspaces" / "bottled-water-dday" / "line.yaml"
)
LEGACY_CONFIG_PATH = REPO_ROOT / "configs" / "plants" / "tipa_assy_demo.yaml"
INSPECTION = "BW-FP-INS01"

FORBIDDEN = (
    re.compile(r"assy", re.IGNORECASE),
    re.compile(r"tipa", re.IGNORECASE),
    re.compile(r"sso2", re.IGNORECASE),
    re.compile(r"rso2", re.IGNORECASE),
    re.compile(r"ap05_jam", re.IGNORECASE),
    re.compile(r"\bap\d{2}\b", re.IGNORECASE),
)

_failures: list[str] = []


def claim(condition: bool, description: str) -> None:
    print(f"  [{'PASS' if condition else 'FAIL'}] {description}")
    if not condition:
        _failures.append(description)


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from strings(item)
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            yield from strings(item)


def leaks(values) -> list[str]:
    hits = []
    for text in values:
        for pattern in FORBIDDEN:
            match = pattern.search(text)
            if match:
                hits.append(f"{match.group(0)!r} in {text!r}")
    return hits


def status_at(line: AssyLineRuntime, position: str) -> str:
    for entry in line.line_facts()["positions"]:
        if entry["position_id"] == position:
            return entry["manufacturing_status"]
    return ""


def config(**_):
    return load_assy_config_from_yaml(str(CONFIG_PATH))


def main() -> int:
    print("=" * 72)
    print("DDAY-B2-C01-A — Bottled Water semantic isolation smoke")
    print(f"config: {CONFIG_PATH}")
    print("=" * 72)

    route = list(load_assy_config_from_yaml(str(CONFIG_PATH)).conveyor.positions)

    # ── entry ───────────────────────────────────────────────────────────────
    print("\n[1] entry state")
    entry = AssyLineRuntime(config=config())
    entry.start()
    unit = entry.produce_unit()
    entry.introduce_unit(unit, "CAR-0001")
    claim(status_at(entry, route[0]) == "in_line",
          "entry manufacturing_status is 'in_line'")
    claim(entry.get_wip(unit).lifecycle is WipLifecycle.IN_LINE,
          "entry lifecycle is IN_LINE")
    claim(not leaks(strings(entry.line_facts())),
          "entry outward facts carry no legacy-domain token")
    claim(not leaks(f"{e.event_type} {e.position} {e.wip_id} {e.detail}"
                    for e in entry.trace),
          "entry trace carries no legacy-domain token")

    # ── in progress ─────────────────────────────────────────────────────────
    print("\n[2] in-progress state (station not yet complete)")
    progress = AssyLineRuntime(config=config())
    progress.global_run_mode = CompletionMode.MANUAL
    progress.start()
    progress.advance_cycle()
    claim(progress.units_on_line() == 1, "one unit is on the line")
    claim(status_at(progress, route[0]) == "in_line",
          "in-progress manufacturing_status is 'in_line'")
    claim(not leaks(strings(progress.line_facts())),
          "in-progress outward facts carry no legacy-domain token")

    # ── station completion ──────────────────────────────────────────────────
    print("\n[3] station completion")
    done = AssyLineRuntime(config=config())
    done.start()
    done.advance_cycle()
    claim(status_at(done, route[1]) == "completed_station",
          "completed station publishes 'completed_station'")

    # ── route completion ────────────────────────────────────────────────────
    print("\n[4] route completion")
    for _ in range(7):
        done.advance_cycle()
    claim(done.get_wip("BTL-000001").lifecycle is WipLifecycle.RELEASED,
          "route-complete unit is RELEASED")
    claim(done.good_count == 1, "route-complete unit counted good")

    # ── reject ──────────────────────────────────────────────────────────────
    print("\n[5] reject")
    reject_cfg = config()
    reject_cfg.quality_stations[INSPECTION].quality.scenario = "ALWAYS_FAIL"
    rejected = AssyLineRuntime(config=reject_cfg)
    rejected.start()
    for _ in range(12):
        rejected.advance_cycle()
    claim(rejected.reject_count == 8, "8 units rejected")
    claim(rejected.get_wip("BTL-000001").lifecycle is WipLifecycle.REJECTED,
          "rejected unit is REJECTED")
    claim(not leaks(strings(rejected.line_facts())),
          "rejected outward facts carry no legacy-domain token")
    claim(not leaks(f"{e.event_type} {e.position} {e.wip_id} {e.detail}"
                    for e in rejected.trace),
          "reject trace carries no legacy-domain token")

    # ── global sweep over every generic surface ─────────────────────────────
    print("\n[6] case-insensitive sweep of all generic outward surfaces")
    for label, line in (("entry", entry), ("progress", progress),
                        ("completion", done), ("reject", rejected)):
        surface = list(strings(line.line_facts()))
        surface += [f"{e.event_type} {e.position} {e.wip_id} {e.detail}"
                    for e in line.trace]
        surface += [f"{sid} {c.to_dict()}"
                    for sid, c in line.station_contracts.items()]
        surface += list(line.wip_ids)
        for position in route:
            surface.append(status_at(line, position))
        hits = leaks(surface)
        claim(not hits, f"{label}: no legacy-domain token ({len(surface)} strings)")
        if hits:
            for hit in hits[:5]:
                print(f"        leak: {hit}")

    # ── legacy profile preserved ────────────────────────────────────────────
    print("\n[7] legacy indexed-line profile preserved")
    legacy = AssyLineRuntime(
        config=load_assy_config_from_yaml(str(LEGACY_CONFIG_PATH)))
    legacy.start()
    legacy_wip = legacy.produce_sso2_wip()
    legacy.introduce_to_assy(legacy_wip, "PAL-001")
    claim(legacy.get_wip(legacy_wip).lifecycle is WipLifecycle.IN_ASSY,
          "legacy introduce_to_assy still yields IN_ASSY")
    claim(WipLifecycle.IN_ASSY.value == "in_assy",
          "legacy IN_ASSY value is unchanged")
    claim(WipLifecycle.IN_LINE is not WipLifecycle.IN_ASSY,
          "IN_LINE is a distinct additional value, not a rename")

    print("\n" + "=" * 72)
    if _failures:
        print(f"SMOKE FAILED — {len(_failures)} claim(s) failed:")
        for failure in _failures:
            print(f"  - {failure}")
        print("=" * 72)
        return 1
    print("SMOKE PASSED — semantic isolation proven")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
