# VF-vNEXT-G3 · Evidence 06 — Tests + regression results

## 1. New G3 tests

Command: `python -m pytest tests/test_event_fact.py tests/test_event_store.py
tests/test_alarm_event_facts.py tests/test_observation_alignment.py -q`

Result: **34 passed** (0 failures).

Covers Issue #48 "Required tests / proofs":
- Event fact immutable + deterministic to serialize;
- Alarm fact is an Event specialization/category, not a separate truth model;
- Alarm condition/state remains mutable projection and does not mutate facts;
- Event store accepts typed immutable facts and preserves append order;
- No arbitrary dict mutation can retroactively change stored facts;
- Existing AlarmManager threshold/output SignalValue behavior compatible;
- AlarmManager produces alarm Event facts for activation/clear transitions
  (smallest correct contract);
- Observation legacy behavior compatible;
- New observation context seam does not fabricate G1/G2 identity;
- Runtime state remains authoritative mutable truth (events/observations are
  downstream facts only);
- No PIM canonical identity or evidence maturity fabricated;
- No G4+ implementation present (EventStore exposes no mutation/deletion).

## 2. Regression groups (Issue #48)

| Group | Files | Result |
|---|---|---|
| Existing observation package | `test_m5_s01..s05` | **244 passed** |
| telemetry/alarm/event | `test_alarm_manager`, `test_telemetry_frame`, `test_output_policy`, `test_telemetry_export`, `test_signal_value`, `test_ring_buffer`, `test_mqtt_gateway`, `test_sparkplug_gateway` | **27 passed** |
| G2 provenance + G3 new | `test_provenance_*`, `test_run_context_adapter`, `test_telemetry_provenance_threading` + 4 new G3 files | **70 passed** |
| G1 workspace | `test_workspace_foundation/validation/config` | **32 passed** |
| ASSY regression oracle | ARCH-05 incl. C01 set | **354 passed** |
| Continuous/compressor baseline | ARCH-06 set | **61 passed** |
| Full repository suite | `tests` | **1749 passed** (0 failures, deterministic re-run) |

## 3. Pre-existing flake (documented, unrelated to G3)

First full-suite run surfaced `test_demo_composition.py::TestReset::
test_reset_creates_fresh_configs` (1 failed / 1748 passed). This is the
documented pre-existing ASSY flake: it asserts disjoint Python `id()`s across a
reset; under GC the allocator can reuse addresses, so the `id()` sets overlap
intermittently. It passes in isolation (49/49) and when its file runs alone; G3
did not modify `assembly/`/`demo_composition`. It is recorded honestly as a
pre-existing baseline anomaly (per Issue #48: document flakes separately; do not
modify forbidden domain code to hide them). Deterministic re-run: **1749 passed,
0 failures**.

## 4. Lint / type / compile / harness

- No configured ruff/mypy/black (unchanged).
- Compile check: `python -m compileall -q` on the 4 changed production modules →
  exit 0.
- Task-contract preflight: baseline matches (`origin/main` =
  `f5261c8ca18cd4e01779c0274b55270ba028b4e5`); clean after commit (evidence 07).
- Changed-file validation against the G3 allowlist: PASS (13 files).
