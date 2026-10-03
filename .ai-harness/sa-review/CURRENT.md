# SA REVIEW INBOX

Task: DDAY-B4 — Full-Factory Basic Simulation + Autonomous Runtime
Status: IMPLEMENTED — PR OPEN — READY FOR SA REVIEW

Authority:
SA Issue hieudovn/virtual-factory#105 (B4 ONLY)
PR: hieudovn/virtual-factory#101 (base main, head sa/dday-track-b-20261003)

Baselines:
SA-issued B4 baseline / branch head at B4 start:
23b6208266751a8c508b0d96fd7a736dffc5676c (match)
harness expected_base_sha (== origin/main):
f5261c8ca18cd4e01779c0274b55270ba028b4e5 (unchanged, not advanced)

What was done:
- The server now owns the production clock. A bounded asyncio runner created in
  the FastAPI lifespan advances the simulation; the B3 skin became observer-only
  and no longer POSTs /advance as the production clock.
- New aggregate whole-factory composition (src/virtual_factory/workspaces/
  bottled_water.py) around the UNCHANGED B2/B3 discrete line runtime: Water
  Treatment (water balance + bounded tank with high/low level hysteresis),
  Bottle Preparation (logical only, no duplicate Blower), Utilities (compressor
  pressure/load, chiller, pump, plant power meter), Warehouse/Dispatch (FG
  receipts - dispatch).
- Conservation/process consistency: treated = raw x recovery, reject = raw -
  treated, tank = initial + treated - draw bounded by the high-level rule,
  product water = filled bottles x 500 mL, draw = product / 0.94, material
  counters tied to real station completions (rejected bottles still consume caps
  and water), plant energy = sum(asset energy) + base load x time, monotonic and
  integrated from power x time, causal utility response to production load,
  FG balance closed and non-negative.
- FactoriX IIoT preparation: one authoritative factory projection
  (GET /bottled-water-demo/factory) whose hierarchy/taxonomy is read from the
  FROZEN B1 topology.yaml (single source of truth, no duplication): source_id,
  name, entity_type (plant|area|asset), parent_source_id, role, equipment_class,
  workspace_id. Every raw fact is attributable (workspace_id, source_id,
  signal_id, value, unit, quality, provenance=SIMULATED_RAW, simulation_time_s).
  No FactoriX canonical IDs invented; BW-FP stays an Area with
  role=production_line; no PlantOS Line entity created.
- Raw-fact boundary kept: no OEE/availability/performance/quality%/energy-per-
  unit/utilization/health-score field; no TIPA/APxx vocabulary.
- Reuse, not fork: line_runtime.py, demo_controller.py, core/, telemetry/,
  protocols/ and scenarios/ are all UNTOUCHED. No second engine, telemetry
  framework, scenario engine, protocol gateway, historian or persistence layer.

Documented interpretation (SA awareness requested):
PAUSE freezes the simulated clock completely (Issue #105 section 2). STOP is a
controlled stop: production stops, the plant stays energized, the clock keeps
running and only explicitly modelled standby/base load accrues energy
(sections 5.3/5.6). FAULT is never emitted (B5 owns abnormal conditions).

Deliberate, disclosed adaptations of earlier artefacts (B4 changes the clock
authority, so deterministic offline harnesses opt out of the autonomous clock):
- tests/test_dday_b3_bottled_water_ui.py: factory_autorun=False at the two app
  constructions; two assertions STRENGTHENED to require no /advance from the
  skin; /bottled-water-demo/factory added to the BW route set.
- .ai-harness/sa-review/evidence/DDAY-B3/smoke_bottled_water_ui.py and
  generate_evidence.py: factory_autorun=False.
No assertion was removed or relaxed.

Tests:
  B4 27/27 | regression subset 164/164 (one pre-existing id()-based flake on the
  first run, green on rerun) | full suite 1716/1716 exit 0
  (1647 baseline, +17 B2, +2 B2-C01, +23 B3, +27 B4)

Smokes:
  SMOKE-BW-FACTORY  PASS (live HTTP: headless autonomy, conservation, controls)
  SMOKE-BW-UI       PASS (B3 target-line skin regression)
  SMOKE-BW          PASS (B2 line runtime regression)

Conservation run (4000 steps, invariants checked every step):
  0 violations, 0 identity errors; tank 0.2405..0.3400 m3 (high 0.34, cap 0.4);
  high-level rule engaged; energy identity exact.

Determinism:
  identical_control_sequences = true, reset_returns_initial_state = true,
  step_size_irrelevant = true (20 x step(20 s) == 400 x step(1 s)).

Pre-existing flake (out of scope per Issue #105 section 13), disclosed:
tests/test_demo_composition.py::TestReset asserts id() disjointness across
reset(); demonstrated deterministically in
.ai-harness/sa-review/evidence/DDAY-B4/flaky_reset_disclosure.py

Evidence:
.ai-harness/sa-review/evidence/DDAY-B4/ (01..05 docs, machine-evidence.json,
factory-state-sample.json, scope-contract-b4-baseline.json, implementation.patch,
smoke_bottled_water_factory.py, JUnit XMLs, flaky-reset-disclosure.txt)
Report:
.ai-harness/sa-review/reports/DDAY-B4.md

Verification commands:
python .ai-harness/sa-review/evidence/DDAY-B4/smoke_bottled_water_factory.py
python .ai-harness/sa-review/evidence/DDAY-B3/smoke_bottled_water_ui.py
python .ai-harness/sa-review/evidence/DDAY-B2/smoke_bottled_water.py
python -m pytest -q
python .ai-harness/scripts/run_task_gate.py --task .ai-harness/tasks/DDAY-B4.json --token <token>

NOT authorized: merge, B5, or any later slice.
