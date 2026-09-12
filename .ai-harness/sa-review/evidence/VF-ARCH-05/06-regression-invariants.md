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

## 3. Functional-semantics oracle (C01-1) — semantic, not token-based

Issue #44 froze route semantics including the conceptual labels `SSO2_BUFFER`,
`RSO2_BUFFER`, and `FINISHED`. Repo-first evidence confirms these are NOT
authoritative conveyor-position tokens, but they DO represent evidence-backed
functional semantics that the regression oracle must preserve. A later migration
could preserve `PRE-ASSY → AP01..AP11` and still be a regression if it broke
SSO2/RSO2 feed/buffer behavior or terminal release/output semantics. The oracle
below is therefore **semantic**: each row states a functional requirement, the
exact repo seam that implements it, and whether a direct test exists today.

### 3.1 SSO2 feed / queue / buffering before entry at PRE-ASSY

| Semantic requirement | Repo seam (exact) | Direct test? |
|---|---|---|
| SSO2 semi-finished WIP is produced as an upstream source intended for ASSY PRE-ASSY | `assembly/upstream.py` ("SSO2: creates stator/shaft semi-finished WIP → ASSY PRE-ASSY"); `line_runtime.py::produce_sso2_wip()` | indirect (every line test produces then introduces) |
| An SSO2 WIP does NOT occupy a conveyor position until introduced; entry happens at PRE-ASSY | `line_runtime.py::introduce_to_assy()` → `conveyor.place_carrier(carrier, "PRE-ASSY", wip_id)` + `LINE_ENTRY` emit at PRE-ASSY | `test_assy_line.py::test_trace_contains_all_key_events` (asserts `LINE_ENTRY`); `test_positions_authoritative` |
| Feed/queue buffering of SSO2 WIPs awaiting entry (per-context demo feed) | `assembly/demo_composition.py` `AssyDemoContext.sso2_ids` feed queue | **NO direct test** → **future regression proof obligation**: assert feed-queue drain → introduce ordering, and that produced-but-not-introduced SSO2 WIPs are buffered (not yet on the conveyor) |

### 3.2 RSO2 buffering / availability feeding AP04 JOIN

| Semantic requirement | Repo seam (exact) | Direct test? |
|---|---|---|
| RSO2 semi-finished WIP is produced and buffered for AP04 JOIN | `line_runtime.py::produce_rso2_wip()` (adds to `_rso2_wips`) | `test_assy_line.py` AP04 tests produce RSO2 |
| AP04 JOIN is blocked when no RSO2 WIP is available (both-parents requirement) | `line_runtime.py::_execute_ap04_join` raises `AssyLineError("AP04 JOIN: no RSO2 WIP available")`; pops one RSO2 on join | `test_assy_line.py::test_ap04_requires_both_parents` (no RSO2 → raises); `test_m6_int_01.py::TestAp04Genealogy` |
| RSO2 buffer count is observable | `line_runtime.py::rso2_buffer_size()` returns `len(self._rso2_wips)` | **NO direct count-assertion test found** → **future regression proof obligation**: assert `rso2_buffer_size()` reflects produced-minus-joined RSO2 WIPs |

### 3.3 Terminal FINISHED → lifecycle / output mapping

| Semantic requirement | Repo seam (exact) | Direct test? |
|---|---|---|
| A good WIP terminal = released as finished good | `line_runtime.py::_execute_release_disposition` sets `ws.lifecycle = WipLifecycle.RELEASED` | `test_assy_line.py::TestA08ReleasedLifecycle::test_child_released_at_ap11`; `test_full_happy_path_released` ("RELEASED_FINISHED_GOOD") |
| `FINISHED` is NOT a conveyor position — it is lifecycle/output semantics | `conveyor.py` `ConveyorConfig.positions` end at `AP11`; `wip.py` `WipLifecycle.RELEASED` | `test_assy_line.py::test_positions_authoritative` (12 positions, no FINISHED) |
| MES LINE_OUT projection maps terminal: RELEASED → GOOD; FAILED_FINAL → REJECT | `assy_mes_bridge.py` `_line_out_fact` (disposition `good`) / `_line_out_reject_fact` (disposition `reject`, `reason_code=QualityStatus.FAILED_FINAL.value`) | `test_demo_assy_mes_v1.py::test_ap11_fail_reject_line_out`; `test_assy_mes_bridge_v1.py` (GOOD/REJECT) |

### 3.4 Discrepancy reporting kept (no invented code tokens)

The conceptual labels `SSO2_BUFFER`, `RSO2_BUFFER`, and `FINISHED` are retained
ONLY as conceptual names in the oracle — never invented as code tokens and never
added to the authoritative route. Full discrepancy wording is in §4 below.

## 4. Exact discrepancies reported (not normalized)

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

## 5. Regression proof strategy (semantic oracle, architecture-level, not implemented)

The frozen invariants above + the functional-semantics oracle (§3) are the
acceptance oracle for later migration. A future regression proof must
demonstrate, at minimum:

- route order unchanged (12 positions, PRE-ASSY first);
- SSO2 feed/queue buffering before entry at PRE-ASSY preserved (produced SSO2
  WIPs enter only via introduction at PRE-ASSY; entry emits `LINE_ENTRY`);
- RSO2 buffering/availability before AP04 JOIN preserved (no RSO2 WIP → AP04
  JOIN blocked; RSO2 consumed on join);
- terminal `FINISHED` semantics preserved as lifecycle/output (`RELEASED` for
  good; MES `LINE_OUT` GOOD/REJECT as applicable) — never as a conveyor
  position;
- AP04 both-parents requirement unchanged;
- AP06 retest / AP08 reinspect / AP11 final-QC statuses unchanged;
- `failed_final` terminal + idempotent;
- `LINE_OUT` good/reject derivation unchanged;
- deterministic timing stream and idempotency keys byte-identical for the same
  seed + inputs;
- continuous/compressor tests still pass (no ASSY migration may touch them);
- the §3 rows marked "NO direct test" are covered by the explicit future
  regression proof obligations recorded there (they must be added as tests or
  documented proof in the migration slice that touches the corresponding seam).

The oracle is **semantic**: passing the route-position oracle alone is
insufficient — a migration must also satisfy §3.1–§3.3 functional semantics.

**Decision F is explicit and evidence-backed; discrepancies reported verbatim;
oracle is semantic, not token-based.**
