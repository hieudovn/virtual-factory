#!/usr/bin/env python
"""VF-vNEXT-R1-C01 — deterministic hold/freeze-reset evidence generator.

Writes ``hold-reset.json``: canonical TIPA session reset must clear the ASSY
domain hold/freeze state while preserving the same-run-id reset semantics and
returning all six sub-lines to the fresh profile baseline.

Deterministic: no timestamps, sorted keys, stable ordering.
Run:  python .ai-harness/sa-review/evidence/VF-vNEXT-R1-C01/generate_evidence.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
TIPA_CONFIG = str(ROOT / "configs" / "plants" / "tipa_assy_demo.yaml")

from virtual_factory.federation import SUB_LINE_IDS  # noqa: E402
from virtual_factory.runcontrol import build_tipa_session  # noqa: E402

HELD = "ASSY-SL03"


def line_state(runtime) -> dict:
    return {
        "simulation_time_s": runtime.simulation_time_s,
        "dwell_number": runtime.conveyor.dwell_number,
        "conveyor_state": runtime.conveyor.state.value,
        "wip_count": runtime.wip_count,
        "motor_count": runtime.motor_count,
        "rso2_buffer_size": runtime.rso2_buffer_size,
        "genealogy_records": len(runtime.genealogy.all_records()),
        "occupied_positions": [
            [pos, runtime.conveyor.wip_at(pos)]
            for pos in runtime.conveyor.positions
            if runtime.conveyor.wip_at(pos)
        ],
    }


def states(federation) -> dict:
    return {sid: line_state(federation.runtime(sid)) for sid in SUB_LINE_IDS}


session = build_tipa_session(TIPA_CONFIG, "tipa-default")
step_1 = session.advance()
federation = session.record.bridge.federation
bridge = session.record.bridge

run_id_before = session.run_id
profile_id_before = session.profile_id
runtime_object_ids_before = {sid: id(federation.runtime(sid)) for sid in SUB_LINE_IDS}
baseline_after_step_1 = states(federation)

# advance -> hold ONE line -> advance twice
bridge.hold_sub_line(HELD)
held_ids_before_reset = list(bridge.held_sub_line_ids)
frozen_after_step_1 = line_state(federation.runtime(HELD))
step_2 = session.advance()
step_3 = session.advance()
frozen_after_step_3 = line_state(federation.runtime(HELD))
others_after_step_3 = {
    sid: line_state(federation.runtime(sid)) for sid in SUB_LINE_IDS if sid != HELD
}

# RuntimeSession.reset()
session.reset()
held_ids_after_reset = list(bridge.held_sub_line_ids)
run_id_after_reset = session.run_id
runtime_object_ids_after = {sid: id(federation.runtime(sid)) for sid in SUB_LINE_IDS}
baseline_after_reset = states(federation)

# advance again: all six participate and progress
step_after_reset = session.advance()
after_reset_step_lines = states(federation)
for _ in range(4):
    session.advance()
after_reset_five_steps = states(federation)

payload = {
    "session_scenario_id": "tipa-default",
    "profile_id": profile_id_before,
    "sequence": [
        "advance",
        f"hold {HELD}",
        "advance",
        "advance",
        "RuntimeSession.reset()",
        "advance",
        "advance x4",
    ],
    "held_line": HELD,
    "before_reset": {
        "held_sub_line_ids": held_ids_before_reset,
        "held_line_after_step_1": frozen_after_step_1,
        "held_line_after_step_3": frozen_after_step_3,
        "held_line_was_frozen": frozen_after_step_1 == frozen_after_step_3,
        "others_after_step_3": others_after_step_3,
        "step_2_participants": list(step_2.participants),
        "step_3_participants": list(step_3.participants),
        "step_1_participants": list(step_1.participants),
    },
    "reset": {
        "held_sub_line_ids_after_reset": held_ids_after_reset,
        "domain_hold_state_cleared": held_ids_after_reset == [],
        "run_id_before": run_id_before,
        "run_id_after": run_id_after_reset,
        "same_run_identity_preserved": run_id_before == run_id_after_reset,
        "runtime_objects_reused": runtime_object_ids_before == runtime_object_ids_after,
        "profile_id_after": session.profile_id,
        "six_lines_fresh_profile_baseline": baseline_after_reset,
        "baseline_after_step_1_was_reached_before_reset": baseline_after_step_1,
    },
    "after_reset_advance": {
        "status": step_after_reset.status,
        "target_time_s": step_after_reset.target_time_s,
        "participants": list(step_after_reset.participants),
        "participant_count": len(step_after_reset.participants),
        "all_six_participated": len(step_after_reset.participants) == len(SUB_LINE_IDS),
        "lines_after_first_advance": after_reset_step_lines,
        "lines_after_five_advances": after_reset_five_steps,
        "all_six_progressed_together": len(
            {
                json.dumps(after_reset_five_steps[sid], sort_keys=True)
                for sid in SUB_LINE_IDS
            }
        )
        == 1,
    },
    "note": (
        "AssyExecutionBridge.reset(...) clears the held sub-line ids of the "
        "scopes it resets (capability-scoped), so a canonical session reset "
        "returns every sub-line to the fresh profile baseline and the next "
        "coordination window includes all six again. The frozen G22 same-run-id "
        "reset semantics are unchanged (same run identity, same runtime objects, "
        "time back to 0, profile-consistent state, no lifecycle change)."
    ),
}

(OUT / "hold-reset.json").write_text(
    json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
    encoding="utf-8",
)
print("wrote hold-reset.json")
