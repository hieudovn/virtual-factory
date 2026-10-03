"""C01-A pre-fix reproduction probe (run before any correction is applied)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(r"D:\Project\Github\virtual-factory")
sys.path.insert(0, str(REPO / "src"))

from virtual_factory.assembly.line_runtime import (  # noqa: E402
    AssyLineRuntime,
    load_assy_config_from_yaml,
)

CFG = REPO / "configs" / "workspaces" / "bottled-water-dday" / "line.yaml"

print("=== A. entry state via public API (produce_unit + introduce_unit) ===")
line = AssyLineRuntime(config=load_assy_config_from_yaml(str(CFG)))
line.start()
unit = line.produce_unit()
line.introduce_unit(unit, "CAR-0001")
facts = line.line_facts()
entry = facts["positions"][0]
print("position:", entry["position_id"])
print("unit_id:", entry["unit_id"])
print("manufacturing_status:", repr(entry["manufacturing_status"]))
print("lifecycle enum value:", line.get_wip(unit).lifecycle.value)
print("leaks 'assy' (case-insensitive):",
      "assy" in entry["manufacturing_status"].lower())

print()
print("=== B. in-progress state when a station overruns the dwell ===")
cfg2 = load_assy_config_from_yaml(str(CFG))
cfg2.conveyor.nominal_line_dwell_time_s = 5.0   # shorter than every station
line2 = AssyLineRuntime(config=cfg2)
line2.start()
line2.advance_cycle()
statuses = {p["position_id"]: p["manufacturing_status"]
            for p in line2.line_facts()["positions"] if p["is_occupied"]}
print("occupancy statuses:", json.dumps(statuses))
leaked = {k: v for k, v in statuses.items() if v and "assy" in v.lower()}
print("leaked statuses:", json.dumps(leaked))

print()
print("=== C. full case-insensitive scan of the outward surfaces ===")
import re
pat = re.compile(r"assy|tipa|sso2|rso2|ap05_jam|\bap\d{2}\b", re.IGNORECASE)


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield str(k)
            yield from strings(v)
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            yield from strings(item)


hits = [s for s in strings(facts) if pat.search(s)]
print("entry-facts hits:", json.dumps(hits))
hits2 = [s for s in strings(line2.line_facts()) if pat.search(s)]
print("in-progress-facts hits:", json.dumps(hits2))
