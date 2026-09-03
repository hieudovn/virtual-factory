# VF-ARCH-05 · Evidence 06 — Decision F: Regression invariants (with repo evidence)

## 1. Method

Each invariant is verified against actual repo evidence. Where repo evidence
DIFFERS from the Issue #44 wording, the difference is reported exactly — it is
not normalized or invented (Issue #44: "report exact evidence; do not invent or
normalize it silently").

## 2. Regression invariant table

| # | Invariant | Repo evidence (exact) | Tests asserting |
|---|---|---|---|
| 1 | Route `SSO2 → SSO2_BUFFER → PRE-ASSY → AP01…AP11 → FINISHED` | Authoritative linear route = `conveyor.py` `ConveyorConfig.positions = ("PRE-ASSY","AP01","AP02","AP03","AP04","AP05","AP06","AP07","AP08","AP09","AP10","AP11")` (12 positions). Sources: `upstream.py` SSO2→PRE-ASSY, RSO2→AP04 JOIN. AP04 JOIN consumes RSO2 (`_execute_ap04_join` raises if no RSO2 WIP). FINISHED = `WipLifecycle.RELEASED`, not a conveyor position | `test_assy_line.py::test_positions_authoritative`; `test_assy_demo.py::TestV02Positions` |
| 2 | Producer token exactly `PRE-ASSY` | `conveyor.py` first position `"PRE-ASSY"`; `line_runtime.py` `place_carrier(…, "PRE-ASSY", …)` + `LINE_ENTRY` emit; `station_contracts.py` `"PRE-ASSY": _exec_only(…)` | `test_assy_line.py::test_load_actual_tipa_yaml` (`station_durations["PRE-ASSY"]==30.0`) |
| 3 | Six sub-lines | `sub_line_identity.py` `CANONICAL_TIPA_SUB_LINE_IDS` (exactly 6); `CANONICAL_HYDRAULIC_IDS` (SL01–03), `CANONICAL_THERMAL_IDS` (SL04–06); raises if ≠6 | `test_sub_line_identity.py::test_all_six_canonical_ids_present` |
| 4 | AP04 genealogy | `genealogy.py` `GenealogyRecord(join_station="AP04", relationship_type="assembly_join")`; `line_runtime.py::_execute_ap04_join` emits `AP04_JOIN`; `ap04_required_parent_sources=("SSO2","RSO2")` | `test_assy_line.py::test_ap04_requires_both_parents`; `test_m6_int_01.py::TestAp04Genealogy` |
| 5 | AP06 retest | `quality_records.py` `QualityStatus.RETEST_PENDING="retest_pending"`; `line_runtime.py::_apply_quality_decision` sets retest for `CheckType.TEST`, routing `STAY_AT_STATION` | `test_quality.py::TestQ05::test_retest_second_attempt`; `test_ops03_interaction.py::test_ap06_fail_retest_keeps_wip_at_ap06` |
| 6 | AP08 reinspect | `quality_records.py` `QualityStatus.REINSPECT_PENDING="reinspect_pending"`; `_QUALITY_STATION_MAP["AP08"]=("ap08", CheckType.VISUAL_INSPECTION)` | `test_ops03_interaction.py::test_ap08_ng_reinspect_stays_at_ap08`; `test_ops04_c01.py::test_ng_decision_reinspects` |
| 7 | `failed_final` | `quality_records.py` `QualityStatus.FAILED_FINAL="failed_final"`; `line_runtime.py::_apply_quality_decision` sets it when `attempt >= max_attempts`, emits `QUALITY_FAILED_FINAL`; `_advance_operation` emits `OPERATION_TERMINAL` detail `"FAILED_FINAL — no recovery, not HELD"` | `test_quality.py::test_failed_final_idempotent`; `test_vf_contract_finality_01.py::TestFailedFinalAuthoritative` |
| 8 | `LINE_OUT` GOOD/REJECT | `demo_assy_mes/model.py` `LineOutDisposition.GOOD="good"/REJECT="reject"`; `assy_mes_bridge.py` derivation: RELEASED→good; `FAILED_FINAL`→reject (`reason_code=QualityStatus.FAILED_FINAL.value`) | `test_demo_assy_mes_v1.py::test_ap11_fail_reject_line_out` |
| 9 | Quality/checklist/measurement evidence | `quality_records.py` `CheckType` (CHECKLIST/MEASUREMENT/TEST/VISUAL_INSPECTION/FINAL_QC), `MeasurementValue`, `QualityRecord` (immutable, measurements/checklist_items/observations); `assy_mes_bridge.py` `_measurement_fact`/`_checklist_fact` with `evidence_source="DEMO_SYNTHETIC"` | `test_assy_mes_03_evidence.py::TestAp03Checklist::test_confirmed_emits_exactly_one` |
| 10 | Deterministic timestamps / idempotency | `auto_timing.py` `TimingResolver` (isolated `random.Random`, DETERMINISTIC); `observation_bridge.py` idempotent `(run_id, source_event_id)` delivery; `assy_mes_bridge.py` `DEMO_EPOCH` + `occurred_at_for`, `idempotency_key == message_key` | `test_auto_timing.py::TestFixed::test_fixed_deterministic`; `test_m6_int_01.py::TestIdempotency::test_repeated_poll_no_duplicates` |
| 11 | Accepted continuous/compressor functionality | No `continuous/` package; continuous = `core/simulation_engine.py` + `equipment/{compressor_train,compressor,process_dynamics,boundary}.py` + `operating_states/state_machine.py` + `control/pid_controller.py` + `balance/*` | `test_compressor_train.py`, `test_compressor_states.py`, `test_operating_states.py`, `test_minimal_process_dynamics.py`, `test_minimal_closed_loop.py`, `test_demand_profile.py` |
| 12 | Existing demo behavior preserved unless classified demo-only | `demo_composition.py` (COMMON_DEMO_CLOCK, DEMO feed policy), `demo_controller.py`; standalone `tests/demo_assy.py::run_tipa_demo()` | `test_demo_composition.py`; `test_auto_equiv_01.py` (manual vs auto equivalence) |

## 3. Exact discrepancies reported (not normalized)

1. **Route token mismatch (SSO2_BUFFER / RSO2_BUFFER):** the literals
   `"SSO2_BUFFER"` / `"RSO2_BUFFER"` do **not** exist in `src/` or `tests/`.
   SSO2 buffering = `AssyDemoContext.sso2_ids` feed queue (no `sso2_buffer_size`
   property); only RSO2 has `rso2_buffer_size`. `sso2_buffer` exists as a
   snapshot field but is left at default `0`. The invariant's buffer names are
   conceptual labels, not code tokens.
2. **`FINISHED` is not a conveyor position.** It is `WipLifecycle.RELEASED`
   (finished-good marker); the MES projection also has `LINE_OUT`
   (good/reject).
3. **`tipa.py::build_tipa_topology()` is legacy M3-S03 single-line topology**
   (`sso2-1, sso2-2 → shared-buffer → AP01..AP06 → final-quality →
   finished-sink / rework AP04`). It does **not** encode the accepted 12-position
   route and is superseded by `AssyLineRuntime` + `AssyDemoComposition`.
4. **`mes_adapter.py` contains no determinism/idempotency logic** — it is a plain
   M4-S04 contract adapter. Determinism/idempotency live in `auto_timing.py`,
   `observation_bridge.py`, `assy_mes_bridge.py`, `demo_assy_mes/model.py`.
5. **AP06 retest ≠ legacy AP04 rework:** accepted M6 model is retest-in-place
   (`RETEST_PENDING`, `STAY_AT_STATION`); the legacy `tipa.py` had
   `final-quality → AP04 (REWORK)` — different semantics; must not be confused.

## 4. Regression proof strategy (architecture-level, not implemented)

The frozen invariants above are the acceptance oracle for later migration. A
future regression proof must demonstrate, at minimum:

- route order unchanged (12 positions, PRE-ASSY first);
- AP04 both-parents requirement unchanged;
- AP06 retest / AP08 reinspect / AP11 final-QC statuses unchanged;
- `failed_final` terminal + idempotent;
- `LINE_OUT` good/reject derivation unchanged;
- deterministic timing stream and idempotency keys byte-identical for the same
  seed + inputs;
- continuous/compressor tests still pass (no ASSY migration may touch them).

**Decision F is explicit and evidence-backed; discrepancies reported verbatim.**
